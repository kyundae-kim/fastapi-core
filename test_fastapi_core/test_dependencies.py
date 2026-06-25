from __future__ import annotations

from fastapi import Depends
from fastapi.testclient import TestClient

from fastapi_core.dependencies.auth import get_current_user, require_permissions
from fastapi_core.factory import create_app
from fastapi_core.schemas.user import UserInfo


class FakeAuthenticatedUser:
    sub = "user-1"
    preferred_username = "bob"
    email = None
    name = "Bob"
    realm_roles = ["user"]
    client_roles = {}
    claims = {"scope": "openid"}


class FakeAuthProvider:
    def extract_user_info(self, token: str):
        self.token = token
        return FakeAuthenticatedUser()



def test_get_current_user_returns_401_when_token_missing(settings):
    app = create_app(settings=settings, include_auth_router=False)
    app.state.auth_provider = FakeAuthProvider()

    @app.get("/me", response_model=UserInfo)
    async def me(user: UserInfo = Depends(get_current_user)):
        return user

    with TestClient(app) as client:
        response = client.get("/me")

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"



def test_require_permissions_returns_403_when_role_missing(settings):
    app = create_app(settings=settings, include_auth_router=False)
    app.state.auth_provider = FakeAuthProvider()

    @app.get("/admin")
    async def admin(_user: UserInfo = Depends(require_permissions("admin"))):
        return {"ok": True}

    with TestClient(app) as client:
        response = client.get("/admin", headers={"Authorization": "Bearer demo-token"})

    assert response.status_code == 403
    assert response.json()["detail"] == "Forbidden"
