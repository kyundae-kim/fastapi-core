from __future__ import annotations

import asyncio
import inspect
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from functools import partial
from typing import Any, Generic, TypeVar

from docmesh_py_core.function_logging import log_function_boundary
from docmesh_py_core import (
    HealthCheckError,
    HealthCheckResult,
    ServiceHealthStatus,
    async_check_all_services,
)
from fastapi import FastAPI

from fastapi_core.resources import ResourceKey

T = TypeVar("T")
Check = Callable[[], object | Awaitable[object]]

_RESERVED_RESOURCE_NAMES = frozenset(
    {
        "auth_provider",
        "config",
        "readiness_registry",
        "resource_registry",
        "resources",
        "root_logger",
        "service_clients",
        "service_runtime",
        "settings",
    }
)


@dataclass(frozen=True)
class ReadinessCheckSpec:
    name: str
    check: Check
    required: bool = True
    timeout_seconds: float | None = None
    redact_errors: bool = True


@dataclass(frozen=True)
class ManagedResource(Generic[T]):
    name: str | ResourceKey[T]
    factory: Callable[[FastAPI], T | Awaitable[T]]
    healthcheck: Callable[[T], object | Awaitable[object]] | None = None
    close: Callable[[T], None | Awaitable[None]] | None = None
    required: bool = True
    readiness_timeout_seconds: float | None = None
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
            service=f"{parent}.{service.service}",
            ok=service.ok,
            latency_ms=service.latency_ms,
            required=required,
            error=service.error,
            error_type=service.error_type,
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
        if nested is None or not nested.services:
            services.append(service)
            continue
        if not nested.ok and all(child.ok for child in nested.services):
            services.append(service)
            continue
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
            timeout_seconds = (
                spec.timeout_seconds
                if spec.timeout_seconds is not None
                else self.default_timeout_seconds
            )

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


class ResourceRegistry:
    @log_function_boundary()
    def __init__(
        self,
        resources: Sequence[ManagedResource[Any]],
        readiness: ReadinessRegistry,
        *,
        reserved_names: set[str] | frozenset[str] = _RESERVED_RESOURCE_NAMES,
    ) -> None:
        self.resources = tuple(resources)
        self.readiness = readiness
        self.instances: dict[str, Any] = {}
        self._healthcheck_names: set[str] = set()
        self._validate(reserved_names)

    @log_function_boundary()
    def _validate(self, reserved_names: set[str] | frozenset[str]) -> None:
        names: set[str] = set()
        for resource in self.resources:
            name = self._name(resource.name)
            if not name.strip():
                raise ValueError("resource name must not be empty")
            if name in reserved_names:
                raise ValueError(f"resource name '{name}' is reserved")
            if name in names:
                raise ValueError(f"resource name '{name}' is already registered")
            if (
                resource.readiness_timeout_seconds is not None
                and resource.readiness_timeout_seconds <= 0
            ):
                raise ValueError(
                    "managed resource readiness_timeout_seconds must be greater than zero"
                )
            names.add(name)

    @staticmethod
    @log_function_boundary()
    def _name(name: str | ResourceKey[Any]) -> str:
        return name.name if isinstance(name, ResourceKey) else name

    @log_function_boundary()
    async def start(self, app: FastAPI) -> None:
        try:
            for resource in self.resources:
                name = self._name(resource.name)
                value = resource.factory(app)
                if inspect.isawaitable(value):
                    value = await value
                self.instances[name] = value
                if resource.healthcheck is not None:
                    check = partial(resource.healthcheck, value)
                    self.readiness.register(
                        ReadinessCheckSpec(
                            name=name,
                            check=check,
                            required=resource.required,
                            timeout_seconds=resource.readiness_timeout_seconds,
                            redact_errors=resource.redact_errors,
                        )
                    )
                    self._healthcheck_names.add(name)
        except BaseException as exc:
            try:
                await self.close()
            except BaseException as close_exc:
                exc.add_note(f"managed resource rollback failed: {close_exc}")
            raise

    @log_function_boundary()
    async def check_startup(
        self,
        *,
        parallel: bool,
        overall_timeout_seconds: float | None,
    ) -> None:
        required_names = {
            self._name(resource.name)
            for resource in self.resources
            if resource.healthcheck is not None and resource.required
        }
        if not required_names:
            return
        await self.readiness.check(
            names=required_names,
            parallel=parallel,
            overall_timeout_seconds=overall_timeout_seconds,
        )

    @log_function_boundary()
    def require(self, name: str) -> Any:
        if name not in self.instances:
            raise KeyError(name)
        return self.instances[name]

    @log_function_boundary()
    async def close(self) -> None:
        failures: list[BaseException] = []
        for resource in reversed(self.resources):
            name = self._name(resource.name)
            if name not in self.instances:
                continue
            value = self.instances.pop(name)
            try:
                await self._close_resource(resource, value)
            except BaseException as exc:
                failures.append(exc)
            finally:
                if name in self._healthcheck_names:
                    self.readiness.unregister(name)
                    self._healthcheck_names.discard(name)
        if failures:
            raise BaseExceptionGroup("managed resource shutdown failed", failures)

    @log_function_boundary()
    async def _close_resource(
        self,
        resource: ManagedResource[Any],
        value: Any,
    ) -> None:
        if resource.close is not None:
            result = resource.close(value)
        elif callable(getattr(value, "aclose", None)):
            result = value.aclose()
        elif callable(getattr(value, "close", None)):
            result = value.close()
        else:
            return
        if inspect.isawaitable(result):
            await result


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
    registry: ReadinessRegistry = app.state.readiness_registry
    registry.register(
        ReadinessCheckSpec(
            name=name,
            check=check,
            required=required,
            timeout_seconds=timeout_seconds,
            redact_errors=redact_errors,
        )
    )
