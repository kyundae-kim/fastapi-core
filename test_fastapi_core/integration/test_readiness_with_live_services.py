from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


@pytest.fixture
def keycloak_only_readiness_app(
    integration_app_config_factory,
    integration_app_factory,
    keycloak_integration_ready,
):
    del keycloak_integration_ready
    config = integration_app_config_factory(
        enabled_services=["keycloak"],
        required_services=["keycloak"],
    )
    return integration_app_factory(config, include_auth_router=False)


@pytest.fixture
def keycloak_and_nats_readiness_app(
    integration_app_config_factory,
    integration_app_factory,
    keycloak_integration_ready,
    nats_integration_ready,
):
    del keycloak_integration_ready
    del nats_integration_ready
    config = integration_app_config_factory(
        enabled_services=["keycloak", "nats"],
        required_services=["keycloak"],
    )
    return integration_app_factory(config, include_auth_router=False)


@pytest.fixture
def nats_required_readiness_app(
    integration_app_config_factory,
    integration_app_factory,
    nats_integration_ready,
):
    del nats_integration_ready
    config = integration_app_config_factory(
        enabled_services=["nats"],
        required_services=["nats"],
    )
    return integration_app_factory(config, include_auth_router=False)



def test_readiness_reports_keycloak_as_required_live_service(
    keycloak_only_readiness_app,
):
    with TestClient(keycloak_only_readiness_app) as client:
        response = client.get("/health/readiness")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "ok"
    assert body["details"]["keycloak"]["ok"] is True
    assert body["details"]["keycloak"]["required"] is True
    assert body["details"]["keycloak"]["enabled"] is True



def test_readiness_reports_optional_nats_service_when_enabled_live(
    keycloak_and_nats_readiness_app,
):
    with TestClient(keycloak_and_nats_readiness_app) as client:
        response = client.get("/health/readiness")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "ok"
    assert body["details"]["keycloak"]["required"] is True
    assert body["details"]["nats"]["required"] is False
    assert body["details"]["nats"]["enabled"] is True
    assert body["details"]["nats"]["ok"] is True



def test_readiness_reports_nats_as_required_live_service(nats_required_readiness_app):
    with TestClient(nats_required_readiness_app) as client:
        response = client.get("/health/readiness")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "ok"
    assert body["details"]["nats"]["ok"] is True
    assert body["details"]["nats"]["required"] is True
    assert body["details"]["nats"]["enabled"] is True



def test_readiness_can_report_degraded_when_optional_nats_target_is_unreachable(
    monkeypatch,
    integration_app_config_factory,
    integration_app_factory,
    keycloak_integration_ready,
):
    del keycloak_integration_ready
    original_servers = os.environ.get("NATS_SERVERS")
    if not original_servers:
        pytest.skip("nats integration env missing: NATS_SERVERS")

    monkeypatch.setenv("NATS_SERVERS", "nats://127.0.0.1:1")
    config = integration_app_config_factory(
        enabled_services=["keycloak", "nats"],
        required_services=["keycloak"],
    )
    app = integration_app_factory(config, include_auth_router=False)

    with TestClient(app) as client:
        response = client.get("/health/readiness")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "degraded"
    assert body["details"]["keycloak"]["required"] is True
    assert body["details"]["nats"]["required"] is False
    assert body["details"]["nats"]["ok"] is False
    assert body["details"]["nats"]["error"]
