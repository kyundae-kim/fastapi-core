from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

HealthStatus = Literal["ok", "degraded", "error"]


class HealthServiceDetail(BaseModel):
    ok: bool
    latency_ms: int | None = None
    error: str | None = None
    required: bool = False
    enabled: bool = True


class HealthResponse(BaseModel):
    status: HealthStatus
    details: dict[str, HealthServiceDetail] | None = None
