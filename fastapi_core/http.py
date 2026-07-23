from __future__ import annotations

import inspect
import logging
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, replace
from http import HTTPStatus
from time import perf_counter
from uuid import uuid4

from docmesh_py_core import mask_sensitive_value
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi_core.function_logging import log_function_boundary
from starlette.datastructures import Headers, MutableHeaders
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from fastapi_core.schemas.error import ProblemDetail

_CORRELATION_ID_PATTERN = re.compile(r"[A-Za-z0-9._:-]{1,128}")
_SAFE_ERROR_DETAILS = frozenset({"Invalid token"})
logger = logging.getLogger(__name__)
access_logger = logging.getLogger("fastapi_core.access")


@dataclass(frozen=True, slots=True)
class ErrorMapping:
    status_code: int
    detail: str
    title: str | None = None
    type_uri: str = "about:blank"
    headers: dict[str, str] | None = None
    code: str | None = None
    extensions: dict[str, object] | None = None


ErrorMapper = Callable[[Request, Exception], ErrorMapping | Awaitable[ErrorMapping]]
ErrorRenderer = Callable[[Request, ErrorMapping], Response | Awaitable[Response]]


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

        async def send_with_correlation_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                MutableHeaders(scope=message)[self.header_name] = correlation_id
            await send(message)

        await self.app(scope, receive, send_with_correlation_id)


class AccessLogMiddleware:
    @log_function_boundary()
    def __init__(self, app: ASGIApp, *, log_health: bool = False) -> None:
        self.app = app
        self.log_health = log_health
        access_logger.setLevel(logging.INFO)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        started = perf_counter()
        status_code = 500
        logged = False

        @log_function_boundary()
        def write_log(*, failed: bool = False) -> None:
            nonlocal logged
            if logged:
                return
            logged = True
            route = getattr(scope.get("route"), "path", None) or scope.get("path", "")
            if not self.log_health and route.startswith("/health/"):
                return
            access_logger.info(
                "http_access",
                extra={
                    "event": {
                        "method": scope.get("method"),
                        "route": route,
                        "status_code": status_code,
                        "duration_ms": round((perf_counter() - started) * 1000, 3),
                        "outcome": (
                            "error" if failed or status_code >= 400 else "success"
                        ),
                        "correlation_id": scope.get("state", {}).get(
                            "correlation_id"
                        ),
                    }
                },
            )

        async def send_with_access_log(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)
            if (
                message["type"] == "http.response.body"
                and not message.get("more_body", False)
            ):
                write_log()

        try:
            await self.app(scope, receive, send_with_access_log)
        except BaseException:
            write_log(failed=True)
            raise


@log_function_boundary()
def _problem_response(
    request: Request,
    mapping: ErrorMapping,
) -> JSONResponse:
    correlation_id = getattr(request.state, "correlation_id", uuid4().hex)
    problem = ProblemDetail(
        type=mapping.type_uri,
        title=mapping.title or _status_title(mapping.status_code),
        status=mapping.status_code,
        detail=mapping.detail,
        instance=request.url.path,
        correlation_id=correlation_id,
    )
    return JSONResponse(
        status_code=mapping.status_code,
        content=problem.model_dump(),
        headers=mapping.headers,
        media_type="application/problem+json",
    )


@log_function_boundary()
def _problem_renderer(request: Request, mapping: ErrorMapping) -> Response:
    return _problem_response(request, mapping)


@log_function_boundary()
async def _render_error(request: Request, mapping: ErrorMapping) -> Response:
    sanitized = replace(mapping, detail=_mask_problem_detail(mapping.detail))
    renderer: ErrorRenderer = request.app.state.error_renderer
    response = renderer(request, sanitized)
    if inspect.isawaitable(response):
        return await response
    return response


@log_function_boundary()
async def _http_exception_handler(request: Request, exc: HTTPException) -> Response:
    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return await _render_error(
        request,
        ErrorMapping(
            status_code=exc.status_code,
            detail=detail,
            headers=exc.headers,
        ),
    )


@log_function_boundary()
async def _validation_exception_handler(
    request: Request,
    _exc: RequestValidationError,
) -> Response:
    return await _render_error(
        request,
        ErrorMapping(status_code=422, detail="Request validation failed"),
    )


@log_function_boundary()
async def _unhandled_exception_handler(
    request: Request,
    _exc: Exception,
) -> Response:
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
    return await _render_error(
        request,
        ErrorMapping(status_code=500, detail="Internal Server Error"),
    )


@log_function_boundary()
def install_problem_handlers(
    app: FastAPI,
    error_renderer: ErrorRenderer | None = None,
) -> None:
    app.state.error_renderer = error_renderer or _problem_renderer
    app.state.error_mapper_types = set()
    app.add_exception_handler(HTTPException, _http_exception_handler)
    app.add_exception_handler(RequestValidationError, _validation_exception_handler)
    app.add_exception_handler(Exception, _unhandled_exception_handler)


@log_function_boundary()
def register_error_mapper(
    app: FastAPI,
    exception_type: type[Exception],
    mapper: ErrorMapper,
) -> None:
    registered: set[type[Exception]] = app.state.error_mapper_types
    if exception_type in registered:
        raise ValueError(
            f"error mapper for '{exception_type.__name__}' is already registered"
        )

    @log_function_boundary()
    async def mapped_exception_handler(
        request: Request,
        exc: Exception,
    ) -> Response:
        mapping = mapper(request, exc)
        if inspect.isawaitable(mapping):
            mapping = await mapping
        return await _render_error(request, mapping)

    app.add_exception_handler(exception_type, mapped_exception_handler)
    registered.add(exception_type)
