from __future__ import annotations

from contextlib import asynccontextmanager

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


@pytest.fixture
def nats_only_lifespan_app(
    integration_app_config_factory,
    integration_app_factory,
    nats_integration_ready,
):
    del nats_integration_ready
    events: list[str] = []

    @asynccontextmanager
    async def lifespan(app):
        app.state.nats_probe = {"connected": True}
        events.append("startup")
        yield
        events.append("shutdown")
        app.state.nats_probe = None

    config = integration_app_config_factory(
        enabled_services=["nats"],
        required_services=["nats"],
    )
    app = integration_app_factory(
        config,
        include_auth_router=False,
        lifespan=lifespan,
    )
    return app, events



def test_custom_lifespan_runs_with_live_nats_service_clients(nats_only_lifespan_app):
    app, events = nats_only_lifespan_app

    with TestClient(app):
        assert app.state.nats_probe == {"connected": True}
        assert events == ["startup"]
        assert "nats" in app.state.service_clients

    assert events == ["startup", "shutdown"]
    assert app.state.nats_probe is None



def test_live_nats_app_can_serve_readiness_during_lifespan(nats_only_lifespan_app):
    app, events = nats_only_lifespan_app

    with TestClient(app) as client:
        response = client.get("/health/readiness")
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["status"] == "ok"
        assert body["details"]["nats"]["ok"] is True
        assert body["details"]["nats"]["required"] is True
        assert app.state.nats_probe == {"connected": True}
        assert events == ["startup"]

    assert events == ["startup", "shutdown"]
