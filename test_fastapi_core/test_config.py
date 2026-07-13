from __future__ import annotations

import os

import pytest
from pydantic import ValidationError

import fastapi_core.docmesh_settings as docmesh_settings_module
from fastapi_core.config import AppConfig, load_app_config
from fastapi_core.docmesh_settings import build_docmesh_env_overlay, load_docmesh_settings



def test_app_config_reads_env_fields_from_settings(monkeypatch):
    monkeypatch.setenv("ROOT_PATH", "/api")
    monkeypatch.setenv("TOKEN_URL", "/api/auth/token")
    monkeypatch.setenv("CORS_ORIGINS", "https://a.example, https://b.example")
    monkeypatch.setenv("CORS_CREDENTIALS", "true")
    monkeypatch.setenv("READINESS_PARALLEL", "true")
    monkeypatch.setenv("READINESS_TIMEOUT_SECONDS", "0.25")
    monkeypatch.setenv("READINESS_OVERALL_TIMEOUT_SECONDS", "1.5")
    monkeypatch.setenv(
        "DOCMESH_SERVICE_ALTERNATIVES",
        "postgres,sqlite;minio,milvus",
    )
    monkeypatch.setenv("DOCMESH_HEALTHCHECK_ENABLED", "true")
    monkeypatch.setenv("DOCMESH_LOG_LEVEL", "INFO")
    monkeypatch.setenv("APP_LOG_PATH", "/tmp/app.log")
    monkeypatch.setenv("APP_LOG_JSON", "false")
    monkeypatch.setenv("APP_LOG_FORCE", "true")
    monkeypatch.setenv("DOCMESH_SERVICES", "keycloak,sqlite")
    monkeypatch.setenv("READINESS_REQUIRED_SERVICES", "sqlite")
    load_app_config.cache_clear()

    config = load_app_config()

    assert config.root_path == "/api"
    assert config.token_url == "/api/auth/token"
    assert config.cors_origins == ["https://a.example", "https://b.example"]
    assert config.cors_credentials is True
    assert config.readiness_parallel is True
    assert config.readiness_timeout_seconds == 0.25
    assert config.readiness_overall_timeout_seconds == 1.5
    assert config.service_alternatives == [
        ["postgres", "sqlite"],
        ["minio", "milvus"],
    ]
    assert config.startup_healthcheck is True
    assert config.log_level == "INFO"
    assert config.log_path == "/tmp/app.log"
    assert config.log_json is False
    assert config.log_force is True
    assert config.enabled_services == ["keycloak", "sqlite"]
    assert config.required_services == ["sqlite"]
    load_app_config.cache_clear()



def test_app_config_defaults_match_existing_behavior(monkeypatch):
    for key in [
        "ROOT_PATH",
        "TOKEN_URL",
        "CORS_ORIGINS",
        "CORS_CREDENTIALS",
        "READINESS_PARALLEL",
        "READINESS_TIMEOUT_SECONDS",
        "READINESS_OVERALL_TIMEOUT_SECONDS",
        "DOCMESH_SERVICE_ALTERNATIVES",
        "DOCMESH_HEALTHCHECK_ENABLED",
        "DOCMESH_LOG_LEVEL",
        "APP_LOG_PATH",
        "APP_LOG_JSON",
        "APP_LOG_FORCE",
        "DOCMESH_SERVICES",
        "READINESS_REQUIRED_SERVICES",
    ]:
        monkeypatch.delenv(key, raising=False)
    load_app_config.cache_clear()

    config = load_app_config()

    assert isinstance(config, AppConfig)
    assert config.root_path == ""
    assert config.token_url == "/token"
    assert config.cors_origins == ["*"]
    assert config.cors_credentials is False
    assert config.readiness_parallel is False
    assert config.readiness_timeout_seconds is None
    assert config.readiness_overall_timeout_seconds is None
    assert config.service_alternatives == []
    assert config.startup_healthcheck is False
    assert config.log_level == "WARNING"
    assert config.log_path is None
    assert config.log_json is True
    assert config.log_force is False
    assert config.enabled_services == ["keycloak"]
    assert config.required_services == ["keycloak"]
    load_app_config.cache_clear()


