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


def ensure_bucket_exists(client: Minio, bucket: str) -> None:
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)


def list_buckets(client: Minio) -> list[str]:
    return [b.name for b in client.list_buckets()]


def check_minio_connection(client: Minio, bucket: str) -> bool:
    try:
        client.bucket_exists(bucket)
        return True
    except Exception:
        return False


def generate_presigned_get_url(
    client: Minio,
    bucket: str,
    object_name: str,
    expires: timedelta = timedelta(minutes=15),
) -> str:
    return client.get_presigned_url(
        "GET",
        bucket,
        object_name,
        expires=expires,
    )


def generate_presigned_put_url(
    client: Minio,
    bucket: str,
    object_name: str,
    expires: timedelta = timedelta(minutes=15),
) -> str:
    return client.get_presigned_url(
        "PUT",
        bucket,
        object_name,
        expires=expires,
    )
