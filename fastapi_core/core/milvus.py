from __future__ import annotations

from collections.abc import Awaitable
from typing import cast

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


def check_milvus_connection(client: MilvusClient) -> bool:
    try:
        client.list_collections()
        return True
    except Exception:
        return False


async def check_async_milvus_connection(client: AsyncMilvusClient) -> bool:
    try:
        await cast(Awaitable[object], client.list_collections())
        return True
    except Exception:
        return False


def list_collection_names(client: MilvusClient) -> list[str]:
    return list(client.list_collections())


async def list_async_collection_names(client: AsyncMilvusClient) -> list[str]:
    names = await cast(Awaitable[list[str]], client.list_collections())
    return list(names)


def ensure_collection_exists(
    client: MilvusClient,
    collection_name: str,
    *,
    dimension: int,
) -> bool:
    if client.has_collection(collection_name=collection_name):
        return False
    client.create_collection(collection_name=collection_name, dimension=dimension)
    return True


async def ensure_async_collection_exists(
    client: AsyncMilvusClient,
    collection_name: str,
    *,
    dimension: int,
) -> bool:
    exists = await cast(
        Awaitable[bool],
        client.has_collection(collection_name=collection_name),
    )
    if exists:
        return False
    await cast(
        Awaitable[object],
        client.create_collection(collection_name=collection_name, dimension=dimension),
    )
    return True
