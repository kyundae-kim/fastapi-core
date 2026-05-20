from __future__ import annotations

from sqlalchemy import Engine, create_engine, text

from fastapi_core.core.config import DatabaseConfig


def create_db_engine(config: DatabaseConfig) -> Engine:
    return create_engine(
        config.sqlalchemy_database_url,
        echo=config.echo,
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
