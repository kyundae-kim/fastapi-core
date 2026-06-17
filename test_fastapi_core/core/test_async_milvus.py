from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

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


class TestAsyncMilvusHelpers:
    @pytest.mark.asyncio
    async def test_check_async_milvus_connection_returns_true_when_list_collections_succeeds(self):
        mock_client = MagicMock()
        mock_client.list_collections = AsyncMock(return_value=["docs"])

        assert await check_async_milvus_connection(mock_client) is True

    @pytest.mark.asyncio
    async def test_check_async_milvus_connection_returns_false_on_error(self):
        mock_client = MagicMock()
        mock_client.list_collections = AsyncMock(side_effect=RuntimeError("milvus down"))

        assert await check_async_milvus_connection(mock_client) is False

    @pytest.mark.asyncio
    async def test_list_async_collection_names_returns_sdk_collection_names(self):
        mock_client = MagicMock()
        mock_client.list_collections = AsyncMock(return_value=["docs", "images"])

        assert await list_async_collection_names(mock_client) == ["docs", "images"]

    @pytest.mark.asyncio
    async def test_ensure_async_collection_exists_skips_existing_collection(self):
        mock_client = MagicMock()
        mock_client.has_collection = AsyncMock(return_value=True)
        mock_client.create_collection = AsyncMock()

        created = await ensure_async_collection_exists(
            mock_client,
            "docs",
            dimension=384,
        )

        assert created is False
        mock_client.has_collection.assert_awaited_once_with(collection_name="docs")
        mock_client.create_collection.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_ensure_async_collection_exists_creates_missing_collection(self):
        mock_client = MagicMock()
        mock_client.has_collection = AsyncMock(return_value=False)
        mock_client.create_collection = AsyncMock()

        created = await ensure_async_collection_exists(
            mock_client,
            "docs",
            dimension=384,
        )

        assert created is True
        mock_client.has_collection.assert_awaited_once_with(collection_name="docs")
        mock_client.create_collection.assert_awaited_once_with(
            collection_name="docs",
            dimension=384,
        )
