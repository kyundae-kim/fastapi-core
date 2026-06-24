from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    DEV = "dev"
    STAGE = "stage"
    PROD = "prod"


class LoggingConfig(BaseModel):
    level: Literal["WARNING", "INFO", "DEBUG"] = "DEBUG"


class KeycloakConfig(BaseModel):
    http_url: HttpUrl = HttpUrl("http://keycloak:8080/")
    manage_url: HttpUrl = HttpUrl("http://keycloak:9000/")
    realm: str = "restapi"
    client_id: str = "fastapi"
    client_secret: str | None = None


class DatabaseConfig(BaseModel):
    host: str = "postgres"
    port: int = 5432
    name: str = "postgres"
    user: str = "postgres"
    password: str = "postgres"
    auth_method: Literal["password", "trust"] = "password"
    sslmode: str = "prefer"
    connect_timeout: int = 5
    echo: bool = False
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30
    pool_recycle: int = 1800
    url: str | None = None

    @property
    def sqlalchemy_database_url(self) -> str:
        if self.url:
            return self.url
        params = f"?sslmode={self.sslmode}&connect_timeout={self.connect_timeout}"
        if self.auth_method == "trust":
            return (
                f"postgresql+psycopg://{self.user}"
                f"@{self.host}:{self.port}/{self.name}{params}"
            )
        return (
            f"postgresql+psycopg://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.name}{params}"
        )


class MinIOConfig(BaseModel):
    endpoint: str = "minio:9000"
    access_key: str = "admin"
    secret_key: str = "password"
    secure: bool = False
    bucket: str = "default"
    presigned_expires_sec: int = 900


class OllamaConfig(BaseModel):
    host: str = "http://ollama:11434"
    model: str = "llama3.2"
    timeout: float = 60.0


class MilvusConfig(BaseModel):
    uri: str = "http://milvus:19530"
    db_name: str = ""
    token: str = ""
    timeout: float | None = None


class LangfuseConfig(BaseModel):
    host: str = "http://langfuse-web:3000"
    public_key: str | None = None
    secret_key: str | None = None
    timeout: int = 5
    tracing_enabled: bool = True
    environment: str | None = None
    release: str | None = None


class NatsConfig(BaseModel):
    servers: str = "nats://nats:4222"
    name: str = "fastapi-core"
    connect_timeout: int = 2
    max_reconnect_attempts: int = 60
    reconnect_time_wait_ms: int = 2000
    queue_group: str = "default-workers"

    @property
    def server_list(self) -> list[str]:
        return [s.strip() for s in self.servers.split(",") if s.strip()]


class CORSSettings(BaseModel):
    origins: list[str] = Field(default_factory=lambda: ["*"])
    credentials: bool = False


class AuthSettings(BaseModel):
    verify_jwt: bool = True
    allow_insecure_jwt_decode: bool = False
    use_introspection: bool = False


class HealthSettings(BaseModel):
    check_keycloak: bool = True
    check_database: bool = True
    check_minio: bool = True
    check_langfuse: bool = False


class LifecycleSettings(BaseModel):
    eager_keycloak: bool | None = None
    eager_database: bool | None = None
    eager_minio: bool | None = None
    eager_langfuse: bool | None = None
    eager_milvus: bool = True
    eager_async_milvus: bool = False
    eager_ollama: bool = True
    eager_nats: bool = False
    use_docmesh_registry: bool = False
    use_docmesh_healthchecks: bool = False


class ServiceSettings(BaseModel):
    cors: CORSSettings = Field(default_factory=CORSSettings)
    auth: AuthSettings = Field(default_factory=AuthSettings)
    health: HealthSettings = Field(default_factory=HealthSettings)
    lifecycle: LifecycleSettings = Field(default_factory=LifecycleSettings)

    @classmethod
    def from_yaml(cls, path: str) -> "ServiceSettings":
        p = Path(path)
        if not p.exists():
            return cls()
        with open(p, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return cls(**data)


@dataclass(frozen=True, slots=True)
class ApplicationSettings:
    config: EnvConfig
    settings: ServiceSettings
    docmesh_settings: Any | None = None


class EnvConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    env: Environment = Environment.DEV
    config_path: str = ".devcontainer/config.yaml"
    root_path: str = "/"
    token_url: str = "/token"

    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    keycloak: KeycloakConfig = Field(default_factory=KeycloakConfig)
    db: DatabaseConfig = Field(default_factory=DatabaseConfig)
    minio: MinIOConfig = Field(default_factory=MinIOConfig)
    ollama: OllamaConfig = Field(default_factory=OllamaConfig)
    milvus: MilvusConfig = Field(default_factory=MilvusConfig)
    langfuse: LangfuseConfig = Field(default_factory=LangfuseConfig)
    nats: NatsConfig = Field(default_factory=NatsConfig)

    keycloak_username: str = "test"
    keycloak_password: str = "test"


def load_env_config(**overrides: Any) -> EnvConfig:
    return EnvConfig(**overrides)


def load_service_settings(config: EnvConfig | None = None) -> ServiceSettings:
    resolved_config = config or load_env_config()
    return ServiceSettings.from_yaml(resolved_config.config_path)


def load_docmesh_settings(config: EnvConfig | None = None) -> Any:
    from fastapi_core.docmesh_bridge import initialize_docmesh_registry

    resolved_config = config or load_env_config()
    initialized = initialize_docmesh_registry(config=resolved_config)
    if initialized is None:
        raise RuntimeError("docmesh registry is unavailable")
    settings, _ = initialized
    return settings


def load_application_settings(
    *,
    config: EnvConfig | None = None,
    include_docmesh: bool = False,
) -> ApplicationSettings:
    resolved_config = config or load_env_config()
    settings = load_service_settings(resolved_config)
    docmesh_settings = (
        load_docmesh_settings(resolved_config) if include_docmesh else None
    )
    return ApplicationSettings(
        config=resolved_config,
        settings=settings,
        docmesh_settings=docmesh_settings,
    )
