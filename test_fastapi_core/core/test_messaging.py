"""Unit tests for fastapi_core.core.messaging."""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import anyio
import pytest

from fastapi_core.core.config import NatsConfig
from fastapi_core.core.messaging import create_nats_client, publish_json, subscribe_json


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


class TestPublishJson:
    def test_publishes_json_bytes(self):
        mock_client = AsyncMock()
        payload = {"event": "test.event", "value": 42}

        async def run():
            await publish_json(mock_client, "test.subject", payload)

        anyio.run(run)

        mock_client.publish.assert_awaited_once_with(
            "test.subject",
            json.dumps(payload).encode("utf-8"),
        )


class TestSubscribeJson:
    def test_subscribe_without_queue(self):
        mock_client = AsyncMock()

        async def cb(data: dict) -> None:
            pass

        async def run():
            await subscribe_json(mock_client, "test.subject", cb)

        anyio.run(run)

        mock_client.subscribe.assert_awaited_once()
        call_kwargs = mock_client.subscribe.call_args
        assert call_kwargs.args[0] == "test.subject"
        assert "queue" not in call_kwargs.kwargs

    def test_subscribe_with_queue(self):
        mock_client = AsyncMock()

        async def cb(data: dict) -> None:
            pass

        async def run():
            await subscribe_json(mock_client, "test.subject", cb, queue="my-group")

        anyio.run(run)

        call_kwargs = mock_client.subscribe.call_args
        assert call_kwargs.kwargs.get("queue") == "my-group"

    def test_handler_deserializes_json(self):
        """subscribe 내부 핸들러가 msg.data를 JSON으로 역직렬화해 콜백에 전달하는지 확인."""
        received: list[dict] = []
        mock_client = AsyncMock()

        async def cb(data: dict) -> None:
            received.append(data)

        async def run():
            await subscribe_json(mock_client, "test.subject", cb)
            internal_handler = mock_client.subscribe.call_args.kwargs["cb"]
            msg = MagicMock()
            msg.data = json.dumps({"key": "value"}).encode("utf-8")
            await internal_handler(msg)

        anyio.run(run)

        assert received == [{"key": "value"}]
