"""Milvus core 통합 테스트 — 실제 Milvus 서비스 필요."""
from __future__ import annotations

from uuid import uuid4

import pytest
from pymilvus import MilvusClient

from fastapi_core.core.config import EnvConfig, MilvusConfig
from fastapi_core.core.milvus import (
    check_milvus_connection,
    create_milvus_client,
    ensure_collection_exists,
    list_collection_names,
)


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
    assert check_milvus_connection(milvus_client) is True


@pytest.mark.integration
def test_list_collection_names_live_server_returns_string_list(
    milvus_client: MilvusClient,
):
    """실제 Milvus 서버 응답에서 컬렉션 이름 목록을 문자열 리스트로 반환한다."""
    collection_names = list_collection_names(milvus_client)

    assert isinstance(collection_names, list)
    assert all(isinstance(name, str) for name in collection_names)


@pytest.mark.integration
def test_ensure_collection_exists_creates_real_collection(
    milvus_client: MilvusClient,
):
    """실제 Milvus 서버에 컬렉션이 없으면 생성한다."""
    collection_name = f"integration_{uuid4().hex[:8]}"
    try:
        ensure_collection_exists(milvus_client, collection_name, dimension=8)
        assert milvus_client.has_collection(collection_name) is True
        assert collection_name in list_collection_names(milvus_client)
    finally:
        if milvus_client.has_collection(collection_name):
            milvus_client.drop_collection(collection_name)
