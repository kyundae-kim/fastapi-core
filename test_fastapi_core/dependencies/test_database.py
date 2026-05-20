from unittest.mock import MagicMock, patch

from fastapi_core.core.config import DatabaseConfig
from fastapi_core.core.database import create_db_engine


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
