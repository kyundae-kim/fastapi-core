from __future__ import annotations

import logging

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from docmesh_py_core import HealthCheckError, build_service_log_event

from fastapi_core.extensions import ReadinessRegistry
from fastapi_core.schemas.health import HealthResponse, HealthServiceDetail, HealthStatus

router = APIRouter(prefix="/health", tags=["health"])
logger = logging.getLogger(__name__)


def _readiness_error(
    service_name: str,
    *,
    ok: bool,
    error: str | None,
    registry: ReadinessRegistry,
) -> str | None:
    if ok:
        return error
    spec = registry.specs[service_name]
    if spec.redact_errors:
        return "readiness check failed"
    if error:
        return error
    timeout_seconds = spec.timeout_seconds or registry.default_timeout_seconds
    if timeout_seconds is not None:
        return "health check timed out"
    return None


def _log_readiness_failure(
    service_name: str,
    detail: HealthServiceDetail,
    *,
    outcome: HealthStatus,
) -> None:
    logger.warning(
        "readiness_check_failed",
        extra={
            "event": build_service_log_event(
                service=service_name,
                operation="readiness_check",
                outcome=outcome,
                latency_ms=detail.latency_ms,
                error=detail.error,
                extra={
                    "required": detail.required,
                    "enabled": detail.enabled,
                },
            )
        },
    )


@router.get("/liveness", response_model=HealthResponse)
async def liveness() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/readiness", response_model=HealthResponse)
async def readiness(request: Request) -> HealthResponse | JSONResponse:
    state = request.app.state
    registry: ReadinessRegistry = state.readiness_registry
    config = state.config
    if not registry.specs:
        return HealthResponse(status="ok")

    try:
        result = await registry.check(
            parallel=config.readiness_parallel,
            overall_timeout_seconds=config.readiness_overall_timeout_seconds,
        )
    except HealthCheckError as exc:
        result = exc.result
    except TimeoutError:
        logger.warning(
            "readiness_check_timeout",
            extra={
                "event": {
                    "operation": "readiness_check",
                    "outcome": "error",
                    "timeout_scope": "overall",
                }
            },
        )
        body = HealthResponse(status="error").model_dump()
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=body,
        )

    details: dict[str, HealthServiceDetail] = {}
    failures: list[tuple[str, HealthServiceDetail]] = []
    for service in result.services:
        spec = registry.specs[service.service]
        detail = HealthServiceDetail(
            ok=service.ok,
            latency_ms=service.latency_ms,
            error=_readiness_error(
                service.service,
                ok=service.ok,
                error=service.error,
                registry=registry,
            ),
            required=spec.required,
            enabled=True,
        )
        details[service.service] = detail
        if not detail.ok:
            failures.append((service.service, detail))

    status_text: HealthStatus
    if any(detail.required for _, detail in failures):
        status_text = "error"
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    elif failures:
        status_text = "degraded"
        status_code = status.HTTP_200_OK
    else:
        status_text = "ok"
        status_code = status.HTTP_200_OK

    for service_name, detail in failures:
        _log_readiness_failure(service_name, detail, outcome=status_text)

    response = HealthResponse(status=status_text, details=details)
    if status_code != status.HTTP_200_OK:
        return JSONResponse(status_code=status_code, content=response.model_dump())
    return response
