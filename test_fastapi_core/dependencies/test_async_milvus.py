from __future__ import annotations

import asyncio
import inspect
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from pymilvus import AsyncMilvusClient

from fastapi_core.core.config import MilvusConfig
from fastapi_core.dependencies.config import get_config
from fastapi_core.dependencies.async_milvus import (
    get_async_milvus_client,
    set_async_milvus_client,
)


class TestGetAsyncMilvusClient:
    def test_dependency_is_async_function(self):
        import fastapi_core.dependencies.async_milvus as async_milvus_dependencies

        assert not hasattr(async_milvus_dependencies, "GetAsyncMilvusClientDependency")
        assert inspect.iscoroutinefunction(async_milvus_dependencies.get_async_milvus_client)

    def test_returns_registered_client(self):
        app = FastAPI()
        mock_client = MagicMock(spec=AsyncMilvusClient)
        asyncio.run(set_async_milvus_client(app, mock_client))

        @app.get("/client-id")
        async def client_id(client: AsyncMilvusClient = Depends(get_async_milvus_client)):
            return {"id": id(client)}

        with patch(
            "fastapi_core.dependencies.async_milvus.create_async_milvus_client"
        ) as mock_create:
            client = TestClient(app)
            response = client.get("/client-id")
            mock_create.assert_not_called()

        assert response.status_code == 200
        assert response.json()["id"] == id(mock_client)

    def test_creates_and_caches_client_when_missing(self):
        app = FastAPI()
        mock_client = MagicMock(spec=AsyncMilvusClient)
        mock_config = MagicMock()
        mock_config.milvus = MilvusConfig()
        app.dependency_overrides[get_config] = lambda: mock_config

        @app.get("/client-id")
        async def client_id(client: AsyncMilvusClient = Depends(get_async_milvus_client)):
            return {"id": id(client)}

        with patch(
            "fastapi_core.dependencies.async_milvus.create_async_milvus_client",
            return_value=mock_client,
        ) as mock_create:
            client = TestClient(app)
            response = client.get("/client-id")
            mock_create.assert_called_once_with(mock_config.milvus)

        assert response.status_code == 200
        assert response.json()["id"] == id(mock_client)
        assert app.state.async_milvus_client is mock_client


class TestSetAsyncMilvusClient:
    def test_sets_direct_client(self):
        app = FastAPI()
        mock_client = MagicMock(spec=AsyncMilvusClient)

        asyncio.run(set_async_milvus_client(app, client=mock_client))

        assert app.state.async_milvus_client is mock_client

    def test_creates_client_from_config(self):
        app = FastAPI()
        mock_client = MagicMock(spec=AsyncMilvusClient)
        mock_config = MagicMock()
        mock_config.milvus = MilvusConfig()

        with patch(
            "fastapi_core.dependencies.async_milvus.create_async_milvus_client",
            return_value=mock_client,
        ) as mock_create:
            asyncio.run(set_async_milvus_client(app, config=mock_config))

        mock_create.assert_called_once_with(mock_config.milvus)
        assert app.state.async_milvus_client is mock_client

    def test_raises_when_client_and_config_missing(self):
        app = FastAPI()

        with pytest.raises(ValueError, match="Either client or config must be provided"):
            asyncio.run(set_async_milvus_client(app))
