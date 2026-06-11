from __future__ import annotations

from fastapi import FastAPI
import pytest

from fastapi_core.core.config import EnvConfig
from fastapi_core.dependencies.config import _CONFIG_STATE_KEY
from fastapi_core.bootstrap import (
    get_or_create_state_value,
    get_or_create_state_value_async,
    get_state_value,
    set_state_value,
    set_state_value_async,
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


@pytest.mark.asyncio
async def test_async_get_or_create_state_value_calls_factory_once():
    app = FastAPI()
    calls = 0

    async def factory() -> str:
        nonlocal calls
        calls += 1
        return "async-value"

    assert await get_or_create_state_value_async(app, "async-demo", factory) == "async-value"
    assert await get_or_create_state_value_async(app, "async-demo", factory) == "async-value"
    assert calls == 1


@pytest.mark.asyncio
async def test_async_set_state_value_round_trip():
    app = FastAPI()
    config = EnvConfig()

    await set_state_value_async(app, "async-config", config)

    assert get_state_value(app, "async-config") is config
