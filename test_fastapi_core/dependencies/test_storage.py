from unittest.mock import MagicMock, patch

from fastapi_core.core.config import MinIOConfig
from fastapi_core.core.storage import create_minio_client
from fastapi_core.dependencies.storage import get_minio_client


def test_get_minio_client_creates_client():
    config = MagicMock()
    config.minio = MinIOConfig(
        endpoint="minio:9000",
        access_key="admin",
        secret_key="password",
        secure=False,
    )

    with patch("fastapi_core.core.storage.Minio") as mock_cls:
        mock_instance = MagicMock()
        mock_cls.return_value = mock_instance
        client = create_minio_client(config.minio)
        assert client is mock_instance
