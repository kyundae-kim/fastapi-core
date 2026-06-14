from __future__ import annotations

from unittest.mock import MagicMock, patch

from fastapi_core.core.config import MilvusConfig
from fastapi_core.core.milvus import create_async_milvus_client


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
