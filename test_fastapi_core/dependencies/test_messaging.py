"""Unit tests for fastapi_core.dependencies.messaging."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import anyio
import pytest
from fastapi import FastAPI, Request

from fastapi_core.core.config import EnvConfig
from fastapi_core.dependencies.messaging import get_nats_client, set_nats_client


def _make_request(app: FastAPI) -> Request:
    scope = {"type": "http", "app": app, "method": "GET", "path": "/", "headers": []}
    return Request(scope)


class TestSetNatsClient:
    def test_set_with_direct_client(self):
        app = FastAPI()
        mock_client = MagicMock()

        async def run():
            await set_nats_client(app, client=mock_client)

        anyio.run(run)
        assert app.state.nats_client is mock_client

    def test_set_with_config_calls_create(self):
        app = FastAPI()
        mock_client = MagicMock()
        config = EnvConfig()

        with patch(
            "fastapi_core.dependencies.messaging.create_nats_client",
            new=AsyncMock(return_value=mock_client),
        ) as mock_create:
            async def run():
                await set_nats_client(app, config=config)

            anyio.run(run)

        mock_create.assert_awaited_once_with(config.nats)
        assert app.state.nats_client is mock_client

    def test_raises_value_error_when_both_none(self):
        app = FastAPI()

        async def run():
            await set_nats_client(app)

        with pytest.raises(ValueError, match="Either client or config must be provided"):
            anyio.run(run)


class TestGetNatsClient:
    def test_returns_registered_client(self):
        app = FastAPI()
        mock_client = MagicMock()
        app.state.nats_client = mock_client

        request = _make_request(app)
        result = get_nats_client(request)
        assert result is mock_client

    def test_raises_runtime_error_when_not_initialized(self):
        app = FastAPI()
        request = _make_request(app)
        with pytest.raises(RuntimeError, match="NATS client is not initialized"):
            get_nats_client(request)
