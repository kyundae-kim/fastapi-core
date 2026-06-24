from pathlib import Path

import pytest

from fastapi_core.core.config import (
    DatabaseConfig,
    EnvConfig,
    LangfuseConfig,
    MinIOConfig,
    ServiceSettings,
    load_application_settings,
    load_docmesh_settings,
    load_service_settings,
)
from fastapi_core.docmesh_bridge import is_docmesh_available


def test_database_config_url_with_password_auth():
    config = DatabaseConfig(
        host="localhost",
        port=5432,
        name="testdb",
        user="user",
        password="pass",
        auth_method="password",
        sslmode="disable",
        connect_timeout=5,
    )
    url = config.sqlalchemy_database_url
    assert url == (
        "postgresql+psycopg://user:pass@localhost:5432/testdb"
        "?sslmode=disable&connect_timeout=5"
    )


def test_database_config_url_with_trust_auth():
    config = DatabaseConfig(
        host="localhost",
        port=5432,
        name="testdb",
        user="user",
        auth_method="trust",
        sslmode="disable",
        connect_timeout=5,
    )
    url = config.sqlalchemy_database_url
    assert url == (
        "postgresql+psycopg://user@localhost:5432/testdb"
        "?sslmode=disable&connect_timeout=5"
    )


def test_database_config_url_direct():
    direct_url = "postgresql+psycopg://custom@host:5432/db"
    config = DatabaseConfig(url=direct_url)
    assert config.sqlalchemy_database_url == direct_url


def test_env_config_defaults():
    config = EnvConfig()
    assert config.env.value == "dev"
    assert config.keycloak.realm == "restapi"
    assert config.keycloak.client_id == "fastapi"
    assert config.db.host == "postgres"
    assert config.db.port == 5432
    assert config.minio.bucket == "default"
    assert config.logging.level in ("WARNING", "INFO", "DEBUG")


def test_minio_config_defaults():
    config = MinIOConfig()
    assert config.endpoint == "minio:9000"
    assert config.secure is False
    assert config.bucket == "default"
    assert config.access_key == "admin"


def test_database_config_password_not_in_trust_url():
    config = DatabaseConfig(
        user="pguser",
        password="secret",
        auth_method="trust",
        host="db",
        port=5432,
        name="mydb",
        sslmode="prefer",
        connect_timeout=10,
    )
    url = config.sqlalchemy_database_url
    assert "secret" not in url
    assert "pguser@db" in url


def test_database_pool_defaults():
    config = DatabaseConfig()
    assert config.pool_size == 5
    assert config.max_overflow == 10
    assert config.pool_timeout == 30
    assert config.pool_recycle == 1800


def test_minio_presigned_default_expires():
    config = MinIOConfig()
    assert config.presigned_expires_sec == 900


def test_langfuse_config_defaults():
    config = LangfuseConfig()
    assert config.host == "http://langfuse-web:3000"
    assert config.public_key is None
    assert config.secret_key is None
    assert config.timeout == 5
    assert config.tracing_enabled is True


def test_env_config_langfuse_defaults():
    config = EnvConfig()
    assert config.langfuse.host == "http://langfuse-web:3000"
    assert config.langfuse.timeout == 5


def test_load_service_settings_uses_config_path(tmp_path: Path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "cors:\n  origins:\n    - https://example.com\n",
        encoding="utf-8",
    )

    settings = load_service_settings(EnvConfig(config_path=str(config_path)))

    assert isinstance(settings, ServiceSettings)
    assert settings.cors.origins == ["https://example.com"]


def test_load_application_settings_reuses_provided_config():
    config = EnvConfig()

    bundle = load_application_settings(config=config)

    assert bundle.config is config
    assert isinstance(bundle.settings, ServiceSettings)
    assert bundle.docmesh_settings is None


@pytest.mark.skipif(not is_docmesh_available(), reason="docmesh_py_core is not installed")
def test_load_docmesh_settings_returns_real_docmesh_settings():
    settings = load_docmesh_settings(config=EnvConfig())

    from docmesh_py_core import Settings

    assert isinstance(settings, Settings)


@pytest.mark.skipif(not is_docmesh_available(), reason="docmesh_py_core is not installed")
def test_load_application_settings_can_include_real_docmesh_settings():
    bundle = load_application_settings(include_docmesh=True)

    from docmesh_py_core import Settings

    assert isinstance(bundle.docmesh_settings, Settings)
