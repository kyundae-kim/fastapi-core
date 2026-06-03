from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from fastapi_core.core.config import AuthSettings, ServiceSettings
from fastapi_core.dependencies.config import settings_schema
from fastapi_core.dependencies.auth import get_auth_provider, get_current_user
from fastapi_core.routers.auth import router
from fastapi_core.schemas.user import UserInfo


@pytest.fixture
def mock_provider():
    return MagicMock()


@pytest.fixture
def app(mock_provider):
    _app = FastAPI()
    _app.include_router(router)
    _app.dependency_overrides[get_auth_provider] = lambda: mock_provider
    _app.dependency_overrides[settings_schema] = lambda: ServiceSettings(
        auth=AuthSettings(verify_jwt=False)
    )
    return _app


# ---------------------------------------------------------------------------
# POST /token
# ---------------------------------------------------------------------------


def test_token_success(app, mock_provider):
    mock_provider.authenticate.return_value = {
        "access_token": "tok",
        "refresh_token": "ref",
        "token_type": "bearer",
    }
    client = TestClient(app)
    response = client.post(
        "/token", data={"username": "user", "password": "pass"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"] == "tok"
    assert body["refresh_token"] == "ref"
    assert body["token_type"] == "bearer"


def test_token_auth_failure(app, mock_provider):
    import httpx

    mock_provider.authenticate.side_effect = httpx.HTTPStatusError(
        "401 Unauthorized", request=MagicMock(), response=MagicMock()
    )
    client = TestClient(app, raise_server_exceptions=False)
    response = client.post(
        "/token", data={"username": "user", "password": "wrong"}
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /user
# ---------------------------------------------------------------------------


def test_user_endpoint(app, mock_provider):
    expected_user = UserInfo(sub="u-1", username="alice", email="alice@example.com")
    mock_provider.decode_token_insecure.return_value = {"sub": "u-1"}
    mock_provider.to_user.return_value = expected_user

    client = TestClient(app)
    response = client.get("/user", headers={"Authorization": "Bearer fake_token"})
    assert response.status_code == 200
    assert response.json()["username"] == "alice"


def test_user_endpoint_unauthorized(app, mock_provider):
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/user")
    assert response.status_code == 401


def test_user_endpoint_invalid_token(app, mock_provider):
    mock_provider.decode_token_insecure.side_effect = ValueError("bad token")
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/user", headers={"Authorization": "Bearer bad"})
    assert response.status_code == 401
