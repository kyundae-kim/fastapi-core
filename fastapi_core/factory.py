from __future__ import annotations

import json
import logging
import os
from collections.abc import Callable, Sequence
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from docmesh_py_core import (
    NatsConnectionBuilder,
    ServiceClientWrapper,
    ServiceCloseError,
    ServiceConfigs,
    ServiceRuntime,
    assemble_service_runtime,
    configure_logging,
    create_keycloak_client,
    create_langfuse_client,
    create_milvus_client,
    create_minio_client,
    create_nats_client,
    create_ollama_client,
    create_postgres_client,
    create_sqlite_client,
    validate_service_requirements,
)

from fastapi_core.config import AppConfig, load_app_config
from fastapi_core.dependencies.auth import oauth2_scheme
from fastapi_core.docmesh_settings import build_docmesh_env_overlay
from fastapi_core.extensions import (
    ManagedResource,
    ReadinessCheckSpec,
    ReadinessRegistry,
    ResourceRegistry,
)
from fastapi_core.http import CorrelationIdMiddleware, install_problem_handlers
from fastapi_core.routers.auth import router as auth_router
from fastapi_core.routers.health import router as health_router

logger = logging.getLogger(__name__)


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "logger": record.name,
            "level": record.levelname,
            "message": record.getMessage(),
        }
        function_event = getattr(record, "function_event", None)
        if function_event not in (None, "-"):
            payload["function_event"] = function_event
        event = getattr(record, "event", None)
        if event is not None:
            payload["event"] = event
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def _configure_application_logging(config: AppConfig) -> logging.Logger:
    root_logger = configure_logging(
        level=config.log_level,
        log_path=config.log_path,
        force=config.log_force,
    )
    if config.log_json:
        formatter = JsonLogFormatter()
        for handler in root_logger.handlers:
            handler.setFormatter(formatter)
    return root_logger


def _build_service_clients(
    settings: ServiceConfigs,
    services: list[str],
) -> dict[str, ServiceClientWrapper | NatsConnectionBuilder]:
    factories: dict[str, Callable[[Any], Any]] = {
        "keycloak": create_keycloak_client,
        "postgres": create_postgres_client,
        "sqlite": create_sqlite_client,
        "minio": create_minio_client,
        "milvus": create_milvus_client,
        "ollama": create_ollama_client,
        "langfuse": create_langfuse_client,
        "nats": create_nats_client,
    }
    clients: dict[str, ServiceClientWrapper | NatsConnectionBuilder] = {}
    for service_name in services:
        factory = factories.get(service_name)
        service_config = getattr(settings, service_name, None)
        if factory is None or service_config is None:
            continue
        client = factory(service_config)
        if service_name != "langfuse" or client is not None:
            clients[service_name] = client
    return clients


def _build_keycloak_check_kwargs() -> dict[str, str]:
    values = {
        "username": os.getenv("KEYCLOAK_TOKEN_USERNAME"),
        "password": os.getenv("KEYCLOAK_TOKEN_PASSWORD"),
        "scope": os.getenv("FASTAPI_CORE_TEST_SCOPE", "").strip(),
    }
    return {name: value for name, value in values.items() if value}


def _configure_keycloak_provider(client: ServiceClientWrapper) -> None:
    provider = getattr(client, "client", None)
    if provider is None or not hasattr(provider, "allowed_algorithms"):
        return
    provider.allowed_algorithms = ["RS256"]


def _build_injected_service_runtime(
    settings: ServiceConfigs,
    config: AppConfig,
) -> ServiceRuntime:
    if config.service_alternatives:
        validate_service_requirements(
            settings,
            one_of=tuple(set(group) for group in config.service_alternatives),
        )
    clients = _build_service_clients(settings, config.enabled_services)
    return ServiceRuntime(
        configs=settings,
        clients=clients,
        selected_services=frozenset(clients),
        required_services=frozenset(config.required_services),
    )


def _configure_oauth2_scheme(app: FastAPI, token_url: str) -> None:
    app_scheme = OAuth2PasswordBearer(tokenUrl=token_url, auto_error=False)
    app.state.oauth2_scheme = app_scheme
    app.dependency_overrides[oauth2_scheme] = app_scheme
    default_openapi = app.openapi

    def app_openapi() -> dict[str, Any]:
        schema = default_openapi()
        security_schemes = schema.get("components", {}).get("securitySchemes", {})
        scheme = security_schemes.get("OAuth2PasswordBearer")
        if scheme is not None:
            scheme["flows"]["password"]["tokenUrl"] = token_url
        return schema

    app.openapi = app_openapi


