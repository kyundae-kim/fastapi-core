from __future__ import annotations

import nats.aio.client
from fastapi import Depends, FastAPI, Request
from fastapi.params import Depends as DependsParam

from fastapi_core.core.config import EnvConfig
from fastapi_core.core.messaging import create_nats_client
from fastapi_core.dependencies.config import get_config

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


async def get_nats_client(
    request: Request,
    config: EnvConfig | DependsParam = Depends(get_config),
) -> nats.aio.client.Client:
    """app.state.nats_client를 반환한다. 미등록 시 생성 후 state에 등록한다."""
    try:
        return getattr(request.app.state, _NATS_CLIENT_STATE_KEY)
    except AttributeError:
        if isinstance(config, DependsParam):
            config = get_config(request)
        client = await create_nats_client(config.nats)
        await set_nats_client(request.app, client)
        return client
