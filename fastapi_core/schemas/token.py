from __future__ import annotations

from pydantic import BaseModel


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
