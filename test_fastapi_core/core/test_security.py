from unittest.mock import MagicMock, patch

import jwt
import pytest

from fastapi_core.core.auth import KeycloakAuthProvider, extract_roles, extract_scopes


# ---------------------------------------------------------------------------
# extract_roles
# ---------------------------------------------------------------------------


def test_extract_roles_normal():
    payload = {"realm_access": {"roles": ["admin", "user"]}}
    assert extract_roles(payload) == ["admin", "user"]


def test_extract_roles_missing_realm_access():
    assert extract_roles({}) == []


def test_extract_roles_empty_roles():
    assert extract_roles({"realm_access": {"roles": []}}) == []


def test_extract_roles_missing_roles_key():
    assert extract_roles({"realm_access": {}}) == []


# ---------------------------------------------------------------------------
# extract_scopes
# ---------------------------------------------------------------------------


def test_extract_scopes_from_scope_string():
    payload = {"scope": "read write"}
    assert extract_scopes(payload) == ["read", "write"]


def test_extract_scopes_from_scp_list():
    payload = {"scp": ["read", "write"]}
    assert extract_scopes(payload) == ["read", "write"]


def test_extract_scopes_from_scp_string():
    payload = {"scp": "read"}
    assert extract_scopes(payload) == ["read"]


def test_extract_scopes_empty():
    assert extract_scopes({}) == []


def test_extract_scopes_empty_scope_string():
    assert extract_scopes({"scope": ""}) == []


# ---------------------------------------------------------------------------
# KeycloakAuthProvider — validation
# ---------------------------------------------------------------------------


def test_keycloak_auth_provider_empty_url_raises():
    with pytest.raises(ValueError, match="http_url"):
        KeycloakAuthProvider(http_url="", realm="realm", client_id="client")


def test_keycloak_auth_provider_empty_realm_raises():
    with pytest.raises(ValueError, match="realm"):
        KeycloakAuthProvider(
            http_url="http://keycloak:8080/", realm="", client_id="client"
        )


def test_keycloak_auth_provider_empty_client_id_raises():
    with pytest.raises(ValueError, match="client_id"):
        KeycloakAuthProvider(
            http_url="http://keycloak:8080/", realm="realm", client_id=""
        )


# ---------------------------------------------------------------------------
# KeycloakAuthProvider — URL construction
# ---------------------------------------------------------------------------


def test_keycloak_auth_provider_url_construction():
    provider = KeycloakAuthProvider(
        http_url="http://keycloak:8080/",
        realm="myrealm",
        client_id="myclient",
    )
    assert provider.token_url == (
        "http://keycloak:8080/realms/myrealm/protocol/openid-connect/token"
    )
    assert provider.jwks_url == (
        "http://keycloak:8080/realms/myrealm/protocol/openid-connect/certs"
    )
    assert provider.issuer == "http://keycloak:8080/realms/myrealm"


# ---------------------------------------------------------------------------
# KeycloakAuthProvider — to_user
# ---------------------------------------------------------------------------


def test_to_user_mapping():
    provider = KeycloakAuthProvider(
        http_url="http://keycloak:8080/",
        realm="realm",
        client_id="client",
    )
    payload = {
        "sub": "user-123",
        "preferred_username": "john",
        "email": "john@example.com",
        "name": "John Doe",
        "realm_access": {"roles": ["admin"]},
        "scope": "openid profile",
    }
    user = provider.to_user(payload)
    assert user.sub == "user-123"
    assert user.username == "john"
    assert user.email == "john@example.com"
    assert user.name == "John Doe"
    assert "admin" in user.roles
    assert "openid" in user.scopes


def test_to_user_minimal_payload():
    provider = KeycloakAuthProvider(
        http_url="http://keycloak:8080/",
        realm="realm",
        client_id="client",
    )
    user = provider.to_user({"sub": "u-1"})
    assert user.sub == "u-1"
    assert user.username == ""
    assert user.email is None
    assert user.roles == []
    assert user.scopes == []


# ---------------------------------------------------------------------------
# KeycloakAuthProvider — decode_token_insecure
# ---------------------------------------------------------------------------


def test_decode_token_insecure_valid():
    token = jwt.encode(
        {"sub": "user-1", "preferred_username": "john"},
        "secret",
        algorithm="HS256",
    )
    provider = KeycloakAuthProvider(
        http_url="http://keycloak:8080/",
        realm="realm",
        client_id="client",
    )
    decoded = provider.decode_token_insecure(token)
    assert decoded["sub"] == "user-1"


