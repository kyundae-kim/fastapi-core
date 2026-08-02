from __future__ import annotations

import asyncio
import inspect
from collections.abc import Callable
from functools import partial
from typing import Any, TypeVar

from fastapi_core.function_logging import log_function_boundary

R = TypeVar("R")


@log_function_boundary()
async def invoke_resource(
    method: Callable[..., R],
    *args: Any,
    timeout_seconds: float | None = None,
    **kwargs: Any,
) -> R:
    """Invoke an SDK method without blocking an async route.

    Coroutine functions are awaited directly. Synchronous callables run in
    ``asyncio``'s default worker pool, which preserves the current contextvars
    context and lets caller cancellation propagate to the awaiting task.
    """

    @log_function_boundary()
    async def invoke() -> R:
        target = getattr(method, "__call__", method)
        if inspect.iscoroutinefunction(method) or inspect.iscoroutinefunction(target):
            return await method(*args, **kwargs)  # type: ignore[misc]
        result = await asyncio.to_thread(partial(method, *args, **kwargs))
        if inspect.isawaitable(result):
            return await result
        return result

    if timeout_seconds is None:
        return await invoke()
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be greater than zero")
    return await asyncio.wait_for(invoke(), timeout=timeout_seconds)


__all__ = ["invoke_resource"]