def _configure_service_runtime(app: FastAPI, runtime: ServiceRuntime) -> None:
    app.state.service_runtime = runtime
    app.state.settings = runtime.configs
    app.state.service_clients = runtime.clients
    readiness_registry: ReadinessRegistry = app.state.readiness_registry
    required_services = set(app.state.config.required_services)
    for service_name, client in runtime.clients.items():
        check = client.check
        if service_name == "keycloak":
            healthcheck = getattr(client, "healthcheck", check)
            kwargs = _build_keycloak_check_kwargs()

            def keycloak_check(healthcheck=healthcheck, kwargs=kwargs) -> object:
                return healthcheck(**kwargs)

            check = keycloak_check
        readiness_registry.register(
            ReadinessCheckSpec(
                name=service_name,
                check=check,
                required=service_name in required_services,
                redact_errors=False,
            )
        )
    keycloak_client = runtime.clients.get("keycloak")
    if keycloak_client is not None:
        _configure_keycloak_provider(keycloak_client)
        if hasattr(keycloak_client, "client"):
            app.state.auth_provider = keycloak_client.client


def _build_lifespan(
    lifespan: Callable | None,
    config: AppConfig,
    runtime: ServiceRuntime | None,
    resources: ResourceRegistry,
) -> Callable:
    @asynccontextmanager
    async def managed_lifespan(app: FastAPI):
        app_runtime = runtime
        try:
            if app_runtime is None:
                app_runtime = await assemble_service_runtime(
                    build_docmesh_env_overlay(),
                    services=set(config.enabled_services),
                    required=set(config.required_services),
                    one_of=tuple(set(group) for group in config.service_alternatives),
                    check_on_startup=config.startup_healthcheck,
                    parallel_healthchecks=config.readiness_parallel,
                    healthcheck_timeout_seconds=config.readiness_timeout_seconds,
                    overall_healthcheck_timeout_seconds=(
                        config.readiness_overall_timeout_seconds
                    ),
                )
                _configure_service_runtime(app, app_runtime)
            elif config.startup_healthcheck:
                await app_runtime.check(
                    parallel=config.readiness_parallel,
                    timeout_seconds=config.readiness_timeout_seconds,
                    overall_timeout_seconds=config.readiness_overall_timeout_seconds,
                )
            await resources.start(app)
            if config.startup_healthcheck:
                await resources.check_startup(
                    parallel=config.readiness_parallel,
                    overall_timeout_seconds=config.readiness_overall_timeout_seconds,
                )
            if lifespan is None:
                yield
            else:
                async with lifespan(app):
                    yield
        finally:
            try:
                await resources.close()
            finally:
                if app_runtime is not None:
                    try:
                        await app_runtime.close()
                    except ServiceCloseError as exc:
                        logger.error(
                            "service_runtime_close_failed",
                            extra={
                                "event": {
                                    "operation": "service_runtime_close",
                                    "outcome": "error",
                                    "failure_count": len(exc.failures),
                                }
                            },
                        )
                        raise

    return managed_lifespan


def create_app(
    config: AppConfig | None = None,
    settings: ServiceConfigs | None = None,
    lifespan: Callable | None = None,
    include_auth_router: bool = True,
    resources: Sequence[ManagedResource[Any]] = (),
) -> FastAPI:
    app_config = config or load_app_config()
    root_logger = _configure_application_logging(app_config)
    service_runtime = (
        _build_injected_service_runtime(settings, app_config)
        if settings is not None
        else None
    )

    readiness_registry = ReadinessRegistry(
        default_timeout_seconds=app_config.readiness_timeout_seconds
    )
    resource_registry = ResourceRegistry(resources, readiness_registry)
    app = FastAPI(
        root_path=app_config.root_path,
        lifespan=_build_lifespan(
            lifespan,
            app_config,
            service_runtime,
            resource_registry,
        ),
    )
    app.state.config = app_config
    app.state.root_logger = root_logger
    app.state.service_runtime = service_runtime
    app.state.settings = settings
    app.state.service_clients = {}
    app.state.readiness_registry = readiness_registry
    app.state.resource_registry = resource_registry
    if service_runtime is not None:
        _configure_service_runtime(app, service_runtime)
    _configure_oauth2_scheme(app, app_config.token_url)
    install_problem_handlers(app)

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