def test_decode_token_insecure_invalid():
    provider = KeycloakAuthProvider(
        http_url="http://keycloak:8080/",
        realm="realm",
        client_id="client",
    )
    with pytest.raises(ValueError):
        provider.decode_token_insecure("not.a.valid.token.here")


# ---------------------------------------------------------------------------
# KeycloakAuthProvider — authenticate
# ---------------------------------------------------------------------------


def test_authenticate_success():
    provider = KeycloakAuthProvider(
        http_url="http://keycloak:8080/",
        realm="realm",
        client_id="client",
    )
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "access_token": "tok",
        "refresh_token": "ref",
        "token_type": "bearer",
    }

    with patch("fastapi_core.core.auth.httpx.Client") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value.__enter__.return_value = mock_client
        mock_client.post.return_value = mock_response
        result = provider.authenticate("user", "pass")

    assert result["access_token"] == "tok"
    assert result["refresh_token"] == "ref"


def test_authenticate_http_error():
    import httpx

    provider = KeycloakAuthProvider(
        http_url="http://keycloak:8080/",
        realm="realm",
        client_id="client",
    )
    with patch("fastapi_core.core.auth.httpx.Client") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value.__enter__.return_value = mock_client
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "401", request=MagicMock(), response=MagicMock()
        )
        mock_client.post.return_value = mock_response
        with pytest.raises(httpx.HTTPStatusError):
            provider.authenticate("user", "wrong")


# ---------------------------------------------------------------------------
# KeycloakAuthProvider — refresh_access_token
# ---------------------------------------------------------------------------


def test_refresh_token_success():
    provider = KeycloakAuthProvider(
        http_url="http://keycloak:8080/",
        realm="realm",
        client_id="client",
    )
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "access_token": "new_tok",
        "token_type": "bearer",
    }

    with patch("fastapi_core.core.auth.httpx.Client") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value.__enter__.return_value = mock_client
        mock_client.post.return_value = mock_response
        result = provider.refresh_access_token("refresh_value")

    assert result["access_token"] == "new_tok"


def test_refresh_token_includes_secret():
    provider = KeycloakAuthProvider(
        http_url="http://keycloak:8080/",
        realm="realm",
        client_id="client",
        client_secret="mysecret",
    )
    mock_response = MagicMock()
    mock_response.json.return_value = {"access_token": "tok", "token_type": "bearer"}

    with patch("fastapi_core.core.auth.httpx.Client") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value.__enter__.return_value = mock_client
        mock_client.post.return_value = mock_response
        provider.refresh_access_token("ref_tok")
        _, kwargs = mock_client.post.call_args
        assert kwargs["data"]["client_secret"] == "mysecret"


# ---------------------------------------------------------------------------
# KeycloakAuthProvider — decode_token (RS256 서명 검증)
# ---------------------------------------------------------------------------


def test_decode_token_valid():
    """PyJWKClient mock을 사용한 RS256 서명 검증 성공 경로."""
    provider = KeycloakAuthProvider(
        http_url="http://keycloak:8080/",
        realm="realm",
        client_id="client",
    )
    expected_payload = {"sub": "user-1", "aud": "client", "iss": provider.issuer}

    with patch("fastapi_core.core.auth.jwt.PyJWKClient") as mock_jwks_cls:
        mock_jwks_client = MagicMock()
        mock_jwks_cls.return_value = mock_jwks_client
        mock_signing_key = MagicMock()
        mock_signing_key.key = "fake_rsa_key"
        mock_jwks_client.get_signing_key_from_jwt.return_value = mock_signing_key

        with patch("fastapi_core.core.auth.jwt.decode", return_value=expected_payload) as mock_decode:
            result = provider.decode_token("some.jwt.token")
            mock_decode.assert_called_once_with(
                "some.jwt.token",
                "fake_rsa_key",
                algorithms=["RS256"],
                audience="client",
                issuer=provider.issuer,
            )

    assert result["sub"] == "user-1"


def test_decode_token_invalid():
    """PyJWKClient에서 오류 발생 시 ValueError로 변환된다."""
    provider = KeycloakAuthProvider(
        http_url="http://keycloak:8080/",
        realm="realm",
        client_id="client",
    )

    with patch("fastapi_core.core.auth.jwt.PyJWKClient") as mock_jwks_cls:
        mock_jwks_client = MagicMock()
        mock_jwks_cls.return_value = mock_jwks_client
        mock_jwks_client.get_signing_key_from_jwt.side_effect = jwt.PyJWTError("invalid key")

        with pytest.raises(ValueError, match="Invalid token"):
            provider.decode_token("bad.jwt.token")
