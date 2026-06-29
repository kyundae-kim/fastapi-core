from __future__ import annotations

import os
from functools import lru_cache

from docmesh_py_core import Settings, load_settings


def build_docmesh_env_overlay() -> dict[str, str]:
    env = dict(os.environ)
    env.setdefault("KEYCLOAK_URL", "http://keycloak.local")
    env.setdefault("KEYCLOAK_REALM", "docmesh")
    env.setdefault("KEYCLOAK_CLIENT_ID", "fastapi-core")
    env.setdefault("KEYCLOAK_CLIENT_SECRET", "dev-secret")
    env.setdefault("SQLITE_PATH", ":memory:")
    env.setdefault("MINIO_ENDPOINT", "minio.local:9000")
    env.setdefault("MINIO_ACCESS_KEY", "minio")
    env.setdefault("MINIO_SECRET_KEY", "miniosecret")
    env.setdefault("MILVUS_URI", "http://milvus.local:19530")
    env.setdefault("OLLAMA_HOST", "http://ollama.local:11434")
    env.setdefault("LANGFUSE_HOST", "http://langfuse.local:3000")
    env.setdefault("LANGFUSE_PUBLIC_KEY", "dev-public")
    env.setdefault("LANGFUSE_SECRET_KEY", "dev-secret")
    env.setdefault("NATS_SERVERS", "nats://nats.local:4222")
    env.setdefault("NATS_TOKEN", "dev-token")
    return env


@lru_cache(maxsize=1)
def load_docmesh_settings(enabled_services: tuple[str, ...] | None = None) -> Settings:
    env = build_docmesh_env_overlay()
    services = set(enabled_services) if enabled_services else None
    return load_settings(env, services=services)
