"""NATS dependencies 통합 테스트 — 실제 NATS 서버 필요.

devcontainer 내 NATS 서비스(nats://nats:4222)가 실행 중이어야 합니다.
anyio_mode = "auto" 설정으로 async def 테스트를 직접 실행합니다.

주의: TestClient lifespan과 async fixture를 함께 쓸 때 이벤트 루프가 달라지므로
NATS 클라이언트는 각 테스트 내에서 lifespan을 통해 생성합니다.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

import anyio
import nats.aio.client
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from fastapi_core.core.config import EnvConfig
from fastapi_core.core.messaging import create_nats_client
from fastapi_core.dependencies.messaging import get_nats_client, set_nats_client


@pytest.fixture(scope="module")
def config() -> EnvConfig:
    return EnvConfig()


# ---------------------------------------------------------------------------
# set_nats_client — 직접 클라이언트 등록
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_set_nats_client_with_direct_client(config: EnvConfig):
    """실제 클라이언트를 app.state에 직접 등록하면 동일 인스턴스가 저장된다."""
    nc = await create_nats_client(config.nats)
    try:
        app = FastAPI()
        await set_nats_client(app, client=nc)
        assert app.state.nats_client is nc
    finally:
        await nc.drain()


@pytest.mark.integration
async def test_set_nats_client_with_config(config: EnvConfig):
    """config로 set_nats_client 호출 시 실제 연결된 클라이언트가 등록된다."""
    app = FastAPI()
    await set_nats_client(app, config=config)
    nc = app.state.nats_client
    try:
        assert isinstance(nc, nats.aio.client.Client)
        assert nc.is_connected
    finally:
        await nc.drain()


# ---------------------------------------------------------------------------
# get_nats_client — Depends를 통한 싱글톤 반환
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_get_nats_client_from_state_integration(config: EnvConfig):
    """app.state에 등록된 클라이언트를 get_nats_client Depends가 동일 인스턴스로 반환한다.

    TestClient는 자체 이벤트 루프를 내부적으로 사용하므로 동기 테스트로 작성합니다.
    """

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await set_nats_client(app, config=config)
        yield
        await app.state.nats_client.drain()

    app = FastAPI(lifespan=lifespan)

    @app.get("/client-connected")
    async def client_connected(nc: nats.aio.client.Client = Depends(get_nats_client)):
        return {"connected": nc.is_connected}

    with TestClient(app) as http:
        response = http.get("/client-connected")

    assert response.status_code == 200
    assert response.json()["connected"] is True


# ---------------------------------------------------------------------------
# publish via Depends — 엔드포인트에서 실제 발행
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_endpoint_publishes_via_depends(config: EnvConfig):
    """get_nats_client Depends로 주입된 클라이언트로 엔드포인트에서 메시지를 발행한다.

    TestClient는 자체 이벤트 루프를 사용하므로 동기 테스트로 작성합니다.
    """
    import json

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await set_nats_client(app, config=config)
        yield
        await app.state.nats_client.drain()

    app = FastAPI(lifespan=lifespan)

    @app.post("/publish")
    async def publish_event(nc: nats.aio.client.Client = Depends(get_nats_client)):
        await nc.publish("test.endpoint", json.dumps({"from": "endpoint"}).encode())
        return {"status": "published"}

    with TestClient(app) as http:
        response = http.post("/publish")

    assert response.status_code == 200
    assert response.json()["status"] == "published"
