from __future__ import annotations

import ollama
from fastapi import Depends, FastAPI, Request
from fastapi.params import Depends as DependsParam

from fastapi_core.core.config import EnvConfig
from fastapi_core.core.ollama import create_ollama_client
from fastapi_core.dependencies.config import get_config

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
    setattr(app.state, _OLLAMA_CLIENT_STATE_KEY, client)


def get_ollama_client(
    request: Request,
    config: EnvConfig | DependsParam = Depends(get_config),
) -> ollama.Client:
    try:
        return getattr(request.app.state, _OLLAMA_CLIENT_STATE_KEY)
    except AttributeError:
        if isinstance(config, DependsParam):
            config = get_config(request)
        client = create_ollama_client(config.ollama)
        set_ollama_client(request.app, client)
        return client
