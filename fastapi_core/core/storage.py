from __future__ import annotations

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
