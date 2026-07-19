from __future__ import annotations

from typing import get_type_hints

import pytest
import fastapi_core.dependencies as dependencies_module
import fastapi_core.dependencies.services as services_module
from docmesh_py_core import (
    AuthenticatedUser,
    KeycloakAuthService,
    NatsConnectionBuilder,
    Service,
    ServiceClientWrapper,
    ServiceRuntime,
    create_keycloak_client,
    create_nats_client,
    create_sqlite_client,
)
from fastapi import Depends, HTTPException, Request
from fastapi.testclient import TestClient
from langfuse import Langfuse
from minio import Minio
from ollama import Client as OllamaClient
from pymilvus import MilvusClient
from sqlalchemy.engine import Engine

from fastapi_core.config import AppConfig
from fastapi_core.dependencies import (
    get_keycloak_auth_service,
    get_nats_connection_builder,
    get_service_client,
    get_service_runtime,
    get_sqlite_engine,
)
from fastapi_core.dependencies.auth import (
    get_current_user,
    require_permissions,
    require_roles,
    require_scopes,
)
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
    client_roles = {"fastapi-core": ["writer"]}
    claims = {"scope": "openid"}


class FakeAuthProvider:
    def extract_user_info(self, token: str):
        self.token = token
        return FakeAuthenticatedUser()


def test_dependency_package_exports_declarative_authorization_helpers():
    assert {
        "require_permissions",
        "require_roles",
        "require_scopes",
    }.issubset(set(dir(dependencies_module)))
    assert get_type_hints(get_current_user)["return"] is AuthenticatedUser


def test_get_settings_returns_runtime_configs(empty_runtime):
    app = create_app(runtime=empty_runtime, include_auth_router=False)
    request = Request({"type": "http", "app": app})

    assert get_settings(request) is empty_runtime.configs


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
        "get_service_runtime",
    }

    assert expected.issubset(set(dir(services_module)))
    assert get_type_hints(services_module.get_keycloak_auth_service)["return"] is KeycloakAuthService
    assert get_type_hints(services_module.get_sqlite_engine)["return"] is Engine
    assert get_type_hints(services_module.get_nats_connection_builder)["return"] is NatsConnectionBuilder
    assert get_type_hints(services_module.get_service_runtime)["return"] is ServiceRuntime


def test_get_service_runtime_returns_lifespan_owned_runtime(empty_runtime):
    app = create_app(runtime=empty_runtime, include_auth_router=False)
    request = Request({"type": "http", "app": app})

    assert get_service_runtime(request) is app.state.service_runtime


def test_service_client_is_resolved_from_runtime(settings):
    class Client:
        def check(self):
            return None

    runtime_client = Client()

    runtime = ServiceRuntime(
        configs=settings,
        clients={Service.SQLITE: runtime_client},
        selected_services=frozenset({Service.SQLITE}),
    )
    app = create_app(
        config=AppConfig(enabled_services=[], required_services=[]),
        runtime=runtime,
        include_auth_router=False,
    )

    request = Request({"type": "http", "app": app})

    dependency = get_service_client("sqlite")

    assert dependency(request) is runtime_client


def test_get_service_runtime_returns_503_before_default_runtime_startup():
    app = create_app(
        config=AppConfig(enabled_services=[], required_services=[]),
        include_auth_router=False,
    )
    request = Request({"type": "http", "app": app})

    with pytest.raises(HTTPException) as exc_info:
        get_service_runtime(request)

    assert getattr(exc_info.value, "status_code", None) == 503
    assert getattr(exc_info.value, "detail", None) == "Service runtime is not available"


def test_get_current_user_returns_401_when_token_missing(auth_app_factory):
    app = auth_app_factory(FakeAuthProvider(), include_auth_router=False)

    @app.get("/me", response_model=UserInfo)
    async def me(user: UserInfo = Depends(get_current_user)):
        return user

    with TestClient(app) as client:
        response = client.get("/me")

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


