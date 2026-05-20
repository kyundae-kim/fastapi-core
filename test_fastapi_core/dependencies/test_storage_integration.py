"""MinIO 연동 통합 테스트 — get_minio_client, set_minio_client."""
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from minio import Minio

from fastapi_core.core.config import EnvConfig
from fastapi_core.core.storage import create_minio_client, ensure_bucket_exists
from fastapi_core.dependencies.storage import get_minio_client, set_minio_client


@pytest.fixture(scope="module")
def config() -> EnvConfig:
    return EnvConfig()


@pytest.fixture(scope="module")
def minio_client(config: EnvConfig) -> Minio:
    return create_minio_client(config.minio)


# ---------------------------------------------------------------------------
# get_minio_client — 실제 state 싱글톤 검증
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_get_minio_client_from_state_integration(minio_client: Minio):
    """실제 MinIO 클라이언트를 app.state에 등록하면 get_minio_client가 동일 인스턴스를 반환한다."""
    app = FastAPI()
    set_minio_client(app, minio_client)

    @app.get("/client-id")
    def client_id(client: Minio = Depends(get_minio_client)):
        return {"id": id(client)}

    http_client = TestClient(app)
    response = http_client.get("/client-id")
    assert response.status_code == 200
    assert response.json()["id"] == id(minio_client)


# ---------------------------------------------------------------------------
# set_minio_client — 실제 config로 등록
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_set_minio_client_from_config_integration(config: EnvConfig):
    """실제 config로 set_minio_client를 호출하면 실제 Minio 클라이언트가 app.state에 등록된다."""
    app = FastAPI()
    set_minio_client(app, config=config)
    assert isinstance(app.state.minio_client, Minio)


# ---------------------------------------------------------------------------
# Depends — 실제 클라이언트로 버킷 접근
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_get_minio_client_bucket_accessible(minio_client: Minio, config: EnvConfig):
    """state에 등록된 실제 클라이언트로 Depends를 통해 버킷 접근이 가능하다."""
    ensure_bucket_exists(minio_client, config.minio.bucket)
    app = FastAPI()
    set_minio_client(app, minio_client)

    @app.get("/bucket-check")
    def bucket_check(client: Minio = Depends(get_minio_client)):
        return {"exists": client.bucket_exists(config.minio.bucket)}

    http_client = TestClient(app)
    response = http_client.get("/bucket-check")
    assert response.status_code == 200
    assert response.json()["exists"] is True
