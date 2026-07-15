from __future__ import annotations

from fastapi import Depends, Request
from docmesh_py_core.function_logging import log_function_boundary
from docmesh_py_core import ServiceConfigs

from fastapi_core.config import AppConfig, load_app_config
from fastapi_core.docmesh_settings import load_docmesh_settings


@log_function_boundary()
def get_config(request: Request) -> AppConfig:
    if hasattr(request.app.state, "config"):
        return request.app.state.config
    return load_app_config()


@log_function_boundary()
def get_settings(
    request: Request,
    config: AppConfig = Depends(get_config),
) -> ServiceConfigs:
    settings = getattr(request.app.state, "settings", None)
    if settings is not None:
        return settings
    return load_docmesh_settings(tuple(config.enabled_services))
