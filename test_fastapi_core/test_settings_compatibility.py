from __future__ import annotations

import pytest
from docmesh_py_core import ConfigError, Service, ServiceRuntime

import fastapi_core.runtime as runtime_module
from fastapi_core.config import AppConfig
from fastapi_core.docmesh_settings import load_docmesh_settings
from fastapi_core.factory import create_app
from fastapi_core.runtime import build_service_clients


def test_create_app_rejects_runtime_with_settings(settings):
    runtime = ServiceRuntime(
        configs=settings,
        clients={},
        selected_services=frozenset(),
    )

    with pytest.raises(ValueError, match="runtime and settings cannot be provided together"):
        create_app(runtime=runtime, settings=settings)


def test_create_app_warns_that_settings_injection_is_deprecated(settings):
    with pytest.deprecated_call(match="Pass a prebuilt ServiceRuntime via runtime instead"):
        create_app(settings=settings, include_auth_router=False)


def test_build_service_clients_resolves_factory_at_call_time(monkeypatch, settings):
    sentinel = object()
    monkeypatch.setattr(
        runtime_module,
        "create_sqlite_client",
        lambda _config: sentinel,
    )

    clients = build_service_clients(settings, ["sqlite"])

    assert clients == {Service.SQLITE: sentinel}


def test_create_app_validates_service_alternatives_for_injected_settings():
    settings = load_docmesh_settings(("sqlite",))
    config = AppConfig(
        enabled_services=["sqlite"],
        required_services=[],
        service_alternatives=[["minio", "milvus"]],
    )

    with pytest.raises(ConfigError, match="At least one service must be configured"):
        create_app(
            config=config,
            settings=settings,
            include_auth_router=False,
        )
