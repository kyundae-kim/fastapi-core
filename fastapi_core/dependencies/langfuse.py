from __future__ import annotations

from typing import Any

from fastapi import Depends, FastAPI, Request
from fastapi.params import Depends as DependsParam

from fastapi_core.bootstrap import get_or_create_state_value, set_state_value
from fastapi_core.core.config import EnvConfig
from fastapi_core.core.langfuse import get_langfuse_client as build_langfuse_client
from fastapi_core.dependencies.config import get_config
from fastapi_core.docmesh_bridge import get_docmesh_service

_LANGFUSE_CLIENT_STATE_KEY = "langfuse_client"


def set_langfuse_client(
    app: FastAPI,
    client: Any | None = None,
    *,
    config: EnvConfig | None = None,
) -> None:
    if client is None:
        if config is None:
            raise ValueError("Either client or config must be provided")
        client = build_langfuse_client(config.langfuse)
    set_state_value(app, _LANGFUSE_CLIENT_STATE_KEY, client)


def get_langfuse_client(
    request: Request,
    config: EnvConfig | DependsParam = Depends(get_config),
) -> Any:
    def factory() -> Any:
        docmesh_client = get_docmesh_service(request.app, "langfuse")
        if docmesh_client is not None:
            return docmesh_client
        resolved_config = config
        if isinstance(resolved_config, DependsParam):
            resolved_config = get_config(request)
        return build_langfuse_client(resolved_config.langfuse)

    return get_or_create_state_value(request.app, _LANGFUSE_CLIENT_STATE_KEY, factory)