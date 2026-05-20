import jwt
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from fastapi_core.core.config import AuthSettings, ServiceSettings
from fastapi_core.core.security import KeycloakAuthProvider
from fastapi_core.dependencies.config import get_settings
from fastapi_core.dependencies.security import (
    get_auth_provider,
    get_current_user,
    require_permissions,
)
from fastapi_core.schemas.user import UserInfo


def _make_app() -> tuple[FastAPI, dict]:
    """Returns (app, overrides_dict) for per-test dependency overrides."""
    app = FastAPI()
    overrides: dict = {}

    @app.get("/me")
    def me(user: UserInfo = pytest.param) -> dict:  # type: ignore[assignment]
        ...

    # re-define properly
    app.routes.clear()

    @app.get("/me")
    def me(user: UserInfo = __import__("fastapi").Depends(get_current_user)):  # noqa: F811
        return user.model_dump()

    @app.get("/admin")
    def admin(user: UserInfo = __import__("fastapi").Depends(require_permissions("admin"))):
        return user.model_dump()

    return app, overrides


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_provider() -> KeycloakAuthProvider:
    from unittest.mock import MagicMock

    provider = MagicMock(spec=KeycloakAuthProvider)
    return provider


@pytest.fixture
def insecure_settings() -> ServiceSettings:
    settings = ServiceSettings()
    settings.auth = AuthSettings(verify_jwt=False)
    return settings


@pytest.fixture
def test_app(mock_provider: KeycloakAuthProvider, insecure_settings: ServiceSettings):
    from fastapi import Depends, FastAPI

    app = FastAPI()

    @app.get("/me")
    def me(user: UserInfo = Depends(get_current_user)):
        return user.model_dump()

    @app.get("/admin")
    def admin(user: UserInfo = Depends(require_permissions("admin"))):
        return user.model_dump()

    app.dependency_overrides[get_auth_provider] = lambda: mock_provider
    app.dependency_overrides[get_settings] = lambda: insecure_settings
    return app


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_get_current_user_missing_token(test_app, mock_provider, insecure_settings):
    client = TestClient(test_app, raise_server_exceptions=False)
    response = client.get("/me")
    assert response.status_code == 401


def test_get_current_user_invalid_token(test_app, mock_provider, insecure_settings):
    mock_provider.decode_token_insecure.side_effect = ValueError("bad token")
    client = TestClient(test_app, raise_server_exceptions=False)
    response = client.get("/me", headers={"Authorization": "Bearer invalid"})
    assert response.status_code == 401


def test_get_current_user_valid(test_app, mock_provider):
    expected_user = UserInfo(sub="u-1", username="alice", roles=["admin"])
    mock_provider.decode_token_insecure.return_value = {"sub": "u-1"}
    mock_provider.to_user.return_value = expected_user

    token = jwt.encode({"sub": "u-1"}, "s", algorithm="HS256")
    client = TestClient(test_app)
    response = client.get("/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["username"] == "alice"


def test_require_permissions_allowed(test_app, mock_provider):
    expected_user = UserInfo(sub="u-1", username="alice", roles=["admin"])
    mock_provider.decode_token_insecure.return_value = {"sub": "u-1"}
    mock_provider.to_user.return_value = expected_user

    token = jwt.encode({"sub": "u-1"}, "s", algorithm="HS256")
    client = TestClient(test_app)
    response = client.get("/admin", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200


def test_require_permissions_forbidden(test_app, mock_provider):
    expected_user = UserInfo(sub="u-1", username="alice", roles=["viewer"])
    mock_provider.decode_token_insecure.return_value = {"sub": "u-1"}
    mock_provider.to_user.return_value = expected_user

    token = jwt.encode({"sub": "u-1"}, "s", algorithm="HS256")
    client = TestClient(test_app, raise_server_exceptions=False)
    response = client.get("/admin", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403
