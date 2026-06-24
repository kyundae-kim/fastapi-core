from __future__ import annotations

from fastapi import Depends, FastAPI, Request
from fastapi.params import Depends as DependsParam
from pymilvus import MilvusClient

from fastapi_core.bootstrap import get_or_create_state_value, set_state_value
from fastapi_core.core.config import EnvConfig
from fastapi_core.core.milvus import create_milvus_client
from fastapi_core.dependencies.config import get_config
from fastapi_core.docmesh_bridge import get_required_docmesh_service, resolve_milvus_config

_MILVUS_CLIENT_STATE_KEY = "milvus_client"


def _resolve_sync_milvus_config(app: FastAPI, config: EnvConfig):
    return resolve_milvus_config(
        config,
        docmesh_settings=getattr(app.state, "docmesh_settings", None),
    )


def set_milvus_client(
    app: FastAPI,
    client: MilvusClient | None = None,
    *,
    config: EnvConfig | None = None,
) -> None:
    if client is None:
        if config is None:
            raise ValueError("Either client or config must be provided")
        if getattr(app.state, "docmesh_registry", None) is not None:
            client = get_required_docmesh_service(
                app,
                _MILVUS_CLIENT_STATE_KEY,
                config=config,
            )
        else:
            client = create_milvus_client(_resolve_sync_milvus_config(app, config))
    set_state_value(app, _MILVUS_CLIENT_STATE_KEY, client)


def get_milvus_client(
    request: Request,
    config: EnvConfig | DependsParam = Depends(get_config),
) -> MilvusClient:
    def factory() -> MilvusClient:
        resolved_config = config
        if isinstance(resolved_config, DependsParam):
            resolved_config = get_config(request)
        if getattr(request.app.state, "docmesh_registry", None) is not None:
            return get_required_docmesh_service(
                request.app,
                _MILVUS_CLIENT_STATE_KEY,
                config=resolved_config,
            )
        return create_milvus_client(
            _resolve_sync_milvus_config(request.app, resolved_config)
        )

    return get_or_create_state_value(request.app, _MILVUS_CLIENT_STATE_KEY, factory)
