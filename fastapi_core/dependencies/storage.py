from __future__ import annotations

from fastapi import Depends, FastAPI, Request
from minio import Minio

from fastapi_core.core.config import EnvConfig
from fastapi_core.core.storage import create_minio_client
from fastapi_core.dependencies.config import config_schema

_MINIO_CLIENT_STATE_KEY = "minio_client"


def set_minio_client(
    app: FastAPI,
    client: Minio | None = None,
    *,
    config: EnvConfig | None = None,
) -> None:
    if client is None:
        if config is None:
            raise ValueError("Either client or config must be provided")
        client = create_minio_client(config.minio)
    setattr(app.state, _MINIO_CLIENT_STATE_KEY, client)


class GetMinioClientDependency:
    def __call__(
        self,
        request: Request,
        config: EnvConfig = Depends(config_schema),
    ) -> Minio:
        try:
            return getattr(request.app.state, _MINIO_CLIENT_STATE_KEY)
        except AttributeError:
            client = create_minio_client(config.minio)
            setattr(request.app.state, _MINIO_CLIENT_STATE_KEY, client)
            return client


get_minio_client = GetMinioClientDependency()
