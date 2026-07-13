from __future__ import annotations

import json
import logging
import os
from collections.abc import Callable
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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
from fastapi_core.dependencies.auth import set_oauth2_token_url
from fastapi_core.docmesh_settings import build_docmesh_env_overlay
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
    clients: dict[str, ServiceClientWrapper | NatsConnectionBuilder] = {}
    for service_name in services:
        if service_name == "keycloak" and settings.keycloak is not None:
            client = create_keycloak_client(settings.keycloak)
            _configure_keycloak_provider(client)
            clients[service_name] = client
        elif service_name == "postgres" and settings.postgres is not None:
            clients[service_name] = create_postgres_client(settings.postgres)
        elif service_name == "sqlite" and settings.sqlite is not None:
            clients[service_name] = create_sqlite_client(settings.sqlite)
        elif service_name == "minio" and settings.minio is not None:
            clients[service_name] = create_minio_client(settings.minio)
        elif service_name == "milvus" and settings.milvus is not None:
            clients[service_name] = create_milvus_client(settings.milvus)
        elif service_name == "ollama" and settings.ollama is not None:
            clients[service_name] = create_ollama_client(settings.ollama)
        elif service_name == "langfuse" and settings.langfuse is not None:
            client = create_langfuse_client(settings.langfuse)
            if client is not None:
                clients[service_name] = client
        elif service_name == "nats" and settings.nats is not None:
            clients[service_name] = create_nats_client(settings.nats)
    return clients


def _build_keycloak_check_kwargs() -> dict[str, str]:
    kwargs: dict[str, str] = {}
    username = os.getenv("KEYCLOAK_TOKEN_USERNAME")
    password = os.getenv("KEYCLOAK_TOKEN_PASSWORD")
    scope = os.getenv("FASTAPI_CORE_TEST_SCOPE", "").strip()
    if username:
        kwargs["username"] = username
    if password:
        kwargs["password"] = password
    if scope:
        kwargs["scope"] = scope
    return kwargs


def _configure_keycloak_provider(client: ServiceClientWrapper) -> None:
    provider = getattr(client, "client", None)
    if provider is None or not hasattr(provider, "allowed_algorithms"):
        return
    provider.allowed_algorithms = ["RS256"]


def _wrap_readiness_check(
    check: Callable[..., object],
    *,
    kwargs: dict[str, str],
) -> Callable[[], object]:
    def run_check() -> object:
        return check(**kwargs)

    return run_check


def _build_readiness_checks(
    service_clients: dict[str, ServiceClientWrapper | NatsConnectionBuilder],
) -> dict[str, Callable[[], object]]:
    checks: dict[str, Callable[[], object]] = {}
    for service_name, client in service_clients.items():
        check = client.check
        if service_name == "keycloak":
            check = getattr(client, "healthcheck", client.check)
            check = _wrap_readiness_check(
                check,
                kwargs=_build_keycloak_check_kwargs(),
            )
        checks[service_name] = check
    return checks


def _build_readiness_metadata(
    enabled_services: list[str],
    required_services: list[str],
) -> dict[str, dict[str, bool]]:
    required = set(required_services)
    return {
        service_name: {
            "enabled": True,
            "required": service_name in required,
        }
        for service_name in enabled_services
    }


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


def _configure_service_runtime(app: FastAPI, runtime: ServiceRuntime) -> None:
    app.state.service_runtime = runtime
    app.state.settings = runtime.configs
    app.state.service_clients = runtime.clients
    app.state.readiness_checks = _build_readiness_checks(runtime.clients)
    keycloak_client = runtime.clients.get("keycloak")
    if keycloak_client is not None:
        _configure_keycloak_provider(keycloak_client)
        if hasattr(keycloak_client, "client"):
            app.state.auth_provider = keycloak_client.client


def _build_lifespan(
    lifespan: Callable | None,
    config: AppConfig,
    runtime: ServiceRuntime | None,
) -> Callable:
    @asynccontextmanager
    async def managed_lifespan(app: FastAPI):
        app_runtime = runtime
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
        try:
            if lifespan is None:
                yield
            else:
                async with lifespan(app):
                    yield
        finally:
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
) -> FastAPI:
    app_config = config or load_app_config()
    root_logger = _configure_application_logging(app_config)
    service_runtime = (
        _build_injected_service_runtime(settings, app_config)
        if settings is not None
        else None
    )

    app = FastAPI(
        root_path=app_config.root_path,
        lifespan=_build_lifespan(lifespan, app_config, service_runtime),
    )
    app.state.config = app_config
    app.state.root_logger = root_logger
    app.state.service_runtime = service_runtime
    app.state.settings = settings
    app.state.service_clients = {}
    app.state.readiness_parallel = app_config.readiness_parallel
    app.state.readiness_timeout_seconds = app_config.readiness_timeout_seconds
    app.state.readiness_overall_timeout_seconds = (
        app_config.readiness_overall_timeout_seconds
    )
    app.state.readiness_checks = {}
    app.state.readiness_services = _build_readiness_metadata(
        app_config.enabled_services,
        app_config.required_services,
    )
    app.state.required_services = set(app_config.required_services)
    if service_runtime is not None:
        _configure_service_runtime(app, service_runtime)
    set_oauth2_token_url(app_config.token_url)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_config.cors_origins,
        allow_credentials=app_config.cors_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    if include_auth_router:
        app.include_router(auth_router)

    return app