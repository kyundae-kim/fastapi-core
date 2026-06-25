from __future__ import annotations

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from docmesh_py_core import HealthCheckError, check_all_services

from fastapi_core.schemas.health import HealthResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/liveness", response_model=HealthResponse)
async def liveness() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/readiness", response_model=HealthResponse)
async def readiness(request: Request) -> HealthResponse:
    checks = getattr(request.app.state, "readiness_checks", {})
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
        body = HealthResponse(status="error", details={exc.service: exc.error}).model_dump()
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=body,
        )

    details = {
        service.service: {
            "ok": service.ok,
            "latency_ms": service.latency_ms,
            "error": service.error,
        }
        for service in result.services
    }
    status_text = "ok" if result.ok else "error"
    status_code = status.HTTP_200_OK if result.ok else status.HTTP_503_SERVICE_UNAVAILABLE

    if status_code != status.HTTP_200_OK:
        body = HealthResponse(status=status_text, details=details).model_dump()
        return JSONResponse(status_code=status_code, content=body)

    return HealthResponse(status=status_text, details=details)
