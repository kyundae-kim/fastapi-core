from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status

from fastapi_core.core.config import EnvConfig, ServiceSettings
from fastapi_core.core.database import check_database_connection
from fastapi_core.core.langfuse import check_langfuse_connection
from fastapi_core.core.storage import check_minio_connection
from fastapi_core.dependencies.config import get_config, get_settings
from fastapi_core.dependencies.database import get_db_engine
from fastapi_core.dependencies.storage import get_minio_client
from fastapi_core.schemas.health import HealthResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/liveness", response_model=HealthResponse)
async def liveness() -> HealthResponse:
    return HealthResponse(status="ok")


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

    if settings.health.check_database:
        engine = get_db_engine(request, config)
        if not check_database_connection(engine):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database not ready",
            )

    if settings.health.check_minio:
        minio_client = get_minio_client(request, config)
        if not check_minio_connection(minio_client, config.minio.bucket):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="MinIO not ready",
            )

    if settings.health.check_langfuse and not check_langfuse_connection(config.langfuse):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Langfuse not ready",
        )

    return HealthResponse(status="ok")
