from __future__ import annotations

import inspect
from unittest.mock import MagicMock, patch

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from fastapi_core.core.config import OllamaConfig
from fastapi_core.dependencies.config import get_config
from fastapi_core.dependencies.ollama import get_ollama_client, set_ollama_client


class TestGetOllamaClient:
    def test_dependency_is_function(self):
        import fastapi_core.dependencies.ollama as ollama_dependencies

        assert not hasattr(ollama_dependencies, "GetOllamaClientDependency")
        assert inspect.isfunction(ollama_dependencies.get_ollama_client)

    def test_returns_registered_client(self):
        app = FastAPI()
        mock_client = MagicMock()
        set_ollama_client(app, mock_client)

        @app.get("/client-id")
        def client_id(client = Depends(get_ollama_client)):
            return {"id": id(client)}

        with patch("fastapi_core.dependencies.ollama.create_ollama_client") as mock_create:
            client = TestClient(app)
            response = client.get("/client-id")
            mock_create.assert_not_called()

        assert response.status_code == 200
        assert response.json()["id"] == id(mock_client)

    def test_creates_and_caches_client_when_missing(self):
        app = FastAPI()
        mock_client = MagicMock()
        mock_config = MagicMock()
        mock_config.ollama = OllamaConfig()
        app.dependency_overrides[get_config] = lambda: mock_config

        @app.get("/client-id")
        def client_id(client = Depends(get_ollama_client)):
            return {"id": id(client)}

        with patch(
            "fastapi_core.dependencies.ollama.create_ollama_client", return_value=mock_client
        ) as mock_create:
            client = TestClient(app)
            response = client.get("/client-id")
            mock_create.assert_called_once_with(mock_config.ollama)

        assert response.status_code == 200
        assert response.json()["id"] == id(mock_client)
        assert app.state.ollama_client is mock_client


class TestSetOllamaClient:
    def test_sets_direct_client(self):
        app = FastAPI()
        mock_client = MagicMock()

        set_ollama_client(app, client=mock_client)

        assert app.state.ollama_client is mock_client

    def test_creates_client_from_config(self):
        app = FastAPI()
        mock_client = MagicMock()
        mock_config = MagicMock()
        mock_config.ollama = OllamaConfig()

        with patch(
            "fastapi_core.dependencies.ollama.create_ollama_client", return_value=mock_client
        ) as mock_create:
            set_ollama_client(app, config=mock_config)

        mock_create.assert_called_once_with(mock_config.ollama)
        assert app.state.ollama_client is mock_client

    def test_raises_when_client_and_config_missing(self):
        app = FastAPI()

        with pytest.raises(ValueError, match="Either client or config must be provided"):
            set_ollama_client(app)
