"""Ollama core 통합 테스트 — 실제 Ollama 서비스 필요."""
from __future__ import annotations

import pytest
import ollama

from fastapi_core.core.config import EnvConfig, OllamaConfig
from fastapi_core.core.ollama import create_ollama_client


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
    assert isinstance(ollama_client, ollama.Client)


@pytest.mark.integration
def test_ollama_client_can_list_models_directly(ollama_client: ollama.Client):
    """생성된 실제 클라이언트에서 기본 list API 호출이 가능하다."""
    response = ollama_client.list()
    assert response is not None
