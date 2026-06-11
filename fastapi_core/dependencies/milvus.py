from __future__ import annotations

from fastapi import Depends, FastAPI, Request
from fastapi.params import Depends as DependsParam
from pymilvus import MilvusClient

from fastapi_core.bootstrap import get_or_create_state_value, set_state_value
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
    set_state_value(app, _MILVUS_CLIENT_STATE_KEY, client)


def get_milvus_client(
    request: Request,
    config: EnvConfig | DependsParam = Depends(get_config),
) -> MilvusClient:
    def factory() -> MilvusClient:
        resolved_config = config
        if isinstance(resolved_config, DependsParam):
            resolved_config = get_config(request)
        return create_milvus_client(resolved_config.milvus)

    return get_or_create_state_value(request.app, _MILVUS_CLIENT_STATE_KEY, factory)
