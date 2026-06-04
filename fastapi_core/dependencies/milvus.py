from __future__ import annotations

from fastapi import Depends, FastAPI, Request
from fastapi.params import Depends as DependsParam
from pymilvus import MilvusClient

from fastapi_core.core.config import EnvConfig
from fastapi_core.core.milvus import create_milvus_client
from fastapi_core.dependencies.config import get_config

_MILVUS_CLIENT_STATE_KEY = "milvus_client"


def set_milvus_client(
    app: FastAPI,
    client: MilvusClient | None = None,
    *,
    config: EnvConfig | None = None,
) -> None:
    if client is None:
        if config is None:
            raise ValueError("Either client or config must be provided")
        client = create_milvus_client(config.milvus)
    setattr(app.state, _MILVUS_CLIENT_STATE_KEY, client)


def get_milvus_client(
    request: Request,
    config: EnvConfig | DependsParam = Depends(get_config),
) -> MilvusClient:
    try:
        return getattr(request.app.state, _MILVUS_CLIENT_STATE_KEY)
    except AttributeError:
        if isinstance(config, DependsParam):
            config = get_config(request)
        client = create_milvus_client(config.milvus)
        set_milvus_client(request.app, client)
        return client
