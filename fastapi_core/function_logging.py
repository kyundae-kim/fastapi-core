from __future__ import annotations

import inspect
import logging
from collections.abc import Callable
from functools import wraps
from typing import Any, ParamSpec, TypeVar, cast

P = ParamSpec("P")
T = TypeVar("T")


def log_function_boundary(
    event: str | None = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Log start, success, and failure at an application function boundary."""

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        logger = logging.getLogger(func.__module__)
        event_name = event or f"{func.__module__}.{func.__qualname__}"
        log_extra = {"function_event": event_name}

        if inspect.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
                if logger.isEnabledFor(logging.INFO):
                    logger.info("function_start", extra=log_extra)
                try:
                    result = await cast(Callable[P, Any], func)(*args, **kwargs)
                except Exception:
                    logger.exception(
                        "function_error",
                        extra=log_extra,
                    )
                    raise
                if logger.isEnabledFor(logging.INFO):
                    logger.info("function_end", extra=log_extra)
                return cast(T, result)

            return cast(Callable[P, T], async_wrapper)

        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            if logger.isEnabledFor(logging.INFO):
                logger.info("function_start", extra=log_extra)
            try:
                result = func(*args, **kwargs)
            except Exception:
                logger.exception(
                    "function_error",
                    extra=log_extra,
                )
                raise
            if logger.isEnabledFor(logging.INFO):
                logger.info("function_end", extra=log_extra)
            return result

        return cast(Callable[P, T], wrapper)

    return decorator


__all__ = ["log_function_boundary"]
