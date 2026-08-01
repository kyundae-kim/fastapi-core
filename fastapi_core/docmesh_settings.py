from __future__ import annotations

from functools import lru_cache

from fastapi_core.function_logging import log_function_boundary
from docmesh_config import ServiceConfigs, load_service_configs


@lru_cache(maxsize=1)
@log_function_boundary()
def load_docmesh_settings(
    enabled_services: tuple[str, ...] | None = None,
) -> ServiceConfigs:
    services = set(enabled_services) if enabled_services is not None else None
    return load_service_configs(services=services)