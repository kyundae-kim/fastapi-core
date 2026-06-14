import inspect
from unittest.mock import MagicMock, patch

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from fastapi_core.core.config import DatabaseConfig
from fastapi_core.core.database import create_db_engine
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



def test_get_db_engine_initializes_docmesh_registry_when_missing():
    app = FastAPI()
    mock_engine = MagicMock(spec=Engine)
    mock_config = MagicMock()
    app.dependency_overrides[get_config] = lambda: mock_config

    @app.get("/engine-id")
    def engine_id(engine: Engine = Depends(get_db_engine)):
        return {"id": id(engine)}

    with patch(
        "fastapi_core.dependencies.database.get_required_docmesh_service",
        return_value=mock_engine,
    ) as mock_get_required:
        client = TestClient(app)
        response = client.get("/engine-id")

    mock_get_required.assert_called_once_with(
        app,
        "db_engine",
        config=mock_config,
    )
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
    app = FastAPI()
    mock_engine = MagicMock(spec=Engine)
    mock_config = MagicMock()
    with patch(
        "fastapi_core.dependencies.database.get_required_docmesh_service",
        return_value=mock_engine,
    ) as mock_get_required:
        set_db_engine(app, config=mock_config)

    mock_get_required.assert_called_once_with(app, "db_engine", config=mock_config)
    assert app.state.db_engine is mock_engine



def test_set_db_engine_requires_engine_or_config():
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
