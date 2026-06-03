from __future__ import annotations

from fastapi import Depends, FastAPI, Request
from fastapi.params import Depends as DependsParam

from fastapi_core.core.config import EnvConfig, ServiceSettings

_CONFIG_STATE_KEY = "config"
_SETTINGS_STATE_KEY = "settings"


def set_config(app: FastAPI, config: EnvConfig) -> None:
    setattr(app.state, _CONFIG_STATE_KEY, config)


def set_settings(app: FastAPI, settings: ServiceSettings) -> None:
    setattr(app.state, _SETTINGS_STATE_KEY, settings)


def get_config(request: Request) -> EnvConfig:
    try:
        return getattr(request.app.state, _CONFIG_STATE_KEY)
    except AttributeError:
        config = EnvConfig()
        set_config(request.app, config)
        return config


def get_settings(
    request: Request,
    config: EnvConfig | DependsParam = Depends(get_config),
) -> ServiceSettings:
    try:
        return getattr(request.app.state, _SETTINGS_STATE_KEY)
    except AttributeError:
        if isinstance(config, DependsParam):
            config = get_config(request)
        settings = ServiceSettings.from_yaml(config.config_path)
        set_settings(request.app, settings)
        return settings
