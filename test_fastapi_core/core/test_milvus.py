from __future__ import annotations

from unittest.mock import MagicMock, patch

from fastapi_core.core.config import MilvusConfig
from fastapi_core.core.milvus import create_milvus_client


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
