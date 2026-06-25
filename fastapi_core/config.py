from __future__ import annotations

import os
from functools import lru_cache

from pydantic import BaseModel, Field
from docmesh_py_core import Settings, load_settings


class AppConfig(BaseModel):
    root_path: str = ""
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])
    cors_credentials: bool = False
    readiness_parallel: bool = False


@lru_cache(maxsize=1)
def load_app_config() -> AppConfig:
    raw_origins = os.getenv("CORS_ORIGINS", "*")
    origins = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
    return AppConfig(
        root_path=os.getenv("ROOT_PATH", ""),
        cors_origins=origins or ["*"],
        cors_credentials=os.getenv("CORS_CREDENTIALS", "false").lower() == "true",
        readiness_parallel=os.getenv("READINESS_PARALLEL", "false").lower() == "true",
    )


@lru_cache(maxsize=1)
def load_default_settings() -> Settings:
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
    return load_settings(env)
