"""Keycloak 연동 통합 테스트 — get_auth_provider, get_current_user, require_permissions."""
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from fastapi_core.core.auth import KeycloakAuthProvider
from fastapi_core.core.config import AuthSettings, EnvConfig, ServiceSettings
from fastapi_core.dependencies.auth import (
    get_auth_provider,
    get_current_user,
    require_permissions,
    set_auth_provider,
)
from fastapi_core.dependencies.config import settings_schema
from fastapi_core.schemas.user import UserInfo


@pytest.fixture(scope="module")
def config() -> EnvConfig:
    return EnvConfig()


@pytest.fixture(scope="module")
def provider(config: EnvConfig) -> KeycloakAuthProvider:
    return KeycloakAuthProvider(
        http_url=str(config.keycloak.http_url),
        realm=config.keycloak.realm,
        client_id=config.keycloak.client_id,
        client_secret=config.keycloak.client_secret,
    )


@pytest.fixture(scope="module")
def access_token(provider: KeycloakAuthProvider, config: EnvConfig) -> str:
    result = provider.authenticate(config.keycloak_username, config.keycloak_password)
    return result["access_token"]


@pytest.fixture(scope="module")
def app(config: EnvConfig) -> FastAPI:
    _app = FastAPI()
    set_auth_provider(_app, config=config)
    _app.dependency_overrides[settings_schema] = lambda: ServiceSettings(
        auth=AuthSettings(verify_jwt=True)
    )

    @_app.get("/me")
    def me(user: UserInfo = Depends(get_current_user)):
        return user.model_dump()

    @_app.get("/admin")
    def admin(user: UserInfo = Depends(require_permissions("nonexistent_role"))):
        return user.model_dump()

    return _app


# ---------------------------------------------------------------------------
# get_auth_provider — 실제 state 싱글톤 검증
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_get_auth_provider_from_state_integration(
    provider: KeycloakAuthProvider,
):
    """실제 KeycloakAuthProvider를 app.state에 등록하면 get_auth_provider가 동일 인스턴스를 반환한다."""
    _app = FastAPI()
    set_auth_provider(_app, provider)

    @_app.get("/provider-id")
    def provider_id(p: KeycloakAuthProvider = Depends(get_auth_provider)):
        return {"id": id(p)}

    client = TestClient(_app)
    response = client.get("/provider-id")
    assert response.status_code == 200
    assert response.json()["id"] == id(provider)


# ---------------------------------------------------------------------------
# get_current_user — 실제 Keycloak 토큰으로 RS256 검증
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_get_current_user_with_real_token(
    app: FastAPI, access_token: str, config: EnvConfig
):
    """실제 Keycloak 토큰으로 RS256 서명 검증을 통해 UserInfo를 반환한다."""
    client = TestClient(app)
    response = client.get("/me", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    body = response.json()
    assert body["username"] == config.keycloak_username
    assert body["sub"]


@pytest.mark.integration
def test_get_current_user_missing_token_integration(app: FastAPI):
    """토큰 없이 요청하면 401을 반환한다."""
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/me")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# require_permissions — 역할 미보유 시 403
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_require_permissions_forbidden_integration(app: FastAPI, access_token: str):
    """실제 토큰이지만 필요 역할을 보유하지 않은 경우 403을 반환한다."""
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get(
        "/admin", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 403
