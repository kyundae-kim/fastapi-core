from __future__ import annotations

from functools import lru_cache
from typing import Any

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import (
    BaseSettings,
    EnvSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)


_CSV_LIST_FIELDS = frozenset(
    {"cors_origins", "enabled_services", "required_services"}
)


class _AppEnvSettingsSource(EnvSettingsSource):
    def prepare_field_value(
        self,
        field_name: str,
        field: Any,
        value: Any,
        value_is_complex: bool,
    ) -> Any:
        if field_name in _CSV_LIST_FIELDS and value == "":
            return []
        return super().prepare_field_value(
            field_name,
            field,
            value,
            value_is_complex,
        )


def _parse_csv_env(raw: str) -> list[str]:
    return [value.strip() for value in raw.split(",") if value.strip()]


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="",
        extra="ignore",
        enable_decoding=False,
    )

    root_path: str = ""
    token_url: str = "/token"
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])
    cors_credentials: bool = False
    readiness_parallel: bool = False
    readiness_timeout_seconds: float | None = Field(
        default=None,
        gt=0,
        validation_alias=AliasChoices(
            "readiness_timeout_seconds",
            "READINESS_TIMEOUT_SECONDS",
        ),
    )
    readiness_overall_timeout_seconds: float | None = Field(
        default=None,
        gt=0,
        validation_alias=AliasChoices(
            "readiness_overall_timeout_seconds",
            "READINESS_OVERALL_TIMEOUT_SECONDS",
        ),
    )
    service_alternatives: list[list[str]] = Field(
        default_factory=list,
        validation_alias=AliasChoices(
            "service_alternatives",
            "DOCMESH_SERVICE_ALTERNATIVES",
        ),
    )
    startup_healthcheck: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "startup_healthcheck",
            "DOCMESH_HEALTHCHECK_ENABLED",
        ),
    )
    log_level: str | None = Field(
        default="WARNING",
        validation_alias=AliasChoices("log_level", "DOCMESH_LOG_LEVEL"),
    )
    log_path: str | None = Field(
        default=None,
        validation_alias=AliasChoices("log_path", "APP_LOG_PATH"),
    )
    log_json: bool = Field(
        default=True,
        validation_alias=AliasChoices("log_json", "APP_LOG_JSON"),
    )
    log_force: bool = Field(
        default=False,
        validation_alias=AliasChoices("log_force", "APP_LOG_FORCE"),
    )
    enabled_services: list[str] = Field(
        default_factory=lambda: ["keycloak"],
        validation_alias=AliasChoices("enabled_services", "DOCMESH_SERVICES"),
    )
    required_services: list[str] = Field(
        default_factory=lambda: ["keycloak"],
        validation_alias=AliasChoices("required_services", "READINESS_REQUIRED_SERVICES"),
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        del env_settings
        return (
            init_settings,
            _AppEnvSettingsSource(settings_cls),
            dotenv_settings,
            file_secret_settings,
        )

    @field_validator("cors_origins", "enabled_services", "required_services", mode="before")
    @classmethod
    def _parse_csv_or_sequence(cls, value: Any) -> Any:
        if isinstance(value, str):
            if not value.strip():
                raise ValueError(
                    "empty strings are only supported through environment variables"
                )
            return _parse_csv_env(value)
        return value

    @model_validator(mode="after")
    def _validate_required_services_are_enabled(self) -> AppConfig:
        missing = set(self.required_services) - set(self.enabled_services)
        if missing:
            names = ", ".join(sorted(missing))
            raise ValueError(
                "required_services must be included in enabled_services: "
                f"{names}"
            )
        return self

    @field_validator("service_alternatives", mode="before")
    @classmethod
    def _parse_service_alternatives(cls, value: Any) -> Any:
        if value in (None, ""):
            return []
        if isinstance(value, str):
            return [
                services
                for group in value.split(";")
                if (services := _parse_csv_env(group))
            ]
        return value


@lru_cache(maxsize=1)
def load_app_config() -> AppConfig:
    return AppConfig()
