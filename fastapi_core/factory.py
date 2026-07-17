from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from docmesh_py_core import ServiceRuntime
from docmesh_py_core.function_logging import log_function_boundary
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer

from fastapi_core.config import AppConfig, load_app_config
from fastapi_core.dependencies.auth import oauth2_scheme
from fastapi_core.http import (
    CorrelationIdMiddleware,
    ErrorRenderer,
    install_problem_handlers,
)
from fastapi_core.lifecycle import build_lifespan
from fastapi_core.logging import configure_application_logging
from fastapi_core.readiness import ReadinessRegistry
from fastapi_core.resources import ManagedResource, ResourceRegistry
from fastapi_core.routers.auth import router as auth_router
from fastapi_core.routers.health import router as health_router
from fastapi_core.runtime import configure_service_runtime


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
def create_app(
    config: AppConfig | None = None,
    *,
    runtime: ServiceRuntime | None = None,
    lifespan: Callable | None = None,
    include_auth_router: bool = True,
    resources: Sequence[ManagedResource[Any]] = (),
    error_renderer: ErrorRenderer | None = None,
) -> FastAPI:
    """Create an application with lifespan-managed DocMesh services.

    ``runtime`` is the explicit service-injection seam. Production applications
    should omit it so startup assembles the runtime from the process environment
    and the configured ``RuntimePlan``.
    """
    app_config = config or load_app_config()
    root_logger = configure_application_logging(app_config)

    readiness_registry = ReadinessRegistry(
        default_timeout_seconds=app_config.readiness_timeout_seconds
    )
    resource_registry = ResourceRegistry(resources, readiness_registry)
    app = FastAPI(
        root_path=app_config.root_path,
        lifespan=build_lifespan(
            lifespan,
            app_config,
            runtime,
            resource_registry,
        ),
    )
    app.state.config = app_config
    app.state.root_logger = root_logger
    app.state.service_runtime = runtime
    app.state.readiness_registry = readiness_registry
    app.state.resource_registry = resource_registry
    if runtime is not None:
        configure_service_runtime(app, runtime)
    _configure_oauth2_scheme(app, app_config.token_url)
    install_problem_handlers(app, error_renderer)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_config.cors_origins,
        allow_credentials=app_config.cors_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(CorrelationIdMiddleware)

    app.include_router(health_router)
    if include_auth_router:
        app.include_router(auth_router)

    return app
