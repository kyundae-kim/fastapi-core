from __future__ import annotations

from collections.abc import Callable, Sequence
from itertools import chain
from typing import Any

from docmesh_py_core import RuntimePlan, Service, ServiceRuntime, diagnose_services
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute
from fastapi.security import OAuth2PasswordBearer

from fastapi_core.config import AppConfig, load_app_config
from fastapi_core.dependencies.auth import oauth2_scheme
from fastapi_core.function_logging import log_function_boundary
from fastapi_core.http import (
    AccessLogMiddleware,
    CorrelationIdMiddleware,
    ErrorRenderer,
    install_problem_handlers,
    register_error_mapper,
)
from fastapi_core.lifecycle import build_lifespan
from fastapi_core.logging import configure_application_logging
from fastapi_core.modules import DomainModule, ErrorMapperSpec
from fastapi_core.readiness import ReadinessCheckSpec, ReadinessRegistry
from fastapi_core.resources import ManagedResource, ResourceRegistry
from fastapi_core.routers.auth import router as auth_router
from fastapi_core.routers.health import router as health_router
from fastapi_core.runtime import build_runtime_plan, configure_service_runtime


@log_function_boundary()
def _configure_oauth2_scheme(app: FastAPI, token_url: str) -> None:
    app_scheme = OAuth2PasswordBearer(tokenUrl=token_url, auto_error=False)
    app.state.oauth2_scheme = app_scheme
    app.dependency_overrides[oauth2_scheme] = app_scheme
    default_openapi = app.openapi

    @log_function_boundary()
    def app_openapi() -> dict[str, Any]:
        schema = default_openapi()
        security_schemes = schema.get("components", {}).get("securitySchemes", {})
        scheme = security_schemes.get("OAuth2PasswordBearer")
        if scheme is not None:
            scheme["flows"]["password"]["tokenUrl"] = token_url
        return schema

    app.openapi = app_openapi


@log_function_boundary()
def _resource_name(resource: ManagedResource[Any]) -> str:
    name = resource.name
    return name.name if hasattr(name, "name") else name


@log_function_boundary()
def _flatten_modules(
    modules: Sequence[DomainModule],
) -> tuple[
    tuple[ManagedResource[Any], ...],
    tuple[ReadinessCheckSpec, ...],
    tuple[ErrorMapperSpec, ...],
]:
    names: set[str] = set()
    resources: list[ManagedResource[Any]] = []
    checks: list[ReadinessCheckSpec] = []
    mappers: list[ErrorMapperSpec] = []
    for module in modules:
        if module.name in names:
            raise ValueError(f"domain module '{module.name}' is already registered")
        names.add(module.name)
        resources.extend(module.resources)
        checks.extend(module.readiness_checks)
        mappers.extend(module.error_mappers)
    return tuple(resources), tuple(checks), tuple(mappers)


@log_function_boundary()
def _validate_routes(routers: Sequence[APIRouter]) -> None:
    contracts: set[tuple[str, str]] = set()
    operation_ids: set[str] = set()
    for router in routers:
        if not isinstance(router, APIRouter):
            raise TypeError("routers must contain APIRouter instances")
        for route in router.routes:
            if not isinstance(route, APIRoute):
                continue
            for method in route.methods or ():
                contract = (route.path, method)
                if contract in contracts:
                    raise ValueError(f"route '{method} {route.path}' is already registered")
                contracts.add(contract)
            if route.unique_id in operation_ids:
                raise ValueError(
                    f"operation ID '{route.unique_id}' is already registered"
                )
            operation_ids.add(route.unique_id)


@log_function_boundary()
def _validate_extension_names(
    resources: Sequence[ManagedResource[Any]],
    checks: Sequence[ReadinessCheckSpec],
    runtime: ServiceRuntime | None,
    runtime_plan: RuntimePlan | None,
) -> None:
    names: set[str] = set()
    for name in chain(
        (_resource_name(resource) for resource in resources),
        (spec.name for spec in checks),
    ):
        if name in names:
            raise ValueError(f"extension name '{name}' is already registered")
        names.add(name)
    if runtime is not None:
        for service in runtime.checks:
            name = Service.parse(service).value
            if name in names:
                raise ValueError(f"extension name '{name}' is already registered")
            names.add(name)
    if runtime_plan is not None:
        planned_services = {
            Service.parse(selection.service).value
            for selection in runtime_plan.services
        }
        planned_services.update(
            Service.parse(service).value
            for group in runtime_plan.one_of
            for service in group
        )
        duplicate_names = names.intersection(planned_services)
        if duplicate_names:
            name = sorted(duplicate_names)[0]
            raise ValueError(f"extension name '{name}' is already registered")


