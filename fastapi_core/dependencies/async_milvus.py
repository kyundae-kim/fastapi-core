from __future__ import annotations

from fastapi import Depends, FastAPI, Request
from fastapi.params import Depends as DependsParam
from pymilvus import AsyncMilvusClient

from fastapi_core.core.config import EnvConfig
from fastapi_core.core.milvus import create_async_milvus_client
from fastapi_core.dependencies.config import get_config

_ASYNC_MILVUS_CLIENT_STATE_KEY = "async_milvus_client"


async def set_async_milvus_client(
    app: FastAPI,
    client: AsyncMilvusClient | None = None,
    *,
    config: EnvConfig | None = None,
) -> None:
    if client is None:
        if config is None:
            raise ValueError("Either client or config must be provided")
        client = create_async_milvus_client(config.milvus)
    setattr(app.state, _ASYNC_MILVUS_CLIENT_STATE_KEY, client)


async def get_async_milvus_client(
    request: Request,
    config: EnvConfig | DependsParam = Depends(get_config),
) -> AsyncMilvusClient:
    try:
        return getattr(request.app.state, _ASYNC_MILVUS_CLIENT_STATE_KEY)
    except AttributeError:
        if isinstance(config, DependsParam):
            config = get_config(request)
        client = create_async_milvus_client(config.milvus)
        await set_async_milvus_client(request.app, client)
        return client
