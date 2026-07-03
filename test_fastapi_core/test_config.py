from __future__ import annotations

from fastapi_core.config import AppConfig, load_app_config
from fastapi_core.docmesh_settings import build_docmesh_env_overlay, load_docmesh_settings



def test_app_config_reads_env_fields_from_settings(monkeypatch):
    monkeypatch.setenv("ROOT_PATH", "/api")
    monkeypatch.setenv("TOKEN_URL", "/api/auth/token")
    monkeypatch.setenv("CORS_ORIGINS", "https://a.example, https://b.example")
    monkeypatch.setenv("CORS_CREDENTIALS", "true")
    monkeypatch.setenv("READINESS_PARALLEL", "true")
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
    assert config.log_level == "WARNING"
    assert config.log_path is None
    assert config.log_json is True
    assert config.log_force is False
    assert config.enabled_services == ["keycloak"]
    assert config.required_services == ["keycloak"]
    load_app_config.cache_clear()



def test_build_docmesh_env_overlay_applies_defaults_without_overwriting(monkeypatch):
    monkeypatch.setenv("KEYCLOAK_URL", "http://override.test")
    monkeypatch.setenv("NATS_TOKEN", "custom-token")
    monkeypatch.delenv("KEYCLOAK_REALM", raising=False)
    monkeypatch.delenv("SQLITE_PATH", raising=False)
    monkeypatch.delenv("LANGFUSE_HOST", raising=False)

    env = build_docmesh_env_overlay()

    assert env["KEYCLOAK_URL"] == "http://override.test"
    assert env["NATS_TOKEN"] == "custom-token"
    assert env["KEYCLOAK_REALM"] == "docmesh"
    assert env["SQLITE_PATH"] == ":memory:"
    assert env["LANGFUSE_HOST"] == "http://langfuse.local:3000"



def test_load_docmesh_settings_uses_selected_services():
    settings = load_docmesh_settings(("sqlite",))

    assert settings.sqlite is not None
    assert settings.keycloak is None
