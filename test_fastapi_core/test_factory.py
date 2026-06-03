from __future__ import annotations

from fastapi_core.core.config import EnvConfig, ServiceSettings
from fastapi_core.factory import create_app


def test_create_app_registers_config_and_settings_on_app_state():
    config = EnvConfig()
    settings = ServiceSettings()

    app = create_app(config=config, settings=settings, include_auth_router=False)

    assert app.state.config is config
    assert app.state.settings is settings
