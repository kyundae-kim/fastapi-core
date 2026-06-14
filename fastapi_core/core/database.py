from __future__ import annotations

from sqlalchemy import Engine, create_engine, text

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
