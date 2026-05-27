"""NATS 연동 통합 테스트 — 실제 NATS 서버 필요.

devcontainer 내 NATS 서비스(nats://nats:4222)가 실행 중이어야 합니다.
"""
from __future__ import annotations

import anyio
import pytest

from fastapi_core.core.config import NatsConfig
from fastapi_core.core.messaging import (
    create_nats_client,
    publish_json,
    subscribe_json,
)


@pytest.fixture(scope="module")
def nats_config() -> NatsConfig:
    return NatsConfig()


# ---------------------------------------------------------------------------
# 연결/종료
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_create_nats_client_connects(nats_config: NatsConfig):
    """실제 NATS 서버에 연결 후 클라이언트가 정상 상태임을 확인한다."""

    async def run():
        nc = await create_nats_client(nats_config)
        assert nc.is_connected
        await nc.drain()

    anyio.run(run)


# ---------------------------------------------------------------------------
# Publish
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_publish_json_succeeds(nats_config: NatsConfig):
    """publish_json이 예외 없이 NATS 서버로 메시지를 발행한다."""

    async def run():
        nc = await create_nats_client(nats_config)
        try:
            await publish_json(nc, "test.publish", {"event": "test", "value": 1})
        finally:
            await nc.drain()

    anyio.run(run)


# ---------------------------------------------------------------------------
# Subscribe — pub/sub round-trip
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_subscribe_json_round_trip(nats_config: NatsConfig):
    """publish_json으로 발행한 메시지를 subscribe_json 구독자가 수신한다."""
    received: list[dict] = []

    async def run():
        async def cb(data: dict) -> None:
            received.append(data)

        nc = await create_nats_client(nats_config)
        try:
            await subscribe_json(nc, "test.roundtrip", cb)
            await publish_json(nc, "test.roundtrip", {"key": "hello"})
            await anyio.sleep(0.3)
        finally:
            await nc.drain()

    anyio.run(run)

    assert len(received) == 1
    assert received[0] == {"key": "hello"}


# ---------------------------------------------------------------------------
# Subscribe — queue group 분배
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_subscribe_json_queue_group(nats_config: NatsConfig):
    """queue group 기반 구독자 2개가 4개 메시지를 나눠 수신한다(총합 4)."""
    received_a: list[dict] = []
    received_b: list[dict] = []

    async def run():
        async def cb_a(data: dict) -> None:
            received_a.append(data)

        async def cb_b(data: dict) -> None:
            received_b.append(data)

        nc = await create_nats_client(nats_config)
        try:
            await subscribe_json(nc, "test.queue", cb_a, queue="test-group")
            await subscribe_json(nc, "test.queue", cb_b, queue="test-group")

            for i in range(4):
                await publish_json(nc, "test.queue", {"seq": i})

            await anyio.sleep(0.5)
        finally:
            await nc.drain()

    anyio.run(run)

    total = len(received_a) + len(received_b)
    assert total == 4
    assert len(received_a) >= 1
    assert len(received_b) >= 1
