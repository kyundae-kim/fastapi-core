from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import OAuth2PasswordBearer
from docmesh_py_core.function_logging import log_function_boundary
from docmesh_py_core import AuthenticatedUser, KeycloakAuthService, ServiceConfigs, TokenValidationError

from fastapi_core.dependencies.config import get_settings
from fastapi_core.schemas.user import UserInfo

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token", auto_error=False)


@log_function_boundary()
def _to_user_info(user: AuthenticatedUser) -> UserInfo:
    roles: list[str] = []
    for role in user.realm_roles:
        if role not in roles:
            roles.append(role)
    for client_roles in user.client_roles.values():
        for role in client_roles:
            if role not in roles:
                roles.append(role)

    scopes: list[str] = []
    raw_scope = user.claims.get("scope")
    if isinstance(raw_scope, str):
        scopes = [scope for scope in raw_scope.split() if scope]

    return UserInfo(
        sub=user.sub,
        username=user.preferred_username or user.sub,
        email=user.email,
        name=user.name,
        roles=roles,
        scopes=scopes,
    )


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
) -> UserInfo:
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

    return _to_user_info(user)


@log_function_boundary()
def _raise_for_missing(required: tuple[str, ...], granted: set[str]) -> None:
    if not set(required).issubset(granted):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden",
        )


@log_function_boundary()
def require_roles(*roles: str) -> Callable[..., UserInfo]:
    @log_function_boundary()
    async def dependency(current_user: UserInfo = Depends(get_current_user)) -> UserInfo:
        _raise_for_missing(roles, set(current_user.roles))
        return current_user

    return dependency


@log_function_boundary()
def require_scopes(*scopes: str) -> Callable[..., UserInfo]:
    @log_function_boundary()
    async def dependency(
        current_user: UserInfo = Security(get_current_user, scopes=list(scopes)),
    ) -> UserInfo:
        _raise_for_missing(scopes, set(current_user.scopes))
        return current_user

    return dependency


@log_function_boundary()
def require_permissions(*permissions: str) -> Callable[..., UserInfo]:
    @log_function_boundary()
    async def dependency(current_user: UserInfo = Depends(get_current_user)) -> UserInfo:
        granted = set(current_user.roles) | set(current_user.scopes)
        _raise_for_missing(permissions, granted)
        return current_user

    return dependency
