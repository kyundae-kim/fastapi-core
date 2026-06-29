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


class FakeRegistryClient:
    def __init__(self, provider: FakeAuthProvider):
        self.client = provider


class FakeRegistry:
    def __init__(self, provider: FakeAuthProvider):
        self.provider = provider
        self.requested_services: list[str] = []

    def create_client(self, service_name: str) -> FakeRegistryClient:
        self.requested_services.append(service_name)
        return FakeRegistryClient(self.provider)



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



def test_get_current_user_uses_registry_backed_auth_provider(settings):
    app = create_app(settings=settings, include_auth_router=False)
    provider = FakeAuthProvider()
    registry = FakeRegistry(provider)
    app.state.registry = registry

    @app.get("/me", response_model=UserInfo)
    async def me(user: UserInfo = Depends(get_current_user)):
        return user

    with TestClient(app) as client:
        response = client.get("/me", headers={"Authorization": "Bearer demo-token"})

    assert response.status_code == 200
    assert response.json()["username"] == "bob"
    assert registry.requested_services == ["keycloak"]
    assert provider.token == "demo-token"
