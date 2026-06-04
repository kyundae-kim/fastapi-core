"""Ollama core 통합 테스트 — 실제 Ollama 서비스 필요."""
from __future__ import annotations

import pytest
import ollama

from fastapi_core.core.config import EnvConfig, OllamaConfig
from fastapi_core.core.ollama import (
    check_ollama_connection,
    create_ollama_client,
    list_model_names,
)


@pytest.fixture(scope="module")
def config() -> EnvConfig:
    return EnvConfig()


@pytest.fixture(scope="module")
def ollama_config(config: EnvConfig) -> OllamaConfig:
    return config.ollama


@pytest.fixture(scope="module")
def ollama_client(ollama_config: OllamaConfig) -> ollama.Client:
    return create_ollama_client(ollama_config)


@pytest.mark.integration
def test_create_ollama_client_connects(ollama_client: ollama.Client):
    """실제 Ollama 서버에 연결 가능한 클라이언트가 생성된다."""
    assert ollama_client is not None
    assert check_ollama_connection(ollama_client) is True


@pytest.mark.integration
def test_list_model_names_live_server_returns_string_list(
    ollama_client: ollama.Client,
):
    """실제 Ollama 서버 응답에서 모델 이름 목록을 문자열 리스트로 변환한다."""
    model_names = list_model_names(ollama_client)

    assert isinstance(model_names, list)
    assert all(isinstance(name, str) for name in model_names)
