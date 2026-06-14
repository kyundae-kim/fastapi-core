from __future__ import annotations

import ollama
from fastapi import Depends, FastAPI, Request
from fastapi.params import Depends as DependsParam

from fastapi_core.bootstrap import get_or_create_state_value, set_state_value
from fastapi_core.core.config import EnvConfig
from fastapi_core.core.ollama import create_ollama_client
from fastapi_core.dependencies.config import get_config
from fastapi_core.docmesh_bridge import get_docmesh_service

_OLLAMA_CLIENT_STATE_KEY = "ollama_client"


def set_ollama_client(
    app: FastAPI,
    client: ollama.Client | None = None,
    *,
    config: EnvConfig | None = None,
) -> None:
    if client is None:
        if config is None:
            raise ValueError("Either client or config must be provided")
        client = create_ollama_client(config.ollama)
    set_state_value(app, _OLLAMA_CLIENT_STATE_KEY, client)


def get_ollama_client(
    request: Request,
    config: EnvConfig | DependsParam = Depends(get_config),
) -> ollama.Client:
    def factory() -> ollama.Client:
        docmesh_client = get_docmesh_service(request.app, "ollama")
        if docmesh_client is not None:
            return docmesh_client
        resolved_config = config
        if isinstance(resolved_config, DependsParam):
            resolved_config = get_config(request)
        return create_ollama_client(resolved_config.ollama)

    return get_or_create_state_value(request.app, _OLLAMA_CLIENT_STATE_KEY, factory)
