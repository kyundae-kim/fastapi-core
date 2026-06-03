from __future__ import annotations

from fastapi import Depends, FastAPI, Request
from fastapi.params import Depends as DependsParam
from minio import Minio

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
    setattr(app.state, _MINIO_CLIENT_STATE_KEY, client)


def get_minio_client(
    request: Request,
    config: EnvConfig | DependsParam = Depends(get_config),
) -> Minio:
    try:
        return getattr(request.app.state, _MINIO_CLIENT_STATE_KEY)
    except AttributeError:
        if isinstance(config, DependsParam):
            config = get_config(request)
        client = create_minio_client(config.minio)
        set_minio_client(request.app, client)
        return client
