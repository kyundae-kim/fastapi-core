"""MinIO 연동 통합 테스트 — get_minio_client, set_minio_client."""
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from minio import Minio

from fastapi_core.core.config import EnvConfig
from fastapi_core.core.storage import check_minio_connection, create_minio_client
from fastapi_core.dependencies.storage import get_minio_client, set_minio_client


@pytest.fixture(scope="module")
def config() -> EnvConfig:
    return EnvConfig()


@pytest.fixture(scope="module")
def minio_client(config: EnvConfig) -> Minio:
    return create_minio_client(config.minio)


@pytest.mark.integration
def test_get_minio_client_from_state_integration(minio_client: Minio):
    app = FastAPI()
    set_minio_client(app, minio_client)

    @app.get("/client-id")
    def client_id(client: Minio = Depends(get_minio_client)):
        return {"id": id(client)}

    http_client = TestClient(app)
    response = http_client.get("/client-id")
    assert response.status_code == 200
    assert response.json()["id"] == id(minio_client)


@pytest.mark.integration
def test_set_minio_client_from_config_integration(config: EnvConfig):
    app = FastAPI()
    set_minio_client(app, config=config)
    assert isinstance(app.state.minio_client, Minio)


@pytest.mark.integration
def test_get_minio_client_bucket_accessible(minio_client: Minio, config: EnvConfig):
    app = FastAPI()
    set_minio_client(app, minio_client)

    @app.get("/bucket-check")
    def bucket_check(client: Minio = Depends(get_minio_client)):
        return {"connected": check_minio_connection(client, config.minio.bucket)}

    http_client = TestClient(app)
    response = http_client.get("/bucket-check")
    assert response.status_code == 200
    assert response.json()["connected"] is True
