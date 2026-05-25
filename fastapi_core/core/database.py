from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session

T = TypeVar("T")

from fastapi_core.core.config import DatabaseConfig


def create_db_engine(config: DatabaseConfig) -> Engine:
    return create_engine(
        config.sqlalchemy_database_url,
        echo=config.echo,
        pool_size=config.pool_size,
        max_overflow=config.max_overflow,
        pool_timeout=config.pool_timeout,
        pool_recycle=config.pool_recycle,
    )


def check_database_connection(engine: Engine) -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def get_database_version(engine: Engine) -> str:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version()"))
        return result.scalar() or ""


def run_in_transaction(
    engine: Engine,
    fn: Callable[[Session], T],
) -> T:
    with Session(engine) as session:
        try:
            result = fn(session)
            session.commit()
            return result
        except Exception:
            session.rollback()
            raise
