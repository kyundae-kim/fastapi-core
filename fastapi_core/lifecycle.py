from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from contextlib import asynccontextmanager

from docmesh_py_core import (
    HealthCheckError,
    RuntimePlan,
    ServiceCloseError,
    ServiceRuntime,
    StartupFailureMode,
)
from fastapi_core.function_logging import log_function_boundary
from fastapi import FastAPI

from fastapi_core.config import AppConfig
from fastapi_core.resources import ResourceRegistry
from fastapi_core.runtime import assemble_runtime, configure_service_runtime

logger = logging.getLogger(__name__)


@log_function_boundary()
async def _check_runtime_on_startup(
    runtime: ServiceRuntime,
    config: AppConfig,
) -> None:
    for attempt in range(config.startup_healthcheck_attempts):
        try:
            runtime.startup_healthcheck_result = await runtime.check(
                parallel=config.readiness_parallel,
                timeout_seconds=config.readiness_timeout_seconds,
                overall_timeout_seconds=config.readiness_overall_timeout_seconds,
            )
            return
        except HealthCheckError as exc:
            runtime.startup_healthcheck_result = exc.result
            if attempt + 1 < config.startup_healthcheck_attempts:
                if config.startup_healthcheck_retry_delay_seconds:
                    await asyncio.sleep(
                        config.startup_healthcheck_retry_delay_seconds
                    )
                continue
            if config.startup_failure_mode == StartupFailureMode.REPORT:
                return
            raise


@log_function_boundary()
def build_lifespan(
    lifespan: Callable | None,
    config: AppConfig,
    runtime: ServiceRuntime | None,
    runtime_plan: RuntimePlan | None,
    resources: ResourceRegistry,
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
            await resources.start(app)
            if config.startup_healthcheck:
                await resources.check_startup(
                    parallel=config.readiness_parallel,
                    overall_timeout_seconds=config.readiness_overall_timeout_seconds,
                )
            if lifespan is None:
                yield
            else:
                async with lifespan(app):
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
