from __future__ import annotations

from collections.abc import Callable

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from docmesh_py_core import Settings

from fastapi_core.config import AppConfig, load_app_config, load_default_settings
from fastapi_core.routers.auth import router as auth_router
from fastapi_core.routers.health import router as health_router


def create_app(
    config: AppConfig | None = None,
    settings: Settings | None = None,
    lifespan: Callable | None = None,
    include_auth_router: bool = True,
) -> FastAPI:
    app_config = config or load_app_config()
    app_settings = settings or load_default_settings()

    app = FastAPI(root_path=app_config.root_path, lifespan=lifespan)
    app.state.config = app_config
    app.state.settings = app_settings
    app.state.readiness_parallel = app_config.readiness_parallel

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
