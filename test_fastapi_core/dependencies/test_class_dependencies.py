from __future__ import annotations

import inspect

import pytest

from fastapi_core.dependencies.messaging import get_nats_client
from fastapi_core.dependencies.storage import get_minio_client


@pytest.mark.parametrize(
    "dependency",
    [
        get_minio_client,
        get_nats_client,
    ],
)
def test_get_dependencies_are_callable_class_instances(dependency):
    assert callable(dependency)
    assert not inspect.isfunction(dependency)
    assert dependency.__class__.__name__.endswith("Dependency")
