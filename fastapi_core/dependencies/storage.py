from __future__ import annotations

from fastapi import Depends, FastAPI, Request
from fastapi.params import Depends as DependsParam
from minio import Minio

from fastapi_core.bootstrap import get_or_create_state_value, set_state_value
from fastapi_core.core.config import EnvConfig
from fastapi_core.core.storage import create_minio_client
from fastapi_core.dependencies.config import get_config

_MINIO_CLIENT_STATE_KEY = "minio_client"


def set_minio_client(
    app: FastAPI,
    client: Minio | None = None,
    *,
    config: EnvConfig | None = None,
) -> None:
    if client is None:
        if config is None:
            raise ValueError("Either client or config must be provided")
        client = create_minio_client(config.minio)
    set_state_value(app, _MINIO_CLIENT_STATE_KEY, client)


def get_minio_client(
    request: Request,
    config: EnvConfig | DependsParam = Depends(get_config),
) -> Minio:
    def factory() -> Minio:
        resolved_config = config
        if isinstance(resolved_config, DependsParam):
            resolved_config = get_config(request)
        return create_minio_client(resolved_config.minio)

    return get_or_create_state_value(request.app, _MINIO_CLIENT_STATE_KEY, factory)
