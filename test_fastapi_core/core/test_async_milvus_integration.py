"""비동기 Milvus core 통합 테스트 — 실제 Milvus 서비스 필요."""
from __future__ import annotations

import pytest
from pymilvus import AsyncMilvusClient

from fastapi_core.core.config import EnvConfig
from fastapi_core.core.milvus import create_async_milvus_client


@pytest.mark.asyncio
async def test_create_async_milvus_client_connects():
    client = create_async_milvus_client(EnvConfig().milvus)
    try:
        assert isinstance(client, AsyncMilvusClient)
        names = await client.list_collections()
        assert isinstance(names, list)
    finally:
        await client.close()
