from __future__ import annotations

from contextlib import asynccontextmanager
import json
import logging

from fastapi.testclient import TestClient

from fastapi_core.config import AppConfig
from fastapi_core.docmesh_settings import load_docmesh_settings
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
    assert app.state.config.token_url.endswith("token")
    assert app.state.registry is not None
    assert app.state.root_logger is not None
    assert sorted(app.state.readiness_checks) == ["keycloak"]
    assert app.state.readiness_services == {
        "keycloak": {"enabled": True, "required": True},
    }
    assert app.state.required_services == {"keycloak"}


def test_create_app_applies_configured_token_url_to_openapi(settings):
    config = AppConfig(token_url="/api/v1/auth/token")

    app = create_app(config=config, settings=settings)

    security_scheme = app.openapi()["components"]["securitySchemes"]["OAuth2PasswordBearer"]
    assert security_scheme["flows"]["password"]["tokenUrl"] == "/api/v1/auth/token"


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


def test_create_app_uses_selected_services_for_readiness_and_settings():
    config = AppConfig(
        enabled_services=["sqlite"],
        required_services=["sqlite"],
    )

    settings = load_docmesh_settings(("sqlite",))
    app = create_app(config=config, settings=settings, include_auth_router=False)

    assert app.state.settings.sqlite is not None
    assert app.state.settings.keycloak is None
    assert sorted(app.state.readiness_checks) == ["sqlite"]
    assert app.state.readiness_services == {
        "sqlite": {"enabled": True, "required": True},
    }
    assert app.state.required_services == {"sqlite"}


def test_create_app_configures_json_logging_to_file(tmp_path):
    log_path = tmp_path / "app.log"
    config = AppConfig(
        log_level="WARNING",
        log_path=str(log_path),
        log_force=True,
        enabled_services=["sqlite"],
        required_services=["sqlite"],
    )
    settings = load_docmesh_settings(("sqlite",))

    app = create_app(config=config, settings=settings, include_auth_router=False)
    logger = logging.getLogger("fastapi_core.test")
    logger.warning("structured-log", extra={"event": {"service": "sqlite", "outcome": "ok"}})

    for handler in app.state.root_logger.handlers:
        handler.flush()

    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert lines
    payload = json.loads(lines[-1])
    assert payload["message"] == "structured-log"
    assert payload["level"] == "WARNING"
    assert payload["logger"] == "fastapi_core.test"
    assert payload["event"] == {"service": "sqlite", "outcome": "ok"}
