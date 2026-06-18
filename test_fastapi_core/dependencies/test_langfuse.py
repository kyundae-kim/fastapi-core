import inspect
from unittest.mock import MagicMock, patch

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from fastapi_core.dependencies.config import get_config
from fastapi_core.dependencies.langfuse import get_langfuse_client, set_langfuse_client


def test_get_langfuse_client_from_state():
    app = FastAPI()
    mock_client = MagicMock(name="langfuse_client")
    set_langfuse_client(app, mock_client)

    @app.get("/client-id")
    def client_id(client=Depends(get_langfuse_client)):
        return {"id": id(client)}

    with patch("fastapi_core.dependencies.langfuse.build_langfuse_client") as mock_build:
        client = TestClient(app)
        response = client.get("/client-id")
        mock_build.assert_not_called()

    assert response.status_code == 200
    assert response.json()["id"] == id(mock_client)
    assert app.state.langfuse_client is mock_client


def test_get_langfuse_client_fallback_prefers_docmesh_registry():
    app = FastAPI()
    mock_client = MagicMock(name="langfuse_client")
    mock_config = MagicMock()
    mock_registry = MagicMock()
    mock_registry.create_client.return_value = MagicMock(client=mock_client)
    app.state.docmesh_registry = mock_registry
    app.dependency_overrides[get_config] = lambda: mock_config

    @app.get("/client-id")
    def client_id(client=Depends(get_langfuse_client)):
        return {"id": id(client)}

    with patch(
        "fastapi_core.dependencies.langfuse.build_langfuse_client",
        return_value=MagicMock(name="native_langfuse_client"),
    ) as mock_build:
        client = TestClient(app)
        response = client.get("/client-id")
        mock_build.assert_not_called()

    mock_registry.create_client.assert_called_once_with("langfuse")
    assert response.status_code == 200
    assert response.json()["id"] == id(mock_client)
    assert app.state.langfuse_client is mock_client


def test_get_langfuse_client_initializes_docmesh_registry_when_missing():
    app = FastAPI()
    mock_client = MagicMock(name="langfuse_client")
    mock_config = MagicMock()
    app.dependency_overrides[get_config] = lambda: mock_config

    @app.get("/client-id")
    def client_id(client=Depends(get_langfuse_client)):
        return {"id": id(client)}

    with patch(
        "fastapi_core.dependencies.langfuse.get_required_docmesh_service",
        return_value=mock_client,
    ) as mock_get_required:
        client = TestClient(app)
        response = client.get("/client-id")

    mock_get_required.assert_called_once_with(
        app,
        "langfuse_client",
        config=mock_config,
    )
    assert response.status_code == 200
    assert response.json()["id"] == id(mock_client)
    assert app.state.langfuse_client is mock_client


def test_langfuse_dependencies_are_functions():
    import fastapi_core.dependencies.langfuse as langfuse_dependencies

    assert not hasattr(langfuse_dependencies, "GetLangfuseClientDependency")
    assert inspect.isfunction(langfuse_dependencies.get_langfuse_client)
