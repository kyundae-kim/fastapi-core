"""MinIO 연동 통합 테스트 — 실제 MinIO 인스턴스 필요."""

import pytest
from minio import Minio

from fastapi_core.core.config import EnvConfig
from fastapi_core.core.storage import check_minio_connection, create_minio_client


@pytest.fixture(scope="module")
def config() -> EnvConfig:
    return EnvConfig()


@pytest.fixture(scope="module")
def minio_client(config: EnvConfig) -> Minio:
    return create_minio_client(config.minio)


@pytest.mark.integration
def test_create_minio_client(minio_client: Minio):
    """실제 MinIO 클라이언트가 생성된다."""
    assert minio_client is not None
    assert isinstance(minio_client, Minio)


@pytest.mark.integration
def test_check_minio_connection(minio_client: Minio, config: EnvConfig):
    """설정된 기본 버킷에 대해 연결 확인이 가능하다."""
    bucket = config.minio.bucket
    assert check_minio_connection(minio_client, bucket) is True
