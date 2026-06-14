"""Ollama dependency 통합 테스트 — get_ollama_client, set_ollama_client."""
from __future__ import annotations

import pytest
import ollama
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from fastapi_core.core.config import EnvConfig
from fastapi_core.core.ollama import create_ollama_client
from fastapi_core.dependencies.ollama import get_ollama_client, set_ollama_client


@pytest.fixture(scope="module")
def config() -> EnvConfig:
    return EnvConfig()


@pytest.fixture(scope="module")
def ollama_client(config: EnvConfig) -> ollama.Client:
    return create_ollama_client(config.ollama)


@pytest.mark.integration
def test_get_ollama_client_from_state_integration(ollama_client: ollama.Client):
    app = FastAPI()
    set_ollama_client(app, ollama_client)

    @app.get("/client-id")
    def client_id(client: ollama.Client = Depends(get_ollama_client)):
        return {"id": id(client)}

    http_client = TestClient(app)
    response = http_client.get("/client-id")
    assert response.status_code == 200
    assert response.json()["id"] == id(ollama_client)


@pytest.mark.integration
def test_set_ollama_client_from_config_integration(config: EnvConfig):
    app = FastAPI()
    set_ollama_client(app, config=config)

    assert isinstance(app.state.ollama_client, ollama.Client)
    assert app.state.ollama_client.list() is not None


@pytest.mark.integration
def test_get_ollama_client_dependency_connects_to_live_server(
    ollama_client: ollama.Client,
):
    app = FastAPI()
    set_ollama_client(app, ollama_client)

    @app.get("/healthz")
    def healthz(client: ollama.Client = Depends(get_ollama_client)):
        return {"ok": client.list() is not None}

    http_client = TestClient(app)
    response = http_client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["ok"] is True
