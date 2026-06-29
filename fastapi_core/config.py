from __future__ import annotations

import os
from functools import lru_cache

from pydantic import BaseModel, Field
from docmesh_py_core import Settings, load_settings


def _parse_csv_env(raw: str) -> list[str]:
    return [value.strip() for value in raw.split(",") if value.strip()]


class AppConfig(BaseModel):
    root_path: str = ""
    token_url: str = "/token"
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])
    cors_credentials: bool = False
    readiness_parallel: bool = False
    log_level: str | None = "WARNING"
    log_path: str | None = None
    log_json: bool = True
    log_force: bool = False
    enabled_services: list[str] = Field(default_factory=lambda: ["keycloak"])
    required_services: list[str] = Field(default_factory=lambda: ["keycloak"])


@lru_cache(maxsize=1)
def load_app_config() -> AppConfig:
    raw_origins = os.getenv("CORS_ORIGINS", "*")
    origins = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
    enabled_services = _parse_csv_env(os.getenv("DOCMESH_SERVICES", "keycloak"))
    required_services = _parse_csv_env(os.getenv("READINESS_REQUIRED_SERVICES", "keycloak"))
    return AppConfig(
        root_path=os.getenv("ROOT_PATH", ""),
        token_url=os.getenv("TOKEN_URL", "/token"),
        cors_origins=origins or ["*"],
        cors_credentials=os.getenv("CORS_CREDENTIALS", "false").lower() == "true",
        readiness_parallel=os.getenv("READINESS_PARALLEL", "false").lower() == "true",
        log_level=os.getenv("DOCMESH_LOG_LEVEL", "WARNING"),
        log_path=os.getenv("APP_LOG_PATH"),
        log_json=os.getenv("APP_LOG_JSON", "true").lower() != "false",
        log_force=os.getenv("APP_LOG_FORCE", "false").lower() == "true",
        enabled_services=enabled_services or ["keycloak"],
        required_services=required_services or ["keycloak"],
    )


@lru_cache(maxsize=1)
def load_default_settings(enabled_services: tuple[str, ...] | None = None) -> Settings:
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
    services = set(enabled_services) if enabled_services else None
    return load_settings(env, services=services)
