"""Milvus dependency 통합 테스트 — get_milvus_client, set_milvus_client."""
from __future__ import annotations

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from pymilvus import MilvusClient

from fastapi_core.core.config import EnvConfig
from fastapi_core.core.milvus import check_milvus_connection, create_milvus_client
from fastapi_core.dependencies.milvus import get_milvus_client, set_milvus_client


@pytest.fixture(scope="module")
def config() -> EnvConfig:
    return EnvConfig()


@pytest.fixture(scope="module")
def milvus_client(config: EnvConfig) -> MilvusClient:
    client = create_milvus_client(config.milvus)
    try:
        yield client
    finally:
        client.close()


@pytest.mark.integration
def test_get_milvus_client_from_state_integration(milvus_client: MilvusClient):
    """실제 Milvus 클라이언트를 app.state에 등록하면 Depends가 동일 인스턴스를 반환한다."""
    app = FastAPI()
    set_milvus_client(app, milvus_client)

    @app.get("/client-id")
    def client_id(client: MilvusClient = Depends(get_milvus_client)):
        return {"id": id(client)}

    http_client = TestClient(app)
    response = http_client.get("/client-id")
    assert response.status_code == 200
    assert response.json()["id"] == id(milvus_client)


@pytest.mark.integration
def test_set_milvus_client_from_config_integration(config: EnvConfig):
    """실제 config로 set_milvus_client를 호출하면 실제 Milvus 클라이언트가 app.state에 등록된다."""
    app = FastAPI()
    set_milvus_client(app, config=config)

    assert isinstance(app.state.milvus_client, MilvusClient)
    assert check_milvus_connection(app.state.milvus_client) is True
    app.state.milvus_client.close()


@pytest.mark.integration
def test_get_milvus_client_dependency_connects_to_live_server(
    milvus_client: MilvusClient,
):
    """state에 등록된 실제 클라이언트를 Depends로 받아 실제 Milvus 연결 상태를 확인할 수 있다."""
    app = FastAPI()
    set_milvus_client(app, milvus_client)

    @app.get("/healthz")
    def healthz(client: MilvusClient = Depends(get_milvus_client)):
        return {"connected": check_milvus_connection(client)}

    http_client = TestClient(app)
    response = http_client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["connected"] is True
