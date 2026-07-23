from __future__ import annotations

import os
from collections.abc import Collection, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

from fastapi import FastAPI
from fastapi.routing import APIRoute

from fastapi_core.config import load_app_config
from fastapi_core.docmesh_settings import load_docmesh_settings
from fastapi_core.function_logging import log_function_boundary
from fastapi_core.modules import DomainModule
from fastapi_core.resources import ManagedResource, ResourceRegistry
from fastapi_core.runtime import create_empty_runtime

T = TypeVar("T")
_MISSING = object()


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
    liveness = client.get("/health/liveness")
    readiness = client.get("/health/readiness")
    assert liveness.status_code == 200
    assert liveness.json()["status"] == "ok"
    assert readiness.status_code == 200
    assert readiness.json()["status"] == "ok"


@log_function_boundary()
def assert_auth_router_contract(client: Any, *, included: bool) -> None:
    """Assert whether the built-in authentication routes are installed."""
    user = client.get("/user")
    token = client.post("/token")
    if included:
        assert user.status_code != 404
        assert token.status_code != 404
    else:
        assert user.status_code == 404
        assert token.status_code == 404


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
        resource.name.name if hasattr(resource.name, "name") else resource.name
        for resource in registry.resources
    }


@log_function_boundary()
def assert_module_contract(app: FastAPI, module: DomainModule) -> None:
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
        name = resource.name.name if hasattr(resource.name, "name") else resource.name
        assert name in installed_resources, f"module resource '{name}' is not installed"
    for spec in module.readiness_checks:
        assert spec.name in app.state.readiness_registry.specs, (
            f"module readiness check '{spec.name}' is not installed"
        )
    for spec in module.error_mappers:
        assert spec.exception_type in app.state.error_mapper_types, (
            f"module error mapper '{spec.exception_type.__name__}' is not installed"
        )


@log_function_boundary()
def assert_openapi_contract(
    app: FastAPI,
    *,
    expected_paths: Mapping[str, Collection[str]],
    expected_security_schemes: Collection[str] = (),
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


__all__ = [
    "ResourceLifecycleProbe",
    "assert_auth_router_contract",
    "assert_health_contract",
    "assert_module_contract",
    "assert_openapi_contract",
    "create_empty_runtime",
    "test_environment",
]
