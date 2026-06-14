"""Unit tests for fastapi_core.core.messaging."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import anyio

from fastapi_core.core.config import NatsConfig
from fastapi_core.core.messaging import create_nats_client


class TestNatsConfig:
    def test_default_values(self):
        cfg = NatsConfig()
        assert cfg.servers == "nats://nats:4222"
        assert cfg.name == "fastapi-core"
        assert cfg.connect_timeout == 2
        assert cfg.max_reconnect_attempts == 60
        assert cfg.reconnect_time_wait_ms == 2000
        assert cfg.queue_group == "default-workers"

    def test_server_list_single(self):
        cfg = NatsConfig(servers="nats://nats:4222")
        assert cfg.server_list == ["nats://nats:4222"]

    def test_server_list_multiple(self):
        cfg = NatsConfig(servers="nats://nats:4222,nats://nats-2:4222")
        assert cfg.server_list == ["nats://nats:4222", "nats://nats-2:4222"]

    def test_server_list_strips_whitespace(self):
        cfg = NatsConfig(servers="nats://a:4222 , nats://b:4222")
        assert cfg.server_list == ["nats://a:4222", "nats://b:4222"]


class TestCreateNatsClient:
    def test_calls_nats_connect_with_correct_args(self):
        cfg = NatsConfig(
            servers="nats://localhost:4222",
            name="test-app",
            connect_timeout=3,
            max_reconnect_attempts=5,
            reconnect_time_wait_ms=1000,
        )
        mock_client = MagicMock()

        with patch("fastapi_core.core.messaging.nats.connect", new=AsyncMock(return_value=mock_client)) as mock_connect:
            async def run():
                return await create_nats_client(cfg)

            result = anyio.run(run)

        mock_connect.assert_awaited_once_with(
            servers=["nats://localhost:4222"],
            name="test-app",
            connect_timeout=3,
            max_reconnect_attempts=5,
            reconnect_time_wait=1.0,
        )
        assert result is mock_client
