from __future__ import annotations

from fastapi import FastAPI, Request

from fastapi_core.core.config import EnvConfig, ServiceSettings
from fastapi_core.dependencies.config import (
    config_schema,
    get_config,
    get_settings,
    settings_schema,
)


def _make_request(app: FastAPI) -> Request:
    scope = {"type": "http", "app": app, "method": "GET", "path": "/", "headers": []}
    return Request(scope)


def test_config_schema_creates_env_config_on_app_state():
    app = FastAPI()
    request = _make_request(app)

    config = config_schema(request)

    assert isinstance(config, EnvConfig)
    assert app.state.config is config


def test_config_schema_returns_cached_app_state_config():
    app = FastAPI()
    request = _make_request(app)

    config1 = config_schema(request)
    config2 = config_schema(request)

    assert config1 is config2


def test_get_config_returns_app_state_config():
    app = FastAPI()
    request = _make_request(app)
    expected = EnvConfig()
    app.state.config = expected

    assert get_config(request) is expected


def test_settings_schema_creates_service_settings_on_app_state():
    app = FastAPI()
    request = _make_request(app)
    config = EnvConfig()
    app.state.config = config

    settings = settings_schema(request)

    assert isinstance(settings, ServiceSettings)
    assert app.state.settings is settings


def test_settings_schema_creates_config_when_missing():
    app = FastAPI()
    request = _make_request(app)

    settings = settings_schema(request)

    assert isinstance(settings, ServiceSettings)
    assert isinstance(app.state.config, EnvConfig)
    assert app.state.settings is settings


def test_settings_schema_returns_cached_app_state_settings():
    app = FastAPI()
    request = _make_request(app)
    expected = ServiceSettings()
    app.state.settings = expected

    assert settings_schema(request) is expected


def test_get_settings_returns_app_state_settings():
    app = FastAPI()
    request = _make_request(app)
    expected = ServiceSettings()
    app.state.settings = expected

    assert get_settings(request) is expected


def test_get_settings_defaults():
    app = FastAPI()
    request = _make_request(app)

    settings = settings_schema(request)

    assert isinstance(settings.cors.origins, list)
    assert isinstance(settings.auth.verify_jwt, bool)
    assert isinstance(settings.health.check_keycloak, bool)
    assert isinstance(settings.health.check_database, bool)
    assert isinstance(settings.health.check_minio, bool)
