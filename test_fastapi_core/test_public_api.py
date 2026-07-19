from __future__ import annotations

import ast
from dataclasses import MISSING, fields
from importlib import import_module
from inspect import Parameter, signature
from pathlib import Path

import fastapi_core
import fastapi_core.dependencies as dependencies
import fastapi_core.factory as factory_module
import fastapi_core.routers.health as health_module
import fastapi_core.schemas as schemas
import docmesh_py_core
from fastapi_core.config import AppConfig
from fastapi_core.extensions import ResourceRegistry
from fastapi_core.factory import create_app
from fastapi_core.readiness import get_readiness_registry


ROOT_EXPORTS = {
    "ErrorMapping",
    "ErrorRenderer",
    "ManagedResource",
    "ReadinessCheckSpec",
    "ResourceKey",
    "create_app",
    "register_error_mapper",
    "register_readiness_check",
}

DEPENDENCY_EXPORTS = {
    "get_auth_provider",
    "get_config",
    "get_current_user",
    "get_keycloak_auth_service",
    "get_langfuse_client",
    "get_milvus_client",
    "get_minio_client",
    "get_nats_connection_builder",
    "get_ollama_client",
    "get_postgres_engine",
    "get_resource",
    "get_service_client",
    "get_service_runtime",
    "get_settings",
    "get_sqlite_engine",
    "require_permissions",
    "require_roles",
    "require_scopes",
}

SCHEMA_EXPORTS = {
    "HealthResponse",
    "HealthServiceDetail",
    "ProblemDetail",
    "TokenResponse",
    "UserInfo",
}


def _parameter_contract(callable_object):
    return [
        (parameter.name, parameter.kind, parameter.default)
        for parameter in signature(callable_object).parameters.values()
    ]


def _field_defaults(dataclass_type):
    return {
        field.name: field.default
        for field in fields(dataclass_type)
        if field.default is not MISSING
    }


def test_curated_package_exports_are_stable():
    assert set(fastapi_core.__all__) == ROOT_EXPORTS
    assert set(dependencies.__all__) == DEPENDENCY_EXPORTS
    assert set(schemas.__all__) == SCHEMA_EXPORTS

    for name in ROOT_EXPORTS:
        assert getattr(fastapi_core, name) is not None
    for name in DEPENDENCY_EXPORTS:
        assert getattr(dependencies, name) is not None
    for name in SCHEMA_EXPORTS:
        assert getattr(schemas, name) is not None


def test_create_app_signature_is_stable():
    assert _parameter_contract(fastapi_core.create_app) == [
        ("config", Parameter.POSITIONAL_OR_KEYWORD, None),
        ("runtime", Parameter.KEYWORD_ONLY, None),
        ("lifespan", Parameter.KEYWORD_ONLY, None),
        ("include_auth_router", Parameter.KEYWORD_ONLY, False),
        ("resources", Parameter.KEYWORD_ONLY, ()),
        ("error_renderer", Parameter.KEYWORD_ONLY, None),
    ]


def test_runtime_extension_contracts_are_stable():
    assert [field.name for field in fields(fastapi_core.ReadinessCheckSpec)] == [
        "name",
        "check",
        "required",
        "timeout_seconds",
        "redact_errors",
    ]
    assert _field_defaults(fastapi_core.ReadinessCheckSpec) == {
        "required": True,
        "timeout_seconds": None,
        "redact_errors": True,
    }

    assert [field.name for field in fields(fastapi_core.ManagedResource)] == [
        "name",
        "factory",
        "healthcheck",
        "close",
        "required",
        "readiness_timeout_seconds",
        "redact_errors",
    ]
    assert _field_defaults(fastapi_core.ManagedResource) == {
        "healthcheck": None,
        "close": None,
        "required": True,
        "readiness_timeout_seconds": None,
        "redact_errors": True,
    }

    assert [field.name for field in fields(fastapi_core.ErrorMapping)] == [
        "status_code",
        "detail",
        "title",
        "type_uri",
        "headers",
        "code",
        "extensions",
    ]
    assert _field_defaults(fastapi_core.ErrorMapping) == {
        "title": None,
        "type_uri": "about:blank",
        "headers": None,
        "code": None,
        "extensions": None,
    }