@log_function_boundary()
def _validate_error_mappers(mappers: Sequence[ErrorMapperSpec]) -> None:
    exception_types: set[type[Exception]] = set()
    for spec in mappers:
        if not isinstance(spec.exception_type, type) or not issubclass(
            spec.exception_type, Exception
        ):
            raise TypeError("error mapper exception_type must be an Exception type")
        if not callable(spec.mapper):
            raise TypeError("error mapper must be callable")
        if spec.exception_type in exception_types:
            raise ValueError(
                f"error mapper for '{spec.exception_type.__name__}' is already registered"
            )
        exception_types.add(spec.exception_type)


@log_function_boundary()
def _diagnose_auth_configuration(config: AppConfig, runtime_plan: Any) -> None:
    if "keycloak" not in config.enabled_services:
        raise ValueError("auth router requires the keycloak service to be enabled")
    if "keycloak" not in config.required_services:
        raise ValueError("auth router requires the keycloak service to be required")
    diagnosis = diagnose_services(plan=runtime_plan)
    if not diagnosis.ok:
        raise ValueError(
            "auth router service configuration is invalid: "
            f"{diagnosis.to_dict()}"
        )


@log_function_boundary()
def create_app(
    config: AppConfig | None = None,
    *,
    runtime: ServiceRuntime | None = None,
    lifespan: Callable | None = None,
    include_auth_router: bool = False,
    routers: Sequence[APIRouter] = (),
    modules: Sequence[DomainModule] = (),
    resources: Sequence[ManagedResource[Any]] = (),
    error_mappers: Sequence[ErrorMapperSpec] = (),
    error_renderer: ErrorRenderer | None = None,
    auth_provider: Any | None = None,
) -> FastAPI:
    """Create an application with lifespan-managed DocMesh services."""
    app_config = config or load_app_config()
    runtime_plan = (
        build_runtime_plan(app_config)
        if runtime is None and app_config.enabled_services
        else None
    )
    if include_auth_router and auth_provider is None and runtime is None:
        if runtime_plan is None:
            raise ValueError("auth router requires the keycloak service to be enabled")
        _diagnose_auth_configuration(app_config, runtime_plan)

    module_resources, module_checks, module_mappers = _flatten_modules(modules)
    all_resources = tuple(resources) + module_resources
    all_mappers = tuple(error_mappers) + module_mappers
    all_routers = (
        (health_router,)
        + ((auth_router,) if include_auth_router else ())
        + tuple(routers)
        + tuple(router for module in modules for router in module.routers)
    )
    _validate_routes(all_routers)
    _validate_extension_names(all_resources, module_checks, runtime, runtime_plan)
    _validate_error_mappers(all_mappers)

    root_logger = configure_application_logging(app_config)
    readiness_registry = ReadinessRegistry(
        default_timeout_seconds=app_config.readiness_timeout_seconds
    )
    for spec in module_checks:
        readiness_registry.register(spec)
    resource_registry = ResourceRegistry(all_resources, readiness_registry)
    app = FastAPI(
        root_path=app_config.root_path,
        lifespan=build_lifespan(
            lifespan,
            app_config,
            runtime,
            runtime_plan,
            resource_registry,
            require_auth_provider=include_auth_router,
        ),
    )
    app.state.config = app_config
    app.state.root_logger = root_logger
    app.state.service_runtime = runtime
    app.state.readiness_registry = readiness_registry
    app.state.resource_registry = resource_registry
    app.state.domain_modules = tuple(modules)
    if runtime is not None:
        configure_service_runtime(app, runtime)
    if auth_provider is not None:
        app.state.auth_provider = auth_provider
    if include_auth_router and runtime is not None and not hasattr(
        app.state, "auth_provider"
    ):
        raise ValueError("auth router requires a configured auth provider")

    _configure_oauth2_scheme(app, app_config.token_url)
    install_problem_handlers(app, error_renderer)
    for spec in all_mappers:
        register_error_mapper(app, spec.exception_type, spec.mapper)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_config.cors_origins,
        allow_credentials=app_config.cors_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    if app_config.access_log_enabled:
        app.add_middleware(
            AccessLogMiddleware,
            log_health=app_config.access_log_health_enabled,
        )
    app.add_middleware(CorrelationIdMiddleware)

    app.include_router(health_router)
    if include_auth_router:
        app.include_router(auth_router)
    for router in routers:
        app.include_router(router)
    for module in modules:
        for router in module.routers:
            app.include_router(router, dependencies=list(module.dependencies))

    return app
