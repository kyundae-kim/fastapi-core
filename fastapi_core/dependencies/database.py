from __future__ import annotations

from collections.abc import Iterator

from fastapi import Depends, FastAPI, Request
from fastapi.params import Depends as DependsParam
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from fastapi_core.bootstrap import get_or_create_state_value, set_state_value
from fastapi_core.core.config import EnvConfig
from fastapi_core.core.database import create_db_engine
from fastapi_core.dependencies.config import get_config
from fastapi_core.docmesh_bridge import get_required_docmesh_service

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
        engine = get_required_docmesh_service(
            app,
            _DB_ENGINE_STATE_KEY,
            config=config,
        )
    set_state_value(app, _DB_ENGINE_STATE_KEY, engine)


def get_db_engine(
    request: Request,
    config: EnvConfig | DependsParam = Depends(get_config),
) -> Engine:
    def factory() -> Engine:
        resolved_config = config
        if isinstance(resolved_config, DependsParam):
            resolved_config = get_config(request)
        return get_required_docmesh_service(
            request.app,
            _DB_ENGINE_STATE_KEY,
            config=resolved_config,
        )

    return get_or_create_state_value(request.app, _DB_ENGINE_STATE_KEY, factory)


def get_db_session(engine: Engine = Depends(get_db_engine)) -> Iterator[Session]:
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()
