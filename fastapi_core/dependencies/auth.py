from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.params import Depends as DependsParam
from fastapi.security import OAuth2PasswordBearer

from fastapi_core.bootstrap import get_or_create_state_value, set_state_value
from fastapi_core.core.auth import KeycloakAuthProvider
from fastapi_core.core.config import EnvConfig, ServiceSettings
from fastapi_core.dependencies.config import get_config, get_settings
from fastapi_core.docmesh_bridge import get_required_docmesh_service
from fastapi_core.schemas.user import UserInfo

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=EnvConfig().token_url,
    auto_error=False,
)

_AUTH_PROVIDER_STATE_KEY = "auth_provider"


class _RegistryKeycloakAuthAdapter:
    def __init__(self, service: object) -> None:
        self._service = service
        allowed_algorithms = getattr(service, "allowed_algorithms", None)
        if isinstance(allowed_algorithms, list) and "RS256" not in allowed_algorithms:
            service.allowed_algorithms = [*allowed_algorithms, "RS256"]

    def decode_token(self, token: str) -> dict[str, object]:
        user = self._service.extract_user_info(token)
        claims = getattr(user, "claims", None)
        if not isinstance(claims, dict):
            raise ValueError("Registry auth service returned invalid claims")
        return claims

    def decode_token_insecure(self, token: str) -> dict[str, object]:
        return KeycloakAuthProvider.decode_token_insecure(self, token)

    def authenticate(self, username: str, password: str) -> dict[str, object]:
        settings = self._service.settings.keycloak
        payload: dict[str, str] = {
            "grant_type": "password",
            "client_id": settings.client_id,
            "username": username,
            "password": password,
        }
        if settings.client_secret:
            payload["client_secret"] = settings.client_secret
        if settings.token_scope:
            payload["scope"] = settings.token_scope

        response = self._service.http_client.post(
            self._service.token_endpoint,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=settings.request_timeout_seconds,
            verify_ssl=settings.verify_ssl,
        )
        status_code = int(response.get("status_code", 0))
        body = response.get("json")
        if not isinstance(body, dict):
            body = {}
        if 200 <= status_code < 300:
            return {
                "access_token": body.get("access_token"),
                "refresh_token": body.get("refresh_token"),
                "token_type": body.get("token_type", "bearer"),
                "expires_in": body.get("expires_in"),
                "scope": body.get("scope"),
            }
        detail = body.get("error_description") or body.get("error") or response.get("text") or "token request failed"
        raise ValueError(str(detail))

    def to_user(self, payload: dict[str, object]) -> UserInfo:
        return UserInfo(
            sub=str(payload["sub"]),
            username=str(payload.get("preferred_username", "")),
            email=payload.get("email") if isinstance(payload.get("email"), str) else None,
            name=payload.get("name") if isinstance(payload.get("name"), str) else None,
            roles=payload.get("realm_access", {}).get("roles", []) if isinstance(payload.get("realm_access"), dict) else [],
            scopes=(
                payload["scp"]
                if isinstance(payload.get("scp"), list)
                else str(payload.get("scope", "")).split() if payload.get("scope") else []
            ),
        )


def _adapt_auth_provider(provider: KeycloakAuthProvider | object) -> KeycloakAuthProvider | object:
    if hasattr(provider, "decode_token") and hasattr(provider, "to_user"):
        return provider
    if hasattr(provider, "extract_user_info"):
        return _RegistryKeycloakAuthAdapter(provider)
    return provider


def set_auth_provider(
    app: FastAPI,
    provider: KeycloakAuthProvider | None = None,
    *,
    config: EnvConfig | None = None,
) -> None:
    if provider is None:
        if config is None:
            raise ValueError("Either provider or config must be provided")
        provider = _adapt_auth_provider(get_required_docmesh_service(
            app,
            _AUTH_PROVIDER_STATE_KEY,
            config=config,
        ))
    set_state_value(app, _AUTH_PROVIDER_STATE_KEY, provider)


def get_auth_provider(
    request: Request,
    config: EnvConfig | DependsParam = Depends(get_config),
) -> KeycloakAuthProvider:
    def factory() -> KeycloakAuthProvider:
        resolved_config = config
        if isinstance(resolved_config, DependsParam):
            resolved_config = get_config(request)
        return _adapt_auth_provider(get_required_docmesh_service(
            request.app,
            _AUTH_PROVIDER_STATE_KEY,
            config=resolved_config,
        ))

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
