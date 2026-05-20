from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from fastapi_core.core.config import EnvConfig, ServiceSettings
from fastapi_core.core.security import KeycloakAuthProvider
from fastapi_core.dependencies.config import get_config, get_settings
from fastapi_core.schemas.user import UserInfo

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token", auto_error=False)


def get_auth_provider(
    config: EnvConfig = Depends(get_config),
) -> KeycloakAuthProvider:
    return KeycloakAuthProvider(
        http_url=str(config.keycloak.http_url),
        realm=config.keycloak.realm,
        client_id=config.keycloak.client_id,
        client_secret=config.keycloak.client_secret,
    )


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    provider: KeycloakAuthProvider = Depends(get_auth_provider),
    settings: ServiceSettings = Depends(get_settings),
) -> UserInfo:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        if settings.auth.verify_jwt:
            payload = provider.decode_token(token)
        else:
            payload = provider.decode_token_insecure(token)
        return provider.to_user(payload)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


def require_permissions(*roles: str):
    def _check(user: UserInfo = Depends(get_current_user)) -> UserInfo:
        for role in roles:
            if role not in user.roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Missing required role: {role}",
                )
        return user

    return _check
