from __future__ import annotations

from collections.abc import Iterator

from fastapi import Depends, FastAPI, Request
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


class GetDbEngineDependency:
    def __call__(
        self,
        request: Request,
        config: EnvConfig = Depends(get_config),
    ) -> Engine:
        try:
            return getattr(request.app.state, _DB_ENGINE_STATE_KEY)
        except AttributeError:
            engine = create_db_engine(config.db)
            setattr(request.app.state, _DB_ENGINE_STATE_KEY, engine)
            return engine


get_db_engine = GetDbEngineDependency()


class GetDbSessionDependency:
    def __call__(self, engine: Engine = Depends(get_db_engine)) -> Iterator[Session]:
        session = Session(engine)
        try:
            yield session
        finally:
            session.close()


get_db_session = GetDbSessionDependency()
