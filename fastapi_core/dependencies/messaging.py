from __future__ import annotations

import nats.aio.client
from fastapi import Depends, FastAPI, Request

from fastapi_core.core.config import EnvConfig
from fastapi_core.core.messaging import create_nats_client
from fastapi_core.dependencies.config import config_schema

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


class GetNatsClientDependency:
    async def __call__(
        self,
        request: Request,
        config: EnvConfig = Depends(config_schema),
    ) -> nats.aio.client.Client:
        """app.state.nats_client를 반환한다. 미등록 시 생성 후 state에 등록한다."""
        try:
            return getattr(request.app.state, _NATS_CLIENT_STATE_KEY)
        except AttributeError:
            client = await create_nats_client(config.nats)
            setattr(request.app.state, _NATS_CLIENT_STATE_KEY, client)
            return client


get_nats_client = GetNatsClientDependency()
