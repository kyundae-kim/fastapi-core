from __future__ import annotations

import inspect
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from pymilvus import MilvusClient

from fastapi_core.core.config import MilvusConfig
from fastapi_core.dependencies.config import get_config
from fastapi_core.dependencies.milvus import get_milvus_client, set_milvus_client


class TestGetMilvusClient:
    def test_dependency_is_function(self):
        import fastapi_core.dependencies.milvus as milvus_dependencies

        assert not hasattr(milvus_dependencies, "GetMilvusClientDependency")
        assert inspect.isfunction(milvus_dependencies.get_milvus_client)

    def test_returns_registered_client(self):
        app = FastAPI()
        mock_client = MagicMock(spec=MilvusClient)
        set_milvus_client(app, mock_client)

        @app.get("/client-id")
        def client_id(client: MilvusClient = Depends(get_milvus_client)):
            return {"id": id(client)}

        with patch("fastapi_core.dependencies.milvus.create_milvus_client") as mock_create:
            client = TestClient(app)
            response = client.get("/client-id")
            mock_create.assert_not_called()

        assert response.status_code == 200
        assert response.json()["id"] == id(mock_client)

    def test_prefers_docmesh_registry_when_missing(self):
        app = FastAPI()
        mock_client = MagicMock(spec=MilvusClient)
        mock_config = MagicMock()
        mock_config.milvus = MilvusConfig()
        mock_registry = MagicMock()
        mock_registry.create_client.return_value = MagicMock(client=mock_client)
        app.state.docmesh_registry = mock_registry
        app.dependency_overrides[get_config] = lambda: mock_config

        @app.get("/client-id")
        def client_id(client: MilvusClient = Depends(get_milvus_client)):
            return {"id": id(client)}

        with patch(
            "fastapi_core.dependencies.milvus.create_milvus_client", return_value=MagicMock(spec=MilvusClient)
        ) as mock_create:
            client = TestClient(app)
            response = client.get("/client-id")
            mock_create.assert_not_called()

        mock_registry.create_client.assert_called_once_with("milvus")
        assert response.status_code == 200
        assert response.json()["id"] == id(mock_client)
        assert app.state.milvus_client is mock_client

    def test_prefers_docmesh_settings_adapter_when_present_without_registry(self):
        app = FastAPI()
        mock_client = MagicMock(spec=MilvusClient)
        mock_config = MagicMock()
        mock_config.milvus = MilvusConfig(
            uri="http://native:19530",
            db_name="native",
            token="native-token",
            timeout=1,
        )
        app.state.docmesh_settings = SimpleNamespace(
            milvus=SimpleNamespace(
                uri="http://docmesh:19530",
                db_name="docmesh-db",
                token="docmesh-token",
                request_timeout_seconds=17,
            )
        )
        app.dependency_overrides[get_config] = lambda: mock_config

        @app.get("/client-id")
        def client_id(client: MilvusClient = Depends(get_milvus_client)):
            return {"id": id(client)}

        with (
            patch(
                "fastapi_core.dependencies.milvus.create_milvus_client",
                return_value=mock_client,
            ) as mock_create,
            patch(
                "fastapi_core.dependencies.milvus.get_required_docmesh_service",
                side_effect=AssertionError("registry path should not run"),
            ),
        ):
            client = TestClient(app)
            response = client.get("/client-id")

        adapted_config = mock_create.call_args.args[0]
        assert isinstance(adapted_config, MilvusConfig)
        assert adapted_config.uri == "http://docmesh:19530"
        assert adapted_config.db_name == "docmesh-db"
        assert adapted_config.token == "docmesh-token"
        assert adapted_config.timeout == 17
        assert response.status_code == 200
        assert response.json()["id"] == id(mock_client)
        assert app.state.milvus_client is mock_client

    def test_creates_native_client_when_registry_and_docmesh_settings_missing(self):
        app = FastAPI()
        mock_client = MagicMock(spec=MilvusClient)
        mock_config = MagicMock()
        mock_config.milvus = MilvusConfig()
        app.dependency_overrides[get_config] = lambda: mock_config

        @app.get("/client-id")
        def client_id(client: MilvusClient = Depends(get_milvus_client)):
            return {"id": id(client)}

        with patch(
            "fastapi_core.dependencies.milvus.create_milvus_client",
            return_value=mock_client,
        ) as mock_create:
            client = TestClient(app)
            response = client.get("/client-id")

        mock_create.assert_called_once_with(mock_config.milvus)
        assert response.status_code == 200
        assert response.json()["id"] == id(mock_client)
        assert app.state.milvus_client is mock_client


class TestSetMilvusClient:
    def test_sets_direct_client(self):
        app = FastAPI()
        mock_client = MagicMock(spec=MilvusClient)

        set_milvus_client(app, client=mock_client)

        assert app.state.milvus_client is mock_client

    def test_creates_native_client_from_config_when_registry_and_docmesh_settings_missing(self):
        app = FastAPI()
        mock_client = MagicMock(spec=MilvusClient)
        mock_config = MagicMock()
        mock_config.milvus = MilvusConfig()

        with patch(
            "fastapi_core.dependencies.milvus.create_milvus_client",
            return_value=mock_client,
        ) as mock_create:
            set_milvus_client(app, config=mock_config)

        mock_create.assert_called_once_with(mock_config.milvus)
        assert app.state.milvus_client is mock_client

    def test_uses_registry_when_present(self):
        app = FastAPI()
        mock_client = MagicMock(spec=MilvusClient)
        mock_config = MagicMock()
        mock_config.milvus = MilvusConfig()
        app.state.docmesh_registry = MagicMock()

        with patch(
            "fastapi_core.dependencies.milvus.get_required_docmesh_service",
            return_value=mock_client,
        ) as mock_get_required:
            set_milvus_client(app, config=mock_config)

        mock_get_required.assert_called_once_with(app, "milvus_client", config=mock_config)
        assert app.state.milvus_client is mock_client

    def test_prefers_docmesh_settings_adapter_when_present_without_registry(self):
        app = FastAPI()
        mock_client = MagicMock(spec=MilvusClient)
        mock_config = MagicMock()
        mock_config.milvus = MilvusConfig(
            uri="http://native:19530",
            db_name="native",
            token="native-token",
            timeout=1,
        )
        app.state.docmesh_settings = SimpleNamespace(
            milvus=SimpleNamespace(
                uri="http://docmesh:19530",
                db_name="docmesh-db",
                token="docmesh-token",
                request_timeout_seconds=17,
            )
        )

        with (
            patch(
                "fastapi_core.dependencies.milvus.create_milvus_client",
                return_value=mock_client,
            ) as mock_create,
            patch(
                "fastapi_core.dependencies.milvus.get_required_docmesh_service",
                side_effect=AssertionError("registry path should not run"),
            ),
        ):
            set_milvus_client(app, config=mock_config)

        adapted_config = mock_create.call_args.args[0]
        assert isinstance(adapted_config, MilvusConfig)
        assert adapted_config.uri == "http://docmesh:19530"
        assert adapted_config.db_name == "docmesh-db"
        assert adapted_config.token == "docmesh-token"
        assert adapted_config.timeout == 17
        assert app.state.milvus_client is mock_client

    def test_raises_when_client_and_config_missing(self):
        app = FastAPI()

        with pytest.raises(ValueError, match="Either client or config must be provided"):
            set_milvus_client(app)
