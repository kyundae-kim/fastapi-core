from __future__ import annotations

from fastapi import Depends
from sqlalchemy import Engine

from fastapi_core.core.config import EnvConfig
from fastapi_core.core.database import create_db_engine
from fastapi_core.dependencies.config import get_config


def get_db_engine(config: EnvConfig = Depends(get_config)) -> Engine:
    return create_db_engine(config.db)
