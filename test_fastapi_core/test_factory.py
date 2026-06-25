from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi.testclient import TestClient

from fastapi_core.factory import create_app



def test_create_app_includes_default_routes(settings):
    app = create_app(settings=settings)

    with TestClient(app) as client:
        response = client.get("/health/liveness")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "details": None}
    assert any(route.path == "/token" for route in app.router.routes)
    assert any(route.path == "/user" for route in app.router.routes)
    assert app.state.settings is settings



def test_create_app_can_exclude_auth_router(settings):
    app = create_app(settings=settings, include_auth_router=False)

    with TestClient(app) as client:
        liveness_response = client.get("/health/liveness")
        user_response = client.get("/user")
        token_response = client.post("/token")

    assert liveness_response.status_code == 200
    assert user_response.status_code == 404
    assert token_response.status_code == 404



def test_create_app_runs_custom_lifespan(settings):
    events: list[str] = []

    @asynccontextmanager
    async def lifespan(app):
        app.state.started_by_lifespan = True
        events.append("startup")
        yield
        events.append("shutdown")

    app = create_app(settings=settings, lifespan=lifespan)

    with TestClient(app):
        assert app.state.started_by_lifespan is True
        assert events == ["startup"]

    assert events == ["startup", "shutdown"]
