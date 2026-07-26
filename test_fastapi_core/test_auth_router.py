from __future__ import annotations

import logging
import threading
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from docmesh_py_core import (
    KeycloakTokenAuthenticationError,
    KeycloakTokenConfigurationError,
    KeycloakTokenError,
    KeycloakTokenTemporaryError,
)

import fastapi_core.routers.auth as auth_module



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


class ThreadRecordingAuthProvider(FakeAuthProvider):
    def fetch_access_token(self, *, scope=None, username=None, password=None):
        self.thread_id = threading.get_ident()
        return super().fetch_access_token(
            scope=scope,
            username=username,
            password=password,
        )


def test_token_issue_errors_are_table_driven():
    assert {error_type for error_type, _ in auth_module._TOKEN_ISSUE_ERRORS} == {
        KeycloakTokenAuthenticationError,
        KeycloakTokenConfigurationError,
        KeycloakTokenTemporaryError,
        KeycloakTokenError,
    }


def test_token_endpoint_returns_token_response(auth_app_factory):
    provider = FakeAuthProvider()
    app = auth_app_factory(provider)

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


@pytest.mark.asyncio
async def test_issue_token_offloads_synchronous_provider_call():
    provider = ThreadRecordingAuthProvider()
    form_data = SimpleNamespace(
        scopes=["openid", "profile"],
        username="alice",
        password="secret",
    )

    response = await auth_module.issue_token(
        form_data=form_data,
        provider=provider,
    )

    assert response.access_token == "access-token"
    assert provider.thread_id != threading.get_ident()



@pytest.mark.parametrize(
    ("exc", "status_code", "detail", "outcome"),
    [
        pytest.param(
            KeycloakTokenAuthenticationError("invalid credentials token=secret"),
            401, "Authentication failed", "authentication_failed", id="authentication",
        ),
        pytest.param(
            KeycloakTokenConfigurationError("missing config token=secret"),
            500, "Authentication service misconfigured", "configuration_error", id="configuration",
        ),
        pytest.param(
            KeycloakTokenTemporaryError("timeout token=secret"),
            503, "Authentication service unavailable", "temporary_error", id="temporary",
        ),
        pytest.param(
            KeycloakTokenError("upstream error token=secret"),
            502, "Authentication service error", "upstream_error", id="upstream",
        ),
    ],
)
def test_token_endpoint_maps_keycloak_failures(
    auth_app_factory,
    caplog,
    exc,
    status_code,
    detail,
    outcome,
):
    app = auth_app_factory(FailingAuthProvider(exc))

    with caplog.at_level(logging.WARNING), TestClient(app) as client:
        response = client.post(
            "/token",
            data={"username": "alice", "password": "secret", "scope": "openid profile"},
        )

    assert response.status_code == status_code
    assert response.json()["detail"] == detail
    assert response.headers["WWW-Authenticate"] == "Bearer"
    records = [record for record in caplog.records if record.getMessage() == "token_issue_failed"]
    assert len(records) == 1
    event = records[0].event
    assert event["service"] == "keycloak"
    assert event["operation"] == "issue_token"
    assert event["outcome"] == outcome
    assert event["status_code"] == status_code
    assert event["scope"] == "openid profile"
    assert "secret" not in event["error"]


def test_token_endpoint_maps_unexpected_failure(auth_app_factory, caplog):
    app = auth_app_factory(FailingAuthProvider(RuntimeError("boom token=secret")))

    with caplog.at_level(logging.WARNING), TestClient(app) as client:
        response = client.post("/token", data={"username": "alice", "password": "secret"})

    assert response.status_code == 500
    assert response.json()["detail"] == "Authentication service error"
    records = [record for record in caplog.records if record.getMessage() == "token_issue_failed"]
    assert len(records) == 1
    assert records[0].event["outcome"] == "unexpected_error"
    assert "secret" not in records[0].event["error"]



def test_user_endpoint_returns_current_user(auth_app_factory):
    app = auth_app_factory(FakeAuthProvider())

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
