from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from docmesh_py_core import (
    KeycloakTokenAuthenticationError,
    KeycloakTokenConfigurationError,
    KeycloakTokenError,
    KeycloakTokenTemporaryError,
    build_service_log_event,
)

from fastapi_core.dependencies.auth import get_auth_provider, get_current_user
from fastapi_core.schemas.token import TokenResponse
from fastapi_core.schemas.user import UserInfo

router = APIRouter(tags=["auth"])
logger = logging.getLogger(__name__)


def _log_token_issue_failure(
    *,
    outcome: str,
    error: str,
    scope: str | None,
    status_code: int,
) -> None:
    logger.warning(
        "token_issue_failed",
        extra={
            "event": build_service_log_event(
                service="keycloak",
                operation="issue_token",
                outcome=outcome,
                error=error,
                extra={
                    "status_code": status_code,
                    "scope": scope,
                },
            )
        },
    )


def _raise_token_issue_error(exc: Exception, scope: str | None) -> None:
    if isinstance(exc, KeycloakTokenAuthenticationError):
        status_code = status.HTTP_401_UNAUTHORIZED
        detail = "Authentication failed"
        outcome = "authentication_failed"
    elif isinstance(exc, KeycloakTokenConfigurationError):
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        detail = "Authentication service misconfigured"
        outcome = "configuration_error"
    elif isinstance(exc, KeycloakTokenTemporaryError):
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        detail = "Authentication service unavailable"
        outcome = "temporary_error"
    elif isinstance(exc, KeycloakTokenError):
        status_code = status.HTTP_502_BAD_GATEWAY
        detail = "Authentication service error"
        outcome = "upstream_error"
    else:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        detail = "Authentication service error"
        outcome = "unexpected_error"

    _log_token_issue_failure(
        outcome=outcome,
        error=str(exc),
        scope=scope,
        status_code=status_code,
    )
    raise HTTPException(
        status_code=status_code,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    ) from exc


@router.post("/token", response_model=TokenResponse)
async def issue_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    provider=Depends(get_auth_provider),
) -> TokenResponse:
    scope = " ".join(form_data.scopes) or None
    try:
        token = provider.fetch_access_token(
            scope=scope,
            username=form_data.username,
            password=form_data.password,
        )
    except Exception as exc:
        _raise_token_issue_error(exc, scope)

    return TokenResponse(
        access_token=token.access_token,
        refresh_token=getattr(token, "refresh_token", None),
        token_type=getattr(token, "token_type", "bearer"),
    )


@router.get("/user", response_model=UserInfo)
async def read_user(current_user: UserInfo = Depends(get_current_user)) -> UserInfo:
    return current_user
