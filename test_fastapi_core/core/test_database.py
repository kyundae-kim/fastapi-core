from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from sqlalchemy import Engine

from fastapi_core.core.database import get_database_version, run_in_transaction


def test_get_database_version_returns_scalar_value() -> None:
    mock_engine = MagicMock(spec=Engine)
    mock_conn = MagicMock()
    mock_result = MagicMock()
    mock_result.scalar.return_value = "PostgreSQL 16.3"
    mock_conn.execute.return_value = mock_result
    mock_engine.connect.return_value.__enter__.return_value = mock_conn

    version = get_database_version(mock_engine)

    assert version == "PostgreSQL 16.3"


def test_get_database_version_returns_none_on_failure() -> None:
    mock_engine = MagicMock(spec=Engine)
    mock_engine.connect.side_effect = RuntimeError("db unavailable")

    assert get_database_version(mock_engine) is None


def test_run_in_transaction_commits_and_closes_on_success() -> None:
    mock_engine = MagicMock(spec=Engine)
    mock_session = MagicMock()

    with run_in_transaction(mock_engine, session_factory=lambda engine: mock_session) as session:
        assert session is mock_session

    mock_session.commit.assert_called_once_with()
    mock_session.rollback.assert_not_called()
    mock_session.close.assert_called_once_with()


def test_run_in_transaction_rolls_back_and_closes_on_error() -> None:
    mock_engine = MagicMock(spec=Engine)
    mock_session = MagicMock()

    with pytest.raises(RuntimeError, match="boom"):
        with run_in_transaction(
            mock_engine,
            session_factory=lambda engine: mock_session,
        ):
            raise RuntimeError("boom")

    mock_session.commit.assert_not_called()
    mock_session.rollback.assert_called_once_with()
    mock_session.close.assert_called_once_with()
