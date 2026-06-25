from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from docmesh_py_core import load_settings

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def build_test_settings():
    return load_settings(
        {
            "KEYCLOAK_URL": "http://keycloak.test",
            "KEYCLOAK_REALM": "docmesh",
            "KEYCLOAK_CLIENT_ID": "fastapi-core",
            "KEYCLOAK_CLIENT_SECRET": "secret",
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
    )


@pytest.fixture
def settings():
    return build_test_settings()
