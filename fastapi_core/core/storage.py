from __future__ import annotations

from datetime import timedelta

from minio import Minio

from fastapi_core.core.config import MinIOConfig


def create_minio_client(config: MinIOConfig) -> Minio:
    return Minio(
        endpoint=config.endpoint,
        access_key=config.access_key,
        secret_key=config.secret_key,
        secure=config.secure,
    )


def check_minio_connection(client: Minio, bucket: str) -> bool:
    try:
        client.bucket_exists(bucket)
        return True
    except Exception:
        return False


def ensure_bucket_exists(client: Minio, bucket: str) -> bool:
    if client.bucket_exists(bucket):
        return False
    client.make_bucket(bucket)
    return True


def list_bucket_names(client: Minio) -> list[str]:
    return [bucket.name for bucket in client.list_buckets()]


def generate_presigned_get_url(
    client: Minio,
    config: MinIOConfig,
    bucket: str,
    object_name: str,
) -> str:
    return client.presigned_get_object(
        bucket,
        object_name,
        expires=timedelta(seconds=config.presigned_expires_sec),
    )


def generate_presigned_put_url(
    client: Minio,
    config: MinIOConfig,
    bucket: str,
    object_name: str,
) -> str:
    return client.presigned_put_object(
        bucket,
        object_name,
        expires=timedelta(seconds=config.presigned_expires_sec),
    )
