from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from fastapi_core.core.auth import KeycloakAuthProvider
from fastapi_core.dependencies.auth import auth_provider_schema, current_user_schema
from fastapi_core.schemas.token import TokenResponse
from fastapi_core.schemas.user import UserInfo

router = APIRouter(tags=["auth"])


@router.post("/token", response_model=TokenResponse)
def token(
    form: OAuth2PasswordRequestForm = Depends(),
    provider: KeycloakAuthProvider = Depends(auth_provider_schema),
) -> TokenResponse:
    try:
        data = provider.authenticate(form.username, form.password)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    return TokenResponse(
        access_token=data["access_token"],
        refresh_token=data.get("refresh_token"),
        token_type=data.get("token_type", "bearer"),
    )


@router.get("/user", response_model=UserInfo)
def user(current_user: UserInfo = Depends(current_user_schema)) -> UserInfo:
    return current_user
