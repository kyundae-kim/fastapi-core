from __future__ import annotations

import os
from collections.abc import Collection, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from fastapi_core.config import load_app_config
from fastapi_core.docmesh_settings import load_docmesh_settings
from fastapi_core.function_logging import log_function_boundary
from fastapi_core.modules import DomainModule
from fastapi_core.resources import ManagedResource, ResourceKey, ResourceRegistry
from fastapi_core.runtime import create_empty_runtime
from fastapi_core.transport import TransportPolicy

T = TypeVar("T")
_MISSING = object()


@dataclass(frozen=True, slots=True)
class ApplicationContractProfile:
    """Declarative composition of health, auth, module, and OpenAPI checks."""

    module_names: Collection[str] = ()
    expected_paths: Mapping[str, Collection[str]] = field(default_factory=dict)
    expected_security_schemes: Collection[str] = ()
    auth_router_included: bool = False
    expected_responses: Mapping[tuple[str, str], Collection[int]] = field(
        default_factory=dict
    )
    validation_status: int | None = None
    include_synthetic_422: bool | None = None
    expected_resource_names: Mapping[str, Collection[str]] = field(default_factory=dict)
    expected_readiness_names: Mapping[str, Collection[str]] = field(default_factory=dict)
    expected_error_mapper_types: Mapping[str, Collection[type[Exception]]] = field(
        default_factory=dict
    )
    expected_transport_policies: Mapping[str, TransportPolicy] = field(default_factory=dict)
    expected_security_dependency_counts: Mapping[str, int] = field(default_factory=dict)
    expected_common_error_statuses: Mapping[str, Collection[int]] = field(
        default_factory=dict
    )


@dataclass
class ResourceLifecycleProbe(Generic[T]):
    """Build a managed resource that records create, check, and close events."""

    value: T
    health_result: object = True
    events: list[str] = field(default_factory=list)

    @log_function_boundary()
    def managed_resource(
        self,
        name: str,
        *,
        required: bool = True,
        readiness_timeout_seconds: float | None = None,
    ) -> ManagedResource[T]:
        @log_function_boundary()
        async def factory(_app: Any) -> T:
            self.events.append(f"create:{name}")
            return self.value

        @log_function_boundary()
        async def healthcheck(value: T) -> object:
            if value is not self.value:
                raise AssertionError(
                    "managed resource probe received an unexpected value"
                )
            self.events.append(f"check:{name}")
            return self.health_result

        @log_function_boundary()
        async def close(value: T) -> None:
            if value is not self.value:
                raise AssertionError(
                    "managed resource probe received an unexpected value"
                )
            self.events.append(f"close:{name}")

        return ManagedResource(
            name=name,
            factory=factory,
            healthcheck=healthcheck,
            close=close,
            required=required,
            readiness_timeout_seconds=readiness_timeout_seconds,
        )


@log_function_boundary()
def assert_health_contract(client: Any) -> None:
    """Assert the built-in liveness and readiness success contract."""
    responses = client.get("/health/liveness"), client.get("/health/readiness")
    for response in responses:
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


@log_function_boundary()
def assert_auth_router_contract(client: Any, *, included: bool) -> None:
    """Assert whether the built-in authentication routes are installed."""
    responses = client.get("/user"), client.post("/token")
    for response in responses:
        assert (response.status_code != 404) == included


@contextmanager
@log_function_boundary()
def test_environment(overrides: Mapping[str, str | None]) -> Iterator[None]:
    """Temporarily override process environment and isolate settings caches."""
    previous = {name: os.environ.get(name, _MISSING) for name in overrides}
    try:
        for name, value in overrides.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        load_app_config.cache_clear()
        load_docmesh_settings.cache_clear()
        yield
    finally:
        for name, value in previous.items():
            if value is _MISSING:
                os.environ.pop(name, None)
            else:
                os.environ[name] = str(value)
        load_app_config.cache_clear()
        load_docmesh_settings.cache_clear()


test_environment.__test__ = False


@log_function_boundary()
def _resource_names(registry: ResourceRegistry) -> set[str]:
    return {
        resource.name.name
        if isinstance(resource.name, ResourceKey)
        else resource.name
        for resource in registry.resources
    }


@log_function_boundary()
def assert_module_contract(
    app: FastAPI,
    module: DomainModule,
    *,
    expected_transport_policy: TransportPolicy | None = None,
    expected_resource_names: Collection[str] = (),
    expected_readiness_names: Collection[str] = (),
    expected_error_mapper_types: Collection[type[Exception]] = (),
    expected_security_dependency_count: int | None = None,
    expected_common_error_statuses: Collection[int] = (),
) -> None:
    """Assert that a declared domain module is installed on an application."""
    assert module in app.state.domain_modules, f"module '{module.name}' is not installed"
    openapi_paths = app.openapi().get("paths", {})
    for router in module.routers:
        for route in router.routes:
            if not isinstance(route, APIRoute):
                continue
            for method in route.methods or ():
                assert method.lower() in openapi_paths.get(route.path, {}), (
                    f"module route '{method} {route.path}' is not installed"
                )

    installed_resources = _resource_names(app.state.resource_registry)
    for resource in module.resources:
        name = resource.name.name if isinstance(resource.name, ResourceKey) else resource.name
        assert name in installed_resources, f"module resource '{name}' is not installed"
    for spec in module.readiness_checks:
        assert spec.name in app.state.readiness_registry.specs, (
            f"module readiness check '{spec.name}' is not installed"
        )
    for spec in module.error_mappers:
        assert spec.exception_type in app.state.error_mapper_types, (
            f"module error mapper '{spec.exception_type.__name__}' is not installed"
        )
    if expected_transport_policy is not None:
        assert module.transport_policy == expected_transport_policy
    actual_resource_names = {
        resource.name.name if isinstance(resource.name, ResourceKey) else resource.name
        for resource in module.resources
    }
    assert set(expected_resource_names) <= actual_resource_names
    actual_readiness_names = {spec.name for spec in module.readiness_checks}
    assert set(expected_readiness_names) <= actual_readiness_names
    actual_mapper_types = {spec.exception_type for spec in module.error_mappers}
    assert set(expected_error_mapper_types) <= actual_mapper_types
    if expected_security_dependency_count is not None:
        policy_dependencies = (
            len(module.transport_policy.dependencies)
            if module.transport_policy is not None
            else 0
        )
        assert len(module.dependencies) + policy_dependencies == expected_security_dependency_count
    if expected_common_error_statuses:
        expected_statuses = set(expected_common_error_statuses)
        for router in module.routers:
            for route in router.routes:
                if not isinstance(route, APIRoute):
                    continue
                for method in route.methods or ():
                    responses = app.openapi()["paths"][route.path][method.lower()]["responses"]
                    assert expected_statuses <= {int(status) for status in responses}


