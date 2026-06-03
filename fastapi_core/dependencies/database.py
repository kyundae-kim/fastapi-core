from __future__ import annotations

from collections.abc import Iterator

from fastapi import Depends, FastAPI, Request
from fastapi.params import Depends as DependsParam
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from fastapi_core.core.config import EnvConfig
from fastapi_core.core.database import create_db_engine
from fastapi_core.dependencies.config import get_config

_DB_ENGINE_STATE_KEY = "db_engine"


def set_db_engine(
    app: FastAPI,
    engine: Engine | None = None,
    *,
    config: EnvConfig | None = None,
) -> None:
    if engine is None:
        if config is None:
            raise ValueError("Either engine or config must be provided")
        engine = create_db_engine(config.db)
    setattr(app.state, _DB_ENGINE_STATE_KEY, engine)


def get_db_engine(
    request: Request,
    config: EnvConfig | DependsParam = Depends(get_config),
) -> Engine:
    try:
        return getattr(request.app.state, _DB_ENGINE_STATE_KEY)
    except AttributeError:
        if isinstance(config, DependsParam):
            config = get_config(request)
        engine = create_db_engine(config.db)
        set_db_engine(request.app, engine)
        return engine


def get_db_session(engine: Engine = Depends(get_db_engine)) -> Iterator[Session]:
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()
