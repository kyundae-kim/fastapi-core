from __future__ import annotations

import inspect
import logging
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from http import HTTPStatus
from uuid import uuid4

from docmesh_py_core.function_logging import log_function_boundary
from docmesh_py_core import mask_sensitive_value
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.datastructures import Headers, MutableHeaders
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from fastapi_core.schemas.error import ProblemDetail

_CORRELATION_ID_PATTERN = re.compile(r"[A-Za-z0-9._:-]{1,128}")
_SAFE_ERROR_DETAILS = frozenset({"Invalid token"})
logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ErrorMapping:
    status_code: int
    detail: str
    title: str | None = None
    type_uri: str = "about:blank"
    headers: dict[str, str] | None = None


ErrorMapper = Callable[[Request, Exception], ErrorMapping | Awaitable[ErrorMapping]]


@log_function_boundary()
def _status_title(status_code: int) -> str:
    try:
        return HTTPStatus(status_code).phrase
    except ValueError:
        return "HTTP Error"


@log_function_boundary()
def _mask_problem_detail(detail: str) -> str:
    if detail in _SAFE_ERROR_DETAILS:
        return detail
    return mask_sensitive_value(detail) or detail


class CorrelationIdMiddleware:
    @log_function_boundary()
    def __init__(self, app: ASGIApp, header_name: str = "X-Correlation-ID") -> None:
        self.app = app
        self.header_name = header_name

    @log_function_boundary()
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming = Headers(scope=scope).get(self.header_name)
        correlation_id = (
            incoming
            if incoming is not None and _CORRELATION_ID_PATTERN.fullmatch(incoming)
            else uuid4().hex
        )
        scope.setdefault("state", {})["correlation_id"] = correlation_id

        @log_function_boundary()
        async def send_with_correlation_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                MutableHeaders(scope=message)[self.header_name] = correlation_id
            await send(message)

        await self.app(scope, receive, send_with_correlation_id)


@log_function_boundary()
def _problem_response(
    request: Request,
    *,
    status_code: int,
    detail: str,
    title: str | None = None,
    type_uri: str = "about:blank",
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    correlation_id = getattr(request.state, "correlation_id", uuid4().hex)
    problem = ProblemDetail(
        type=type_uri,
        title=title or _status_title(status_code),
        status=status_code,
        detail=_mask_problem_detail(detail),
        instance=request.url.path,
        correlation_id=correlation_id,
    )
    return JSONResponse(
        status_code=status_code,
        content=problem.model_dump(),
        headers=headers,
        media_type="application/problem+json",
    )


@log_function_boundary()
async def _http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return _problem_response(
        request,
        status_code=exc.status_code,
        detail=detail,
        headers=exc.headers,
    )


@log_function_boundary()
async def _validation_exception_handler(
    request: Request,
    _exc: RequestValidationError,
) -> JSONResponse:
    return _problem_response(
        request,
        status_code=422,
        detail="Request validation failed",
    )


@log_function_boundary()
async def _unhandled_exception_handler(
    request: Request,
    _exc: Exception,
) -> JSONResponse:
    correlation_id = getattr(request.state, "correlation_id", None)
    logger.error(
        "unhandled_request_error",
        extra={
            "event": {
                "operation": "request",
                "outcome": "error",
                "correlation_id": correlation_id,
            }
        },
    )
    return _problem_response(
        request,
        status_code=500,
        detail="Internal Server Error",
    )


@log_function_boundary()
def install_problem_handlers(app: FastAPI) -> None:
    app.add_exception_handler(HTTPException, _http_exception_handler)
    app.add_exception_handler(RequestValidationError, _validation_exception_handler)
    app.add_exception_handler(Exception, _unhandled_exception_handler)


@log_function_boundary()
def register_error_mapper(
    app: FastAPI,
    exception_type: type[Exception],
    mapper: ErrorMapper,
) -> None:
    @log_function_boundary()
    async def mapped_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        mapping = mapper(request, exc)
        if inspect.isawaitable(mapping):
            mapping = await mapping
        return _problem_response(
            request,
            status_code=mapping.status_code,
            detail=mapping.detail,
            title=mapping.title,
            type_uri=mapping.type_uri,
            headers=mapping.headers,
        )

    app.add_exception_handler(exception_type, mapped_exception_handler)
