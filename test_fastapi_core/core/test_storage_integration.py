"""MinIO 연동 통합 테스트 — 실제 MinIO 인스턴스 필요."""
import pytest
from minio import Minio

from fastapi_core.core.config import EnvConfig
from fastapi_core.core.storage import (
    create_minio_client,
    ensure_bucket_exists,
    list_buckets,
)


@pytest.fixture(scope="module")
def config() -> EnvConfig:
    return EnvConfig()


@pytest.fixture(scope="module")
def minio_client(config: EnvConfig) -> Minio:
    return create_minio_client(config.minio)


# ---------------------------------------------------------------------------
# 클라이언트 생성
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_create_minio_client(minio_client: Minio):
    """실제 MinIO 클라이언트가 생성된다."""
    assert minio_client is not None
    assert isinstance(minio_client, Minio)


# ---------------------------------------------------------------------------
# 버킷 자동 생성
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_ensure_bucket_exists(minio_client: Minio, config: EnvConfig):
    """버킷이 없으면 생성하고, 있으면 그대로 유지한다."""
    bucket = config.minio.bucket
    ensure_bucket_exists(minio_client, bucket)
    assert minio_client.bucket_exists(bucket)


# ---------------------------------------------------------------------------
# 버킷 목록 조회
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_list_buckets(minio_client: Minio, config: EnvConfig):
    """버킷 목록에 기본 버킷이 포함된다."""
    bucket = config.minio.bucket
    ensure_bucket_exists(minio_client, bucket)
    buckets = list_buckets(minio_client)
    assert bucket in buckets
