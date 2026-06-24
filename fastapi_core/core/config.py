from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any, Literal

import yaml
from docmesh_py_core.config import KeycloakConfig, MinioConfig
from pydantic import BaseModel, Field, HttpUrl, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    DEV = "dev"
    STAGE = "stage"
    PROD = "prod"


class LoggingConfig(BaseModel):
    level: Literal["WARNING", "INFO", "DEBUG"] = "DEBUG"


class KeycloakOverlayConfig(BaseModel):
    manage_url: HttpUrl = HttpUrl("http://keycloak:9000/")


class MinioOverlayConfig(BaseModel):
    presigned_expires_sec: int = 900


def _default_keycloak_config() -> KeycloakConfig:
    return KeycloakConfig(
        url="http://keycloak:8080/",
        realm="restapi",
        client_id="fastapi",
        client_secret=None,
        client_public=True,
        verify_ssl=False,
    )


def _default_minio_config() -> MinioConfig:
    return MinioConfig(
        endpoint="minio:9000",
        access_key="admin",
        secret_key="password",
        secure=False,
        bucket="default",
    )


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
    keycloak: KeycloakConfig = Field(default_factory=_default_keycloak_config)
    keycloak_overlay: KeycloakOverlayConfig = Field(default_factory=KeycloakOverlayConfig)
    db: DatabaseConfig = Field(default_factory=DatabaseConfig)
    minio: MinioConfig = Field(default_factory=_default_minio_config)
    minio_overlay: MinioOverlayConfig = Field(default_factory=MinioOverlayConfig)
    ollama: OllamaConfig = Field(default_factory=OllamaConfig)
    milvus: MilvusConfig = Field(default_factory=MilvusConfig)
    langfuse: LangfuseConfig = Field(default_factory=LangfuseConfig)
    nats: NatsConfig = Field(default_factory=NatsConfig)

    keycloak_username: str = "test"
    keycloak_password: str = "test"

    @model_validator(mode="before")
    @classmethod
    def normalize_config_inputs(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        normalized = dict(data)
        raw_keycloak = normalized.get("keycloak")
        if isinstance(raw_keycloak, dict):
            keycloak_data = dict(raw_keycloak)
            manage_url = keycloak_data.pop("manage_url", None)
            if "url" not in keycloak_data and "http_url" in keycloak_data:
                keycloak_data["url"] = keycloak_data.pop("http_url")
            if "url" in keycloak_data and "verify_ssl" not in keycloak_data:
                keycloak_data["verify_ssl"] = str(keycloak_data["url"]).startswith(
                    "https://"
                )

            merged_keycloak = _default_keycloak_config().model_dump(mode="python")
            merged_keycloak.update(keycloak_data)
            normalized["keycloak"] = merged_keycloak

            if manage_url is not None:
                raw_overlay = normalized.get("keycloak_overlay")
                if isinstance(raw_overlay, dict):
                    overlay_data = dict(raw_overlay)
                elif raw_overlay is None:
                    overlay_data = {}
                else:
                    overlay_data = raw_overlay.model_dump(mode="python")
                overlay_data.setdefault("manage_url", manage_url)
                normalized["keycloak_overlay"] = overlay_data

        raw_minio = normalized.get("minio")
        if isinstance(raw_minio, dict):
            minio_data = dict(raw_minio)
            presigned_expires_sec = minio_data.pop("presigned_expires_sec", None)

            merged_minio = _default_minio_config().model_dump(mode="python")
            merged_minio.update(minio_data)
            normalized["minio"] = merged_minio

            if presigned_expires_sec is not None:
                raw_minio_overlay = normalized.get("minio_overlay")
                if isinstance(raw_minio_overlay, dict):
                    minio_overlay_data = dict(raw_minio_overlay)
                elif raw_minio_overlay is None:
                    minio_overlay_data = {}
                else:
                    minio_overlay_data = raw_minio_overlay.model_dump(mode="python")
                minio_overlay_data.setdefault(
                    "presigned_expires_sec",
                    presigned_expires_sec,
                )
                normalized["minio_overlay"] = minio_overlay_data

        return normalized


def load_env_config(**overrides: Any) -> EnvConfig:
    return EnvConfig(**overrides)


def load_service_settings(config: EnvConfig | None = None) -> ServiceSettings:
    resolved_config = config or load_env_config()
    return ServiceSettings.from_yaml(resolved_config.config_path)
