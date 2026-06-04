from __future__ import annotations

from pymilvus import MilvusClient

from fastapi_core.core.config import MilvusConfig


def create_milvus_client(config: MilvusConfig) -> MilvusClient:
    kwargs: dict[str, object] = {
        "uri": config.uri,
        "db_name": config.db_name,
        "timeout": config.timeout,
    }
    if config.token is not None:
        kwargs["token"] = config.token
    return MilvusClient(**kwargs)


def check_milvus_connection(client: MilvusClient) -> bool:
    try:
        client.list_collections()
        return True
    except Exception:
        return False


def list_collection_names(client: MilvusClient) -> list[str]:
    return [str(name) for name in client.list_collections()]


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
