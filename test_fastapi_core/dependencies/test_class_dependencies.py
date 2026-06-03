from __future__ import annotations

import inspect

from fastapi_core.dependencies.messaging import get_nats_client


def test_get_dependencies_are_callable_class_instances():
    dependency = get_nats_client

    assert callable(dependency)
    assert not inspect.isfunction(dependency)
    assert dependency.__class__.__name__.endswith("Dependency")
