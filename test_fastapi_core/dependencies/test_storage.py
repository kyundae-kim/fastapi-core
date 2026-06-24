import inspect
from unittest.mock import MagicMock, patch

import pytest
from docmesh_py_core.config import MinioConfig
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from minio import Minio

from fastapi_core.core.config import EnvConfig
from fastapi_core.core.storage import create_minio_client
from fastapi_core.dependencies.config import get_config
from fastapi_core.dependencies.storage import get_minio_client, set_minio_client


def test_get_minio_client_creates_client():
    config = MagicMock()
    config.minio = MinioConfig(
        endpoint="minio:9000",
        access_key="admin",
        secret_key="password",
        secure=False,
        bucket="default",
    )

    with patch("fastapi_core.core.storage.Minio") as mock_cls:
        mock_instance = MagicMock()
        mock_cls.return_value = mock_instance
        client = create_minio_client(config.minio)
        assert client is mock_instance


# ---------------------------------------------------------------------------
# get_minio_client — state 기반 싱글톤 테스트
# ---------------------------------------------------------------------------


def test_get_minio_client_from_state():
    """app.state에 minio_client가 등록돼 있으면 동일 인스턴스를 반환하고
    create_minio_client를 호출하지 않는다."""
    app = FastAPI()
    mock_client = MagicMock(spec=Minio)
    set_minio_client(app, mock_client)

    @app.get("/client-id")
    def client_id(client: Minio = Depends(get_minio_client)):
        return {"id": id(client)}

    with patch("fastapi_core.dependencies.storage.create_minio_client") as mock_create:
        client = TestClient(app)
        response = client.get("/client-id")
        mock_create.assert_not_called()
    assert response.status_code == 200
    assert response.json()["id"] == id(mock_client)


def test_get_minio_client_fallback_prefers_docmesh_registry():
    """docmesh registry가 있으면 native create 대신 registry client를 state에 등록한다."""
    app = FastAPI()
    mock_client = MagicMock(spec=Minio)
    mock_config = MagicMock()
    mock_registry = MagicMock()
    mock_registry.create_client.return_value = MagicMock(client=mock_client)
    app.state.docmesh_registry = mock_registry
    app.dependency_overrides[get_config] = lambda: mock_config

    @app.get("/client-id")
    def client_id(client: Minio = Depends(get_minio_client)):
        return {"id": id(client)}

    with patch(
        "fastapi_core.dependencies.storage.create_minio_client", return_value=MagicMock(spec=Minio)
    ) as mock_create:
        client = TestClient(app)
        response = client.get("/client-id")
        mock_create.assert_not_called()

    mock_registry.create_client.assert_called_once_with("minio")
    assert response.status_code == 200
    assert response.json()["id"] == id(mock_client)
    assert app.state.minio_client is mock_client


def test_get_minio_client_initializes_docmesh_registry_when_missing():
    """app.state에 registry와 minio_client가 없으면 docmesh registry로 생성 후 state에 등록한다."""
    app = FastAPI()
    mock_client = MagicMock(spec=Minio)
    mock_config = MagicMock()
    app.dependency_overrides[get_config] = lambda: mock_config

    @app.get("/client-id")
    def client_id(client: Minio = Depends(get_minio_client)):
        return {"id": id(client)}

    with patch(
        "fastapi_core.dependencies.storage.get_required_docmesh_service",
        return_value=mock_client,
    ) as mock_get_required:
        client = TestClient(app)
        response = client.get("/client-id")

    mock_get_required.assert_called_once_with(
        app,
        "minio_client",
        config=mock_config,
    )
    assert response.status_code == 200
    assert response.json()["id"] == id(mock_client)
    assert app.state.minio_client is mock_client


def test_storage_dependencies_are_functions():
    import fastapi_core.dependencies.storage as storage_dependencies

    assert not hasattr(storage_dependencies, "GetMinioClientDependency")
    assert inspect.isfunction(storage_dependencies.get_minio_client)


def test_set_minio_client_from_config():
    """config를 전달하면 docmesh registry를 통해 client를 state에 등록한다."""
    app = FastAPI()
    mock_client = MagicMock(spec=Minio)
    mock_config = MagicMock()
    with patch(
        "fastapi_core.dependencies.storage.get_required_docmesh_service", return_value=mock_client
    ) as mock_get_required:
        set_minio_client(app, config=mock_config)

    mock_get_required.assert_called_once_with(app, "minio_client", config=mock_config)
    assert app.state.minio_client is mock_client


def test_set_minio_client_requires_client_or_config():
    """client와 config 모두 생략하면 ValueError를 발생시킨다."""
    app = FastAPI()
    with pytest.raises(ValueError):
        set_minio_client(app)
