from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.params import Depends as DependsParam
from fastapi.security import OAuth2PasswordBearer

from fastapi_core.bootstrap import get_or_create_state_value, set_state_value
from fastapi_core.core.auth import KeycloakAuthProvider
from fastapi_core.core.config import EnvConfig, ServiceSettings
from fastapi_core.dependencies.config import get_config, get_settings
from fastapi_core.docmesh_bridge import get_docmesh_service
from fastapi_core.schemas.user import UserInfo

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=EnvConfig().token_url,
    auto_error=False,
)

_AUTH_PROVIDER_STATE_KEY = "auth_provider"


def set_auth_provider(
    app: FastAPI,
    provider: KeycloakAuthProvider | None = None,
    *,
    config: EnvConfig | None = None,
) -> None:
    if provider is None:
        if config is None:
            raise ValueError("Either provider or config must be provided")
        provider = KeycloakAuthProvider(
            http_url=str(config.keycloak.http_url),
            realm=config.keycloak.realm,
            client_id=config.keycloak.client_id,
            client_secret=config.keycloak.client_secret,
        )
    set_state_value(app, _AUTH_PROVIDER_STATE_KEY, provider)


def get_auth_provider(
    request: Request,
    config: EnvConfig | DependsParam = Depends(get_config),
) -> KeycloakAuthProvider:
    def factory() -> KeycloakAuthProvider:
        docmesh_provider = get_docmesh_service(request.app, "keycloak")
        if docmesh_provider is not None:
            return docmesh_provider
        resolved_config = config
        if isinstance(resolved_config, DependsParam):
            resolved_config = get_config(request)
        return KeycloakAuthProvider(
            http_url=str(resolved_config.keycloak.http_url),
            realm=resolved_config.keycloak.realm,
            client_id=resolved_config.keycloak.client_id,
            client_secret=resolved_config.keycloak.client_secret,
        )

    return get_or_create_state_value(request.app, _AUTH_PROVIDER_STATE_KEY, factory)


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
