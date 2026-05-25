"""PostgreSQL 연동 통합 테스트 — 실제 PostgreSQL 인스턴스 필요."""
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from fastapi_core.core.config import EnvConfig
from fastapi_core.core.database import (
    check_database_connection,
    create_db_engine,
    get_database_version,
    run_in_transaction,
)
from fastapi_core.dependencies.database import get_db_engine, get_db_session, set_db_engine


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


@pytest.mark.integration
def test_get_db_session_integration(engine: Engine):
    """get_db_session이 실제 세션을 제공해 쿼리를 수행할 수 있다."""
    app = FastAPI()
    set_db_engine(app, engine)

    @app.get("/db-session-check")
    def db_session_check(session=Depends(get_db_session)):
        row = session.execute(text("SELECT 1")).scalar()
        return {"value": row}

    client = TestClient(app)
    response = client.get("/db-session-check")
    assert response.status_code == 200
    assert response.json()["value"] == 1


@pytest.mark.integration
def test_run_in_transaction_integration(engine: Engine):
    """run_in_transaction이 실제 트랜잭션에서 함수를 실행하고 값을 반환한다."""

    def _fn(session):
        return session.execute(text("SELECT 1")).scalar()

    result = run_in_transaction(engine, _fn)
    assert result == 1
