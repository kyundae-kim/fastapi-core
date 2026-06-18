from __future__ import annotations

from collections.abc import Callable

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status

from fastapi_core.core.config import EnvConfig, ServiceSettings
from fastapi_core.core.database import check_database_connection
from fastapi_core.core.langfuse import check_langfuse_connection
from fastapi_core.core.storage import check_minio_connection
from fastapi_core.dependencies.config import get_config, get_settings
from fastapi_core.dependencies.database import get_db_engine
from fastapi_core.dependencies.storage import get_minio_client
from fastapi_core.docmesh_bridge import (
    check_docmesh_service_connection,
    run_docmesh_healthchecks,
)
from fastapi_core.schemas.health import HealthResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/liveness", response_model=HealthResponse)
async def liveness() -> HealthResponse:
    return HealthResponse(status="ok")


def _build_native_service_checks(
    request: Request,
    config: EnvConfig,
    settings: ServiceSettings,
) -> tuple[dict[str, Callable[[], bool]], set[str]]:
    service_checks: dict[str, Callable[[], bool]] = {}
    required_services: set[str] = set()

    if settings.health.check_database:
        service_checks["database"] = lambda: check_database_connection(
            get_db_engine(request, config)
        )
        required_services.add("database")

    if settings.health.check_minio:
        service_checks["minio"] = lambda: check_minio_connection(
            get_minio_client(request, config), config.minio.bucket
        )
        required_services.add("minio")

    return service_checks, required_services


@router.get("/readiness", response_model=HealthResponse)
async def readiness(
    request: Request,
    config: EnvConfig = Depends(get_config),
    settings: ServiceSettings = Depends(get_settings),
) -> HealthResponse:
    if settings.health.check_keycloak:
        manage_url = str(config.keycloak.manage_url).rstrip("/")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{manage_url}/health/ready", timeout=5.0
                )
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Keycloak not ready",
                )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Keycloak unreachable: {e}",
            ) from e

    native_checks, required_services = _build_native_service_checks(
        request, config, settings
    )

    if (
        settings.lifecycle.use_docmesh_healthchecks
        and native_checks
        and run_docmesh_healthchecks(
            native_checks, required_services=required_services
        )
    ):
        native_checks = {}
        required_services = set()

    if settings.health.check_database and "database" in native_checks:
        if not native_checks["database"]():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database not ready",
            )

    if settings.health.check_minio and "minio" in native_checks:
        if not native_checks["minio"]():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="MinIO not ready",
            )

    langfuse_ready = check_docmesh_service_connection(request.app, "langfuse_client")
    if langfuse_ready is None:
        langfuse_ready = check_langfuse_connection(config.langfuse)

    if settings.health.check_langfuse and not langfuse_ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Langfuse not ready",
        )

    return HealthResponse(status="ok")
