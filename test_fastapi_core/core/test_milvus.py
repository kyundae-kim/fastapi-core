from __future__ import annotations

from unittest.mock import MagicMock, patch

from fastapi_core.core.config import MilvusConfig
from fastapi_core.core.milvus import (
    check_milvus_connection,
    create_milvus_client,
    ensure_collection_exists,
    list_collection_names,
)


class TestMilvusConfig:
    def test_default_values(self):
        cfg = MilvusConfig()
        assert cfg.uri == "http://milvus:19530"
        assert cfg.db_name == ""
        assert cfg.token == ""
        assert cfg.timeout is None


class TestCreateMilvusClient:
    def test_uses_uri_db_name_token_and_timeout_from_config(self):
        cfg = MilvusConfig(
            uri="http://localhost:19530",
            db_name="tenant-a",
            token="secret-token",
            timeout=15.5,
        )
        mock_client = MagicMock()

        with patch("fastapi_core.core.milvus.MilvusClient", return_value=mock_client) as mock_cls:
            client = create_milvus_client(cfg)

        mock_cls.assert_called_once_with(
            uri="http://localhost:19530",
            db_name="tenant-a",
            token="secret-token",
            timeout=15.5,
        )
        assert client is mock_client


class TestMilvusHelpers:
    def test_check_milvus_connection_returns_true_when_list_collections_succeeds(self):
        mock_client = MagicMock()
        mock_client.list_collections.return_value = ["docs"]

        assert check_milvus_connection(mock_client) is True

    def test_check_milvus_connection_returns_false_on_error(self):
        mock_client = MagicMock()
        mock_client.list_collections.side_effect = RuntimeError("milvus down")

        assert check_milvus_connection(mock_client) is False

    def test_list_collection_names_returns_sdk_collection_names(self):
        mock_client = MagicMock()
        mock_client.list_collections.return_value = ["docs", "images"]

        assert list_collection_names(mock_client) == ["docs", "images"]

    def test_ensure_collection_exists_skips_existing_collection(self):
        mock_client = MagicMock()
        mock_client.has_collection.return_value = True

        created = ensure_collection_exists(mock_client, "docs", dimension=384)

        assert created is False
        mock_client.has_collection.assert_called_once_with(collection_name="docs")
        mock_client.create_collection.assert_not_called()

    def test_ensure_collection_exists_creates_missing_collection(self):
        mock_client = MagicMock()
        mock_client.has_collection.return_value = False

        created = ensure_collection_exists(mock_client, "docs", dimension=384)

        assert created is True
        mock_client.has_collection.assert_called_once_with(collection_name="docs")
        mock_client.create_collection.assert_called_once_with(
            collection_name="docs",
            dimension=384,
        )
