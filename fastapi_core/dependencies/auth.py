from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import OAuth2PasswordBearer
from docmesh_py_core.function_logging import log_function_boundary
from docmesh_py_core import (
    AuthenticatedUser,
    KeycloakAuthService,
    ServiceConfigs,
    TokenValidationError,
)

from fastapi_core.dependencies.config import get_settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token", auto_error=False)


@log_function_boundary()
def _get_roles(user: AuthenticatedUser) -> set[str]:
    roles = set(user.realm_roles)
    for client_roles in user.client_roles.values():
        roles.update(client_roles)
    return roles


@log_function_boundary()
def _get_scopes(user: AuthenticatedUser) -> set[str]:
    raw_scope = user.claims.get("scope")
    if isinstance(raw_scope, str):
        return set(raw_scope.split())
    return set()


@log_function_boundary()
def get_auth_provider(
    request: Request,
    settings: ServiceConfigs = Depends(get_settings),
) -> KeycloakAuthService:
    cached_provider = getattr(request.app.state, "auth_provider", None)
    if cached_provider is not None:
        return cached_provider
    service_clients = getattr(request.app.state, "service_clients", None)
    if service_clients is not None:
        client = service_clients.get("keycloak")
        if client is not None:
            provider = client.client
            request.app.state.auth_provider = provider
            return provider
    if settings.keycloak is None:
        raise RuntimeError("Keycloak configuration is not enabled")
    provider = KeycloakAuthService(settings.keycloak, allowed_algorithms=["RS256"])
    request.app.state.auth_provider = provider
    return provider


@log_function_boundary()
async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    provider: KeycloakAuthService = Depends(get_auth_provider),
    settings: ServiceConfigs = Depends(get_settings),
) -> AuthenticatedUser:
    del settings
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
def _raise_for_missing(required: tuple[str, ...], granted: set[str]) -> None:
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
        granted = _get_roles(current_user) | _get_scopes(current_user)
        _raise_for_missing(permissions, granted)
        return current_user

    return dependency
