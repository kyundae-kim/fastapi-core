from __future__ import annotations

import inspect
import logging
import re
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, replace
from http import HTTPStatus
from time import perf_counter
from types import MappingProxyType
from typing import Any
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
ErrorMappingValue = ErrorMapping | ErrorMapper


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


@dataclass(frozen=True, slots=True)
class ExceptionMappingTable:
    """Immutable exception-to-error mapping table with MRO selection."""

    mappings: Mapping[type[Exception], ErrorMappingValue]
    fallback: ErrorMappingValue | None = None

    @log_function_boundary()
    def __post_init__(self) -> None:
        normalized = dict(self.mappings)
        for exception_type, mapping in normalized.items():
            if not isinstance(exception_type, type) or not issubclass(
                exception_type, Exception
            ):
                raise TypeError("exception mapping keys must be Exception types")
            if not isinstance(mapping, ErrorMapping) and not callable(mapping):
                raise TypeError("exception mapping values must be ErrorMapping or callable")
        if self.fallback is not None and not isinstance(self.fallback, ErrorMapping) and not callable(
            self.fallback
        ):
            raise TypeError("exception mapping fallback must be ErrorMapping or callable")
        if self.fallback is not None and Exception in normalized:
            raise ValueError(
                "exception mapping fallback is unreachable when Exception is mapped"
            )
        object.__setattr__(self, "mappings", MappingProxyType(normalized))

    @classmethod
    @log_function_boundary()
    def from_specs(
        cls,
        specs: list[tuple[type[Exception], ErrorMappingValue]],
        *,
        fallback: ErrorMappingValue | None = None,
    ) -> ExceptionMappingTable:
        mappings: dict[type[Exception], ErrorMappingValue] = {}
        for exception_type, mapping in specs:
            if exception_type in mappings:
                raise ValueError(
                    f"exception mapping for '{exception_type.__name__}' is already registered"
                )
            mappings[exception_type] = mapping
        return cls(mappings, fallback=fallback)

    @log_function_boundary()
    async def resolve(self, request: Request, exc: Exception) -> ErrorMapping | None:
        mapping: ErrorMappingValue | None = None
        for exception_type in type(exc).mro():
            if exception_type in self.mappings:
                mapping = self.mappings[exception_type]
                break
        if mapping is None:
            mapping = self.fallback
        if mapping is None:
            return None
        result = mapping if isinstance(mapping, ErrorMapping) else mapping(request, exc)
        if inspect.isawaitable(result):
            result = await result
        if not isinstance(result, ErrorMapping):
            raise TypeError("exception mapping callable must return ErrorMapping")
        return result


@log_function_boundary()
def _problem_response(
    request: Request,
    mapping: ErrorMapping,
    correlation_id: str | None = None,
    *,
    include_code: bool = True,
    include_extensions: bool = True,
) -> JSONResponse:
    if correlation_id is None:
        try:
            correlation_id = request.state.correlation_id
        except AttributeError:
            correlation_id = uuid4().hex
    problem = ProblemDetail(
        type=mapping.type_uri,
        title=mapping.title or _status_title(mapping.status_code),
        status=mapping.status_code,
        detail=mapping.detail,
        instance=request.url.path,
        correlation_id=correlation_id,
    )
    content = problem.model_dump()
    if include_code and mapping.code is not None:
        content["code"] = mapping.code
    if include_extensions and mapping.extensions:
        content.update(mapping.extensions)
    headers = dict(mapping.headers or {})
    headers.setdefault("X-Correlation-ID", correlation_id)
    return JSONResponse(
        status_code=mapping.status_code,
        content=content,
        headers=headers,
        media_type="application/problem+json",
    )


@log_function_boundary()
def _problem_renderer(request: Request, mapping: ErrorMapping) -> Response:
    return _problem_response(request, mapping)


@log_function_boundary()
def _default_correlation_id(request: Request) -> str:
    try:
        return request.state.correlation_id
    except AttributeError:
        return uuid4().hex


