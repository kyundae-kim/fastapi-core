"""Milvus core 통합 테스트 — 실제 Milvus 서비스 필요."""
from __future__ import annotations

import pytest
from pymilvus import MilvusClient

from fastapi_core.core.config import EnvConfig, MilvusConfig
from fastapi_core.core.milvus import create_milvus_client


@pytest.fixture(scope="module")
def config() -> EnvConfig:
    return EnvConfig()


@pytest.fixture(scope="module")
def milvus_config(config: EnvConfig) -> MilvusConfig:
    return config.milvus


@pytest.fixture(scope="module")
def milvus_client(milvus_config: MilvusConfig) -> MilvusClient:
    client = create_milvus_client(milvus_config)
    try:
        yield client
    finally:
        client.close()


@pytest.mark.integration
def test_create_milvus_client_connects(milvus_client: MilvusClient):
    """실제 Milvus 서버에 연결 가능한 클라이언트가 생성된다."""
    assert milvus_client is not None
    assert isinstance(milvus_client, MilvusClient)


@pytest.mark.integration
def test_milvus_client_can_list_collections_directly(milvus_client: MilvusClient):
    """생성된 실제 클라이언트로 기본 list API 호출이 가능하다."""
    names = milvus_client.list_collections()
    assert isinstance(names, list)
    assert all(isinstance(name, str) for name in names)
