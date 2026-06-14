from unittest.mock import MagicMock, patch

from fastapi_core.core.config import MinIOConfig
from fastapi_core.core.storage import check_minio_connection, create_minio_client



def test_create_minio_client():
    config = MinIOConfig(
        endpoint="minio:9000",
        access_key="admin",
        secret_key="password",
        secure=False,
    )
    with patch("fastapi_core.core.storage.Minio") as mock_cls:
        mock_instance = MagicMock()
        mock_cls.return_value = mock_instance
        client = create_minio_client(config)
        mock_cls.assert_called_once_with(
            endpoint="minio:9000",
            access_key="admin",
            secret_key="password",
            secure=False,
        )
        assert client is mock_instance



def test_check_minio_connection_success():
    mock_client = MagicMock()
    mock_client.bucket_exists.return_value = True
    assert check_minio_connection(mock_client, "bucket") is True



def test_check_minio_connection_failure():
    mock_client = MagicMock()
    mock_client.bucket_exists.side_effect = Exception("connection error")
    assert check_minio_connection(mock_client, "bucket") is False
