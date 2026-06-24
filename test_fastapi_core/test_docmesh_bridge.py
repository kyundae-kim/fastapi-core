from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from fastapi_core.core.config import EnvConfig
from fastapi_core.docmesh_bridge import (
    REGISTRY_SERVICE_SPECS,
    RegistryServiceSpec,
    build_docmesh_env,
    build_docmesh_keycloak_config,
    get_registry_service_spec,
    initialize_docmesh_registry,
    is_docmesh_available,
    run_docmesh_healthchecks,
)


def test_registry_service_specs_cover_supported_fastapi_state_keys():
    assert REGISTRY_SERVICE_SPECS["auth_provider"] == RegistryServiceSpec(
        registry_name="keycloak",
        state_key="auth_provider",
        mode="sync",
    )
    assert REGISTRY_SERVICE_SPECS["db_engine"] == RegistryServiceSpec(
        registry_name="postgres",
        state_key="db_engine",
        mode="sync",
    )
    assert REGISTRY_SERVICE_SPECS["nats_client"] == RegistryServiceSpec(
        registry_name="nats",
        state_key="nats_client",
        mode="async_builder",
    )
    assert REGISTRY_SERVICE_SPECS["langfuse_client"] == RegistryServiceSpec(
        registry_name="langfuse",
        state_key="langfuse_client",
        mode="sync",
    )


def test_get_registry_service_spec_returns_none_for_unsupported_async_milvus():
    assert get_registry_service_spec("async_milvus_client") is None
    assert "async_milvus_client" not in REGISTRY_SERVICE_SPECS


def test_build_docmesh_env_translates_fastapi_env_config():
    config = EnvConfig()

    env = build_docmesh_env(config)

    assert env["DOCMESH_ENV"] == "development"
    assert env["KEYCLOAK_URL"] == str(config.keycloak.url)
    assert env["POSTGRES_DSN"] == config.db.sqlalchemy_database_url
    assert env["OLLAMA_GENERATION_MODEL"] == config.ollama.model
    assert env["NATS_SERVERS"] == config.nats.servers
    assert env["LANGFUSE_ENABLED"] == (
        "true"
        if (
            config.langfuse.tracing_enabled
            and config.langfuse.public_key
            and config.langfuse.secret_key
        )
        else "false"
    )
    assert env["KEYCLOAK_CLIENT_PUBLIC"] == "true"


@pytest.mark.skipif(not is_docmesh_available(), reason="docmesh_py_core is not installed")
def test_build_docmesh_keycloak_config_adapts_fastapi_config():
    config = EnvConfig(
        keycloak={
            "url": "https://keycloak.example.com/",
            "realm": "myrealm",
            "client_id": "myclient",
            "client_secret": "topsecret",
        }
    )

    keycloak_config = build_docmesh_keycloak_config(config)

    from docmesh_py_core.config import KeycloakConfig as DocmeshKeycloakConfig

    assert isinstance(keycloak_config, DocmeshKeycloakConfig)
    assert keycloak_config.url == str(config.keycloak.url)
    assert keycloak_config.realm == config.keycloak.realm
    assert keycloak_config.client_id == config.keycloak.client_id
    assert keycloak_config.client_secret == config.keycloak.client_secret
    assert keycloak_config.verify_ssl is True


def test_initialize_docmesh_registry_builds_settings_and_registry_from_env_mapping():
    captured_env: dict[str, str] = {}

    def fake_load_settings(env: dict[str, str]) -> object:
        captured_env.update(env)
        return {"settings": True}

    class FakeRegistry:
        def __init__(self, settings: object) -> None:
            self.settings = settings

    fake_module = SimpleNamespace(
        load_settings=fake_load_settings,
        ServiceFactoryRegistry=FakeRegistry,
    )

    with patch(
        "fastapi_core.docmesh_bridge._load_docmesh_module",
        return_value=fake_module,
    ):
        settings, registry = initialize_docmesh_registry(env={"APP_ENV": "test"})

    assert settings == {"settings": True}
    assert registry.settings == settings
    assert captured_env == {"APP_ENV": "test"}


def test_is_docmesh_available_false_when_import_fails():
    with patch(
        "fastapi_core.docmesh_bridge._load_docmesh_module",
        side_effect=ImportError,
    ):
        assert is_docmesh_available() is False


@pytest.mark.skipif(not is_docmesh_available(), reason="docmesh_py_core is not installed")
def test_initialize_docmesh_registry_with_real_package_works_from_fastapi_config():
    settings, registry = initialize_docmesh_registry(config=EnvConfig())

    from docmesh_py_core import ServiceFactoryRegistry, Settings

    assert isinstance(settings, Settings)
    assert isinstance(registry, ServiceFactoryRegistry)
    assert settings.keycloak.client_id == "fastapi"
    assert settings.langfuse.enabled is bool(
        EnvConfig().langfuse.tracing_enabled
        and EnvConfig().langfuse.public_key
        and EnvConfig().langfuse.secret_key
    )


@pytest.mark.skipif(not is_docmesh_available(), reason="docmesh_py_core is not installed")
def test_run_docmesh_healthchecks_uses_real_package():
    ok = run_docmesh_healthchecks(
        {"database": lambda: True, "minio": lambda: True},
        required_services={"database", "minio"},
    )

    assert ok is True


def test_run_docmesh_healthchecks_uses_external_check_all_services():
    called: dict[str, object] = {}

    def fake_check_all_services(service_checks, required_services=None):
        called["service_checks"] = service_checks
        called["required_services"] = required_services
        return SimpleNamespace(ok=True)

    fake_module = SimpleNamespace(check_all_services=fake_check_all_services)

    with patch(
        "fastapi_core.docmesh_bridge._load_docmesh_module",
        return_value=fake_module,
    ):
        ok = run_docmesh_healthchecks(
            {"database": lambda: True},
            required_services={"database"},
        )

    assert ok is True
    assert set(called["service_checks"]) == {"database"}
    assert called["required_services"] == {"database"}
