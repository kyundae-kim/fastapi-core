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

    def test_prefers_docmesh_registry_when_missing(self):
        app = FastAPI()
        mock_client = MagicMock()
        mock_config = MagicMock()
        mock_config.ollama = OllamaConfig()
        mock_registry = MagicMock()
        mock_registry.create_client.return_value = MagicMock(client=mock_client)
        app.state.docmesh_registry = mock_registry
        app.dependency_overrides[get_config] = lambda: mock_config

        @app.get("/client-id")
        def client_id(client = Depends(get_ollama_client)):
            return {"id": id(client)}

        with patch(
            "fastapi_core.dependencies.ollama.create_ollama_client", return_value=MagicMock()
        ) as mock_create:
            client = TestClient(app)
            response = client.get("/client-id")
            mock_create.assert_not_called()

        mock_registry.create_client.assert_called_once_with("ollama")
        assert response.status_code == 200
        assert response.json()["id"] == id(mock_client)
        assert app.state.ollama_client is mock_client

    def test_initializes_docmesh_registry_when_missing(self):
        app = FastAPI()
        mock_client = MagicMock()
        mock_config = MagicMock()
        mock_config.ollama = OllamaConfig()
        app.dependency_overrides[get_config] = lambda: mock_config

        @app.get("/client-id")
        def client_id(client = Depends(get_ollama_client)):
            return {"id": id(client)}

        with patch(
            "fastapi_core.dependencies.ollama.get_required_docmesh_service",
            return_value=mock_client,
        ) as mock_get_required:
            client = TestClient(app)
            response = client.get("/client-id")

        mock_get_required.assert_called_once_with(
            app,
            "ollama_client",
            config=mock_config,
        )
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
            "fastapi_core.dependencies.ollama.get_required_docmesh_service",
            return_value=mock_client,
        ) as mock_get_required:
            set_ollama_client(app, config=mock_config)

        mock_get_required.assert_called_once_with(app, "ollama_client", config=mock_config)
        assert app.state.ollama_client is mock_client

    def test_raises_when_client_and_config_missing(self):
        app = FastAPI()

        with pytest.raises(ValueError, match="Either client or config must be provided"):
            set_ollama_client(app)
