from __future__ import annotations

import asyncio
import inspect
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from docmesh_py_core import (
    HealthCheckError,
    HealthCheckResult,
    ServiceHealthStatus,
    async_check_all_services,
)
from fastapi_core.function_logging import log_function_boundary
from fastapi import FastAPI

Check = Callable[[], object | Awaitable[object]]


@dataclass(frozen=True)
class ReadinessCheckSpec:
    name: str
    check: Check
    required: bool = True
    timeout_seconds: float | None = None
    redact_errors: bool = True


@log_function_boundary()
async def _invoke_check(check: Check, timeout_seconds: float | None) -> object:
    @log_function_boundary()
    async def invoke() -> object:
        if inspect.iscoroutinefunction(check):
            return await check()
        result = await asyncio.to_thread(check)
        if inspect.isawaitable(result):
            return await result
        return result

    return await asyncio.wait_for(invoke(), timeout=timeout_seconds)


@log_function_boundary()
def _structured_result(
    parent: str,
    result: HealthCheckResult,
    *,
    required: bool,
) -> HealthCheckResult:
    services = [
        ServiceHealthStatus(
            service=f"{parent}.{service.service}", ok=service.ok,
            latency_ms=service.latency_ms, required=required,
            error=service.error, error_type=service.error_type,
        )
        for service in result.services
    ]
    return HealthCheckResult(
        ok=result.ok and all(service.ok for service in services),
        services=services,
    )


@log_function_boundary()
def _merge_structured_results(
    result: HealthCheckResult,
    structured: dict[str, HealthCheckResult],
) -> HealthCheckResult:
    services: list[ServiceHealthStatus] = []
    for service in result.services:
        nested = structured.get(service.service)
        if (
            nested is None
            or not nested.services
            or (not nested.ok and all(child.ok for child in nested.services))
        ):
            services.append(service)
        else:
            services.extend(nested.services)
    return HealthCheckResult(
        ok=all(service.ok for service in services),
        services=services,
    )


class ReadinessRegistry:
    @log_function_boundary()
    def __init__(self, *, default_timeout_seconds: float | None = None) -> None:
        self.default_timeout_seconds = default_timeout_seconds
        self.specs: dict[str, ReadinessCheckSpec] = {}

    @log_function_boundary()
    def register(self, spec: ReadinessCheckSpec) -> None:
        if not spec.name.strip():
            raise ValueError("readiness check name must not be empty")
        if spec.name in self.specs:
            raise ValueError(f"readiness check '{spec.name}' is already registered")
        if spec.timeout_seconds is not None and spec.timeout_seconds <= 0:
            raise ValueError("readiness check timeout_seconds must be greater than zero")
        self.specs[spec.name] = spec

    @log_function_boundary()
    def unregister(self, name: str) -> None:
        self.specs.pop(name, None)

    @log_function_boundary()
    def resolve_spec(self, name: str) -> ReadinessCheckSpec:
        if (spec := self.specs.get(name)) is not None:
            return spec
        return self.specs[name.split(".", 1)[0]]

    @log_function_boundary()
    async def check(
        self,
        *,
        names: set[str] | None = None,
        parallel: bool = False,
        overall_timeout_seconds: float | None = None,
    ) -> HealthCheckResult:
        selected = {
            name: spec
            for name, spec in self.specs.items()
            if names is None or name in names
        }
        checks: dict[str, Check] = {}
        structured: dict[str, HealthCheckResult] = {}
        for name, spec in selected.items():
            timeout_seconds = spec.timeout_seconds or self.default_timeout_seconds

            @log_function_boundary()
            async def run(
                name: str = name,
                check: Check = spec.check,
                required: bool = spec.required,
                timeout: float | None = timeout_seconds,
            ) -> None:
                result = await _invoke_check(check, timeout)
                if result is False:
                    raise RuntimeError("readiness check returned False")
                if isinstance(result, HealthCheckResult):
                    nested = _structured_result(name, result, required=required)
                    structured[name] = nested
                    if not nested.ok:
                        raise RuntimeError("structured readiness check failed")

            checks[name] = run
        try:
            result = await async_check_all_services(
                checks,
                required_services={
                    name for name, spec in selected.items() if spec.required
                },
                parallel=parallel,
                overall_timeout_seconds=overall_timeout_seconds,
            )
        except HealthCheckError as exc:
            result = _merge_structured_results(exc.result, structured)
            failure = next(
                service for service in result.services if service.required and not service.ok
            )
            raise HealthCheckError(failure, result=result) from exc
        return _merge_structured_results(result, structured)


@log_function_boundary()
def get_readiness_registry(app: FastAPI) -> ReadinessRegistry:
    return app.state.readiness_registry


@log_function_boundary()
def register_readiness_check(
    app: FastAPI,
    name: str,
    check: Check,
    *,
    required: bool = True,
    timeout_seconds: float | None = None,
    redact_errors: bool = True,
) -> None:
    get_readiness_registry(app).register(
        ReadinessCheckSpec(
            name=name,
            check=check,
            required=required,
            timeout_seconds=timeout_seconds,
            redact_errors=redact_errors,
        )
    )


__all__ = [
    "Check",
    "ReadinessCheckSpec",
    "ReadinessRegistry",
    "register_readiness_check",
]
