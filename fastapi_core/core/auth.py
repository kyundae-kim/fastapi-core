from __future__ import annotations

from typing import Any

import httpx
import jwt

from fastapi_core.schemas.user import UserInfo


def _extract_roles(payload: dict[str, Any]) -> list[str]:
    return payload.get("realm_access", {}).get("roles", [])


def _extract_scopes(payload: dict[str, Any]) -> list[str]:
    if "scp" in payload:
        scp = payload["scp"]
        return scp if isinstance(scp, list) else [scp]
    scope = payload.get("scope", "")
    return scope.split() if scope else []


class KeycloakAuthProvider:
    def __init__(
        self,
        http_url: str,
        realm: str,
        client_id: str,
        client_secret: str | None = None,
    ) -> None:
        if not http_url:
            raise ValueError("http_url must not be empty")
        if not realm:
            raise ValueError("realm must not be empty")
        if not client_id:
            raise ValueError("client_id must not be empty")

        base = str(http_url).rstrip("/")
        self.realm = realm
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_url = (
            f"{base}/realms/{realm}/protocol/openid-connect/token"
        )
        self.jwks_url = (
            f"{base}/realms/{realm}/protocol/openid-connect/certs"
        )
        self.issuer = f"{base}/realms/{realm}"

    def to_user(self, payload: dict[str, Any]) -> UserInfo:
        return UserInfo(
            sub=payload["sub"],
            username=payload.get("preferred_username", ""),
            email=payload.get("email"),
            name=payload.get("name"),
            roles=_extract_roles(payload),
            scopes=_extract_scopes(payload),
        )

    def decode_token_insecure(self, token: str) -> dict[str, Any]:
        try:
            return jwt.decode(
                token,
                options={"verify_signature": False},
                algorithms=["RS256", "HS256"],
            )
        except jwt.PyJWTError as e:
            raise ValueError(f"Invalid token: {e}") from e

    def decode_token(self, token: str) -> dict[str, Any]:
        try:
            jwks_client = jwt.PyJWKClient(self.jwks_url)
            signing_key = jwks_client.get_signing_key_from_jwt(token)
            return jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self.client_id,
                issuer=self.issuer,
            )
        except jwt.PyJWTError as e:
            raise ValueError(f"Invalid token: {e}") from e

    def authenticate(self, username: str, password: str) -> dict[str, Any]:
        data: dict[str, str] = {
            "grant_type": "password",
            "username": username,
            "password": password,
            "client_id": self.client_id,
        }
        if self.client_secret:
            data["client_secret"] = self.client_secret

        with httpx.Client() as client:
            response = client.post(self.token_url, data=data)
        response.raise_for_status()
        return response.json()

    def refresh_access_token(self, refresh_token: str) -> dict[str, Any]:
        data: dict[str, str] = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.client_id,
        }
        if self.client_secret:
            data["client_secret"] = self.client_secret

        with httpx.Client() as client:
            response = client.post(self.token_url, data=data)
        response.raise_for_status()
        return response.json()
