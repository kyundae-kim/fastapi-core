from __future__ import annotations

from typing import Any

import httpx
from langfuse import Langfuse, get_client as langfuse_get_client

from fastapi_core.core.config import LangfuseConfig


_PUBLIC_HEALTH_PATH = "/api/public/health"


def _create_langfuse_client(config: LangfuseConfig) -> Langfuse:
    kwargs: dict[str, Any] = {
        "host": config.host,
        "timeout": config.timeout,
        "tracing_enabled": config.tracing_enabled,
    }
    if config.public_key is not None:
        kwargs["public_key"] = config.public_key
    if config.secret_key is not None:
        kwargs["secret_key"] = config.secret_key
    if config.environment is not None:
        kwargs["environment"] = config.environment
    if config.release is not None:
        kwargs["release"] = config.release
    return Langfuse(**kwargs)


def get_langfuse_client(config: LangfuseConfig | None = None) -> Langfuse:
    if config is None:
        return langfuse_get_client()

    _create_langfuse_client(config)
    if config.public_key is not None:
        return langfuse_get_client(public_key=config.public_key)
    return langfuse_get_client()


def check_langfuse_connection(config: LangfuseConfig) -> bool:
    try:
        response = httpx.get(
            f"{config.host.rstrip('/')}{_PUBLIC_HEALTH_PATH}",
            timeout=config.timeout,
        )
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError):
        return False

    return str(payload.get("status", "")).upper() == "OK"
