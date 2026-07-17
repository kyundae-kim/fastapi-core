from __future__ import annotations

import os
import socket
from collections.abc import Iterator
from contextlib import contextmanager
from urllib.parse import urlparse

import pytest
from docmesh_py_core import (
    Service,
    ServiceRuntime,
    create_keycloak_client,
    create_langfuse_client,
    create_milvus_client,
    create_minio_client,
    create_nats_client,
    create_ollama_client,
    create_postgres_client,
    create_sqlite_client,
)

from fastapi_core.config import AppConfig, load_app_config
from fastapi_core.docmesh_settings import load_docmesh_settings
from fastapi_core.factory import create_app

pytestmark = pytest.mark.integration


KEYCLOAK_REQUIRED_ENV = (
    "KEYCLOAK_URL",
    "KEYCLOAK_REALM",
    "KEYCLOAK_CLIENT_ID",
    "KEYCLOAK_CLIENT_SECRET",
    "KEYCLOAK_TOKEN_USERNAME",
    "KEYCLOAK_TOKEN_PASSWORD",
)

NATS_REQUIRED_ENV = ("NATS_SERVERS",)
MILVUS_REQUIRED_ENV = ("MILVUS_URI",)
SQLITE_REQUIRED_ENV = ("SQLITE_PATH",)
MINIO_REQUIRED_ENV = (
    "MINIO_ENDPOINT",
    "MINIO_ACCESS_KEY",
    "MINIO_SECRET_KEY",
)
POSTGRES_CONNECTION_ENV = (
    "POSTGRES_HOST",
    "POSTGRES_DB",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
)

SERVICE_CLIENT_FACTORIES = {
    "keycloak": create_keycloak_client,
    "postgres": create_postgres_client,
    "sqlite": create_sqlite_client,
    "minio": create_minio_client,
    "milvus": create_milvus_client,
    "ollama": create_ollama_client,
    "langfuse": create_langfuse_client,
    "nats": create_nats_client,
}


@contextmanager
def cleared_config_caches() -> Iterator[None]:
    load_app_config.cache_clear()
    load_docmesh_settings.cache_clear()
    try:
        yield
    finally:
        load_app_config.cache_clear()
        load_docmesh_settings.cache_clear()


def _require_env(keys: tuple[str, ...], *, label: str) -> None:
    missing = [key for key in keys if not os.getenv(key)]
    if missing:
        pytest.skip(f"{label} integration env missing: {', '.join(missing)}")


def _is_tcp_reachable(host: str | None, port: int | None, *, timeout: float = 2.0) -> bool:
    if not host or not port:
        return False
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _parse_nats_server(server: str) -> tuple[str | None, int | None]:
    parsed = urlparse(server)
    host = parsed.hostname
    port = parsed.port or 4222
    return host, port


def _parse_minio_endpoint(endpoint: str) -> tuple[str | None, int | None]:
    parsed = urlparse(endpoint if "://" in endpoint else f"//{endpoint}")
    return parsed.hostname, parsed.port or 9000


def _parse_milvus_uri(uri: str) -> tuple[str | None, int | None]:
    parsed = urlparse(uri if "://" in uri else f"//{uri}")
    return parsed.hostname, parsed.port or 19530


def _postgres_target() -> tuple[str | None, int | None]:
    dsn = os.getenv("POSTGRES_DSN")
    if dsn:
        parsed = urlparse(dsn)
        return parsed.hostname, parsed.port or 5432
    _require_env(POSTGRES_CONNECTION_ENV, label="postgres")
    return os.getenv("POSTGRES_HOST"), int(os.getenv("POSTGRES_PORT", "5432"))


def require_keycloak_integration() -> None:
    _require_env(KEYCLOAK_REQUIRED_ENV, label="keycloak")
    parsed = urlparse(os.environ["KEYCLOAK_URL"])
    if not _is_tcp_reachable(parsed.hostname, parsed.port or 80):
        pytest.skip(
            "keycloak integration target is not reachable at "
            f"{parsed.hostname}:{parsed.port or 80}"
        )


