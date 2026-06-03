from __future__ import annotations

import inspect

import pytest

from fastapi_core.dependencies.auth import get_auth_provider, get_current_user
from fastapi_core.dependencies.config import config_schema, settings_schema
from fastapi_core.dependencies.database import get_db_engine, get_db_session
from fastapi_core.dependencies.messaging import get_nats_client
from fastapi_core.dependencies.storage import get_minio_client


@pytest.mark.parametrize(
    "dependency",
    [
        config_schema,
        settings_schema,
        get_auth_provider,
        get_current_user,
        get_db_engine,
        get_db_session,
        get_minio_client,
        get_nats_client,
    ],
)
def test_get_dependencies_are_callable_class_instances(dependency):
    assert callable(dependency)
    assert not inspect.isfunction(dependency)
    assert dependency.__class__.__name__.endswith("Dependency")
