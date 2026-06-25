from __future__ import annotations

from fastapi.testclient import TestClient

from fastapi_core.factory import create_app



def test_readiness_returns_ok_when_checks_pass(settings):
    app = create_app(settings=settings, include_auth_router=False)
    app.state.readiness_checks = {
        "keycloak": lambda: None,
        "nats": lambda: None,
    }
    app.state.required_services = {"keycloak"}

    with TestClient(app) as client:
        response = client.get("/health/readiness")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["details"]["keycloak"]["ok"] is True
    assert body["details"]["nats"]["ok"] is True



def test_readiness_returns_503_when_required_check_fails(settings):
    app = create_app(settings=settings, include_auth_router=False)

    def fail_check():
        raise RuntimeError("keycloak unavailable")

    app.state.readiness_checks = {"keycloak": fail_check}
    app.state.required_services = {"keycloak"}

    with TestClient(app) as client:
        response = client.get("/health/readiness")

    assert response.status_code == 503
    assert response.json()["status"] == "error"
    assert response.json()["details"]["keycloak"]
