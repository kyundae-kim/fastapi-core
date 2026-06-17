from __future__ import annotations

import inspect
import json
import re
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

import nats
import nats.aio.client

from fastapi_core.core.config import NatsConfig

_EVENT_SUBJECT_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*\.[a-z0-9]+(?:-[a-z0-9]+)*\.[a-z0-9]+(?:-[a-z0-9]+)*$")


async def create_nats_client(config: NatsConfig) -> nats.aio.client.Client:
    return await nats.connect(
        servers=config.server_list,
        name=config.name,
        connect_timeout=config.connect_timeout,
        max_reconnect_attempts=config.max_reconnect_attempts,
        reconnect_time_wait=config.reconnect_time_wait_ms / 1000,
    )


def validate_event_subject(subject: str) -> bool:
    return bool(_EVENT_SUBJECT_RE.fullmatch(subject))


def build_event_subject(domain: str, entity: str, action: str) -> str:
    subject = f"{domain}.{entity}.{action}"
    if not validate_event_subject(subject):
        raise ValueError(f"Invalid event subject: {subject}")
    return subject


def _encode_payload(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


async def publish_event(
    client: nats.aio.client.Client,
    subject: str,
    payload: Mapping[str, Any],
) -> None:
    if not validate_event_subject(subject):
        raise ValueError(f"Invalid event subject: {subject}")
    await client.publish(subject, _encode_payload(payload))


async def _handle_message(
    handler: Callable[[str, dict[str, Any]], Awaitable[None] | None],
    msg: Any,
) -> None:
    payload = json.loads(msg.data.decode("utf-8"))
    result = handler(msg.subject, payload)
    if inspect.isawaitable(result):
        await result


async def subscribe_event(
    client: nats.aio.client.Client,
    subject: str,
    handler: Callable[[str, dict[str, Any]], Awaitable[None] | None],
) -> Any:
    if not validate_event_subject(subject):
        raise ValueError(f"Invalid event subject: {subject}")
    return await client.subscribe(
        subject,
        cb=lambda msg: _handle_message(handler, msg),
    )


async def subscribe_queue_event(
    client: nats.aio.client.Client,
    subject: str,
    queue: str,
    handler: Callable[[str, dict[str, Any]], Awaitable[None] | None],
) -> Any:
    if not validate_event_subject(subject):
        raise ValueError(f"Invalid event subject: {subject}")
    return await client.subscribe(
        subject,
        queue=queue,
        cb=lambda msg: _handle_message(handler, msg),
    )
