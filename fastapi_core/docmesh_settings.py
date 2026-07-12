from __future__ import annotations

import os
from contextlib import contextmanager
from functools import lru_cache
from typing import Iterator

from docmesh_py_core import ServiceConfigs, load_service_configs


def _docmesh_default_env() -> dict[str, str]:
    return {
        "KEYCLOAK_URL": "http://keycloak.local",
        "KEYCLOAK_REALM": "docmesh",
        "KEYCLOAK_CLIENT_ID": "fastapi-core",
        "KEYCLOAK_CLIENT_SECRET": "dev-secret",
        "POSTGRES_DSN": (
            "postgresql+psycopg://docmesh:dev-secret@postgres.local:5432/docmesh"
        ),
        "SQLITE_PATH": ":memory:",
        "MINIO_ENDPOINT": "minio.local:9000",
        "MINIO_ACCESS_KEY": "minio",
        "MINIO_SECRET_KEY": "miniosecret",
        "MILVUS_URI": "http://milvus.local:19530",
        "OLLAMA_HOST": "http://ollama.local:11434",
        "LANGFUSE_HOST": "http://langfuse.local:3000",
        "LANGFUSE_PUBLIC_KEY": "dev-public",
        "LANGFUSE_SECRET_KEY": "dev-secret",
        "NATS_SERVERS": "nats://nats.local:4222",
        "NATS_TOKEN": "dev-token",
    }


def build_docmesh_env_overlay() -> dict[str, str]:
    env = dict(os.environ)
    for key, value in _docmesh_default_env().items():
        env.setdefault(key, value)
    return env


@contextmanager
def _apply_missing_docmesh_defaults() -> Iterator[None]:
    added_keys: list[str] = []
    for key, value in _docmesh_default_env().items():
        if key in os.environ:
            continue
        os.environ[key] = value
        added_keys.append(key)
    try:
        yield
    finally:
        for key in added_keys:
            os.environ.pop(key, None)


@lru_cache(maxsize=1)
def load_docmesh_settings(
    enabled_services: tuple[str, ...] | None = None,
) -> ServiceConfigs:
    services = set(enabled_services) if enabled_services else None
    with _apply_missing_docmesh_defaults():
        return load_service_configs(services=services)