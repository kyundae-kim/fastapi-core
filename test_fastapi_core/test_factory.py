from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from fastapi_core.core.config import EnvConfig, ServiceSettings
from fastapi_core.factory import create_app


def test_create_app_registers_config_and_settings_on_app_state():
    config = EnvConfig()
    settings = ServiceSettings()

    app = create_app(config=config, settings=settings, include_auth_router=False)

    assert app.state.config is config
    assert app.state.settings is settings


def test_create_app_uses_managed_lifespan_by_default():
    config = EnvConfig()
    settings = ServiceSettings()
    calls: list[str] = []

    @asynccontextmanager
    async def fake_lifespan(app: FastAPI):
        calls.append("startup")
        yield
        calls.append("shutdown")

    with patch("fastapi_core.factory.create_managed_lifespan", return_value=fake_lifespan) as mock_create_managed_lifespan:
        app = create_app(config=config, settings=settings, include_auth_router=False)
        with TestClient(app):
            pass

    mock_create_managed_lifespan.assert_called_once_with(config, settings)
    assert calls == ["startup", "shutdown"]


def test_create_app_preserves_custom_lifespan():
    config = EnvConfig()
    settings = ServiceSettings()
    calls: list[str] = []

    @asynccontextmanager
    async def custom_lifespan(app: FastAPI):
        calls.append("custom-startup")
        yield
        calls.append("custom-shutdown")

    with patch("fastapi_core.factory.create_managed_lifespan") as mock_create_managed_lifespan:
        app = create_app(
            config=config,
            settings=settings,
            include_auth_router=False,
            lifespan=custom_lifespan,
        )
        with TestClient(app):
            pass

    mock_create_managed_lifespan.assert_not_called()
    assert calls == ["custom-startup", "custom-shutdown"]
