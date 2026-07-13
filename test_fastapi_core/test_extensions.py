from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager

import pytest
from docmesh_py_core import HealthCheckError
from fastapi import Depends
from fastapi.testclient import TestClient

from fastapi_core import ManagedResource, create_app, register_readiness_check
from fastapi_core.config import AppConfig
from fastapi_core.dependencies import get_resource


def _empty_config(**overrides) -> AppConfig:
    return AppConfig(
        enabled_services=[],
        required_services=[],
        **overrides,
    )


def test_register_readiness_check_applies_optional_policy_and_redacts_error(settings):
    app = create_app(
        config=_empty_config(),
        settings=settings,
        include_auth_router=False,
    )

    def fail():
        raise RuntimeError("backend unavailable token=secret-token")

    register_readiness_check(app, "search", fail, required=False)

    with TestClient(app) as client:
        response = client.get("/health/readiness")

    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    assert response.json()["details"]["search"]["error"] == "readiness check failed"


def test_register_readiness_check_uses_app_timeout_as_fallback(settings):
    app = create_app(
        config=_empty_config(readiness_timeout_seconds=0.001),
        settings=settings,
        include_auth_router=False,
    )

    async def slow_check():
        await asyncio.sleep(0.05)

    register_readiness_check(app, "search", slow_check, required=True)

    with TestClient(app) as client:
        response = client.get("/health/readiness")

    assert response.status_code == 503
    assert response.json()["details"]["search"]["ok"] is False


def test_register_readiness_check_reports_explicit_timeout_when_not_redacted(
    settings,
):
    app = create_app(
        config=_empty_config(),
        settings=settings,
        include_auth_router=False,
    )

    async def slow_check():
        await asyncio.sleep(0.05)

    register_readiness_check(
        app,
        "search",
        slow_check,
        required=True,
        timeout_seconds=0.001,
        redact_errors=False,
    )

    with TestClient(app) as client:
        response = client.get("/health/readiness")

    assert response.status_code == 503
    assert response.json()["details"]["search"]["error"] == (
        "health check timed out"
    )


def test_register_readiness_check_rejects_duplicate_name(settings):
    app = create_app(
        config=_empty_config(),
        settings=settings,
        include_auth_router=False,
    )
    register_readiness_check(app, "search", lambda: None)

    with pytest.raises(ValueError, match="already registered"):
        register_readiness_check(app, "search", lambda: None)


def test_managed_resources_follow_lifecycle_order(settings):
    events: list[str] = []

    class Resource:
        def __init__(self, name: str):
            self.name = name

    def build(name: str):
        def factory(_app):
            events.append(f"create:{name}")
            return Resource(name)

        return factory

    def close(resource: Resource):
        events.append(f"close:{resource.name}")

    @asynccontextmanager
    async def lifespan(_app):
        events.append("custom:start")
        yield
        events.append("custom:stop")

    app = create_app(
        config=_empty_config(),
        settings=settings,
        lifespan=lifespan,
        include_auth_router=False,
        resources=[
            ManagedResource("first", factory=build("first"), close=close),
            ManagedResource("second", factory=build("second"), close=close),
        ],
    )

    with TestClient(app):
        assert events == ["create:first", "create:second", "custom:start"]

    assert events == [
        "create:first",
        "create:second",
        "custom:start",
        "custom:stop",
        "close:second",
        "close:first",
    ]


def test_get_resource_returns_lifecycle_managed_instance(settings):
    class Resource:
        value = "ready"

    app = create_app(
        config=_empty_config(),
        settings=settings,
        include_auth_router=False,
        resources=[ManagedResource("sdk", factory=lambda _app: Resource())],
    )

    @app.get("/resource")
    async def resource_endpoint(resource=Depends(get_resource("sdk"))):
        return {"value": resource.value}

    with TestClient(app) as client:
        response = client.get("/resource")

    assert response.status_code == 200
    assert response.json() == {"value": "ready"}


def test_get_resource_returns_503_when_resource_is_not_registered(settings):
    app = create_app(
        config=_empty_config(),
        settings=settings,
        include_auth_router=False,
    )

    @app.get("/resource")
    async def resource_endpoint(resource=Depends(get_resource("sdk"))):
        return {"resource": resource}

    with TestClient(app) as client:
        response = client.get("/resource")

    assert response.status_code == 503
    assert response.json()["detail"] == "Managed resource 'sdk' is not available"


def test_managed_resource_healthcheck_is_registered_for_readiness(settings):
    checks: list[str] = []

    class Resource:
        pass

    async def healthcheck(_resource: Resource):
        checks.append("checked")

    app = create_app(
        config=_empty_config(),
        settings=settings,
        include_auth_router=False,
        resources=[
            ManagedResource(
                "sdk",
                factory=lambda _app: Resource(),
                healthcheck=healthcheck,
                required=True,
            )
        ],
    )

    with TestClient(app) as client:
        response = client.get("/health/readiness")

    assert response.status_code == 200
    assert response.json()["details"]["sdk"]["required"] is True
    assert checks == ["checked"]


def test_managed_resource_sync_healthcheck_respects_timeout(settings):
    def slow_healthcheck(_resource: object):
        time.sleep(0.05)

    app = create_app(
        config=_empty_config(),
        settings=settings,
        include_auth_router=False,
        resources=[
            ManagedResource(
                "sdk",
                factory=lambda _app: object(),
                healthcheck=slow_healthcheck,
                readiness_timeout_seconds=0.001,
                required=True,
            )
        ],
    )

    with TestClient(app) as client:
        response = client.get("/health/readiness")

    assert response.status_code == 503


def test_managed_resource_rolls_back_when_later_factory_fails(settings):
    events: list[str] = []

    class Resource:
        def close(self):
            events.append("close:first")

    def first_factory(_app):
        events.append("create:first")
        return Resource()

    def failing_factory(_app):
        events.append("create:second")
        raise RuntimeError("second failed")

    app = create_app(
        config=_empty_config(),
        settings=settings,
        include_auth_router=False,
        resources=[
            ManagedResource("first", factory=first_factory),
            ManagedResource("second", factory=failing_factory),
        ],
    )

    with pytest.raises(RuntimeError, match="second failed"):
        with TestClient(app):
            pass

    assert events == ["create:first", "create:second", "close:first"]


def test_required_managed_resource_startup_check_failure_rolls_back(settings):
    events: list[str] = []

    class Resource:
        async def aclose(self):
            events.append("closed")

    def factory(_app):
        events.append("created")
        return Resource()

    async def healthcheck(_resource: Resource):
        events.append("checked")
        raise RuntimeError("not ready")

    app = create_app(
        config=_empty_config(startup_healthcheck=True),
        settings=settings,
        include_auth_router=False,
        resources=[
            ManagedResource(
                "sdk",
                factory=factory,
                healthcheck=healthcheck,
                required=True,
            )
        ],
    )

    with pytest.raises(HealthCheckError):
        with TestClient(app):
            pass

    assert events == ["created", "checked", "closed"]


@pytest.mark.parametrize("name", ["", "config", "readiness_checks"])
def test_managed_resource_rejects_invalid_or_reserved_name(settings, name):
    with pytest.raises(ValueError, match="resource name"):
        create_app(
            config=_empty_config(),
            settings=settings,
            include_auth_router=False,
            resources=[ManagedResource(name, factory=lambda _app: object())],
        )
