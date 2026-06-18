from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from fastapi_core.core.config import NatsConfig
from fastapi_core.core.messaging import (
    build_event_subject,
    create_nats_client,
    publish_event,
    subscribe_event,
    subscribe_queue_event,
    validate_event_subject,
)


class FakeNatsClient:
    def __init__(self) -> None:
        self.published: list[tuple[str, bytes]] = []
        self.subscriptions: list[tuple[str, str | None, object]] = []

    async def publish(self, subject: str, payload: bytes) -> None:
        self.published.append((subject, payload))

    async def subscribe(self, subject: str, queue: str | None = None, cb=None):
        self.subscriptions.append((subject, queue, cb))
        return {"subject": subject, "queue": queue, "cb": cb}


class FakeMessage:
    def __init__(self, subject: str, payload: dict[str, object]) -> None:
        self.subject = subject
        self.data = json.dumps(payload).encode("utf-8")


@pytest.mark.asyncio
async def test_create_nats_client_connects_using_config_values():
    config = NatsConfig(
        servers="nats://one:4222,nats://two:4222",
        name="docmesh-test",
        connect_timeout=7,
        max_reconnect_attempts=11,
        reconnect_time_wait_ms=3456,
    )

    with patch(
        "fastapi_core.core.messaging.nats.connect",
        new=AsyncMock(return_value={"connected": True}),
    ) as mock_connect:
        client = await create_nats_client(config)

    assert client == {"connected": True}
    mock_connect.assert_awaited_once_with(
        servers=["nats://one:4222", "nats://two:4222"],
        name="docmesh-test",
        connect_timeout=7,
        max_reconnect_attempts=11,
        reconnect_time_wait=3.456,
    )


def test_build_event_subject_formats_domain_entity_action():
    assert build_event_subject("billing", "invoice", "created") == "billing.invoice.created"


def test_validate_event_subject_rejects_invalid_subjects():
    assert validate_event_subject("billing.invoice.created") is True
    assert validate_event_subject("billing.invoice") is False
    assert validate_event_subject("Billing.invoice.created") is False
    assert validate_event_subject("billing.invoice.created.now") is False


@pytest.mark.asyncio
async def test_publish_event_json_encodes_payload_and_uses_subject():
    client = FakeNatsClient()
    payload = {"event_id": "evt-1", "amount": 12}

    await publish_event(client, "billing.invoice.created", payload)

    assert client.published == [
        ("billing.invoice.created", b'{"event_id":"evt-1","amount":12}')
    ]


@pytest.mark.asyncio
async def test_subscribe_event_decodes_payload_before_calling_handler():
    client = FakeNatsClient()
    received: list[tuple[str, dict[str, object]]] = []

    async def handler(subject: str, payload: dict[str, object]) -> None:
        received.append((subject, payload))

    subscription = await subscribe_event(client, "billing.invoice.created", handler)

    callback = client.subscriptions[0][2]
    assert callback is not None
    await callback(FakeMessage("billing.invoice.created", {"event_id": "evt-1"}))

    assert subscription["subject"] == "billing.invoice.created"
    assert received == [("billing.invoice.created", {"event_id": "evt-1"})]


@pytest.mark.asyncio
async def test_subscribe_queue_event_uses_explicit_queue_group():
    client = FakeNatsClient()

    async def handler(subject: str, payload: dict[str, object]) -> None:
        return None

    subscription = await subscribe_queue_event(
        client,
        "billing.invoice.created",
        "billing-workers",
        handler,
    )

    assert client.subscriptions[0][0] == "billing.invoice.created"
    assert client.subscriptions[0][1] == "billing-workers"
    assert subscription["queue"] == "billing-workers"
