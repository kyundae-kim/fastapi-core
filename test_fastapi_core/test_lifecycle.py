from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import anyio
from fastapi import FastAPI

from fastapi_core.core.config import EnvConfig
from fastapi_core.lifecycle import (
    create_managed_lifespan,
    initialize_app_services,
    shutdown_app_services,
)


def test_initialize_app_services_initializes_selected_services():
    app = FastAPI()
    config = EnvConfig()

    with (
        patch("fastapi_core.lifecycle.set_auth_provider") as mock_set_auth_provider,
        patch("fastapi_core.lifecycle.set_db_engine") as mock_set_db_engine,
        patch("fastapi_core.lifecycle.set_minio_client") as mock_set_minio_client,
        patch("fastapi_core.lifecycle.set_milvus_client") as mock_set_milvus_client,
        patch("fastapi_core.lifecycle.set_ollama_client") as mock_set_ollama_client,
        patch("fastapi_core.lifecycle.get_langfuse_client") as mock_get_langfuse_client,
        patch("fastapi_core.lifecycle.set_nats_client", new=AsyncMock()) as mock_set_nats_client,
    ):
        anyio.run(lambda: initialize_app_services(app, config, init_nats=True))

    mock_set_auth_provider.assert_called_once_with(app, config=config)
    mock_set_db_engine.assert_called_once_with(app, config=config)
    mock_set_minio_client.assert_called_once_with(app, config=config)
    mock_set_milvus_client.assert_called_once_with(app, config=config)
    mock_set_ollama_client.assert_called_once_with(app, config=config)
    mock_get_langfuse_client.assert_called_once_with(config.langfuse)
    mock_set_nats_client.assert_awaited_once_with(app, config=config)


def test_shutdown_app_services_closes_registered_resources():
    app = FastAPI()
    app.state.db_engine = MagicMock()
    app.state.milvus_client = MagicMock()
    app.state.nats_client = MagicMock(drain=AsyncMock())
    app.state.async_milvus_client = MagicMock(close=AsyncMock())

    anyio.run(lambda: shutdown_app_services(app))

    app.state.db_engine.dispose.assert_called_once_with()
    app.state.milvus_client.close.assert_called_once_with()
    app.state.nats_client.drain.assert_awaited_once_with()
    app.state.async_milvus_client.close.assert_awaited_once_with()


def test_create_managed_lifespan_runs_init_and_shutdown():
    config = EnvConfig()
    app = FastAPI()

    with (
        patch("fastapi_core.lifecycle.initialize_app_services", new=AsyncMock()) as mock_init,
        patch("fastapi_core.lifecycle.shutdown_app_services", new=AsyncMock()) as mock_shutdown,
    ):
        lifespan = create_managed_lifespan(config, init_nats=True)

        async def run() -> None:
            async with lifespan(app):
                mock_init.assert_awaited_once_with(app, config, init_nats=True)
                mock_shutdown.assert_not_called()

        anyio.run(run)

    mock_shutdown.assert_awaited_once_with(app)
