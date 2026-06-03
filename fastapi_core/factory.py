from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from fastapi_core.core.config import EnvConfig, ServiceSettings
from fastapi_core.core.exceptions import AuthError, auth_error_handler
from fastapi_core.core.logging import setup_logging
from fastapi_core.dependencies.config import set_config, set_settings
from fastapi_core.routers import auth, health


def create_app(
    config: EnvConfig | None = None,
    settings: ServiceSettings | None = None,
    lifespan: Callable[[FastAPI], AsyncIterator] | None = None,
    include_auth_router: bool = True,
) -> FastAPI:
    if config is None:
        config = EnvConfig()
    if settings is None:
        settings = ServiceSettings.from_yaml(config.config_path)

    setup_logging(config.logging.level)

    app = FastAPI(root_path=config.root_path, lifespan=lifespan)
    set_config(app, config)
    set_settings(app, settings)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors.origins,
        allow_credentials=settings.cors.credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_exception_handler(AuthError, auth_error_handler)  # type: ignore[arg-type]

    app.include_router(health.router)

    if include_auth_router:
        app.include_router(auth.router)

    return app
