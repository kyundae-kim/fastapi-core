from unittest.mock import MagicMock, patch

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from minio import Minio

from fastapi_core.core.config import EnvConfig, MinIOConfig
from fastapi_core.core.storage import create_minio_client
from fastapi_core.dependencies.config import get_config
from fastapi_core.dependencies.storage import get_minio_client, set_minio_client


def test_get_minio_client_creates_client():
    config = MagicMock()
    config.minio = MinIOConfig(
        endpoint="minio:9000",
        access_key="admin",
        secret_key="password",
        secure=False,
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


def test_get_minio_client_fallback():
    """app.state에 minio_client가 없으면 생성 후 state에 등록하여 반환한다."""
    app = FastAPI()
    mock_client = MagicMock(spec=Minio)
    mock_config = MagicMock()
    app.dependency_overrides[get_config] = lambda: mock_config

    @app.get("/client-id")
    def client_id(client: Minio = Depends(get_minio_client)):
        return {"id": id(client)}

    with patch(
        "fastapi_core.dependencies.storage.create_minio_client", return_value=mock_client
    ) as mock_create:
        client = TestClient(app)
        response = client.get("/client-id")
        mock_create.assert_called_once_with(mock_config.minio)
    assert response.status_code == 200
    assert response.json()["id"] == id(mock_client)
    assert app.state.minio_client is mock_client


def test_set_minio_client_from_config():
    """config를 전달하면 create_minio_client를 호출하여 state에 등록한다."""
    app = FastAPI()
    mock_client = MagicMock(spec=Minio)
    mock_config = MagicMock()
    with patch(
        "fastapi_core.dependencies.storage.create_minio_client", return_value=mock_client
    ) as mock_create:
        set_minio_client(app, config=mock_config)
        mock_create.assert_called_once_with(mock_config.minio)
    assert app.state.minio_client is mock_client


def test_set_minio_client_requires_client_or_config():
    """client와 config 모두 생략하면 ValueError를 발생시킨다."""
    app = FastAPI()
    with pytest.raises(ValueError):
        set_minio_client(app)