@pytest.mark.asyncio
async def test_get_current_user_preserves_authenticated_user():
    user = AuthenticatedUser(
        sub="user-1",
        preferred_username="bob",
        email="bob@example.com",
        given_name="Bob",
        family_name="Builder",
        name="Bob Builder",
        realm_roles=["user"],
        client_roles={"fastapi-core": ["writer"]},
        claims={"scope": "openid profile"},
    )

    class Provider:
        def extract_user_info(self, token: str) -> AuthenticatedUser:
            assert token == "demo-token"
            return user

    result = await get_current_user("demo-token", Provider())

    assert result is user


def test_require_permissions_returns_403_when_role_missing(auth_app_factory):
    app = auth_app_factory(FakeAuthProvider(), include_auth_router=False)

    @app.get("/admin")
    async def admin(_user: UserInfo = Depends(require_permissions("admin"))):
        return {"ok": True}

    with TestClient(app) as client:
        response = client.get("/admin", headers={"Authorization": "Bearer demo-token"})

    assert response.status_code == 403
    assert response.json()["detail"] == "Forbidden"


def test_require_permissions_accepts_scope_permissions(auth_app_factory):
    app = auth_app_factory(FakeAuthProvider(), include_auth_router=False)

    @app.get("/profile")
    async def profile(_user: UserInfo = Depends(require_permissions("openid"))):
        return {"ok": True}

    with TestClient(app) as client:
        response = client.get(
            "/profile",
            headers={"Authorization": "Bearer demo-token"},
        )

    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_require_permissions_accepts_client_roles(auth_app_factory):
    app = auth_app_factory(FakeAuthProvider(), include_auth_router=False)

    @app.get("/write")
    async def write(_user=Depends(require_permissions("writer"))):
        return {"ok": True}

    with TestClient(app) as client:
        response = client.get(
            "/write",
            headers={"Authorization": "Bearer demo-token"},
        )

    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_require_roles_and_scopes_are_declarative_dependencies(auth_app_factory):
    app = auth_app_factory(FakeAuthProvider(), include_auth_router=False)

    @app.get("/secured")
    async def secured(
        _role_user: UserInfo = Depends(require_roles("user")),
        _scope_user: UserInfo = Depends(require_scopes("openid")),
    ):
        return {"ok": True}

    with TestClient(app) as client:
        response = client.get(
            "/secured",
            headers={"Authorization": "Bearer demo-token"},
        )

    assert response.status_code == 200
    security = app.openapi()["paths"]["/secured"]["get"]["security"]
    assert {"OAuth2PasswordBearer": ["openid"]} in security


def test_get_current_user_uses_service_client_backed_auth_provider(
    monkeypatch,
    settings,
    runtime_factory,
):
    wrapper = create_keycloak_client(settings.keycloak)
    provider = wrapper.unwrap()
    tokens: list[str] = []

    def extract_user_info(token: str):
        tokens.append(token)
        return FakeAuthenticatedUser()

    monkeypatch.setattr(provider, "extract_user_info", extract_user_info)
    app = create_app(
        config=AppConfig(enabled_services=[], required_services=[]),
        runtime=runtime_factory(clients={"keycloak": wrapper}),
        include_auth_router=False,
    )

    @app.get("/me")
    async def me(user: AuthenticatedUser = Depends(get_current_user)):
        return {"preferred_username": user.preferred_username}

    with TestClient(app) as client:
        response = client.get("/me", headers={"Authorization": "Bearer demo-token"})

    assert response.status_code == 200
    assert response.json()["preferred_username"] == "bob"
    assert tokens == ["demo-token"]


def test_get_service_client_returns_initialized_service_client(
    settings,
    runtime_factory,
):
    config = AppConfig(
        enabled_services=["sqlite"],
        required_services=["sqlite"],
    )
    runtime = runtime_factory(
        clients={"sqlite": create_sqlite_client(settings.sqlite)},
        required=("sqlite",),
    )
    app = create_app(config=config, runtime=runtime, include_auth_router=False)

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


