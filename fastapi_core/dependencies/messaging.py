from __future__ import annotations

import nats.aio.client
from fastapi import Depends, FastAPI, Request
from fastapi.params import Depends as DependsParam

from fastapi_core.bootstrap import get_or_create_state_value_async, set_state_value_async
from fastapi_core.core.config import EnvConfig
from fastapi_core.dependencies.config import get_config
from fastapi_core.docmesh_bridge import get_required_docmesh_service_async

_NATS_CLIENT_STATE_KEY = "nats_client"


async def set_nats_client(
    app: FastAPI,
    client: nats.aio.client.Client | None = None,
    *,
    config: EnvConfig | None = None,
) -> None:
    """NATS 클라이언트를 app.state에 등록한다.

    - client 직접 전달 → app.state.nats_client에 할당
    - config 전달 → docmesh registry를 통해 생성 후 할당
    - 둘 다 None → ValueError
    """
    if client is None:
        if config is None:
            raise ValueError("Either client or config must be provided")
        client = await get_required_docmesh_service_async(
            app,
            _NATS_CLIENT_STATE_KEY,
            config=config,
        )
    await set_state_value_async(app, _NATS_CLIENT_STATE_KEY, client)


async def get_nats_client(
    request: Request,
    config: EnvConfig | DependsParam = Depends(get_config),
) -> nats.aio.client.Client:
    """app.state.nats_client를 반환한다. 미등록 시 docmesh registry로 생성 후 state에 등록한다."""

    async def factory() -> nats.aio.client.Client:
        resolved_config = config
        if isinstance(resolved_config, DependsParam):
            resolved_config = get_config(request)
        return await get_required_docmesh_service_async(
            request.app,
            _NATS_CLIENT_STATE_KEY,
            config=resolved_config,
        )

    return await get_or_create_state_value_async(
        request.app, _NATS_CLIENT_STATE_KEY, factory
    )
