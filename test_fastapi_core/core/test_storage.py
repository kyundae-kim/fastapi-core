from unittest.mock import MagicMock, patch

from fastapi_core.core.config import MinIOConfig
from fastapi_core.core.storage import (
    check_minio_connection,
    create_minio_client,
    ensure_bucket_exists,
    list_buckets,
)


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


def test_ensure_bucket_exists_creates_bucket():
    mock_client = MagicMock()
    mock_client.bucket_exists.return_value = False
    ensure_bucket_exists(mock_client, "test-bucket")
    mock_client.bucket_exists.assert_called_once_with("test-bucket")
    mock_client.make_bucket.assert_called_once_with("test-bucket")


def test_ensure_bucket_exists_no_create_if_exists():
    mock_client = MagicMock()
    mock_client.bucket_exists.return_value = True
    ensure_bucket_exists(mock_client, "test-bucket")
    mock_client.make_bucket.assert_not_called()


def test_list_buckets():
    mock_client = MagicMock()
    b1, b2 = MagicMock(), MagicMock()
    b1.name = "bucket-a"
    b2.name = "bucket-b"
    mock_client.list_buckets.return_value = [b1, b2]
    result = list_buckets(mock_client)
    assert result == ["bucket-a", "bucket-b"]


def test_list_buckets_empty():
    mock_client = MagicMock()
    mock_client.list_buckets.return_value = []
    assert list_buckets(mock_client) == []


def test_check_minio_connection_success():
    mock_client = MagicMock()
    mock_client.bucket_exists.return_value = True
    assert check_minio_connection(mock_client, "bucket") is True


def test_check_minio_connection_failure():
    mock_client = MagicMock()
    mock_client.bucket_exists.side_effect = Exception("connection error")
    assert check_minio_connection(mock_client, "bucket") is False
