from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from fastapi_core.dependencies.auth import get_auth_provider, get_current_user
from fastapi_core.schemas.token import TokenResponse
from fastapi_core.schemas.user import UserInfo

router = APIRouter(tags=["auth"])


@router.post("/token", response_model=TokenResponse)
async def issue_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    provider=Depends(get_auth_provider),
) -> TokenResponse:
    scope = " ".join(form_data.scopes) or None
    try:
        token = provider.fetch_access_token(scope=scope)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    return TokenResponse(
        access_token=token.access_token,
        refresh_token=getattr(token, "refresh_token", None),
        token_type=getattr(token, "token_type", "bearer"),
    )


@router.get("/user", response_model=UserInfo)
async def read_user(current_user: UserInfo = Depends(get_current_user)) -> UserInfo:
    return current_user
