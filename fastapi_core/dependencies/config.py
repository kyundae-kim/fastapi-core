from __future__ import annotations

from fastapi import Depends, FastAPI, Request
from fastapi.params import Depends as DependsParam

from fastapi_core.bootstrap import get_or_create_state_value, set_state_value
from fastapi_core.core.config import (
    EnvConfig,
    ServiceSettings,
    load_env_config,
    load_service_settings,
)

_CONFIG_STATE_KEY = "config"
_SETTINGS_STATE_KEY = "settings"


def set_config(app: FastAPI, config: EnvConfig) -> None:
    set_state_value(app, _CONFIG_STATE_KEY, config)


def set_settings(app: FastAPI, settings: ServiceSettings) -> None:
    set_state_value(app, _SETTINGS_STATE_KEY, settings)


def get_config(request: Request) -> EnvConfig:
    return get_or_create_state_value(request.app, _CONFIG_STATE_KEY, load_env_config)


def get_settings(
    request: Request,
    config: EnvConfig | DependsParam = Depends(get_config),
) -> ServiceSettings:
    def factory() -> ServiceSettings:
        resolved_config = config
        if isinstance(resolved_config, DependsParam):
            resolved_config = get_config(request)
        return load_service_settings(resolved_config)

    return get_or_create_state_value(request.app, _SETTINGS_STATE_KEY, factory)
