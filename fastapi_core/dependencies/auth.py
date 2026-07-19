from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import OAuth2PasswordBearer
from fastapi_core.function_logging import log_function_boundary
from docmesh_py_core import AuthenticatedUser, KeycloakAuthService, TokenValidationError

from fastapi_core.dependencies.services import get_keycloak_auth_service

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token", auto_error=False)


@log_function_boundary()
def _get_roles(user: AuthenticatedUser) -> list[str]:
    return list(
        dict.fromkeys(
            role
            for roles in (user.realm_roles, *user.client_roles.values())
            for role in roles
        )
    )


@log_function_boundary()
def _get_scopes(user: AuthenticatedUser) -> list[str]:
    raw_scope = user.claims.get("scope")
    if isinstance(raw_scope, str):
        return raw_scope.split()
    return []


@log_function_boundary()
def get_auth_provider(request: Request) -> KeycloakAuthService:
    cached_provider = getattr(request.app.state, "auth_provider", None)
    if cached_provider is not None:
        return cached_provider
    provider = get_keycloak_auth_service(request)
    request.app.state.auth_provider = provider
    return provider


@log_function_boundary()
async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    provider: KeycloakAuthService = Depends(get_auth_provider),
) -> AuthenticatedUser:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user = provider.extract_user_info(token)
    except TokenValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    return user


@log_function_boundary()
def _raise_for_missing(required: tuple[str, ...], granted: list[str]) -> None:
    if not set(required).issubset(granted):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden",
        )


@log_function_boundary()
def require_roles(*roles: str) -> Callable[..., AuthenticatedUser]:
    @log_function_boundary()
    async def dependency(
        current_user: AuthenticatedUser = Depends(get_current_user),
    ) -> AuthenticatedUser:
        _raise_for_missing(roles, _get_roles(current_user))
        return current_user

    return dependency


@log_function_boundary()
def require_scopes(*scopes: str) -> Callable[..., AuthenticatedUser]:
    @log_function_boundary()
    async def dependency(
        current_user: AuthenticatedUser = Security(
            get_current_user,
            scopes=list(scopes),
        ),
    ) -> AuthenticatedUser:
        _raise_for_missing(scopes, _get_scopes(current_user))
        return current_user

    return dependency


@log_function_boundary()
def require_permissions(*permissions: str) -> Callable[..., AuthenticatedUser]:
    @log_function_boundary()
    async def dependency(
        current_user: AuthenticatedUser = Depends(get_current_user),
    ) -> AuthenticatedUser:
        granted = _get_roles(current_user) + _get_scopes(current_user)
        _raise_for_missing(permissions, granted)
        return current_user

    return dependency
