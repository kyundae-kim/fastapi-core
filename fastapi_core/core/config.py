from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import AliasChoices, BaseModel, Field, HttpUrl, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    DEV = "dev"
    STAGE = "stage"
    PROD = "prod"


class LoggingConfig(BaseModel):
    level: Literal["WARNING", "INFO", "DEBUG"] = "DEBUG"


class KeycloakConfig(BaseModel):
    url: HttpUrl = Field(
        default=HttpUrl("http://keycloak:8080/"),
        validation_alias=AliasChoices("url", "http_url"),
    )
    manage_url: HttpUrl = HttpUrl("http://keycloak:9000/")
    realm: str = "restapi"
    client_id: str = "fastapi"
    client_secret: str | None = None

    @property
    def http_url(self) -> HttpUrl:
        return self.url


class KeycloakOverlayConfig(BaseModel):
    manage_url: HttpUrl = HttpUrl("http://keycloak:9000/")


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
    keycloak_overlay: KeycloakOverlayConfig = Field(default_factory=KeycloakOverlayConfig)
    db: DatabaseConfig = Field(default_factory=DatabaseConfig)
    minio: MinIOConfig = Field(default_factory=MinIOConfig)
    ollama: OllamaConfig = Field(default_factory=OllamaConfig)
    milvus: MilvusConfig = Field(default_factory=MilvusConfig)
    langfuse: LangfuseConfig = Field(default_factory=LangfuseConfig)
    nats: NatsConfig = Field(default_factory=NatsConfig)

    keycloak_username: str = "test"
    keycloak_password: str = "test"

    @model_validator(mode="after")
    def backfill_keycloak_overlay_manage_url(self) -> "EnvConfig":
        default_manage_url = KeycloakOverlayConfig().manage_url
        if (
            self.keycloak_overlay.manage_url == default_manage_url
            and self.keycloak.manage_url != default_manage_url
        ):
            self.keycloak_overlay.manage_url = self.keycloak.manage_url
        return self


def load_env_config(**overrides: Any) -> EnvConfig:
    return EnvConfig(**overrides)


def load_service_settings(config: EnvConfig | None = None) -> ServiceSettings:
    resolved_config = config or load_env_config()
    return ServiceSettings.from_yaml(resolved_config.config_path)