def test_extension_function_signatures_are_stable():
    assert _parameter_contract(fastapi_core.register_readiness_check) == [
        ("app", Parameter.POSITIONAL_OR_KEYWORD, Parameter.empty),
        ("name", Parameter.POSITIONAL_OR_KEYWORD, Parameter.empty),
        ("check", Parameter.POSITIONAL_OR_KEYWORD, Parameter.empty),
        ("required", Parameter.KEYWORD_ONLY, True),
        ("timeout_seconds", Parameter.KEYWORD_ONLY, None),
        ("redact_errors", Parameter.KEYWORD_ONLY, True),
    ]
    assert _parameter_contract(fastapi_core.register_error_mapper) == [
        ("app", Parameter.POSITIONAL_OR_KEYWORD, Parameter.empty),
        ("exception_type", Parameter.POSITIONAL_OR_KEYWORD, Parameter.empty),
        ("mapper", Parameter.POSITIONAL_OR_KEYWORD, Parameter.empty),
    ]


def test_readiness_state_exposes_only_typed_registry(runtime_factory):
    class Client:
        def check(self):
            return None

    runtime = runtime_factory(
        clients={"keycloak": Client()},
        required=("keycloak",),
    )
    app = create_app(
        config=AppConfig(enabled_services=["keycloak"], required_services=["keycloak"]),
        runtime=runtime,
        include_auth_router=False,
    )
    registry = app.state.readiness_registry

    for name in (
        "readiness_checks",
        "readiness_services",
        "required_services",
        "readiness_parallel",
        "readiness_timeout_seconds",
        "readiness_overall_timeout_seconds",
    ):
        assert not hasattr(app.state, name)

    assert set(registry.specs) == {"keycloak"}
    assert not hasattr(registry, "checks")
    assert not hasattr(registry, "services")
    assert not hasattr(registry, "required_services")
    assert not hasattr(registry, "owns_legacy_state")
    assert not hasattr(app.state.resource_registry, "_healthcheck_names")


def test_readiness_registry_state_lookup_is_owned_by_readiness_module(empty_runtime):
    app = create_app(runtime=empty_runtime)

    assert get_readiness_registry(app) is app.state.readiness_registry


def test_obsolete_refactoring_helpers_are_not_reintroduced():
    assert not hasattr(health_module, "_build_service_detail")
    assert not hasattr(factory_module, "_wrap_readiness_check")
    assert not hasattr(factory_module, "_build_readiness_checks")
    assert not hasattr(ResourceRegistry, "_bind_healthcheck")
    assert not hasattr(factory_module, "build_injected_service_runtime")
    runtime = import_module("fastapi_core.runtime")
    assert not hasattr(runtime, "build_injected_service_runtime")
    assert not hasattr(runtime, "build_service_clients")


def test_readiness_and_resource_implementations_have_explicit_module_owners():
    readiness = import_module("fastapi_core.readiness")
    resources = import_module("fastapi_core.resources")

    assert readiness.ReadinessCheckSpec is fastapi_core.ReadinessCheckSpec
    assert readiness.register_readiness_check is fastapi_core.register_readiness_check
    assert resources.ManagedResource is fastapi_core.ManagedResource
    assert resources.ResourceKey is fastapi_core.ResourceKey


def test_factory_collaborators_have_explicit_module_owners():
    application_logging = import_module("fastapi_core.logging")
    lifecycle = import_module("fastapi_core.lifecycle")
    runtime = import_module("fastapi_core.runtime")

    assert application_logging.JsonLogFormatter.__module__ == "fastapi_core.logging"
    assert lifecycle.build_lifespan.__module__ == "fastapi_core.lifecycle"
    assert runtime.configure_service_runtime.__module__ == "fastapi_core.runtime"


def test_production_code_imports_docmesh_py_core_only_from_package_root():
    package_root = Path(__file__).parents[1] / "fastapi_core"
    private_imports: list[str] = []
    root_imports: set[str] = set()

    for path in sorted(package_root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module.startswith("docmesh_py_core."):
                    private_imports.append(
                        f"{path.relative_to(package_root)}:{node.lineno}:{module}"
                    )
                elif module == "docmesh_py_core":
                    root_imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("docmesh_py_core."):
                        private_imports.append(
                            f"{path.relative_to(package_root)}:{node.lineno}:{alias.name}"
                        )

    assert private_imports == []
    assert root_imports <= set(docmesh_py_core.__all__)
