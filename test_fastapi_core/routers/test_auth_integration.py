"""/token, /user 라우터 Keycloak 연동 통합 테스트 — 실제 Keycloak 인스턴스 필요."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from fastapi_core.core.config import AuthSettings, EnvConfig, ServiceSettings
from fastapi_core.dependencies.auth import set_auth_provider
from fastapi_core.dependencies.config import get_settings
from fastapi_core.routers.auth import router


@pytest.fixture(scope="module")
def config() -> EnvConfig:
    return EnvConfig()


@pytest.fixture(scope="module")
def app(config: EnvConfig) -> FastAPI:
    _app = FastAPI()
    _app.include_router(router)
    set_auth_provider(_app, config=config)
    # RS256 서명 검증 활성화
    _app.dependency_overrides[get_settings] = lambda: ServiceSettings(
        auth=AuthSettings(verify_jwt=True)
    )
    return _app


# ---------------------------------------------------------------------------
# POST /token — 실제 토큰 발급
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_token_integration(app: FastAPI, config: EnvConfig):
    """/token 엔드포인트에서 실제 Keycloak 액세스 토큰이 발급된다."""
    client = TestClient(app)
    response = client.post(
        "/token",
        data={
            "username": config.keycloak_username,
            "password": config.keycloak_password,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert body["access_token"]
    assert body["token_type"].lower() == "bearer"


# ---------------------------------------------------------------------------
# GET /user — 실제 토큰으로 사용자 정보 조회
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_user_integration(app: FastAPI, config: EnvConfig):
    """/user 엔드포인트가 실제 토큰으로 사용자 정보를 반환한다."""
    client = TestClient(app)
    token_response = client.post(
        "/token",
        data={
            "username": config.keycloak_username,
            "password": config.keycloak_password,
        },
    )
    assert token_response.status_code == 200
    access_token = token_response.json()["access_token"]

    response = client.get("/user", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    body = response.json()
    assert body["username"] == config.keycloak_username
