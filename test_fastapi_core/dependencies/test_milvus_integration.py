"""Milvus dependency 통합 테스트 — get_milvus_client, set_milvus_client."""
from __future__ import annotations

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from pymilvus import MilvusClient

from fastapi_core.core.config import EnvConfig
from fastapi_core.core.milvus import create_milvus_client
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
    app = FastAPI()
    set_milvus_client(app, config=config)

    try:
        assert isinstance(app.state.milvus_client, MilvusClient)
        names = app.state.milvus_client.list_collections()
        assert isinstance(names, list)
    finally:
        app.state.milvus_client.close()


@pytest.mark.integration
def test_get_milvus_client_dependency_connects_to_live_server(
    milvus_client: MilvusClient,
):
    app = FastAPI()
    set_milvus_client(app, milvus_client)

    @app.get("/healthz")
    def healthz(client: MilvusClient = Depends(get_milvus_client)):
        return {"count": len(client.list_collections())}

    http_client = TestClient(app)
    response = http_client.get("/healthz")
    assert response.status_code == 200
    assert isinstance(response.json()["count"], int)
