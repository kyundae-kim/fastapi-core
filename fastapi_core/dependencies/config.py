from __future__ import annotations

from fastapi import Request
from fastapi_core.function_logging import log_function_boundary
from docmesh_py_core import ServiceConfigs

from fastapi_core.config import AppConfig, load_app_config
from fastapi_core.dependencies.services import get_service_runtime


@log_function_boundary()
def get_config(request: Request) -> AppConfig:
    if hasattr(request.app.state, "config"):
        return request.app.state.config
    return load_app_config()


@log_function_boundary()
def get_settings(request: Request) -> ServiceConfigs:
    return get_service_runtime(request).configs
