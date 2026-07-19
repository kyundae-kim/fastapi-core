from __future__ import annotations

from pathlib import Path

import pytest
from docmesh_py_core import StartupFailureMode
from pydantic import ValidationError

import fastapi_core.docmesh_settings as docmesh_settings_module
from fastapi_core.config import AppConfig, load_app_config
from fastapi_core.docmesh_settings import load_docmesh_settings



def test_app_config_reads_env_fields_from_settings(monkeypatch):
    cases = (
        ("ROOT_PATH", "/api", "root_path", "/api"),
        ("TOKEN_URL", "/api/auth/token", "token_url", "/api/auth/token"),
        (
            "CORS_ORIGINS",
            "https://a.example, https://b.example",
            "cors_origins",
            ["https://a.example", "https://b.example"],
        ),
        ("CORS_CREDENTIALS", "true", "cors_credentials", True),
        ("READINESS_PARALLEL", "true", "readiness_parallel", True),
        (
            "READINESS_TIMEOUT_SECONDS",
            "0.25",
            "readiness_timeout_seconds",
            0.25,
        ),
        (
            "READINESS_OVERALL_TIMEOUT_SECONDS",
            "1.5",
            "readiness_overall_timeout_seconds",
            1.5,
        ),
        (
            "DOCMESH_SERVICE_ALTERNATIVES",
            "postgres,sqlite;minio,milvus",
            "service_alternatives",
            [["postgres", "sqlite"], ["minio", "milvus"]],
        ),
        ("DOCMESH_HEALTHCHECK_ENABLED", "true", "startup_healthcheck", True),
        (
            "DOCMESH_STARTUP_FAILURE_MODE",
            "report",
            "startup_failure_mode",
            StartupFailureMode.REPORT,
        ),
        (
            "DOCMESH_STARTUP_HEALTHCHECK_ATTEMPTS",
            "3",
            "startup_healthcheck_attempts",
            3,
        ),
        (
            "DOCMESH_STARTUP_HEALTHCHECK_RETRY_DELAY_SECONDS",
            "0.25",
            "startup_healthcheck_retry_delay_seconds",
            0.25,
        ),
        ("DOCMESH_LOG_LEVEL", "INFO", "log_level", "INFO"),
        ("APP_LOG_PATH", "/tmp/app.log", "log_path", "/tmp/app.log"),
        ("APP_LOG_JSON", "false", "log_json", False),
        ("APP_LOG_FORCE", "true", "log_force", True),
        (
            "DOCMESH_SERVICES",
            "keycloak,sqlite",
            "enabled_services",
            ["keycloak", "sqlite"],
        ),
        ("READINESS_REQUIRED_SERVICES", "sqlite", "required_services", ["sqlite"]),
    )
    for environment_name, raw_value, _, _ in cases:
        monkeypatch.setenv(environment_name, raw_value)
    load_app_config.cache_clear()

    config = load_app_config()

    for _, _, field_name, expected in cases:
        assert getattr(config, field_name) == expected
    load_app_config.cache_clear()



def test_app_config_defaults_match_existing_behavior(monkeypatch):
    environment_names = {
        "ROOT_PATH",
        "TOKEN_URL",
        "CORS_ORIGINS",
        "CORS_CREDENTIALS",
        "READINESS_PARALLEL",
        "READINESS_TIMEOUT_SECONDS",
        "READINESS_OVERALL_TIMEOUT_SECONDS",
        "DOCMESH_SERVICE_ALTERNATIVES",
        "DOCMESH_HEALTHCHECK_ENABLED",
        "DOCMESH_STARTUP_FAILURE_MODE",
        "DOCMESH_STARTUP_HEALTHCHECK_ATTEMPTS",
        "DOCMESH_STARTUP_HEALTHCHECK_RETRY_DELAY_SECONDS",
        "DOCMESH_LOG_LEVEL",
        "APP_LOG_PATH",
        "APP_LOG_JSON",
        "APP_LOG_FORCE",
        "DOCMESH_SERVICES",
        "READINESS_REQUIRED_SERVICES",
    }
    for key in environment_names:
        monkeypatch.delenv(key, raising=False)
    load_app_config.cache_clear()

    config = load_app_config()

    assert config == AppConfig()
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


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("startup_healthcheck_attempts", 0),
        ("startup_healthcheck_retry_delay_seconds", -0.1),
    ],
)
def test_app_config_rejects_invalid_startup_healthcheck_retry_policy(
    field_name,
    value,
):
    with pytest.raises(ValidationError, match=field_name):
        AppConfig(**{field_name: value})


def test_env_example_does_not_advertise_removed_postgres_dsn():
    env_example = Path(__file__).parents[1].joinpath(".env.example").read_text(
        encoding="utf-8"
    )

    assert "POSTGRES_DSN" not in env_example


def test_app_config_prefers_field_name_over_environment_alias():
    config = AppConfig(log_level="INFO", DOCMESH_LOG_LEVEL="DEBUG")

    assert config.log_level == "INFO"


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        ({"log_level": "INFO"}, "INFO"),
        ({"DOCMESH_LOG_LEVEL": "DEBUG"}, "DEBUG"),
        (
            {"log_level": "INFO", "DOCMESH_LOG_LEVEL": "DEBUG"},
            "INFO",
        ),
    ],
)
def test_app_config_preserves_field_name_and_alias_precedence(values, expected):
    assert AppConfig(**values).log_level == expected



def test_load_docmesh_settings_uses_selected_services():
    settings = load_docmesh_settings(("sqlite",))

    assert settings.sqlite is not None
    assert settings.keycloak is None


def test_load_docmesh_settings_preserves_explicitly_empty_selection():
    settings = load_docmesh_settings(())

    assert all(
        getattr(settings, service) is None
        for service in (
            "keycloak",
            "postgres",
            "sqlite",
            "minio",
            "milvus",
            "ollama",
            "langfuse",
            "nats",
        )
    )


def test_load_docmesh_settings_uses_v04_keyword_only_loader(monkeypatch):
    captured: dict[str, object] = {}
    sentinel = object()

    def fake_load_service_configs(*, services):
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
    load_docmesh_settings.cache_clear()
