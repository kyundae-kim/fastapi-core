from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from docmesh_py_core import KeycloakAuthService, TokenValidationError
from docmesh_py_core import AuthenticatedUser, Settings

from fastapi_core.dependencies.config import get_settings
from fastapi_core.schemas.user import UserInfo

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token", auto_error=False)


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


def get_auth_provider(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> KeycloakAuthService:
    if hasattr(request.app.state, "auth_provider"):
        return request.app.state.auth_provider
    provider = KeycloakAuthService(settings)
    request.app.state.auth_provider = provider
    return provider


async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    provider: KeycloakAuthService = Depends(get_auth_provider),
    settings: Settings = Depends(get_settings),
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


def require_permissions(*roles: str) -> Callable[..., UserInfo]:
    async def dependency(current_user: UserInfo = Depends(get_current_user)) -> UserInfo:
        if not set(roles).issubset(set(current_user.roles)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden",
            )
        return current_user

    return dependency
