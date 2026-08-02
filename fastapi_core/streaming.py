from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping
from typing import Any

from starlette.responses import StreamingResponse
from starlette.types import Receive, Scope, Send

from fastapi_core.function_logging import log_function_boundary
from fastapi_core.invocation import invoke_resource


class ManagedStreamingResponse(StreamingResponse):
    """A ``StreamingResponse`` that owns and closes a producer resource.

    The resource is closed exactly once after normal completion, producer
    failure, client disconnect, or task cancellation. Synchronous close
    methods run in the default worker pool. All normal ``StreamingResponse``
    response metadata and background-task behavior are retained.
    """

    @log_function_boundary()
    def __init__(
        self,
        content: Any,
        *,
        resource: Any | None = None,
        close: Callable[[], Any] | None = None,
        status_code: int = 200,
        headers: Mapping[str, str] | None = None,
        media_type: str | None = None,
        background: Any | None = None,
    ) -> None:
        super().__init__(
            content,
            status_code=status_code,
            headers=headers,
            media_type=media_type,
            background=background,
        )
        self.resource = resource
        self._resource_close = close
        self._close_lock = asyncio.Lock()
        self._closed = False

    @log_function_boundary()
    def _close_callable(self) -> Callable[[], Any] | None:
        if self._resource_close is not None:
            return self._resource_close
        if self.resource is None:
            return None
        aclose = getattr(self.resource, "aclose", None)
        if callable(aclose):
            return aclose
        close = getattr(self.resource, "close", None)
        return close if callable(close) else None

    @log_function_boundary()
    async def _close_once(self) -> None:
        async with self._close_lock:
            if self._closed:
                return
            self._closed = True
            close = self._close_callable()
            if close is None:
                return
            await invoke_resource(close)

    @log_function_boundary()
    async def _close_with_cancellation_protection(self) -> None:
        task = asyncio.create_task(self._close_once())
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            try:
                await task
            except asyncio.CancelledError:
                pass
            raise

    @log_function_boundary()
    async def _close_preserving_error(self, error: BaseException) -> None:
        try:
            await self._close_with_cancellation_protection()
        except BaseException as close_error:
            error.add_note(f"managed streaming resource close failed: {close_error}")

    @log_function_boundary()
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        try:
            await super().__call__(scope, receive, send)
        except BaseException as error:
            await self._close_preserving_error(error)
            raise
        else:
            await self._close_with_cancellation_protection()


__all__ = ["ManagedStreamingResponse"]