def test_app_config_treats_explicitly_empty_csv_environment_as_empty_lists(
    monkeypatch,
):
    monkeypatch.setenv("CORS_ORIGINS", "")
    monkeypatch.setenv("DOCMESH_SERVICES", "")
    monkeypatch.setenv("READINESS_REQUIRED_SERVICES", "")
    load_app_config.cache_clear()

    config = load_app_config()

    assert config.cors_origins == []
    assert config.enabled_services == []
    assert config.required_services == []
    load_app_config.cache_clear()


@pytest.mark.parametrize(
    "field_name",
    ["cors_origins", "enabled_services", "required_services"],
)
def test_app_config_rejects_empty_csv_string_in_direct_constructor(field_name):
    with pytest.raises(ValidationError, match=field_name):
        AppConfig(**{field_name: ""})


def test_app_config_rejects_required_service_that_is_not_enabled():
    with pytest.raises(
        ValidationError,
        match="required_services must be included in enabled_services",
    ):
        AppConfig(
            enabled_services=["sqlite"],
            required_services=["keycloak"],
        )



def test_build_docmesh_env_overlay_applies_defaults_without_overwriting(monkeypatch):
    monkeypatch.setenv("KEYCLOAK_URL", "http://override.test")
    monkeypatch.setenv("NATS_TOKEN", "custom-token")
    monkeypatch.delenv("KEYCLOAK_REALM", raising=False)
    monkeypatch.delenv("POSTGRES_DSN", raising=False)
    monkeypatch.delenv("SQLITE_PATH", raising=False)
    monkeypatch.delenv("LANGFUSE_HOST", raising=False)

    env = build_docmesh_env_overlay()

    assert env["KEYCLOAK_URL"] == "http://override.test"
    assert env["NATS_TOKEN"] == "custom-token"
    assert env["KEYCLOAK_REALM"] == "docmesh"
    assert env["POSTGRES_DSN"] == (
        "postgresql+psycopg://docmesh:dev-secret@postgres.local:5432/docmesh"
    )
    assert env["SQLITE_PATH"] == ":memory:"
    assert env["LANGFUSE_HOST"] == "http://langfuse.local:3000"



def test_load_docmesh_settings_uses_selected_services():
    settings = load_docmesh_settings(("sqlite",))

    assert settings.sqlite is not None
    assert settings.keycloak is None


def test_load_docmesh_settings_passes_overlay_without_mutating_environment(monkeypatch):
    captured: dict[str, object] = {}
    sentinel = object()
    original_environment = dict(os.environ)

    def fake_load_service_configs(env, *, services):
        captured["env"] = env
        captured["services"] = services
        return sentinel

    monkeypatch.setattr(
        docmesh_settings_module,
        "load_service_configs",
        fake_load_service_configs,
    )
    load_docmesh_settings.cache_clear()

    result = load_docmesh_settings(("sqlite",))

    assert result is sentinel
    assert captured["services"] == {"sqlite"}
    assert captured["env"]["SQLITE_PATH"] == ":memory:"
    assert dict(os.environ) == original_environment
    load_docmesh_settings.cache_clear()


def test_load_docmesh_settings_loads_postgres_from_default_env(monkeypatch):
    monkeypatch.delenv("POSTGRES_DSN", raising=False)
    load_docmesh_settings.cache_clear()

    settings = load_docmesh_settings(("postgres",))

    assert settings.postgres is not None
    assert settings.postgres.dsn == (
        "postgresql+psycopg://docmesh:dev-secret@postgres.local:5432/docmesh"
    )
    load_docmesh_settings.cache_clear()
