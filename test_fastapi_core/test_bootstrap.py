from __future__ import annotations

from fastapi import FastAPI

from fastapi_core.core.config import EnvConfig
from fastapi_core.dependencies.config import _CONFIG_STATE_KEY
from fastapi_core.bootstrap import (
    get_or_create_state_value,
    get_state_value,
    set_state_value,
)


def test_set_and_get_state_value_round_trip():
    app = FastAPI()
    config = EnvConfig()

    set_state_value(app, _CONFIG_STATE_KEY, config)

    assert get_state_value(app, _CONFIG_STATE_KEY) is config


def test_get_or_create_state_value_calls_factory_once():
    app = FastAPI()
    calls = 0

    def factory() -> str:
        nonlocal calls
        calls += 1
        return "value"

    assert get_or_create_state_value(app, "demo", factory) == "value"
    assert get_or_create_state_value(app, "demo", factory) == "value"
    assert calls == 1
