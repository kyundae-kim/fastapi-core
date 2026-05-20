"""PostgreSQL 연동 통합 테스트 — 실제 PostgreSQL 인스턴스 필요."""
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from fastapi_core.core.config import EnvConfig
from fastapi_core.core.database import (
    check_database_connection,
    create_db_engine,
    get_database_version,
)
from fastapi_core.dependencies.database import get_db_engine, set_db_engine


@pytest.fixture(scope="module")
def config() -> EnvConfig:
    return EnvConfig()


@pytest.fixture(scope="module")
def engine(config: EnvConfig):
    e = create_db_engine(config.db)
    yield e
    e.dispose()


# ---------------------------------------------------------------------------
# 엔진 생성
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_create_db_engine(engine: Engine):
    """실제 PostgreSQL 엔진이 생성된다."""
    assert engine is not None
    assert isinstance(engine, Engine)


# ---------------------------------------------------------------------------
# 연결 확인 (SELECT 1)
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_check_database_connection(engine: Engine):
    """실제 DB에 SELECT 1 연결 확인이 성공한다."""
    assert check_database_connection(engine) is True


# ---------------------------------------------------------------------------
# DB 버전 조회
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_get_database_version(engine: Engine):
    """실제 DB 버전 문자열을 반환한다."""
    version = get_database_version(engine)
    assert version
    assert "PostgreSQL" in version


# ---------------------------------------------------------------------------
# get_db_engine — 실제 엔진으로 state 싱글톤 검증
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_get_db_engine_from_state_integration(engine: Engine):
    """app.state에 실제 엔진이 등록돼 있을 때 get_db_engine이 동일 인스턴스를 반환한다."""
    app = FastAPI()
    set_db_engine(app, engine)

    @app.get("/engine-id")
    def engine_id(e: Engine = Depends(get_db_engine)):
        return {"id": id(e)}

    client = TestClient(app)
    response = client.get("/engine-id")
    assert response.status_code == 200
    assert response.json()["id"] == id(engine)
