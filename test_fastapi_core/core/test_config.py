import inspect
from pathlib import Path

import pytest

import fastapi_core.core.config as core_config
from fastapi_core.core.config import (
    DatabaseConfig,
    EnvConfig,
    KeycloakConfig,
    KeycloakOverlayConfig,
    LangfuseConfig,
    MilvusConfig,
    MinioConfig,
    MinioOverlayConfig,
    ServiceSettings,
    load_service_settings,
)
from fastapi_core.docmesh_bridge import (
    is_docmesh_available,
    load_docmesh_settings,
    resolve_milvus_config,
)


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
    assert str(config.keycloak.url) == "http://keycloak:8080/"
    assert config.keycloak.realm == "restapi"
    assert config.keycloak.client_id == "fastapi"
    assert str(config.keycloak_overlay.manage_url) == "http://keycloak:9000/"
    assert config.db.host == "postgres"
    assert config.db.port == 5432
    assert config.minio.bucket == "default"
    assert config.minio.secure is False
    assert config.minio_overlay.presigned_expires_sec == 900
    assert config.logging.level in ("WARNING", "INFO", "DEBUG")


def test_env_config_keycloak_overlay_override():
    config = EnvConfig(
        keycloak_overlay=KeycloakOverlayConfig(
            manage_url="https://keycloak-admin.example.com/"
        )
    )

    assert str(config.keycloak_overlay.manage_url) == "https://keycloak-admin.example.com/"


def test_core_config_reexports_docmesh_keycloak_config():
    from docmesh_py_core.config import KeycloakConfig as DocmeshKeycloakConfig

    assert KeycloakConfig is DocmeshKeycloakConfig
    assert KeycloakConfig.__module__ == "docmesh_py_core.config"


def test_core_config_reexports_docmesh_minio_config():
    from docmesh_py_core.config import MinioConfig as DocmeshMinioConfig

    assert MinioConfig is DocmeshMinioConfig
    assert MinioConfig.__module__ == "docmesh_py_core.config"


def test_env_config_normalizes_legacy_keycloak_inputs_for_docmesh_model():
    config = EnvConfig(
        keycloak={
            "http_url": "https://legacy-keycloak.example.com/",
            "manage_url": "https://keycloak-admin.example.com/",
            "realm": "myrealm",
            "client_id": "myclient",
        }
    )

    assert str(config.keycloak.url) == "https://legacy-keycloak.example.com/"
    assert config.keycloak.realm == "myrealm"
    assert config.keycloak.client_id == "myclient"
    assert config.keycloak.client_public is True
    assert config.keycloak.verify_ssl is True
    assert str(config.keycloak_overlay.manage_url) == "https://keycloak-admin.example.com/"


def test_env_config_normalizes_legacy_minio_presigned_override():
    config = EnvConfig(
        minio={
            "endpoint": "minio.example.com:9000",
            "access_key": "key",
            "secret_key": "secret",
            "secure": True,
            "bucket": "documents",
            "presigned_expires_sec": 321,
        }
    )

    assert config.minio.endpoint == "minio.example.com:9000"
    assert config.minio.access_key == "key"
    assert config.minio.secret_key == "secret"
    assert config.minio.secure is True
    assert config.minio.bucket == "documents"
    assert config.minio_overlay.presigned_expires_sec == 321


def test_minio_config_defaults():
    config = MinioConfig(
        endpoint="minio:9000",
        access_key="admin",
        secret_key="password",
        secure=False,
        bucket="default",
    )
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
    config = MinioOverlayConfig()
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


def test_core_config_exports_only_pure_config_helpers():
    assert inspect.isfunction(core_config.load_env_config)
    assert inspect.isfunction(core_config.load_service_settings)
    assert not hasattr(core_config, "ApplicationSettings")
    assert not hasattr(core_config, "load_application_settings")
    assert not hasattr(core_config, "load_docmesh_settings")
    assert not hasattr(core_config, "resolve_milvus_config")


@pytest.mark.skipif(not is_docmesh_available(), reason="docmesh_py_core is not installed")
def test_load_docmesh_settings_returns_real_docmesh_settings():
    settings = load_docmesh_settings(config=EnvConfig())

    from docmesh_py_core import Settings

    assert isinstance(settings, Settings)


def test_resolve_milvus_config_prefers_docmesh_settings():
    config = EnvConfig(
        milvus=MilvusConfig(
            uri="http://native:19530",
            db_name="native",
            token="native-token",
            timeout=1,
        )
    )

    class _DocmeshMilvus:
        uri = "http://docmesh:19530"
        db_name = "docmesh-db"
        token = "docmesh-token"
        request_timeout_seconds = 17

    class _DocmeshSettings:
        milvus = _DocmeshMilvus()

    resolved = resolve_milvus_config(config, docmesh_settings=_DocmeshSettings())

    assert isinstance(resolved, MilvusConfig)
    assert resolved.uri == "http://docmesh:19530"
    assert resolved.db_name == "docmesh-db"
    assert resolved.token == "docmesh-token"
    assert resolved.timeout == 17


def test_resolve_milvus_config_falls_back_to_native_config():
    config = EnvConfig(
        milvus=MilvusConfig(
            uri="http://native:19530",
            db_name="native",
            token="native-token",
            timeout=1,
        )
    )

    resolved = resolve_milvus_config(config)

    assert resolved is config.milvus
