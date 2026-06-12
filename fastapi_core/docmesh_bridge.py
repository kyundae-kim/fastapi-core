from __future__ import annotations

from collections.abc import Mapping
import importlib
import os
from typing import Any


DOCMESH_MODULE_NAME = "docmesh_py_core"


def _load_docmesh_module() -> Any:
    return importlib.import_module(DOCMESH_MODULE_NAME)


def is_docmesh_available() -> bool:
    try:
        _load_docmesh_module()
    except ImportError:
        return False
    return True


def initialize_docmesh_registry(
    env: Mapping[str, str] | None = None,
) -> tuple[object, object] | None:
    try:
        module = _load_docmesh_module()
    except ImportError:
        return None

    source_env = dict(os.environ if env is None else env)
    settings = module.load_settings(source_env)
    registry = module.ServiceFactoryRegistry(settings)
    return settings, registry


def run_docmesh_healthchecks(
    service_checks: Mapping[str, Any],
    *,
    required_services: set[str] | None = None,
) -> bool:
    try:
        module = _load_docmesh_module()
    except ImportError:
        return False

    result = module.check_all_services(
        dict(service_checks),
        required_services=required_services,
    )
    return bool(getattr(result, "ok", False))
