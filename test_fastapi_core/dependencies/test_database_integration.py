"""PostgreSQL 연동 통합 테스트 — 실제 PostgreSQL 인스턴스 필요."""
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from fastapi_core.core.config import EnvConfig
from fastapi_core.core.database import check_database_connection, create_db_engine
from fastapi_core.dependencies.database import get_db_engine, get_db_session, set_db_engine


@pytest.fixture(scope="module")
def config() -> EnvConfig:
    return EnvConfig()


@pytest.fixture(scope="module")
def engine(config: EnvConfig):
    e = create_db_engine(config.db)
    yield e
    e.dispose()


@pytest.mark.integration
def test_create_db_engine(engine: Engine):
    assert engine is not None
    assert isinstance(engine, Engine)


@pytest.mark.integration
def test_check_database_connection(engine: Engine):
    assert check_database_connection(engine) is True


@pytest.mark.integration
def test_engine_can_execute_query_directly(engine: Engine):
    with engine.connect() as connection:
        value = connection.execute(text("SELECT 1")).scalar()
    assert value == 1


@pytest.mark.integration
def test_get_db_engine_from_state_integration(engine: Engine):
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
