from __future__ import annotations

import sys
from pathlib import Path

import pytest

from fastapi_core import register_readiness_check
from fastapi_core.config import AppConfig
from fastapi_core.docmesh_settings import load_docmesh_settings
from fastapi_core.factory import create_app

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def build_test_settings(monkeypatch: pytest.MonkeyPatch):
    env = {
        "KEYCLOAK_URL": "http://keycloak.test",
        "KEYCLOAK_REALM": "docmesh",
        "KEYCLOAK_CLIENT_ID": "fastapi-core",
        "KEYCLOAK_CLIENT_SECRET": "secret",
        "POSTGRES_DSN": (
            "postgresql+psycopg://docmesh:secret@postgres.test:5432/docmesh"
        ),
        "SQLITE_PATH": ":memory:",
        "MINIO_ENDPOINT": "minio.test:9000",
        "MINIO_ACCESS_KEY": "minio",
        "MINIO_SECRET_KEY": "miniosecret",
        "MILVUS_URI": "http://milvus.test:19530",
        "OLLAMA_HOST": "http://ollama.test:11434",
        "LANGFUSE_HOST": "http://langfuse.test:3000",
        "LANGFUSE_PUBLIC_KEY": "pk",
        "LANGFUSE_SECRET_KEY": "sk",
        "NATS_SERVERS": "nats://nats.test:4222",
        "NATS_TOKEN": "token",
    }
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    load_docmesh_settings.cache_clear()
    return load_docmesh_settings(("keycloak", "postgres", "sqlite"))


@pytest.fixture
def settings(monkeypatch: pytest.MonkeyPatch):
    return build_test_settings(monkeypatch)


@pytest.fixture
def empty_app_factory(settings):
    def factory(*, resources=(), lifespan=None, **config):
        return create_app(
            config=AppConfig(enabled_services=[], required_services=[], **config),
            settings=settings,
            lifespan=lifespan,
            include_auth_router=False,
            resources=resources,
        )

    return factory


@pytest.fixture
def auth_app_factory(settings):
    def factory(provider, *, include_auth_router=True):
        app = create_app(settings=settings, include_auth_router=include_auth_router)
        app.state.auth_provider = provider
        return app

    return factory


@pytest.fixture
def readiness_app_factory(empty_app_factory):
    def factory(checks, *, required=(), **config):
        app = empty_app_factory(**config)
        for name, check in checks.items():
            register_readiness_check(
                app,
                name,
                check,
                required=name in required,
                redact_errors=False,
            )
        return app

    return factory