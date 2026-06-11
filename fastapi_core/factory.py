from __future__ import annotations

from collections.abc import AsyncIterator, Callable

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from fastapi_core.bootstrap import set_state_value
from fastapi_core.core.config import EnvConfig, ServiceSettings
from fastapi_core.core.exceptions import AuthError, auth_error_handler
from fastapi_core.core.logging import setup_logging
from fastapi_core.dependencies.config import _CONFIG_STATE_KEY, _SETTINGS_STATE_KEY
from fastapi_core.lifecycle import create_managed_lifespan
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
    if lifespan is None:
        lifespan = create_managed_lifespan(config)

    setup_logging(config.logging.level)

    app = FastAPI(root_path=config.root_path, lifespan=lifespan)
    set_state_value(app, _CONFIG_STATE_KEY, config)
    set_state_value(app, _SETTINGS_STATE_KEY, settings)

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
