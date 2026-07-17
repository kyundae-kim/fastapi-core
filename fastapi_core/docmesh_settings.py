from __future__ import annotations

import os
from functools import lru_cache

from docmesh_py_core.function_logging import log_function_boundary
from docmesh_py_core import ServiceConfigs, load_service_configs


@log_function_boundary()
def build_docmesh_env_overlay() -> dict[str, str]:
    return dict(os.environ)


@lru_cache(maxsize=1)
@log_function_boundary()
def load_docmesh_settings(
    enabled_services: tuple[str, ...] | None = None,
) -> ServiceConfigs:
    services = set(enabled_services) if enabled_services is not None else None
    return load_service_configs(
        build_docmesh_env_overlay(),
        services=services,
    )