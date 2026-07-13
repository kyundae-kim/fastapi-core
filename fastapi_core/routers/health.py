from __future__ import annotations

import logging

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from docmesh_py_core import (
    HealthCheckError,
    async_check_all_services,
    build_service_log_event,
)

from fastapi_core.extensions import ReadinessRegistry
from fastapi_core.schemas.health import HealthResponse, HealthServiceDetail, HealthStatus

router = APIRouter(prefix="/health", tags=["health"])
logger = logging.getLogger(__name__)


def _build_service_detail(
    service_name: str,
    metadata: dict[str, bool],
    *,
    ok: bool,
    latency_ms: int | None = None,
    error: str | None = None,
) -> HealthServiceDetail:
    del service_name
    return HealthServiceDetail(
        ok=ok,
        latency_ms=latency_ms,
        error=error,
        required=metadata.get("required", False),
        enabled=metadata.get("enabled", True),
    )


def _readiness_error(
    service_name: str,
    *,
    ok: bool,
    error: str | None,
    timeout_seconds: float | None,
    registry: ReadinessRegistry | None,
    use_registry: bool,
) -> str | None:
    if ok:
        return error
    if use_registry and registry is not None:
        spec = registry.specs[service_name]
        if spec.redact_errors:
            return "readiness check failed"
        timeout_seconds = spec.timeout_seconds or registry.default_timeout_seconds
    if error:
        return error
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
    checks = getattr(request.app.state, "readiness_checks", {})
    service_metadata = getattr(request.app.state, "readiness_services", {})
    required_services = getattr(request.app.state, "required_services", set())
    parallel = getattr(request.app.state, "readiness_parallel", False)
    timeout_seconds = getattr(
        request.app.state,
        "readiness_timeout_seconds",
        None,
    )
    overall_timeout_seconds = getattr(
        request.app.state,
        "readiness_overall_timeout_seconds",
        None,
    )
    registry: ReadinessRegistry | None = getattr(
        request.app.state,
        "readiness_registry",
        None,
    )
    use_registry = (
        registry is not None
        and registry.owns_legacy_state(
            checks,
            service_metadata,
            required_services,
        )
    )

    if not checks:
        return HealthResponse(status="ok")

    try:
        if use_registry:
            result = await registry.check(
                parallel=parallel,
                overall_timeout_seconds=overall_timeout_seconds,
            )
        else:
            result = await async_check_all_services(
                checks,
                required_services=required_services,
                parallel=parallel,
                timeout_seconds=timeout_seconds,
                overall_timeout_seconds=overall_timeout_seconds,
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

    details: dict[str, HealthServiceDetail] = {
        service.service: _build_service_detail(
            service.service,
            service_metadata.get(service.service, {}),
            ok=service.ok,
            latency_ms=service.latency_ms,
            error=_readiness_error(
                service.service,
                ok=service.ok,
                error=service.error,
                timeout_seconds=timeout_seconds,
                registry=registry,
                use_registry=use_registry,
            ),
        )
        for service in result.services
    }
    failing_required = any(
        not detail.ok and detail.required
        for detail in details.values()
    )
    failing_optional = any(
        not detail.ok and not detail.required
        for detail in details.values()
    )
    status_text: HealthStatus
    if failing_required:
        status_text = "error"
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    elif failing_optional:
        status_text = "degraded"
        status_code = status.HTTP_200_OK
    else:
        status_text = "ok"
        status_code = status.HTTP_200_OK

    if status_text != "ok":
        for service_name, detail in details.items():
            if not detail.ok:
                _log_readiness_failure(service_name, detail, outcome=status_text)

    if status_code != status.HTTP_200_OK:
        body = HealthResponse(status=status_text, details=details).model_dump()
        return JSONResponse(status_code=status_code, content=body)

    return HealthResponse(status=status_text, details=details)
