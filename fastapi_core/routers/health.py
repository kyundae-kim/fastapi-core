from __future__ import annotations

import logging

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from docmesh_py_core import HealthCheckError, build_service_log_event, check_all_services

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
async def readiness(request: Request) -> HealthResponse:
    checks = getattr(request.app.state, "readiness_checks", {})
    service_metadata = getattr(request.app.state, "readiness_services", {})
    required_services = getattr(request.app.state, "required_services", set())
    parallel = getattr(request.app.state, "readiness_parallel", False)

    if not checks:
        return HealthResponse(status="ok")

    try:
        result = check_all_services(
            checks,
            required_services=required_services,
            parallel=parallel,
        )
    except HealthCheckError as exc:
        metadata = service_metadata.get(exc.service, {"required": True, "enabled": True})
        detail = _build_service_detail(
            exc.service,
            metadata,
            ok=False,
            error=exc.error,
        )
        _log_readiness_failure(exc.service, detail, outcome="error")
        body = HealthResponse(
            status="error",
            details={exc.service: detail},
        ).model_dump()
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
            error=service.error,
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
