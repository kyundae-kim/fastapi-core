"""Keycloak 연동 통합 테스트 — 실제 Keycloak 인스턴스 필요."""
import pytest

from fastapi_core.core.auth import KeycloakAuthProvider
from fastapi_core.core.config import EnvConfig


@pytest.fixture(scope="module")
def config() -> EnvConfig:
    return EnvConfig()


@pytest.fixture(scope="module")
def provider(config: EnvConfig) -> KeycloakAuthProvider:
    return KeycloakAuthProvider(
        http_url=str(config.keycloak.url),
        realm=config.keycloak.realm,
        client_id=config.keycloak.client_id,
        client_secret=config.keycloak.client_secret,
    )


# ---------------------------------------------------------------------------
# 실제 Keycloak 토큰 발급
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_authenticate(provider: KeycloakAuthProvider, config: EnvConfig):
    """실제 Keycloak 서버에서 액세스 토큰을 발급받는다."""
    result = provider.authenticate(config.keycloak_username, config.keycloak_password)
    assert "access_token" in result
    assert result["access_token"]


# ---------------------------------------------------------------------------
# RS256 서명 검증 디코드
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_decode_token_rs256(provider: KeycloakAuthProvider, config: EnvConfig):
    """발급된 토큰을 RS256 서명 검증으로 디코드한다."""
    token_data = provider.authenticate(config.keycloak_username, config.keycloak_password)
    access_token = token_data["access_token"]

    payload = provider.decode_token(access_token)

    assert "sub" in payload
    assert payload.get("iss") == provider.issuer


# ---------------------------------------------------------------------------
# 클레임 추출 검증
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_extract_claims(provider: KeycloakAuthProvider, config: EnvConfig):
    """디코드된 payload에서 UserInfo 모델로 클레임이 올바르게 매핑된다."""
    token_data = provider.authenticate(config.keycloak_username, config.keycloak_password)
    access_token = token_data["access_token"]
    payload = provider.decode_token(access_token)

    user = provider.to_user(payload)

    assert user.sub
    assert user.username == config.keycloak_username
