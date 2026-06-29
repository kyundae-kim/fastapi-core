from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from collections.abc import Callable

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from docmesh_py_core import ServiceFactoryRegistry, Settings, configure_logging

from fastapi_core.config import AppConfig, load_app_config, load_default_settings
from fastapi_core.dependencies.auth import set_oauth2_token_url
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


def _build_registry_readiness_checks(
    registry: ServiceFactoryRegistry,
    services: list[str],
) -> dict[str, Callable[[], object]]:
    checks: dict[str, Callable[[], object]] = {}
    for service_name in services:
        checks[service_name] = lambda service_name=service_name: registry.create_client(service_name).check()
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
    registry: ServiceFactoryRegistry,
) -> Callable:
    @asynccontextmanager
    async def managed_lifespan(app: FastAPI):
        if lifespan is None:
            yield
        else:
            async with lifespan(app):
                yield
        registry.close_all()

    return managed_lifespan


def create_app(
    config: AppConfig | None = None,
    settings: Settings | None = None,
    lifespan: Callable | None = None,
    include_auth_router: bool = True,
) -> FastAPI:
    app_config = config or load_app_config()
    root_logger = _configure_application_logging(app_config)
    app_settings = settings or load_default_settings(tuple(app_config.enabled_services))
    registry = ServiceFactoryRegistry(app_settings)

    app = FastAPI(
        root_path=app_config.root_path,
        lifespan=_build_lifespan(lifespan, registry),
    )
    app.state.config = app_config
    app.state.root_logger = root_logger
    app.state.settings = app_settings
    app.state.registry = registry
    app.state.readiness_parallel = app_config.readiness_parallel
    app.state.readiness_checks = _build_registry_readiness_checks(
        registry,
        app_config.enabled_services,
    )
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
