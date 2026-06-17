from datetime import timedelta
from unittest.mock import MagicMock, patch

from fastapi_core.core.config import MinIOConfig
from fastapi_core.core.storage import (
    check_minio_connection,
    create_minio_client,
    ensure_bucket_exists,
    generate_presigned_get_url,
    generate_presigned_put_url,
    list_bucket_names,
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



def test_check_minio_connection_success():
    mock_client = MagicMock()
    mock_client.bucket_exists.return_value = True
    assert check_minio_connection(mock_client, "bucket") is True



def test_check_minio_connection_failure():
    mock_client = MagicMock()
    mock_client.bucket_exists.side_effect = Exception("connection error")
    assert check_minio_connection(mock_client, "bucket") is False



def test_ensure_bucket_exists_creates_missing_bucket():
    mock_client = MagicMock()
    mock_client.bucket_exists.return_value = False

    created = ensure_bucket_exists(mock_client, "documents")

    assert created is True
    mock_client.bucket_exists.assert_called_once_with("documents")
    mock_client.make_bucket.assert_called_once_with("documents")



def test_ensure_bucket_exists_skips_existing_bucket():
    mock_client = MagicMock()
    mock_client.bucket_exists.return_value = True

    created = ensure_bucket_exists(mock_client, "documents")

    assert created is False
    mock_client.make_bucket.assert_not_called()



def test_list_bucket_names_returns_bucket_names():
    bucket_a = MagicMock(name="bucket-a")
    bucket_a.name = "bucket-a"
    bucket_b = MagicMock(name="bucket-b")
    bucket_b.name = "bucket-b"
    mock_client = MagicMock()
    mock_client.list_buckets.return_value = [bucket_a, bucket_b]

    bucket_names = list_bucket_names(mock_client)

    assert bucket_names == ["bucket-a", "bucket-b"]



def test_generate_presigned_get_url_uses_config_expiry():
    config = MinIOConfig(presigned_expires_sec=321)
    mock_client = MagicMock()
    mock_client.presigned_get_object.return_value = "https://minio/get"

    url = generate_presigned_get_url(mock_client, config, "documents", "report.pdf")

    assert url == "https://minio/get"
    mock_client.presigned_get_object.assert_called_once_with(
        "documents",
        "report.pdf",
        expires=timedelta(seconds=321),
    )



def test_generate_presigned_put_url_uses_config_expiry():
    config = MinIOConfig(presigned_expires_sec=654)
    mock_client = MagicMock()
    mock_client.presigned_put_object.return_value = "https://minio/put"

    url = generate_presigned_put_url(mock_client, config, "documents", "report.pdf")

    assert url == "https://minio/put"
    mock_client.presigned_put_object.assert_called_once_with(
        "documents",
        "report.pdf",
        expires=timedelta(seconds=654),
    )