def require_nats_integration() -> None:
    _require_env(NATS_REQUIRED_ENV, label="nats")
    first_server = os.environ["NATS_SERVERS"].split(",", 1)[0].strip()
    host, port = _parse_nats_server(first_server)
    if not _is_tcp_reachable(host, port):
        pytest.skip(f"nats integration target is not reachable at {host}:{port}")


def require_minio_integration() -> None:
    _require_env(MINIO_REQUIRED_ENV, label="minio")
    host, port = _parse_minio_endpoint(os.environ["MINIO_ENDPOINT"])
    if not _is_tcp_reachable(host, port):
        pytest.skip(f"minio integration target is not reachable at {host}:{port}")


def require_milvus_integration() -> None:
    _require_env(MILVUS_REQUIRED_ENV, label="milvus")
    host, port = _parse_milvus_uri(os.environ["MILVUS_URI"])
    if not _is_tcp_reachable(host, port):
        pytest.skip(f"milvus integration target is not reachable at {host}:{port}")


def require_postgres_integration() -> None:
    host, port = _postgres_target()
    if not _is_tcp_reachable(host, port):
        pytest.skip(f"postgres integration target is not reachable at {host}:{port}")


def require_sqlite_integration() -> None:
    _require_env(SQLITE_REQUIRED_ENV, label="sqlite")


@pytest.fixture
def keycloak_integration_ready() -> None:
    require_keycloak_integration()


@pytest.fixture
def nats_integration_ready() -> None:
    require_nats_integration()


@pytest.fixture
def minio_integration_ready() -> None:
    require_minio_integration()


@pytest.fixture
def milvus_integration_ready() -> None:
    require_milvus_integration()


@pytest.fixture
def postgres_integration_ready() -> None:
    require_postgres_integration()


@pytest.fixture
def sqlite_integration_ready() -> None:
    require_sqlite_integration()


@pytest.fixture
def integration_app_config_factory():
    def build(
        *,
        enabled_services: list[str],
        required_services: list[str],
        token_url: str = "/token",
        readiness_parallel: bool = False,
    ) -> AppConfig:
        return AppConfig(
            token_url=token_url,
            enabled_services=enabled_services,
            required_services=required_services,
            readiness_parallel=readiness_parallel,
        )

    return build


@pytest.fixture
def integration_runtime_factory():
    def build(config: AppConfig) -> ServiceRuntime:
        with cleared_config_caches():
            settings = load_docmesh_settings(tuple(config.enabled_services))
        clients = {}
        for service_name in config.enabled_services:
            service_config = getattr(settings, service_name)
            client = SERVICE_CLIENT_FACTORIES[service_name](service_config)
            if client is not None:
                clients[Service.parse(service_name)] = client
        return ServiceRuntime(
            configs=settings,
            clients=clients,
            selected_services=frozenset(clients),
            required_services=frozenset(
                Service.parse(service_name)
                for service_name in config.required_services
            ),
        )

    return build


@pytest.fixture
def integration_app_factory(integration_runtime_factory):
    def build(
        config: AppConfig,
        *,
        include_auth_router: bool = True,
        lifespan=None,
    ):
        runtime = integration_runtime_factory(config)
        return create_app(
            config=config,
            runtime=runtime,
            include_auth_router=include_auth_router,
            lifespan=lifespan,
        )

    return build


@pytest.fixture
def integration_credentials() -> dict[str, str]:
    require_keycloak_integration()
    return {
        "username": os.environ["KEYCLOAK_TOKEN_USERNAME"],
        "password": os.environ["KEYCLOAK_TOKEN_PASSWORD"],
        "scope": os.getenv("FASTAPI_CORE_TEST_SCOPE", "").strip(),
    }


@pytest.fixture
def invalid_bearer_token() -> str:
    return os.getenv("FASTAPI_CORE_TEST_INVALID_TOKEN", "invalid.token.value")
