from __future__ import annotations

from fastapi import FastAPI, Request

from fastapi_core.core.config import EnvConfig, ServiceSettings


_CONFIG_STATE_KEY = "config"
_SETTINGS_STATE_KEY = "settings"


def set_config(app: FastAPI, config: EnvConfig) -> None:
    setattr(app.state, _CONFIG_STATE_KEY, config)


def set_settings(app: FastAPI, settings: ServiceSettings) -> None:
    setattr(app.state, _SETTINGS_STATE_KEY, settings)


def get_config(request: Request) -> EnvConfig:
    return getattr(request.app.state, _CONFIG_STATE_KEY)


def get_settings(request: Request) -> ServiceSettings:
    return getattr(request.app.state, _SETTINGS_STATE_KEY)


class GetConfigDependency:
    def __call__(self, request: Request) -> EnvConfig:
        try:
            return get_config(request)
        except AttributeError:
            config = EnvConfig()
            set_config(request.app, config)
            return config


class GetSettingsDependency:
    def __call__(self, request: Request) -> ServiceSettings:
        try:
            return get_settings(request)
        except AttributeError:
            config = config_schema(request)
            settings = ServiceSettings.from_yaml(config.config_path)
            set_settings(request.app, settings)
            return settings


config_schema = GetConfigDependency()
settings_schema = GetSettingsDependency()
