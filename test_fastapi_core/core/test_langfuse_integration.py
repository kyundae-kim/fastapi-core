"""Langfuse core 통합 테스트 — 실제 Langfuse 서비스 필요."""
from __future__ import annotations

import pytest

from fastapi_core.core.config import EnvConfig, LangfuseConfig
from fastapi_core.core.langfuse import check_langfuse_connection, get_langfuse_client


@pytest.fixture(scope="module")
def config() -> EnvConfig:
    return EnvConfig()


@pytest.fixture(scope="module")
def langfuse_config(config: EnvConfig) -> LangfuseConfig:
    return config.langfuse


@pytest.mark.integration
def test_check_langfuse_connection_live_server(langfuse_config: LangfuseConfig):
    """Langfuse public health endpoint가 열려 있으면 OK를 반환한다."""
    if not check_langfuse_connection(langfuse_config):
        pytest.skip("Langfuse public health endpoint is unavailable in this environment")


@pytest.mark.integration
def test_get_langfuse_client_returns_client_instance(langfuse_config: LangfuseConfig):
    """실제 config로 Langfuse singleton client를 초기화/조회할 수 있다."""
    client = get_langfuse_client(langfuse_config)
    assert client is not None
