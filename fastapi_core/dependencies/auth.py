from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer

from fastapi_core.core.auth import KeycloakAuthProvider
from fastapi_core.core.config import EnvConfig, ServiceSettings
from fastapi_core.dependencies.config import config_schema, settings_schema
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
    setattr(app.state, _AUTH_PROVIDER_STATE_KEY, provider)


class GetAuthProviderDependency:
    def __call__(
        self,
        request: Request,
        config: EnvConfig = Depends(config_schema),
    ) -> KeycloakAuthProvider:
        try:
            return getattr(request.app.state, _AUTH_PROVIDER_STATE_KEY)
        except AttributeError:
            provider = KeycloakAuthProvider(
                http_url=str(config.keycloak.http_url),
                realm=config.keycloak.realm,
                client_id=config.keycloak.client_id,
                client_secret=config.keycloak.client_secret,
            )
            setattr(request.app.state, _AUTH_PROVIDER_STATE_KEY, provider)
            return provider


get_auth_provider = GetAuthProviderDependency()


class GetCurrentUserDependency:
    def __call__(
        self,
        token: str | None = Depends(oauth2_scheme),
        provider: KeycloakAuthProvider = Depends(get_auth_provider),
        settings: ServiceSettings = Depends(settings_schema),
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


get_current_user = GetCurrentUserDependency()


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
