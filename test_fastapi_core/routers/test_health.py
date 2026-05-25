from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from fastapi_core.core.config import EnvConfig, HealthSettings, ServiceSettings
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
