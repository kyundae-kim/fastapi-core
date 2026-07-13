from __future__ import annotations

from typing import get_type_hints

import fastapi_core.dependencies.config as config_module
import fastapi_core.dependencies.services as services_module
from docmesh_py_core import KeycloakAuthService, NatsConnectionBuilder
from fastapi import Depends, Request
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine

from fastapi_core.config import AppConfig
from fastapi_core.dependencies import (
    get_keycloak_auth_service,
    get_nats_connection_builder,
    get_service_client,
    get_sqlite_engine,
)
from fastapi_core.dependencies.auth import get_current_user, require_permissions
from fastapi_core.dependencies.config import get_settings
from fastapi_core.docmesh_settings import load_docmesh_settings
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


class FakeServiceClient:
    def __init__(self, provider: FakeAuthProvider):
        self.client = provider


class FakeServiceClients(dict[str, FakeServiceClient]):
    def __init__(self, provider: FakeAuthProvider):
        super().__init__({"keycloak": FakeServiceClient(provider)})


def test_get_settings_falls_back_before_default_runtime_startup(monkeypatch):
    sentinel = object()
    config = AppConfig(
        enabled_services=["sqlite"],
        required_services=["sqlite"],
    )
    app = create_app(config=config, include_auth_router=False)
    request = Request({"type": "http", "app": app})
    monkeypatch.setattr(
        config_module,
        "load_docmesh_settings",
        lambda _services: sentinel,
    )

    result = get_settings(request, config)

    assert result is sentinel


def test_service_dependency_module_exposes_typed_service_getters():
    expected = {
        "get_keycloak_auth_service",
        "get_postgres_engine",
        "get_sqlite_engine",
        "get_minio_client",
        "get_milvus_client",
        "get_ollama_client",
        "get_langfuse_client",
        "get_nats_connection_builder",
    }

    assert expected.issubset(set(dir(services_module)))
    assert get_type_hints(services_module.get_keycloak_auth_service)["return"] is KeycloakAuthService
    assert get_type_hints(services_module.get_sqlite_engine)["return"] is Engine
    assert get_type_hints(services_module.get_nats_connection_builder)["return"] is NatsConnectionBuilder


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


def test_get_current_user_uses_service_client_backed_auth_provider(settings):
    app = create_app(settings=settings, include_auth_router=False)
    provider = FakeAuthProvider()
    app.state.auth_provider = None
    app.state.service_clients = FakeServiceClients(provider)

    @app.get("/me", response_model=UserInfo)
    async def me(user: UserInfo = Depends(get_current_user)):
        return user

    with TestClient(app) as client:
        response = client.get("/me", headers={"Authorization": "Bearer demo-token"})

    assert response.status_code == 200
    assert response.json()["username"] == "bob"
    assert provider.token == "demo-token"


def test_get_service_client_returns_initialized_service_client(settings):
    config = AppConfig(
        enabled_services=["sqlite"],
        required_services=["sqlite"],
    )
    app = create_app(config=config, settings=settings, include_auth_router=False)

    @app.get("/sqlite")
    async def sqlite_client(client=Depends(get_service_client("sqlite"))):
        return {
            "service_type": type(client).__name__,
            "has_check": hasattr(client, "check"),
        }

    with TestClient(app) as client:
        response = client.get("/sqlite")

    assert response.status_code == 200
    assert response.json()["has_check"] is True


def test_get_service_specific_dependencies_return_concrete_clients(settings):
    config = AppConfig(
        enabled_services=["keycloak", "sqlite", "nats"],
        required_services=["keycloak"],
    )
    service_settings = load_docmesh_settings(("keycloak", "sqlite", "nats"))
    app = create_app(config=config, settings=service_settings, include_auth_router=False)

    @app.get("/clients")
    async def clients(
        sqlite_engine: Engine = Depends(get_sqlite_engine),
        keycloak_auth_service: KeycloakAuthService = Depends(get_keycloak_auth_service),
        nats_connection_builder: NatsConnectionBuilder = Depends(get_nats_connection_builder),
    ):
        return {
            "sqlite_type": type(sqlite_engine).__name__,
            "keycloak_type": type(keycloak_auth_service).__name__,
            "nats_type": type(nats_connection_builder).__name__,
            "sqlite_has_connect": hasattr(sqlite_engine, "connect"),
            "keycloak_has_extract_user_info": hasattr(keycloak_auth_service, "extract_user_info"),
            "nats_has_connect": hasattr(nats_connection_builder, "connect"),
        }

    with TestClient(app) as client:
        response = client.get("/clients")

    assert response.status_code == 200
    assert response.json() == {
        "sqlite_type": "Engine",
        "keycloak_type": "KeycloakAuthService",
        "nats_type": "NatsConnectionBuilder",
        "sqlite_has_connect": True,
        "keycloak_has_extract_user_info": True,
        "nats_has_connect": True,
    }


def test_get_service_client_returns_503_when_service_is_not_enabled(settings):
    app = create_app(settings=settings, include_auth_router=False)

    @app.get("/sqlite")
    async def sqlite_client(client=Depends(get_service_client("sqlite"))):
        return {"service_type": type(client).__name__}

    with TestClient(app) as client:
        response = client.get("/sqlite")

    assert response.status_code == 503
    assert response.json()["detail"] == "Service client 'sqlite' is not enabled"


def test_get_nats_connection_builder_returns_503_when_service_is_not_enabled(settings):
    app = create_app(settings=settings, include_auth_router=False)

    @app.get("/nats")
    async def nats_client(_client: NatsConnectionBuilder = Depends(get_nats_connection_builder)):
        return {"ok": True}

    with TestClient(app) as client:
        response = client.get("/nats")

    assert response.status_code == 503
    assert response.json()["detail"] == "Service client 'nats' is not enabled"
