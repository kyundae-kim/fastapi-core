"""NATS core 통합 테스트 — 실제 NATS 서버 필요.

devcontainer 내 NATS 서비스(nats://nats:4222)가 실행 중이어야 합니다.
anyio_mode = "auto" 설정으로 async def 테스트를 직접 실행합니다.
"""
from __future__ import annotations

import pytest

from fastapi_core.core.config import NatsConfig
from fastapi_core.core.messaging import create_nats_client


@pytest.fixture(scope="module")
def nats_config() -> NatsConfig:
    return NatsConfig()


@pytest.mark.integration
async def test_create_nats_client_connects(nats_config: NatsConfig):
    """실제 NATS 서버에 연결 후 클라이언트가 정상 상태임을 확인한다."""
    nc = await create_nats_client(nats_config)
    try:
        assert nc.is_connected
    finally:
        await nc.drain()


@pytest.mark.integration
async def test_nats_client_can_publish_raw_bytes(nats_config: NatsConfig):
    """생성된 클라이언트로 기본 publish API 호출이 가능하다."""
    nc = await create_nats_client(nats_config)
    try:
        await nc.publish("test.publish", b'{"event":"test","value":1}')
        await nc.flush()
        assert nc.is_connected
    finally:
        await nc.drain()


@pytest.mark.integration
async def test_nats_client_can_subscribe_with_queue_group(nats_config: NatsConfig):
    """생성된 클라이언트로 queue group 구독을 생성할 수 있다."""
    nc = await create_nats_client(nats_config)
    try:
        subscription = await nc.subscribe("test.queue", queue="test-group")
        assert subscription is not None
        assert subscription.subject == "test.queue"
    finally:
        await nc.drain()
