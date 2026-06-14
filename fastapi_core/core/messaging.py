from __future__ import annotations

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
