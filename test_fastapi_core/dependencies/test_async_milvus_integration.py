"""비동기 Milvus dependency 통합 테스트 — get_async_milvus_client, set_async_milvus_client."""
from __future__ import annotations

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from pymilvus import AsyncMilvusClient

from fastapi_core.core.config import EnvConfig
from fastapi_core.core.milvus import check_async_milvus_connection
from fastapi_core.dependencies.async_milvus import (
    get_async_milvus_client,
    set_async_milvus_client,
)


@pytest.mark.asyncio
async def test_get_async_milvus_client_from_state_integration():
    app = FastAPI()
    config = EnvConfig()
    client = AsyncMilvusClient(uri=config.milvus.uri, timeout=config.milvus.timeout)
    await set_async_milvus_client(app, client)

    @app.get("/client-id")
    async def client_id(milvus: AsyncMilvusClient = Depends(get_async_milvus_client)):
        return {"id": id(milvus)}

    try:
        response = TestClient(app).get("/client-id")
    finally:
        await client.close()

    assert response.status_code == 200
    assert response.json()["id"] == id(client)


@pytest.mark.asyncio
async def test_set_async_milvus_client_from_config_integration():
    app = FastAPI()
    config = EnvConfig()

    await set_async_milvus_client(app, config=config)
    client = app.state.async_milvus_client
    try:
        assert isinstance(client, AsyncMilvusClient)
        assert await check_async_milvus_connection(client) is True
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_get_async_milvus_client_connection_available():
    app = FastAPI()

    @app.get("/collections")
    async def collections(milvus: AsyncMilvusClient = Depends(get_async_milvus_client)):
        ok = await check_async_milvus_connection(milvus)
        names = await milvus.list_collections()
        return {"ok": ok, "count": len(names)}

    response = TestClient(app).get("/collections")

    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert isinstance(response.json()["count"], int)

    await app.state.async_milvus_client.close()
