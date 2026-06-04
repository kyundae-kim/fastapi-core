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


def check_milvus_connection(client: MilvusClient) -> bool:
    try:
        client.list_collections()
        return True
    except Exception:
        return False


async def check_async_milvus_connection(client: AsyncMilvusClient) -> bool:
    try:
        await client.list_collections()
        return True
    except Exception:
        return False


def list_collection_names(client: MilvusClient) -> list[str]:
    return [str(name) for name in client.list_collections()]


async def list_async_collection_names(client: AsyncMilvusClient) -> list[str]:
    return [str(name) for name in await client.list_collections()]


def ensure_collection_exists(
    client: MilvusClient,
    collection_name: str,
    *,
    dimension: int,
    metric_type: str = "COSINE",
    auto_id: bool = False,
) -> None:
    if client.has_collection(collection_name):
        return
    client.create_collection(
        collection_name=collection_name,
        dimension=dimension,
        metric_type=metric_type,
        auto_id=auto_id,
    )


async def ensure_async_collection_exists(
    client: AsyncMilvusClient,
    collection_name: str,
    *,
    dimension: int,
    metric_type: str = "COSINE",
    auto_id: bool = False,
) -> None:
    if await client.has_collection(collection_name):
        return
    await client.create_collection(
        collection_name=collection_name,
        dimension=dimension,
        metric_type=metric_type,
        auto_id=auto_id,
    )
