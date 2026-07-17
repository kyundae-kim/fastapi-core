from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager

import pytest
from docmesh_py_core import HealthCheckError, HealthCheckResult, ServiceHealthStatus
from fastapi import Depends
from fastapi.testclient import TestClient

from fastapi_core import ManagedResource, ResourceKey, register_readiness_check
from fastapi_core.dependencies import get_resource


def test_register_readiness_check_applies_optional_policy_and_redacts_error(empty_app_factory):
    app = empty_app_factory()

    def fail():
        raise RuntimeError("backend unavailable token=secret-token")

    register_readiness_check(app, "search", fail, required=False)

    with TestClient(app) as client:
        response = client.get("/health/readiness")

    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    assert response.json()["details"]["search"]["error"] == "readiness check failed"


def test_register_readiness_check_uses_app_timeout_as_fallback(empty_app_factory):
    app = empty_app_factory(readiness_timeout_seconds=0.001)

    async def slow_check():
        await asyncio.sleep(0.05)

    register_readiness_check(app, "search", slow_check, required=True)

    with TestClient(app) as client:
        response = client.get("/health/readiness")

    assert response.status_code == 503
    assert response.json()["details"]["search"]["ok"] is False


def test_register_readiness_check_reports_explicit_timeout_when_not_redacted(
    empty_app_factory,
):
    app = empty_app_factory()

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


def test_register_readiness_check_rejects_duplicate_name(empty_app_factory):
    app = empty_app_factory()
    register_readiness_check(app, "search", lambda: None)

    with pytest.raises(ValueError, match="already registered"):
        register_readiness_check(app, "search", lambda: None)


def test_managed_resources_follow_lifecycle_order(empty_app_factory):
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

    app = empty_app_factory(
        lifespan=lifespan,
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


def test_get_resource_returns_lifecycle_managed_instance(empty_app_factory):
    class Resource:
        value = "ready"

    app = empty_app_factory(
        resources=[ManagedResource("sdk", factory=lambda _app: Resource())],
    )

    @app.get("/resource")
    async def resource_endpoint(resource=Depends(get_resource("sdk"))):
        return {"value": resource.value}

    with TestClient(app) as client:
        response = client.get("/resource")

    assert response.status_code == 200
    assert response.json() == {"value": "ready"}


def test_get_resource_returns_503_when_resource_is_not_registered(empty_app_factory):
    app = empty_app_factory()

    @app.get("/resource")
    async def resource_endpoint(resource=Depends(get_resource("sdk"))):
        return {"resource": resource}

    with TestClient(app) as client:
        response = client.get("/resource")

    assert response.status_code == 503
    assert response.json()["detail"] == "Managed resource 'sdk' is not available"


def test_resource_key_is_shared_by_registration_and_typed_dependency(empty_app_factory):
    class Resource:
        value = "ready"

    resource_key = ResourceKey[Resource]("sdk")
    app = empty_app_factory(
        resources=[ManagedResource(resource_key, factory=lambda _app: Resource())],
    )

    @app.get("/typed-resource")
    async def resource_endpoint(resource: Resource = Depends(resource_key.dependency)):
        return {"value": resource.value}

    with TestClient(app) as client:
        response = client.get("/typed-resource")

    assert response.status_code == 200
    assert response.json() == {"value": "ready"}


def test_managed_resource_healthcheck_is_registered_for_readiness(empty_app_factory):
    checks: list[str] = []

    class Resource:
        pass

    async def healthcheck(_resource: Resource):
        checks.append("checked")

    app = empty_app_factory(
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


def test_required_managed_resource_false_healthcheck_fails_readiness(empty_app_factory):
    app = empty_app_factory(
        resources=[
            ManagedResource(
                "sdk",
                factory=lambda _app: object(),
                healthcheck=lambda _resource: False,
                required=True,
            )
        ],
    )

    with TestClient(app) as client:
        response = client.get("/health/readiness")

    assert response.status_code == 503
    assert response.json()["status"] == "error"
    assert response.json()["details"]["sdk"]["ok"] is False


def test_managed_resource_structured_healthcheck_preserves_namespaced_details(
    empty_app_factory,
):
    result = HealthCheckResult(
        ok=False,
        services=[
            ServiceHealthStatus(
                service="postgres",
                ok=False,
                latency_ms=7,
                error="password=database-secret",
            ),
            ServiceHealthStatus(service="minio", ok=True, latency_ms=11),
        ],
    )
    app = empty_app_factory(
        resources=[
            ManagedResource(
                "dms",
                factory=lambda _app: object(),
                healthcheck=lambda _resource: result,
                required=True,
            )
        ],
    )

    with TestClient(app) as client:
        response = client.get("/health/readiness")

    assert response.status_code == 503
    assert response.json() == {
        "status": "error",
        "details": {
            "dms.postgres": {
                "ok": False,
                "latency_ms": 7,
                "error": "readiness check failed",
                "required": True,
                "enabled": True,
            },
            "dms.minio": {
                "ok": True,
                "latency_ms": 11,
                "error": None,
                "required": True,
                "enabled": True,
            },
        },
    }


def test_managed_resource_sync_healthcheck_respects_timeout(empty_app_factory):
    def slow_healthcheck(_resource: object):
        time.sleep(0.05)

    app = empty_app_factory(
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


def test_managed_resource_rolls_back_when_later_factory_fails(empty_app_factory):
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

    app = empty_app_factory(
        resources=[
            ManagedResource("first", factory=first_factory),
            ManagedResource("second", factory=failing_factory),
        ],
    )

    with pytest.raises(RuntimeError, match="second failed"):
        with TestClient(app):
            pass

    assert events == ["create:first", "create:second", "close:first"]


def test_required_managed_resource_startup_check_failure_rolls_back(empty_app_factory):
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

    app = empty_app_factory(
        startup_healthcheck=True,
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


@pytest.mark.parametrize("name", ["", "config", "readiness_registry"])
def test_managed_resource_rejects_invalid_or_reserved_name(empty_app_factory, name):
    with pytest.raises(ValueError, match="resource name"):
        empty_app_factory(
            resources=[ManagedResource(name, factory=lambda _app: object())],
        )
