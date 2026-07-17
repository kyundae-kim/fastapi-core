from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from docmesh_py_core.function_logging import log_function_boundary
from docmesh_py_core import (
    AuthenticatedUser,
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

_TOKEN_ISSUE_ERRORS = (
    (KeycloakTokenAuthenticationError, (401, "Authentication failed", "authentication_failed")),
    (KeycloakTokenConfigurationError, (500, "Authentication service misconfigured", "configuration_error")),
    (KeycloakTokenTemporaryError, (503, "Authentication service unavailable", "temporary_error")),
    (KeycloakTokenError, (502, "Authentication service error", "upstream_error")),
)
_UNEXPECTED_TOKEN_ISSUE_ERROR = (500, "Authentication service error", "unexpected_error")


@log_function_boundary()
def _to_user_info(user: AuthenticatedUser) -> UserInfo:
    roles = list(
        dict.fromkeys(
            [
                *user.realm_roles,
                *(
                    role
                    for client_roles in user.client_roles.values()
                    for role in client_roles
                ),
            ]
        )
    )
    raw_scope = user.claims.get("scope")
    scopes = raw_scope.split() if isinstance(raw_scope, str) else []
    return UserInfo(
        sub=user.sub,
        username=user.preferred_username or user.sub,
        email=user.email,
        name=user.name,
        roles=roles,
        scopes=scopes,
    )


@log_function_boundary()
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


@log_function_boundary()
def _raise_token_issue_error(exc: Exception, scope: str | None) -> None:
    status_code, detail, outcome = next(
        (mapping for error_type, mapping in _TOKEN_ISSUE_ERRORS if isinstance(exc, error_type)),
        _UNEXPECTED_TOKEN_ISSUE_ERROR,
    )

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
@log_function_boundary()
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
        token_type=str(getattr(token, "token_type", "bearer")).lower(),
    )


@router.get("/user", response_model=UserInfo)
@log_function_boundary()
async def read_user(
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> UserInfo:
    return _to_user_info(current_user)
