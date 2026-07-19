from __future__ import annotations

from fastapi.testclient import TestClient

import fastapi_core.runtime as runtime_module
import fastapi_core.testing as testing_module
from fastapi_core import create_app
from fastapi_core.testing import (
    ResourceLifecycleProbe,
    assert_auth_router_contract,
    assert_health_contract,
    create_empty_runtime,
)


def test_testing_module_exports_only_contract_helpers():
    assert set(testing_module.__all__) == {
        "ResourceLifecycleProbe",
        "assert_auth_router_contract",
        "assert_health_contract",
        "create_empty_runtime",
    }


def test_create_empty_runtime_has_no_selected_or_required_services():
    runtime = create_empty_runtime()

    assert runtime.selected_services == frozenset()
    assert runtime.required_services == frozenset()
    assert runtime.clients == {}


def test_testing_empty_runtime_uses_production_canonical_helper():
    assert testing_module.create_empty_runtime is runtime_module.create_empty_runtime


def test_resource_lifecycle_probe_exercises_real_app_lifespan_and_readiness():
    value = object()
    probe = ResourceLifecycleProbe(value=value)
    app = create_app(
        runtime=create_empty_runtime(),
        resources=[probe.managed_resource("sdk")],
    )

    with TestClient(app) as client:
        assert probe.events == ["create:sdk"]
        assert_health_contract(client)
        assert probe.events == ["create:sdk", "check:sdk"]

    assert probe.events == ["create:sdk", "check:sdk", "close:sdk"]


def test_contract_assertions_cover_auth_router_opt_in_and_out():
    disabled_app = create_app(runtime=create_empty_runtime())
    enabled_app = create_app(
        runtime=create_empty_runtime(),
        include_auth_router=True,
    )

    with TestClient(disabled_app) as client:
        assert_auth_router_contract(client, included=False)

    with TestClient(enabled_app) as client:
        assert_auth_router_contract(client, included=True)
