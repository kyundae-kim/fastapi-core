from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from fastapi_core.core.config import EnvConfig, HealthSettings, LifecycleSettings, ServiceSettings
from fastapi_core.dependencies.config import get_config, get_settings
from fastapi_core.factory import create_app


@pytest.fixture
def client():
    app = create_app(include_auth_router=False)
    app.dependency_overrides[get_config] = lambda: EnvConfig()
    app.dependency_overrides[get_settings] = lambda: ServiceSettings(
        health=HealthSettings(
            check_keycloak=True,
            check_database=True,
            check_minio=True,
            check_langfuse=False,
        )
    )
    return TestClient(app)


# ---------------------------------------------------------------------------
# Liveness
# ---------------------------------------------------------------------------


def test_liveness(client):
    response = client.get("/health/liveness")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# Readiness
# ---------------------------------------------------------------------------


def test_readiness_ok(client):
    mock_response = MagicMock()
    mock_response.status_code = 200

    with (
        patch("fastapi_core.routers.health.httpx.AsyncClient") as mock_cls,
        patch(
            "fastapi_core.routers.health.check_database_connection",
            return_value=True,
        ),
        patch("fastapi_core.routers.health.check_minio_connection", return_value=True),
    ):
        mock_ctx = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_ctx.get = AsyncMock(return_value=mock_response)

        response = client.get("/health/readiness")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_readiness_keycloak_not_ready(client):
    mock_response = MagicMock()
    mock_response.status_code = 503

    with (
        patch("fastapi_core.routers.health.httpx.AsyncClient") as mock_cls,
        patch(
            "fastapi_core.routers.health.check_database_connection",
            return_value=True,
        ),
        patch("fastapi_core.routers.health.check_minio_connection", return_value=True),
    ):
        mock_ctx = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_ctx.get = AsyncMock(return_value=mock_response)

        response = client.get("/health/readiness")

    assert response.status_code == 503


def test_readiness_keycloak_unreachable(client):
    with (
        patch("fastapi_core.routers.health.httpx.AsyncClient") as mock_cls,
        patch(
            "fastapi_core.routers.health.check_database_connection",
            return_value=True,
        ),
        patch("fastapi_core.routers.health.check_minio_connection", return_value=True),
    ):
        mock_ctx = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_ctx.get = AsyncMock(
            side_effect=httpx.RequestError("connection refused")
        )

        response = client.get("/health/readiness")

    assert response.status_code == 503


def test_readiness_database_not_ready(client):
    mock_response = MagicMock()
    mock_response.status_code = 200

    with (
        patch("fastapi_core.routers.health.httpx.AsyncClient") as mock_cls,
        patch(
            "fastapi_core.routers.health.check_database_connection",
            return_value=False,
        ),
        patch("fastapi_core.routers.health.check_minio_connection", return_value=True),
    ):
        mock_ctx = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_ctx.get = AsyncMock(return_value=mock_response)

        response = client.get("/health/readiness")

    assert response.status_code == 503
    assert response.json()["detail"] == "Database not ready"


def test_readiness_minio_not_ready(client):
    mock_response = MagicMock()
    mock_response.status_code = 200

    with (
        patch("fastapi_core.routers.health.httpx.AsyncClient") as mock_cls,
        patch(
            "fastapi_core.routers.health.check_database_connection",
            return_value=True,
        ),
        patch("fastapi_core.routers.health.check_minio_connection", return_value=False),
    ):
        mock_ctx = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_ctx.get = AsyncMock(return_value=mock_response)

        response = client.get("/health/readiness")

    assert response.status_code == 503
    assert response.json()["detail"] == "MinIO not ready"


def test_readiness_langfuse_not_ready():
    app = create_app(include_auth_router=False)
    app.dependency_overrides[get_config] = lambda: EnvConfig()
    app.dependency_overrides[get_settings] = lambda: ServiceSettings(
        health=HealthSettings(
            check_keycloak=True,
            check_database=True,
            check_minio=True,
            check_langfuse=True,
        )
    )
    client = TestClient(app)
    mock_response = MagicMock()
    mock_response.status_code = 200

    with (
        patch("fastapi_core.routers.health.httpx.AsyncClient") as mock_cls,
        patch(
            "fastapi_core.routers.health.check_database_connection",
            return_value=True,
        ),
        patch("fastapi_core.routers.health.check_minio_connection", return_value=True),
        patch("fastapi_core.routers.health.check_langfuse_connection", return_value=False),
    ):
        mock_ctx = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_ctx.get = AsyncMock(return_value=mock_response)

        response = client.get("/health/readiness")

    assert response.status_code == 503
    assert response.json()["detail"] == "Langfuse not ready"


def test_readiness_uses_docmesh_healthchecks_when_enabled():
    app = create_app(include_auth_router=False)
    app.dependency_overrides[get_config] = lambda: EnvConfig()
    app.dependency_overrides[get_settings] = lambda: ServiceSettings(
        health=HealthSettings(
            check_keycloak=False,
            check_database=True,
            check_minio=True,
            check_langfuse=False,
        ),
        lifecycle=LifecycleSettings(use_docmesh_healthchecks=True),
    )
    client = TestClient(app)

    with (
        patch(
            "fastapi_core.routers.health.run_docmesh_healthchecks",
            return_value=True,
        ) as mock_run_docmesh_healthchecks,
        patch(
            "fastapi_core.routers.health.check_database_connection",
            side_effect=AssertionError("native database readiness should not run"),
        ),
        patch(
            "fastapi_core.routers.health.check_minio_connection",
            side_effect=AssertionError("native minio readiness should not run"),
        ),
    ):
        response = client.get("/health/readiness")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    service_checks = mock_run_docmesh_healthchecks.call_args.args[0]
    required_services = mock_run_docmesh_healthchecks.call_args.kwargs["required_services"]
    assert set(service_checks) == {"database", "minio"}
    assert required_services == {"database", "minio"}


def test_readiness_skips_database_dependency_when_check_disabled():
    app = create_app(include_auth_router=False)
    app.dependency_overrides[get_config] = lambda: EnvConfig()
    app.dependency_overrides[get_settings] = lambda: ServiceSettings(
        health=HealthSettings(
            check_keycloak=False,
            check_database=False,
            check_minio=False,
            check_langfuse=False,
        )
    )
    client = TestClient(app)

    with patch(
        "fastapi_core.dependencies.database.create_db_engine",
        side_effect=AssertionError("database engine should not be created"),
    ):
        response = client.get("/health/readiness")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_skips_minio_dependency_when_check_disabled():
    app = create_app(include_auth_router=False)
    app.dependency_overrides[get_config] = lambda: EnvConfig()
    app.dependency_overrides[get_settings] = lambda: ServiceSettings(
        health=HealthSettings(
            check_keycloak=False,
            check_database=False,
            check_minio=False,
            check_langfuse=False,
        )
    )
    client = TestClient(app)

    with patch(
        "fastapi_core.dependencies.storage.create_minio_client",
        side_effect=AssertionError("minio client should not be created"),
    ):
        response = client.get("/health/readiness")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
