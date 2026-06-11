from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
import inspect
from typing import Any

from fastapi import FastAPI

from fastapi_core.core.config import EnvConfig
from fastapi_core.core.langfuse import get_langfuse_client
from fastapi_core.dependencies.async_milvus import set_async_milvus_client
from fastapi_core.dependencies.auth import set_auth_provider
from fastapi_core.dependencies.database import set_db_engine
from fastapi_core.dependencies.messaging import set_nats_client
from fastapi_core.dependencies.milvus import set_milvus_client
from fastapi_core.dependencies.ollama import set_ollama_client
from fastapi_core.dependencies.storage import set_minio_client


async def initialize_app_services(
    app: FastAPI,
    config: EnvConfig,
    *,
    init_auth: bool = True,
    init_database: bool = True,
    init_minio: bool = True,
    init_milvus: bool = True,
    init_async_milvus: bool = False,
    init_ollama: bool = True,
    init_langfuse: bool = True,
    init_nats: bool = False,
) -> None:
    if init_auth:
        set_auth_provider(app, config=config)
    if init_database:
        set_db_engine(app, config=config)
    if init_minio:
        set_minio_client(app, config=config)
    if init_milvus:
        set_milvus_client(app, config=config)
    if init_async_milvus:
        await set_async_milvus_client(app, config=config)
    if init_ollama:
        set_ollama_client(app, config=config)
    if init_langfuse:
        get_langfuse_client(config.langfuse)
    if init_nats:
        await set_nats_client(app, config=config)


async def _call_maybe_async(method: Callable[[], Any]) -> None:
    result = method()
    if inspect.isawaitable(result):
        await result


async def shutdown_app_services(app: FastAPI) -> None:
    for state_key, method_name in (
        ("nats_client", "drain"),
        ("async_milvus_client", "close"),
        ("milvus_client", "close"),
        ("db_engine", "dispose"),
    ):
        resource = getattr(app.state, state_key, None)
        if resource is None:
            continue
        method = getattr(resource, method_name, None)
        if method is None:
            continue
        await _call_maybe_async(method)


def create_managed_lifespan(
    config: EnvConfig,
    *,
    init_nats: bool = False,
) -> Callable[[FastAPI], AsyncIterator[None]]:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        await initialize_app_services(app, config, init_nats=init_nats)
        try:
            yield
        finally:
            await shutdown_app_services(app)

    return lifespan
