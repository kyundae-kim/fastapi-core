from fastapi_core.core.config import DatabaseConfig, EnvConfig, MinIOConfig


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
