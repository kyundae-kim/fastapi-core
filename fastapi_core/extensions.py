from __future__ import annotations

import asyncio
import inspect
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from functools import partial
from typing import Any, Generic, TypeVar

from docmesh_py_core import HealthCheckResult, async_check_all_services
from fastapi import FastAPI

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
    name: str
    factory: Callable[[FastAPI], T | Awaitable[T]]
    healthcheck: Callable[[T], object | Awaitable[object]] | None = None
    close: Callable[[T], None | Awaitable[None]] | None = None
    required: bool = True
    readiness_timeout_seconds: float | None = None
    redact_errors: bool = True


async def _invoke_check(check: Check, timeout_seconds: float | None) -> None:
    async def invoke() -> None:
        if inspect.iscoroutinefunction(check):
            await check()
            return
        result = await asyncio.to_thread(check)
        if inspect.isawaitable(result):
            await result

    await asyncio.wait_for(invoke(), timeout=timeout_seconds)


class ReadinessRegistry:
    def __init__(self, *, default_timeout_seconds: float | None = None) -> None:
        self.default_timeout_seconds = default_timeout_seconds
        self.specs: dict[str, ReadinessCheckSpec] = {}

    def register(self, spec: ReadinessCheckSpec) -> None:
        if not spec.name.strip():
            raise ValueError("readiness check name must not be empty")
        if spec.name in self.specs:
            raise ValueError(f"readiness check '{spec.name}' is already registered")
        if spec.timeout_seconds is not None and spec.timeout_seconds <= 0:
            raise ValueError("readiness check timeout_seconds must be greater than zero")
        self.specs[spec.name] = spec

    def unregister(self, name: str) -> None:
        self.specs.pop(name, None)

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
        for name, spec in selected.items():
            timeout_seconds = (
                spec.timeout_seconds
                if spec.timeout_seconds is not None
                else self.default_timeout_seconds
            )

            async def run(
                check: Check = spec.check,
                timeout: float | None = timeout_seconds,
            ) -> None:
                await _invoke_check(check, timeout)

            checks[name] = run
        return await async_check_all_services(
            checks,
            required_services={
                name for name, spec in selected.items() if spec.required
            },
            parallel=parallel,
            overall_timeout_seconds=overall_timeout_seconds,
        )


class ResourceRegistry:
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

    def _validate(self, reserved_names: set[str] | frozenset[str]) -> None:
        names: set[str] = set()
        for resource in self.resources:
            if not resource.name.strip():
                raise ValueError("resource name must not be empty")
            if resource.name in reserved_names:
                raise ValueError(f"resource name '{resource.name}' is reserved")
            if resource.name in names:
                raise ValueError(f"resource name '{resource.name}' is already registered")
            if (
                resource.readiness_timeout_seconds is not None
                and resource.readiness_timeout_seconds <= 0
            ):
                raise ValueError(
                    "managed resource readiness_timeout_seconds must be greater than zero"
                )
            names.add(resource.name)

    async def start(self, app: FastAPI) -> None:
        try:
            for resource in self.resources:
                value = resource.factory(app)
                if inspect.isawaitable(value):
                    value = await value
                self.instances[resource.name] = value
                if resource.healthcheck is not None:
                    check = partial(resource.healthcheck, value)
                    self.readiness.register(
                        ReadinessCheckSpec(
                            name=resource.name,
                            check=check,
                            required=resource.required,
                            timeout_seconds=resource.readiness_timeout_seconds,
                            redact_errors=resource.redact_errors,
                        )
                    )
                    self._healthcheck_names.add(resource.name)
        except BaseException as exc:
            try:
                await self.close()
            except BaseException as close_exc:
                exc.add_note(f"managed resource rollback failed: {close_exc}")
            raise

    async def check_startup(
        self,
        *,
        parallel: bool,
        overall_timeout_seconds: float | None,
    ) -> None:
        required_names = {
            resource.name
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

    def require(self, name: str) -> Any:
        if name not in self.instances:
            raise KeyError(name)
        return self.instances[name]

    async def close(self) -> None:
        failures: list[BaseException] = []
        for resource in reversed(self.resources):
            if resource.name not in self.instances:
                continue
            value = self.instances.pop(resource.name)
            try:
                await self._close_resource(resource, value)
            except BaseException as exc:
                failures.append(exc)
            finally:
                if resource.name in self._healthcheck_names:
                    self.readiness.unregister(resource.name)
                    self._healthcheck_names.discard(resource.name)
        if failures:
            raise BaseExceptionGroup("managed resource shutdown failed", failures)

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