def test_get_service_specific_dependencies_return_concrete_clients(
    runtime_factory,
):
    config = AppConfig(
        enabled_services=["keycloak", "sqlite", "nats"],
        required_services=["keycloak"],
    )
    service_settings = load_docmesh_settings(("keycloak", "sqlite", "nats"))
    runtime = runtime_factory(
        clients={
            "keycloak": create_keycloak_client(service_settings.keycloak),
            "sqlite": create_sqlite_client(service_settings.sqlite),
            "nats": create_nats_client(service_settings.nats),
        },
        required=("keycloak",),
    )
    app = create_app(config=config, runtime=runtime, include_auth_router=False)

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


@pytest.mark.parametrize(
    ("service_name", "dependency", "client_type"),
    [
        ("postgres", services_module.get_postgres_engine, Engine),
        ("minio", services_module.get_minio_client, Minio),
        ("milvus", services_module.get_milvus_client, MilvusClient),
        ("ollama", services_module.get_ollama_client, OllamaClient),
        ("langfuse", services_module.get_langfuse_client, Langfuse),
    ],
)
def test_remaining_typed_service_dependencies_return_expected_client_types(
    settings,
    runtime_factory,
    service_name,
    dependency,
    client_type,
):
    if client_type is Engine:
        client = create_sqlite_client(settings.sqlite).unwrap()
    else:
        client = object.__new__(client_type)
    wrapper = ServiceClientWrapper(
        client=client,
        healthcheck=lambda: None,
        service_name=service_name,
    )
    app = create_app(
        config=AppConfig(enabled_services=[], required_services=[]),
        runtime=runtime_factory(clients={service_name: wrapper}),
        include_auth_router=False,
    )
    request = Request({"type": "http", "app": app})

    try:
        assert dependency(request) is client
    finally:
        if isinstance(client, Engine):
            client.dispose()


@pytest.mark.parametrize(
    ("service_name", "dependency", "expected_type"),
    [
        ("keycloak", services_module.get_keycloak_auth_service, "KeycloakAuthService"),
        ("postgres", services_module.get_postgres_engine, "Engine"),
        ("sqlite", services_module.get_sqlite_engine, "Engine"),
        ("minio", services_module.get_minio_client, "Minio"),
        ("milvus", services_module.get_milvus_client, "MilvusClient"),
        ("ollama", services_module.get_ollama_client, "Client"),
        ("langfuse", services_module.get_langfuse_client, "Langfuse"),
    ],
)
def test_typed_service_dependency_rejects_wrong_unwrapped_client(
    runtime_factory,
    service_name,
    dependency,
    expected_type,
):
    wrapper = ServiceClientWrapper(
        client=object(),
        healthcheck=lambda: None,
        service_name=service_name,
    )
    app = create_app(
        config=AppConfig(enabled_services=[], required_services=[]),
        runtime=runtime_factory(clients={service_name: wrapper}),
        include_auth_router=False,
    )
    request = Request({"type": "http", "app": app})

    with pytest.raises(HTTPException) as exc_info:
        dependency(request)

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == (
        f"Service client '{service_name}' is not a {expected_type}"
    )


@pytest.mark.parametrize(
    ("service_name", "dependency"),
    [
        pytest.param("sqlite", get_service_client("sqlite"), id="generic"),
        pytest.param("nats", get_nats_connection_builder, id="typed-nats"),
    ],
)
def test_service_dependencies_return_503_when_service_is_not_enabled(
    empty_runtime,
    service_name,
    dependency,
):
    app = create_app(
        config=AppConfig(enabled_services=[], required_services=[]),
        runtime=empty_runtime,
        include_auth_router=False,
    )

    @app.get("/service")
    async def service_client(client=Depends(dependency)):
        return {"service_type": type(client).__name__}

    with TestClient(app) as client:
        response = client.get("/service")

    assert response.status_code == 503
    assert response.json()["detail"] == f"Service client '{service_name}' is not enabled"
