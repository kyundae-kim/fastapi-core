from __future__ import annotations

from functools import lru_cache

from fastapi_core.core.config import EnvConfig, ServiceSettings


@lru_cache
def get_config() -> EnvConfig:
    return EnvConfig()


def get_settings(config: EnvConfig | None = None) -> ServiceSettings:
    if config is None:
        config = get_config()
    return ServiceSettings.from_yaml(config.config_path)
