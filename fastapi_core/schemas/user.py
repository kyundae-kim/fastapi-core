from __future__ import annotations

from pydantic import BaseModel, Field


class UserInfo(BaseModel):
    sub: str
    username: str
    email: str | None = None
    name: str | None = None
    roles: list[str] = Field(default_factory=list)
    scopes: list[str] = Field(default_factory=list)
