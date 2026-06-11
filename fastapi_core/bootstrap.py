from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TypeVar

from fastapi import FastAPI

T = TypeVar("T")


def set_state_value(app: FastAPI, key: str, value: T) -> T:
    setattr(app.state, key, value)
    return value


async def set_state_value_async(app: FastAPI, key: str, value: T) -> T:
    return set_state_value(app, key, value)


def get_state_value(app: FastAPI, key: str) -> T:
    return getattr(app.state, key)


def get_or_create_state_value(app: FastAPI, key: str, factory: Callable[[], T]) -> T:
    try:
        return get_state_value(app, key)
    except AttributeError:
        value = factory()
        return set_state_value(app, key, value)


async def get_or_create_state_value_async(
    app: FastAPI,
    key: str,
    factory: Callable[[], Awaitable[T]],
) -> T:
    try:
        return get_state_value(app, key)
    except AttributeError:
        value = await factory()
        return await set_state_value_async(app, key, value)
