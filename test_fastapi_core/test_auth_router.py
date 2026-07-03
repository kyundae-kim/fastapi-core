from __future__ import annotations

import logging

from fastapi.testclient import TestClient
from docmesh_py_core import (
    KeycloakTokenAuthenticationError,
    KeycloakTokenConfigurationError,
    KeycloakTokenTemporaryError,
)

from fastapi_core.factory import create_app


class FakeAccessTokenResult:
    access_token = "access-token"
    refresh_token = "refresh-token"
    token_type = "Bearer"


class FakeAuthenticatedUser:
    sub = "user-1"
    preferred_username = "alice"
    email = "alice@example.com"
    name = "Alice"
    realm_roles = ["admin"]
    client_roles = {"fastapi-core": ["writer"]}
    claims = {"scope": "openid profile"}


class FakeAuthProvider:
    def fetch_access_token(self, *, scope=None, username=None, password=None):
        self.scope = scope
        self.username = username
        self.password = password
        return FakeAccessTokenResult()

    def extract_user_info(self, token: str):
        self.token = token
        return FakeAuthenticatedUser()


class FailingAuthProvider(FakeAuthProvider):
    def __init__(self, exc: Exception):
        self.exc = exc

    def fetch_access_token(self, *, scope=None, username=None, password=None):
        self.scope = scope
        self.username = username
        self.password = password
        raise self.exc



def test_token_endpoint_returns_token_response(settings):
    app = create_app(settings=settings)
    provider = FakeAuthProvider()
    app.state.auth_provider = provider

    with TestClient(app) as client:
        response = client.post(
            "/token",
            data={"username": "alice", "password": "secret", "scope": "openid profile"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "access_token": "access-token",
        "refresh_token": "refresh-token",
        "token_type": "bearer",
    }
    assert provider.scope == "openid profile"
    assert provider.username == "alice"
    assert provider.password == "secret"



def test_token_endpoint_returns_401_for_authentication_failures(settings, caplog):
    app = create_app(settings=settings)
    app.state.auth_provider = FailingAuthProvider(
        KeycloakTokenAuthenticationError("invalid credentials token=secret"),
    )

    with caplog.at_level(logging.WARNING):
        with TestClient(app) as client:
            response = client.post(
                "/token",
                data={"username": "alice", "password": "secret", "scope": "openid profile"},
            )

    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication failed"
    assert response.headers["WWW-Authenticate"] == "Bearer"
    records = [record for record in caplog.records if record.getMessage() == "token_issue_failed"]
    assert len(records) == 1
    record = records[0]
    assert record.event["service"] == "keycloak"
    assert record.event["operation"] == "issue_token"
    assert record.event["outcome"] == "authentication_failed"
    assert record.event["status_code"] == 401
    assert record.event["scope"] == "openid profile"
    assert "secret" not in record.event["error"]



def test_token_endpoint_returns_500_for_configuration_failures(settings, caplog):
    app = create_app(settings=settings)
    app.state.auth_provider = FailingAuthProvider(
        KeycloakTokenConfigurationError("missing password grant config"),
    )

    with caplog.at_level(logging.WARNING):
        with TestClient(app) as client:
            response = client.post(
                "/token",
                data={"username": "alice", "password": "secret"},
            )

    assert response.status_code == 500
    assert response.json()["detail"] == "Authentication service misconfigured"
    records = [record for record in caplog.records if record.getMessage() == "token_issue_failed"]
    assert len(records) == 1
    assert records[0].event["outcome"] == "configuration_error"
    assert records[0].event["status_code"] == 500



def test_token_endpoint_returns_503_for_temporary_failures(settings, caplog):
    app = create_app(settings=settings)
    app.state.auth_provider = FailingAuthProvider(
        KeycloakTokenTemporaryError("keycloak timeout token=temporary-secret"),
    )

    with caplog.at_level(logging.WARNING):
        with TestClient(app) as client:
            response = client.post(
                "/token",
                data={"username": "alice", "password": "secret"},
            )

    assert response.status_code == 503
    assert response.json()["detail"] == "Authentication service unavailable"
    records = [record for record in caplog.records if record.getMessage() == "token_issue_failed"]
    assert len(records) == 1
    assert records[0].event["outcome"] == "temporary_error"
    assert records[0].event["status_code"] == 503
    assert "temporary-secret" not in records[0].event["error"]



def test_user_endpoint_returns_current_user(settings):
    app = create_app(settings=settings)
    app.state.auth_provider = FakeAuthProvider()

    with TestClient(app) as client:
        response = client.get("/user", headers={"Authorization": "Bearer demo-token"})

    assert response.status_code == 200
    assert response.json() == {
        "sub": "user-1",
        "username": "alice",
        "email": "alice@example.com",
        "name": "Alice",
        "roles": ["admin", "writer"],
        "scopes": ["openid", "profile"],
    }
