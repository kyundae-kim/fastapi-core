from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session

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


def get_database_version(engine: Engine) -> str | None:
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.scalar()
    except Exception:
        return None
    return str(version) if version is not None else None


@contextmanager
def run_in_transaction(
    engine: Engine,
    *,
    session_factory: Callable[[Engine], Session] = Session,
) -> Iterator[Session]:
    session = session_factory(engine)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
