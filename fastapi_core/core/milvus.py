from __future__ import annotations

from pymilvus import AsyncMilvusClient, MilvusClient

from fastapi_core.core.config import MilvusConfig


def _milvus_client_kwargs(config: MilvusConfig) -> dict[str, object]:
    kwargs: dict[str, object] = {
        "uri": config.uri,
        "db_name": config.db_name,
        "timeout": config.timeout,
    }
    if config.token is not None:
        kwargs["token"] = config.token
    return kwargs


def create_milvus_client(config: MilvusConfig) -> MilvusClient:
    return MilvusClient(**_milvus_client_kwargs(config))


def create_async_milvus_client(config: MilvusConfig) -> AsyncMilvusClient:
    return AsyncMilvusClient(**_milvus_client_kwargs(config))
