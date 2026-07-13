from __future__ import annotations

import asyncio
import json
import logging

import pytest
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from fastapi_core.factory import create_app
from fastapi_core.routers.health import readiness


def test_readiness_returns_ok_when_checks_pass(settings, caplog):
    app = create_app(settings=settings, include_auth_router=False)
    app.state.readiness_checks = {
        "keycloak": lambda: None,
        "nats": lambda: None,
    }
    app.state.readiness_services = {
        "keycloak": {"required": True, "enabled": True},
        "nats": {"required": False, "enabled": True},
    }
    app.state.required_services = {"keycloak"}

    with caplog.at_level(logging.WARNING):
        with TestClient(app) as client:
            response = client.get("/health/readiness")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["details"]["keycloak"]["ok"] is True
    assert body["details"]["keycloak"]["required"] is True
    assert body["details"]["nats"]["ok"] is True
    assert body["details"]["nats"]["required"] is False
    assert [record.getMessage() for record in caplog.records] == []


def test_readiness_returns_degraded_when_optional_check_fails(settings, caplog):
    app = create_app(settings=settings, include_auth_router=False)

    def fail_optional():
        raise RuntimeError("nats unavailable token=secret-token")

    app.state.readiness_checks = {
        "keycloak": lambda: None,
        "nats": fail_optional,
    }
    app.state.readiness_services = {
        "keycloak": {"required": True, "enabled": True},
        "nats": {"required": False, "enabled": True},
    }
    app.state.required_services = {"keycloak"}

    with caplog.at_level(logging.WARNING):
        with TestClient(app) as client:
            response = client.get("/health/readiness")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["details"]["keycloak"]["ok"] is True
    assert body["details"]["nats"]["ok"] is False
    assert body["details"]["nats"]["required"] is False
    assert body["details"]["nats"]["error"]

    records = [record for record in caplog.records if record.getMessage() == "readiness_check_failed"]
    assert len(records) == 1
    record = records[0]
    assert record.getMessage() == "readiness_check_failed"
    assert record.event["service"] == "nats"
    assert record.event["operation"] == "readiness_check"
    assert record.event["outcome"] == "degraded"
    assert record.event["required"] is False
    assert record.event["enabled"] is True
    assert "secret-token" not in record.event["error"]


def test_readiness_preserves_legacy_in_place_state_override(settings):
    app = create_app(settings=settings, include_auth_router=False)

    def fail_optional():
        raise RuntimeError("nats unavailable")

    app.state.readiness_checks.clear()
    app.state.readiness_checks["nats"] = fail_optional
    app.state.readiness_services.clear()
    app.state.readiness_services["nats"] = {
        "required": False,
        "enabled": True,
    }
    app.state.required_services.clear()

    with TestClient(app) as client:
        response = client.get("/health/readiness")

    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    assert response.json()["details"]["nats"]["ok"] is False


def test_readiness_returns_503_when_required_check_fails(settings, caplog):
    app = create_app(settings=settings, include_auth_router=False)

    def fail_check():
        raise RuntimeError("keycloak unavailable token=top-secret")

    app.state.readiness_checks = {"keycloak": fail_check}
    app.state.readiness_services = {
        "keycloak": {"required": True, "enabled": True},
    }
    app.state.required_services = {"keycloak"}

    with caplog.at_level(logging.WARNING):
        with TestClient(app) as client:
            response = client.get("/health/readiness")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "error"
    assert body["details"]["keycloak"]["required"] is True
    assert body["details"]["keycloak"]["ok"] is False
    assert body["details"]["keycloak"]["error"]

    records = [record for record in caplog.records if record.getMessage() == "readiness_check_failed"]
    assert len(records) == 1
    record = records[0]
    assert record.getMessage() == "readiness_check_failed"
    assert record.event["service"] == "keycloak"
    assert record.event["operation"] == "readiness_check"
    assert record.event["outcome"] == "error"
    assert record.event["required"] is True
    assert record.event["enabled"] is True
    assert "top-secret" not in record.event["error"]


def test_readiness_preserves_all_service_results_when_required_check_fails(settings):
    app = create_app(settings=settings, include_auth_router=False)

    def fail_required():
        raise RuntimeError("keycloak unavailable")

    app.state.readiness_checks = {
        "keycloak": fail_required,
        "nats": lambda: None,
    }
    app.state.readiness_services = {
        "keycloak": {"required": True, "enabled": True},
        "nats": {"required": False, "enabled": True},
    }
    app.state.required_services = {"keycloak"}

    with TestClient(app) as client:
        response = client.get("/health/readiness")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "error"
    assert body["details"]["keycloak"]["ok"] is False
    assert body["details"]["nats"]["ok"] is True


@pytest.mark.asyncio
async def test_readiness_applies_per_service_timeout(settings):
    app = create_app(settings=settings, include_auth_router=False)

    async def slow_check():
        await asyncio.sleep(0.05)

    app.state.readiness_checks = {"keycloak": slow_check}
    app.state.readiness_services = {
        "keycloak": {"required": True, "enabled": True},
    }
    app.state.required_services = {"keycloak"}
    app.state.readiness_timeout_seconds = 0.001
    request = Request({"type": "http", "app": app})

    response = await readiness(request)

    assert isinstance(response, JSONResponse)
    assert response.status_code == 503
    body = json.loads(response.body)
    assert body["status"] == "error"
    assert body["details"]["keycloak"]["ok"] is False
    assert body["details"]["keycloak"]["error"]


@pytest.mark.asyncio
async def test_readiness_returns_503_on_overall_timeout(settings):
    app = create_app(settings=settings, include_auth_router=False)

    async def slow_check():
        await asyncio.sleep(0.05)

    app.state.readiness_checks = {"keycloak": slow_check}
    app.state.readiness_services = {
        "keycloak": {"required": True, "enabled": True},
    }
    app.state.required_services = {"keycloak"}
    app.state.readiness_overall_timeout_seconds = 0.001
    request = Request({"type": "http", "app": app})

    response = await readiness(request)

    assert isinstance(response, JSONResponse)
    assert response.status_code == 503
    assert json.loads(response.body) == {"status": "error", "details": None}
