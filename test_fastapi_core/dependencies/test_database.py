import inspect
from unittest.mock import MagicMock, patch

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from fastapi_core.core.config import DatabaseConfig, EnvConfig
from fastapi_core.core.database import create_db_engine, run_in_transaction
from fastapi_core.dependencies.config import get_config
from fastapi_core.dependencies.database import (
    get_db_engine,
    get_db_session,
    set_db_engine,
)


def test_get_db_engine_creates_engine():
    config = DatabaseConfig(
        host="localhost",
        port=5432,
        name="testdb",
        user="user",
        password="pass",
        auth_method="password",
        sslmode="disable",
        connect_timeout=5,
        echo=False,
    )
    with patch("fastapi_core.core.database.create_engine") as mock_create:
        mock_engine = MagicMock()
        mock_create.return_value = mock_engine
        engine = create_db_engine(config)
        mock_create.assert_called_once_with(
            config.sqlalchemy_database_url,
            echo=False,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=1800,
        )
        assert engine is mock_engine


def test_check_database_connection_success():
    from fastapi_core.core.database import check_database_connection

    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_engine.connect.return_value.__enter__.return_value = mock_conn
    assert check_database_connection(mock_engine) is True


def test_check_database_connection_failure():
    from fastapi_core.core.database import check_database_connection

    mock_engine = MagicMock()
    mock_engine.connect.side_effect = Exception("connection refused")
    assert check_database_connection(mock_engine) is False


# ---------------------------------------------------------------------------
# get_db_engine — state 기반 싱글톤 테스트
# ---------------------------------------------------------------------------


def test_get_db_engine_from_state():
    """app.state에 db_engine이 등록돼 있으면 동일 인스턴스를 반환하고
    create_db_engine을 호출하지 않는다."""
    app = FastAPI()
    mock_engine = MagicMock(spec=Engine)
    set_db_engine(app, mock_engine)

    @app.get("/engine-id")
    def engine_id(engine: Engine = Depends(get_db_engine)):
        return {"id": id(engine)}

    with patch("fastapi_core.dependencies.database.create_db_engine") as mock_create:
        client = TestClient(app)
        response = client.get("/engine-id")
        mock_create.assert_not_called()
    assert response.status_code == 200
    assert response.json()["id"] == id(mock_engine)
    assert app.state.db_engine is mock_engine


def test_get_db_engine_fallback_prefers_docmesh_registry():
    """docmesh registry가 있으면 native create 대신 registry client를 state에 등록한다."""
    app = FastAPI()
    mock_engine = MagicMock(spec=Engine)
    mock_config = MagicMock()
    mock_registry = MagicMock()
    mock_registry.create_client.return_value = MagicMock(client=mock_engine)
    app.state.docmesh_registry = mock_registry
    app.dependency_overrides[get_config] = lambda: mock_config

    @app.get("/engine-id")
    def engine_id(engine: Engine = Depends(get_db_engine)):
        return {"id": id(engine)}

    with patch(
        "fastapi_core.dependencies.database.create_db_engine", return_value=MagicMock(spec=Engine)
    ) as mock_create:
        client = TestClient(app)
        response = client.get("/engine-id")
        mock_create.assert_not_called()

    mock_registry.create_client.assert_called_once_with("postgres")
    assert response.status_code == 200
    assert response.json()["id"] == id(mock_engine)
    assert app.state.db_engine is mock_engine


def test_get_db_engine_fallback():
    """app.state에 db_engine이 없으면 생성 후 state에 등록하여 반환한다."""
    app = FastAPI()
    mock_engine = MagicMock(spec=Engine)
    mock_config = MagicMock()
    app.dependency_overrides[get_config] = lambda: mock_config

    @app.get("/engine-id")
    def engine_id(engine: Engine = Depends(get_db_engine)):
        return {"id": id(engine)}

    with patch(
        "fastapi_core.dependencies.database.create_db_engine", return_value=mock_engine
    ) as mock_create:
        client = TestClient(app)
        response = client.get("/engine-id")
        mock_create.assert_called_once_with(mock_config.db)
    assert response.status_code == 200
    assert response.json()["id"] == id(mock_engine)
    assert app.state.db_engine is mock_engine


def test_database_dependencies_are_functions():
    import fastapi_core.dependencies.database as database_dependencies

    assert not hasattr(database_dependencies, "GetDbEngineDependency")
    assert not hasattr(database_dependencies, "GetDbSessionDependency")
    assert inspect.isfunction(database_dependencies.get_db_engine)
    assert inspect.isfunction(database_dependencies.get_db_session)


def test_set_db_engine_from_config():
    """config를 전달하면 create_db_engine을 호출하여 state에 등록한다."""
    app = FastAPI()
    mock_engine = MagicMock(spec=Engine)
    mock_config = MagicMock()
    with patch(
        "fastapi_core.dependencies.database.create_db_engine", return_value=mock_engine
    ) as mock_create:
        set_db_engine(app, config=mock_config)
        mock_create.assert_called_once_with(mock_config.db)
    assert app.state.db_engine is mock_engine


def test_set_db_engine_requires_engine_or_config():
    """engine과 config 모두 생략하면 ValueError를 발생시킨다."""
    app = FastAPI()
    with pytest.raises(ValueError):
        set_db_engine(app)


def test_get_db_session_closes_session():
    mock_engine = MagicMock(spec=Engine)
    mock_session = MagicMock()

    with patch("fastapi_core.dependencies.database.Session", return_value=mock_session):
        gen = get_db_session(mock_engine)
        yielded = next(gen)
        assert yielded is mock_session

        with pytest.raises(StopIteration):
            next(gen)

    mock_session.close.assert_called_once()


def test_run_in_transaction_commit_and_return_value():
    mock_engine = MagicMock(spec=Engine)
    mock_session = MagicMock()
    mock_ctx = MagicMock()
    mock_ctx.__enter__.return_value = mock_session
    mock_ctx.__exit__.return_value = False

    with patch("fastapi_core.core.database.Session", return_value=mock_ctx) as mock_cls:
        fn = MagicMock(return_value="ok")
        result = run_in_transaction(mock_engine, fn)

    mock_cls.assert_called_once_with(mock_engine)
    fn.assert_called_once_with(mock_session)
    mock_session.commit.assert_called_once()
    mock_session.rollback.assert_not_called()
    assert result == "ok"


def test_run_in_transaction_rollback_on_error():
    mock_engine = MagicMock(spec=Engine)
    mock_session = MagicMock()
    mock_ctx = MagicMock()
    mock_ctx.__enter__.return_value = mock_session
    mock_ctx.__exit__.return_value = False

    with patch("fastapi_core.core.database.Session", return_value=mock_ctx):
        with pytest.raises(RuntimeError):
            run_in_transaction(
                mock_engine,
                lambda _session: (_ for _ in ()).throw(RuntimeError("boom")),
            )

    mock_session.rollback.assert_called_once()
    mock_session.commit.assert_not_called()
