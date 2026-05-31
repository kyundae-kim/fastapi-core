from __future__ import annotations

import nats.aio.client
from fastapi import FastAPI, Request

from fastapi_core.core.config import EnvConfig
from fastapi_core.core.messaging import create_nats_client

_NATS_CLIENT_STATE_KEY = "nats_client"


async def set_nats_client(
    app: FastAPI,
    client: nats.aio.client.Client | None = None,
    *,
    config: EnvConfig | None = None,
) -> None:
    """NATS 클라이언트를 app.state에 등록한다.

    - client 직접 전달 → app.state.nats_client에 할당
    - config 전달 → create_nats_client(config.nats) 호출 후 할당
    - 둘 다 None → ValueError
    """
    if client is None:
        if config is None:
            raise ValueError("Either client or config must be provided")
        client = await create_nats_client(config.nats)
    setattr(app.state, _NATS_CLIENT_STATE_KEY, client)


def get_nats_client(request: Request) -> nats.aio.client.Client:
    """app.state.nats_client를 반환한다. 미등록 시 RuntimeError."""
    try:
        return getattr(request.app.state, _NATS_CLIENT_STATE_KEY)
    except AttributeError:
        raise RuntimeError(
            "NATS client is not initialized. "
            "Call set_nats_client() in the application lifespan."
        )
