from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from fastapi_core.docmesh_bridge import (
    initialize_docmesh_registry,
    is_docmesh_available,
    run_docmesh_healthchecks,
)


def test_initialize_docmesh_registry_builds_settings_and_registry():
    captured_env: dict[str, str] = {}

    def fake_load_settings(env: dict[str, str]) -> object:
        captured_env.update(env)
        return {"settings": True}

    class FakeRegistry:
        def __init__(self, settings: object) -> None:
            self.settings = settings

    fake_module = SimpleNamespace(
        load_settings=fake_load_settings,
        ServiceFactoryRegistry=FakeRegistry,
    )

    with patch(
        "fastapi_core.docmesh_bridge._load_docmesh_module",
        return_value=fake_module,
    ):
        settings, registry = initialize_docmesh_registry({"APP_ENV": "test"})

    assert settings == {"settings": True}
    assert registry.settings == settings
    assert captured_env == {"APP_ENV": "test"}


def test_is_docmesh_available_false_when_import_fails():
    with patch(
        "fastapi_core.docmesh_bridge._load_docmesh_module",
        side_effect=ImportError,
    ):
        assert is_docmesh_available() is False


def test_run_docmesh_healthchecks_uses_external_check_all_services():
    called: dict[str, object] = {}

    def fake_check_all_services(service_checks, required_services=None):
        called["service_checks"] = service_checks
        called["required_services"] = required_services
        return SimpleNamespace(ok=True)

    fake_module = SimpleNamespace(check_all_services=fake_check_all_services)

    with patch(
        "fastapi_core.docmesh_bridge._load_docmesh_module",
        return_value=fake_module,
    ):
        ok = run_docmesh_healthchecks(
            {"database": lambda: True},
            required_services={"database"},
        )

    assert ok is True
    assert set(called["service_checks"]) == {"database"}
    assert called["required_services"] == {"database"}
