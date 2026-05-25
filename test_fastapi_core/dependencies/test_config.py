from fastapi_core.core.config import EnvConfig, ServiceSettings
from fastapi_core.dependencies.config import get_config, get_settings


def test_get_config_returns_env_config():
    config = get_config()
    assert isinstance(config, EnvConfig)


def test_get_config_cached():
    config1 = get_config()
    config2 = get_config()
    assert config1 is config2


def test_get_settings_returns_service_settings():
    config = EnvConfig()
    settings = get_settings(config)
    assert isinstance(settings, ServiceSettings)


def test_get_settings_defaults():
    config = EnvConfig()
    settings = get_settings(config)
    assert isinstance(settings.cors.origins, list)
    assert isinstance(settings.auth.verify_jwt, bool)
    assert isinstance(settings.health.check_keycloak, bool)
    assert isinstance(settings.health.check_database, bool)
    assert isinstance(settings.health.check_minio, bool)
