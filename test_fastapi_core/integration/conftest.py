from __future__ import annotations

import os
import socket
from collections.abc import Iterator
from contextlib import contextmanager
from urllib.parse import urlparse

import pytest

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


@pytest.fixture
def keycloak_integration_ready() -> None:
    require_keycloak_integration()


@pytest.fixture
def nats_integration_ready() -> None:
    require_nats_integration()


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
def integration_settings_factory():
    def build(config: AppConfig):
        with cleared_config_caches():
            return load_docmesh_settings(tuple(config.enabled_services))

    return build


@pytest.fixture
def integration_app_factory(integration_settings_factory):
    def build(
        config: AppConfig,
        *,
        include_auth_router: bool = True,
        lifespan=None,
    ):
        settings = integration_settings_factory(config)
        return create_app(
            config=config,
            settings=settings,
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