@log_function_boundary()
def assert_openapi_contract(
    app: FastAPI,
    *,
    expected_paths: Mapping[str, Collection[str]],
    expected_security_schemes: Collection[str] = (),
    expected_responses: Mapping[tuple[str, str], Collection[int]] | None = None,
    validation_status: int | None = None,
    include_synthetic_422: bool | None = None,
) -> None:
    """Assert stable semantic properties of the generated OpenAPI schema."""
    schema = app.openapi()
    paths = schema.get("paths", {})
    operation_ids: list[str] = []
    for path, methods in expected_paths.items():
        assert path in paths, f"OpenAPI path '{path}' is missing"
        for method in methods:
            normalized = method.lower()
            assert normalized in paths[path], (
                f"OpenAPI operation '{method.upper()} {path}' is missing"
            )
    for (path, method), statuses in (expected_responses or {}).items():
        operation = paths[path][method.lower()]
        response_codes = {int(code) for code in operation.get("responses", {})}
        assert set(statuses) <= response_codes, (
            f"OpenAPI operation '{method.upper()} {path}' is missing expected responses"
        )
    if validation_status is not None:
        for path, methods in expected_paths.items():
            for method in methods:
                operation = paths[path][method.lower()]
                assert str(validation_status) in operation.get("responses", {})
                if include_synthetic_422 is False:
                    assert "422" not in operation.get("responses", {})
    for path_item in paths.values():
        for method, operation in path_item.items():
            if method.lower() not in {
                "get",
                "put",
                "post",
                "delete",
                "options",
                "head",
                "patch",
                "trace",
            }:
                continue
            operation_id = operation.get("operationId")
            if operation_id is not None:
                operation_ids.append(operation_id)
    assert len(operation_ids) == len(set(operation_ids)), (
        "OpenAPI operation IDs must be unique"
    )

    security_schemes = schema.get("components", {}).get("securitySchemes", {})
    for name in expected_security_schemes:
        assert name in security_schemes, f"OpenAPI security scheme '{name}' is missing"

    component_schemas = schema.get("components", {}).get("schemas", {})

    @log_function_boundary()
    def validate_references(value: Any) -> None:
        if isinstance(value, dict):
            reference = value.get("$ref")
            if isinstance(reference, str) and reference.startswith("#/components/schemas/"):
                name = reference.rsplit("/", 1)[-1]
                assert name in component_schemas, (
                    f"OpenAPI component schema '{name}' is missing"
                )
            for child in value.values():
                validate_references(child)
        elif isinstance(value, list):
            for child in value:
                validate_references(child)

    validate_references(schema)


@log_function_boundary()
def assert_application_contract(
    app: FastAPI,
    profile: ApplicationContractProfile,
) -> None:
    """Run the standard application contract checks from one profile."""
    installed_names = tuple(module.name for module in app.state.domain_modules)
    if profile.module_names:
        assert tuple(profile.module_names) == installed_names
    with TestClient(app) as client:
        assert_health_contract(client)
        assert_auth_router_contract(client, included=profile.auth_router_included)
    assert_openapi_contract(
        app,
        expected_paths=profile.expected_paths,
        expected_security_schemes=profile.expected_security_schemes,
        expected_responses=profile.expected_responses,
        validation_status=profile.validation_status,
        include_synthetic_422=profile.include_synthetic_422,
    )
    for module in app.state.domain_modules:
        assert_module_contract(
            app,
            module,
            expected_transport_policy=profile.expected_transport_policies.get(module.name),
            expected_resource_names=profile.expected_resource_names.get(module.name, ()),
            expected_readiness_names=profile.expected_readiness_names.get(module.name, ()),
            expected_error_mapper_types=profile.expected_error_mapper_types.get(
                module.name, ()
            ),
            expected_security_dependency_count=profile.expected_security_dependency_counts.get(
                module.name
            ),
            expected_common_error_statuses=profile.expected_common_error_statuses.get(
                module.name, ()
            ),
        )


__all__ = [
    "ApplicationContractProfile",
    "ResourceLifecycleProbe",
    "assert_auth_router_contract",
    "assert_application_contract",
    "assert_health_contract",
    "assert_module_contract",
    "assert_openapi_contract",
    "create_empty_runtime",
    "test_environment",
]
