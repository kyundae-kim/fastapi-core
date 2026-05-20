from __future__ import annotations

from fastapi import Depends, FastAPI, Request
from sqlalchemy import Engine

from fastapi_core.core.config import EnvConfig
from fastapi_core.core.database import create_db_engine
from fastapi_core.dependencies.config import get_config

_DB_ENGINE_STATE_KEY = "db_engine"


def set_db_engine(app: FastAPI, engine: Engine) -> None:
    setattr(app.state, _DB_ENGINE_STATE_KEY, engine)


def get_db_engine(
    request: Request,
    config: EnvConfig = Depends(get_config),
) -> Engine:
    try:
        return getattr(request.app.state, _DB_ENGINE_STATE_KEY)
    except AttributeError:
        return create_db_engine(config.db)
