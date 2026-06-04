"""비동기 Milvus core 통합 테스트 — 실제 Milvus 서비스 필요."""
from __future__ import annotations

from uuid import uuid4

import pytest
from pymilvus import AsyncMilvusClient

from fastapi_core.core.config import EnvConfig
from fastapi_core.core.milvus import (
    check_async_milvus_connection,
    create_async_milvus_client,
    ensure_async_collection_exists,
    list_async_collection_names,
)


@pytest.mark.asyncio
async def test_create_async_milvus_client_connects():
    client = create_async_milvus_client(EnvConfig().milvus)
    try:
        assert isinstance(client, AsyncMilvusClient)
        assert await check_async_milvus_connection(client) is True
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_list_async_collection_names_returns_list():
    client = create_async_milvus_client(EnvConfig().milvus)
    try:
        names = await list_async_collection_names(client)
    finally:
        await client.close()

    assert isinstance(names, list)
    assert all(isinstance(name, str) for name in names)


@pytest.mark.asyncio
async def test_ensure_async_collection_exists_creates_collection():
    client = create_async_milvus_client(EnvConfig().milvus)
    collection_name = f"test_async_{uuid4().hex[:8]}"
    try:
        await ensure_async_collection_exists(client, collection_name, dimension=8)
        assert await client.has_collection(collection_name) is True
    finally:
        if await client.has_collection(collection_name):
            await client.drop_collection(collection_name)
        await client.close()