@log_function_boundary()
def create_error_renderer(
    *,
    correlation_id_extractor: Callable[[Request], str] | None = None,
    envelope_builder: Callable[[Request, ErrorMapping, str], Mapping[str, Any]] | None = None,
    fallback_codes: Mapping[int, str] | None = None,
    safe_fields: set[str] | frozenset[str] | None = None,
    problem_details: bool = True,
) -> ErrorRenderer:
    """Build a standard renderer from product-specific formatting hooks."""

    extract_correlation_id = correlation_id_extractor or _default_correlation_id
    codes = MappingProxyType(dict(fallback_codes or {}))
    explicit_safe_fields = safe_fields is not None
    fields = frozenset(safe_fields or {"code", "message", "correlation_id", "metadata"})

    @log_function_boundary()
    def default_envelope(
        request: Request,
        mapping: ErrorMapping,
        correlation_id: str,
    ) -> Mapping[str, Any]:
        error: dict[str, Any] = {}
        if "code" in fields:
            error["code"] = mapping.code or codes.get(mapping.status_code, f"http_{mapping.status_code}")
        if "message" in fields:
            error["message"] = mapping.detail
        if "correlation_id" in fields:
            error["correlation_id"] = correlation_id
        if "metadata" in fields and mapping.extensions:
            error["metadata"] = dict(mapping.extensions)
        return {"error": error}

    build_envelope = envelope_builder or default_envelope

    @log_function_boundary()
    def safe_mapping(mapping: ErrorMapping) -> ErrorMapping:
        if not explicit_safe_fields:
            return mapping
        return replace(
            mapping,
            detail=(
                mapping.detail
                if {"detail", "message"}.intersection(fields)
                else "Request failed"
            ),
            title=mapping.title if "title" in fields else None,
            type_uri=mapping.type_uri if "type" in fields else "about:blank",
            code=mapping.code if "code" in fields else None,
            extensions=(
                mapping.extensions
                if {"extensions", "metadata"}.intersection(fields)
                else None
            ),
        )

    @log_function_boundary()
    def renderer(request: Request, mapping: ErrorMapping) -> Response:
        correlation_id = extract_correlation_id(request)
        selected_mapping = safe_mapping(mapping)
        if selected_mapping.code is None:
            selected_mapping = replace(
                selected_mapping,
                code=codes.get(mapping.status_code),
            )
        if problem_details:
            return _problem_response(
                request,
                selected_mapping,
                correlation_id,
                include_code=not explicit_safe_fields or "code" in fields,
                include_extensions=(
                    not explicit_safe_fields
                    or bool({"extensions", "metadata"}.intersection(fields))
                ),
            )
        headers = dict(selected_mapping.headers or {})
        headers.setdefault("X-Correlation-ID", correlation_id)
        return JSONResponse(
            status_code=selected_mapping.status_code,
            content=dict(build_envelope(request, selected_mapping, correlation_id)),
            headers=headers,
        )

    return renderer


@log_function_boundary()
def _route_policy(request: Request) -> Any | None:
    route = request.scope.get("route")
    path = getattr(route, "path", None)
    if path is None:
        return None
    return getattr(request.app.state, "transport_policies", {}).get(
        (request.method.upper(), path)
    )


@log_function_boundary()
async def _render_error(request: Request, mapping: ErrorMapping) -> Response:
    sanitized = replace(mapping, detail=_mask_problem_detail(mapping.detail))
    policy = _route_policy(request)
    renderer: ErrorRenderer = getattr(policy, "error_renderer", None) or request.app.state.error_renderer
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
    policy = _route_policy(request)
    status_code = (
        policy.effective_validation_status
        if policy is not None
        else 422
    )
    return await _render_error(
        request,
        ErrorMapping(status_code=status_code, detail="Request validation failed"),
    )


@log_function_boundary()
async def _unhandled_exception_handler(
    request: Request,
    _exc: Exception,
) -> Response:
    table: ExceptionMappingTable | None = getattr(
        request.app.state, "error_mapping_table", None
    )
    if table is not None:
        mapped = await table.resolve(request, _exc)
        if mapped is not None:
            return await _render_error(request, mapped)
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
    error_mapping_table: ExceptionMappingTable | None = None,
) -> None:
    app.state.error_renderer = error_renderer or _problem_renderer
    app.state.error_mapper_types = set()
    app.state.error_mapping_table = error_mapping_table
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
