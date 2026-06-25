from typing import Any

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    details: dict[str, Any] | None = None
