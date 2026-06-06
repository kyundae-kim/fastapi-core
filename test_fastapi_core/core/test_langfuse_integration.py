"""Langfuse core 통합 테스트 — 실제 Langfuse 서비스 필요."""
from __future__ import annotations

import pytest
from langfuse import Langfuse

from fastapi_core.core.config import EnvConfig, LangfuseConfig
from fastapi_core.core.langfuse import check_langfuse_connection, create_langfuse_client


@pytest.fixture(scope="module")
def config() -> EnvConfig:
    return EnvConfig()


@pytest.fixture(scope="module")
def langfuse_config(config: EnvConfig) -> LangfuseConfig:
    return config.langfuse


@pytest.mark.integration
def test_check_langfuse_connection_live_server(langfuse_config: LangfuseConfig):
    """실제 Langfuse public health endpoint가 OK를 반환한다."""
    assert check_langfuse_connection(langfuse_config) is True


@pytest.mark.integration
def test_create_langfuse_client_returns_langfuse_instance(
    langfuse_config: LangfuseConfig,
):
    """실제 config로 Langfuse 클라이언트 객체를 생성할 수 있다."""
    client = create_langfuse_client(langfuse_config)

    assert isinstance(client, Langfuse)
