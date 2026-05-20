from __future__ import annotations

from fastapi import Depends
from minio import Minio

from fastapi_core.core.config import EnvConfig
from fastapi_core.core.storage import create_minio_client
from fastapi_core.dependencies.config import get_config


def get_minio_client(config: EnvConfig = Depends(get_config)) -> Minio:
    return create_minio_client(config.minio)
