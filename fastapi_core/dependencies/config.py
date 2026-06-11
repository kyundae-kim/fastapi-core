from __future__ import annotations

from fastapi import Depends, FastAPI, Request
from fastapi.params import Depends as DependsParam

from fastapi_core.bootstrap import get_or_create_state_value, set_state_value
from fastapi_core.core.config import EnvConfig, ServiceSettings

_CONFIG_STATE_KEY = "config"
_SETTINGS_STATE_KEY = "settings"


def set_config(app: FastAPI, config: EnvConfig) -> None:
    set_state_value(app, _CONFIG_STATE_KEY, config)


def set_settings(app: FastAPI, settings: ServiceSettings) -> None:
    set_state_value(app, _SETTINGS_STATE_KEY, settings)


def get_config(request: Request) -> EnvConfig:
    return get_or_create_state_value(request.app, _CONFIG_STATE_KEY, EnvConfig)


def get_settings(
    request: Request,
    config: EnvConfig | DependsParam = Depends(get_config),
) -> ServiceSettings:
    def factory() -> ServiceSettings:
        resolved_config = config
        if isinstance(resolved_config, DependsParam):
            resolved_config = get_config(request)
        return ServiceSettings.from_yaml(resolved_config.config_path)

    return get_or_create_state_value(request.app, _SETTINGS_STATE_KEY, factory)
