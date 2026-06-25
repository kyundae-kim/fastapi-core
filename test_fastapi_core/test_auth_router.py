from __future__ import annotations

from fastapi.testclient import TestClient

from fastapi_core.factory import create_app


class FakeAccessTokenResult:
    access_token = "access-token"
    refresh_token = "refresh-token"
    token_type = "bearer"


class FakeAuthenticatedUser:
    sub = "user-1"
    preferred_username = "alice"
    email = "alice@example.com"
    name = "Alice"
    realm_roles = ["admin"]
    client_roles = {"fastapi-core": ["writer"]}
    claims = {"scope": "openid profile"}


class FakeAuthProvider:
    def fetch_access_token(self, *, scope=None):
        self.scope = scope
        return FakeAccessTokenResult()

    def extract_user_info(self, token: str):
        self.token = token
        return FakeAuthenticatedUser()



def test_token_endpoint_returns_token_response(settings):
    app = create_app(settings=settings)
    app.state.auth_provider = FakeAuthProvider()

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
