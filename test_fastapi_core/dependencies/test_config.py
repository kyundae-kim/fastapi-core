from __future__ import annotations

from fastapi import FastAPI, Request

import fastapi_core.dependencies.config as config_dependencies
from fastapi_core.core.config import EnvConfig, ServiceSettings
from fastapi_core.dependencies.config import get_config, get_settings


def _make_request(app: FastAPI) -> Request:
    scope = {"type": "http", "app": app, "method": "GET", "path": "/", "headers": []}
    return Request(scope)


def test_config_schema_aliases_are_removed():
    assert not hasattr(config_dependencies, "config_schema")
    assert not hasattr(config_dependencies, "settings_schema")


def test_get_config_creates_env_config_on_app_state():
    app = FastAPI()
    request = _make_request(app)

    config = get_config(request)

    assert isinstance(config, EnvConfig)
    assert app.state.config is config


def test_get_config_returns_cached_app_state_config():
    app = FastAPI()
    request = _make_request(app)

    config1 = get_config(request)
    config2 = get_config(request)

    assert config1 is config2


def test_get_settings_creates_service_settings_on_app_state():
    app = FastAPI()
    request = _make_request(app)
    config = EnvConfig()
    app.state.config = config

    settings = get_settings(request)

    assert isinstance(settings, ServiceSettings)
    assert app.state.settings is settings


def test_get_settings_creates_config_when_missing():
    app = FastAPI()
    request = _make_request(app)

    settings = get_settings(request)

    assert isinstance(settings, ServiceSettings)
    assert isinstance(app.state.config, EnvConfig)
    assert app.state.settings is settings


def test_get_settings_returns_cached_app_state_settings():
    app = FastAPI()
    request = _make_request(app)
    expected = ServiceSettings()
    app.state.settings = expected

    assert get_settings(request) is expected


def test_get_settings_defaults():
    app = FastAPI()
    request = _make_request(app)

    settings = get_settings(request)

    assert isinstance(settings.cors.origins, list)
    assert isinstance(settings.auth.verify_jwt, bool)
    assert isinstance(settings.health.check_keycloak, bool)
    assert isinstance(settings.health.check_database, bool)
    assert isinstance(settings.health.check_minio, bool)
