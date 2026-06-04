from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi_core.core.config import MilvusConfig
from fastapi_core.core.milvus import (
    check_async_milvus_connection,
    create_async_milvus_client,
    ensure_async_collection_exists,
    list_async_collection_names,
)


class TestCreateAsyncMilvusClient:
    def test_uses_uri_db_name_token_and_timeout_from_config(self):
        cfg = MilvusConfig(
            uri="http://localhost:19530",
            db_name="tenant-a",
            token="secret-token",
            timeout=15.5,
        )
        mock_client = MagicMock()

        with patch(
            "fastapi_core.core.milvus.AsyncMilvusClient", return_value=mock_client
        ) as mock_cls:
            client = create_async_milvus_client(cfg)

        mock_cls.assert_called_once_with(
            uri="http://localhost:19530",
            db_name="tenant-a",
            token="secret-token",
            timeout=15.5,
        )
        assert client is mock_client


class TestListAsyncCollectionNames:
    def test_returns_collection_names(self):
        mock_client = MagicMock()
        mock_client.list_collections = AsyncMock(return_value=["docs", "images"])

        result = asyncio.run(list_async_collection_names(mock_client))

        assert result == ["docs", "images"]


class TestCheckAsyncMilvusConnection:
    def test_returns_true_when_list_succeeds(self):
        mock_client = MagicMock()
        mock_client.list_collections = AsyncMock(return_value=[])

        result = asyncio.run(check_async_milvus_connection(mock_client))

        assert result is True
        mock_client.list_collections.assert_awaited_once_with()

    def test_returns_false_when_list_raises(self):
        mock_client = MagicMock()
        mock_client.list_collections = AsyncMock(side_effect=RuntimeError("connection error"))

        result = asyncio.run(check_async_milvus_connection(mock_client))

        assert result is False


class TestEnsureAsyncCollectionExists:
    def test_creates_collection_when_missing(self):
        mock_client = MagicMock()
        mock_client.has_collection = AsyncMock(return_value=False)
        mock_client.create_collection = AsyncMock()

        asyncio.run(ensure_async_collection_exists(mock_client, "documents", dimension=768))

        mock_client.has_collection.assert_awaited_once_with("documents")
        mock_client.create_collection.assert_awaited_once_with(
            collection_name="documents",
            dimension=768,
            metric_type="COSINE",
            auto_id=False,
        )

    def test_does_not_create_when_collection_exists(self):
        mock_client = MagicMock()
        mock_client.has_collection = AsyncMock(return_value=True)
        mock_client.create_collection = AsyncMock()

        asyncio.run(ensure_async_collection_exists(mock_client, "documents", dimension=768))

        mock_client.has_collection.assert_awaited_once_with("documents")
        mock_client.create_collection.assert_not_awaited()
