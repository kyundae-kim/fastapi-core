from __future__ import annotations

import asyncio
import inspect
import json
import logging
import os
from collections.abc import Callable
from contextlib import asynccontextmanager
from threading import Thread
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from docmesh_py_core import (
    NatsConnectionBuilder,
    ServiceClientWrapper,
    ServiceConfigs,
    close_service_clients,
    configure_logging,
    create_keycloak_client,
    create_langfuse_client,
    create_milvus_client,
    create_minio_client,
    create_nats_client,
    create_ollama_client,
    create_postgres_client,
    create_sqlite_client,
)

from fastapi_core.config import AppConfig, load_app_config
from fastapi_core.dependencies.auth import set_oauth2_token_url
from fastapi_core.docmesh_settings import load_docmesh_settings
from fastapi_core.routers.auth import router as auth_router
from fastapi_core.routers.health import router as health_router


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


def _run_awaitable_synchronously(awaitable: Any) -> Any:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(awaitable)

    result: dict[str, Any] = {}
    error: dict[str, BaseException] = {}

    def _runner() -> None:
        try:
            result["value"] = asyncio.run(awaitable)
        except BaseException as exc:  # pragma: no cover
            error["exception"] = exc

    thread = Thread(target=_runner)
    thread.start()
    thread.join()
    if error:
        raise error["exception"]
    return result.get("value")


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
    kwargs: dict[str, str] | None = None,
) -> Callable[[], object]:
    def run_check() -> object:
        result = check(**(kwargs or {}))
        if inspect.isawaitable(result):
            return _run_awaitable_synchronously(result)
        return result

    return run_check


def _build_readiness_checks(
    service_clients: dict[str, ServiceClientWrapper | NatsConnectionBuilder],
) -> dict[str, Callable[[], object]]:
    checks: dict[str, Callable[[], object]] = {}
    for service_name, client in service_clients.items():
        check = client.check
        kwargs = None
        if service_name == "keycloak":
            kwargs = _build_keycloak_check_kwargs()
            check = getattr(client, "healthcheck", client.check)
        checks[service_name] = _wrap_readiness_check(check, kwargs=kwargs)
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


def _build_lifespan(
    lifespan: Callable | None,
    service_clients: dict[str, ServiceClientWrapper | NatsConnectionBuilder],
) -> Callable:
    @asynccontextmanager
    async def managed_lifespan(app: FastAPI):
        if lifespan is None:
            yield
        else:
            async with lifespan(app):
                yield
        close_service_clients(service_clients.values())

    return managed_lifespan


def create_app(
    config: AppConfig | None = None,
    settings: ServiceConfigs | None = None,
    lifespan: Callable | None = None,
    include_auth_router: bool = True,
) -> FastAPI:
    app_config = config or load_app_config()
    root_logger = _configure_application_logging(app_config)
    app_settings = settings or load_docmesh_settings(tuple(app_config.enabled_services))
    service_clients = _build_service_clients(app_settings, app_config.enabled_services)

    app = FastAPI(
        root_path=app_config.root_path,
        lifespan=_build_lifespan(lifespan, service_clients),
    )
    app.state.config = app_config
    app.state.root_logger = root_logger
    app.state.settings = app_settings
    app.state.service_clients = service_clients
    keycloak_client = service_clients.get("keycloak")
    if keycloak_client is not None and hasattr(keycloak_client, "client"):
        app.state.auth_provider = keycloak_client.client
    app.state.readiness_parallel = app_config.readiness_parallel
    app.state.readiness_checks = _build_readiness_checks(service_clients)
    app.state.readiness_services = _build_readiness_metadata(
        app_config.enabled_services,
        app_config.required_services,
    )
    app.state.required_services = set(app_config.required_services)
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