from __future__ import annotations

import logging
from collections.abc import Callable
from contextlib import asynccontextmanager, nullcontext

from docmesh_config import RuntimePlan
from docmesh_py_core import (
    HealthCheckError,
    ServiceCloseError,
    ServiceRuntime,
)
from fastapi_core.function_logging import log_function_boundary
from fastapi import FastAPI

from fastapi_core.config import AppConfig
from fastapi_core.resources import ResourceRegistry
from fastapi_core.runtime import (
    _build_healthcheck_policy,
    assemble_runtime,
    configure_service_runtime,
)

logger = logging.getLogger(__name__)


@log_function_boundary()
async def _check_runtime_on_startup(
    runtime: ServiceRuntime,
    config: AppConfig,
) -> None:
    try:
        runtime.startup_healthcheck_result = await runtime.check_with_policy(
            _build_healthcheck_policy(config)
        )
    except HealthCheckError as exc:
        runtime.startup_healthcheck_result = exc.result
        raise


@log_function_boundary()
def build_lifespan(
    lifespan: Callable | None,
    config: AppConfig,
    runtime: ServiceRuntime | None,
    runtime_plan: RuntimePlan | None,
    resources: ResourceRegistry,
    *,
    require_auth_provider: bool = False,
) -> Callable:
    @asynccontextmanager
    @log_function_boundary()
    async def managed_lifespan(app: FastAPI):
        app_runtime = runtime
        try:
            if app_runtime is None:
                app_runtime = await assemble_runtime(runtime_plan)
                configure_service_runtime(app, app_runtime)
            elif config.startup_healthcheck:
                await _check_runtime_on_startup(app_runtime, config)
            if require_auth_provider and not hasattr(app.state, "auth_provider"):
                raise ValueError("auth router requires a configured auth provider")
            await resources.start(app)
            if config.startup_healthcheck:
                await resources.check_startup(
                    parallel=config.readiness_parallel,
                    overall_timeout_seconds=config.readiness_overall_timeout_seconds,
                )
            async with lifespan(app) if lifespan is not None else nullcontext():
                yield
        finally:
            try:
                await resources.close()
            finally:
                if app_runtime is not None:
                    try:
                        await app_runtime.close()
                    except ServiceCloseError as exc:
                        logger.error(
                            "service_runtime_close_failed",
                            extra={
                                "event": {
                                    "operation": "service_runtime_close",
                                    "outcome": "error",
                                    "failure_count": len(exc.failures),
                                }
                            },
                        )
                        raise

    return managed_lifespan


__all__ = ["build_lifespan"]
