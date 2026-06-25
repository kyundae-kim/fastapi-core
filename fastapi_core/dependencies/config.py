from __future__ import annotations

from fastapi import Depends, Request
from docmesh_py_core import Settings

from fastapi_core.config import AppConfig, load_app_config, load_default_settings


def get_config(request: Request) -> AppConfig:
    if hasattr(request.app.state, "config"):
        return request.app.state.config
    return load_app_config()


def get_settings(
    request: Request,
    config: AppConfig = Depends(get_config),
) -> Settings:
    del config
    if hasattr(request.app.state, "settings"):
        return request.app.state.settings
    return load_default_settings()
