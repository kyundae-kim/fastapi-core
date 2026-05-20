from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException, status

from fastapi_core.core.config import EnvConfig
from fastapi_core.dependencies.config import get_config
from fastapi_core.schemas.health import HealthResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/liveness", response_model=HealthResponse)
async def liveness() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/readiness", response_model=HealthResponse)
async def readiness(
    config: EnvConfig = Depends(get_config),
) -> HealthResponse:
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
    return HealthResponse(status="ok")
