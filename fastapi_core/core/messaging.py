from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any

import nats
import nats.aio.client

from fastapi_core.core.config import NatsConfig


async def create_nats_client(config: NatsConfig) -> nats.aio.client.Client:
    """NATS 서버에 연결된 클라이언트를 생성한다."""
    nc = await nats.connect(
        servers=config.server_list,
        name=config.name,
        connect_timeout=config.connect_timeout,
        max_reconnect_attempts=config.max_reconnect_attempts,
        reconnect_time_wait=config.reconnect_time_wait_ms / 1000,
    )
    return nc


async def publish_json(
    client: nats.aio.client.Client,
    subject: str,
    payload: dict[str, Any],
) -> None:
    """JSON payload를 UTF-8 bytes로 직렬화하여 subject로 발행한다."""
    data = json.dumps(payload).encode("utf-8")
    await client.publish(subject, data)


async def subscribe_json(
    client: nats.aio.client.Client,
    subject: str,
    cb: Callable[[dict[str, Any]], Awaitable[None]],
    queue: str | None = None,
) -> None:
    """subject를 구독하고 수신 메시지를 JSON으로 역직렬화하여 콜백에 전달한다."""

    async def _handler(msg: nats.aio.client.Msg) -> None:
        data = json.loads(msg.data.decode("utf-8"))
        await cb(data)

    kwargs: dict[str, Any] = {"cb": _handler}
    if queue:
        kwargs["queue"] = queue

    await client.subscribe(subject, **kwargs)
