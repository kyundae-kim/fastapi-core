from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from functools import partial
from typing import Any, Generic, TypeVar, cast

from docmesh_py_core.function_logging import log_function_boundary
from fastapi import FastAPI, HTTPException, Request, status

from fastapi_core.readiness import ReadinessCheckSpec, ReadinessRegistry

T = TypeVar("T")

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


@dataclass(frozen=True, slots=True)
class ResourceKey(Generic[T]):
    name: str

    @log_function_boundary()
    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("resource key name must not be empty")

    @log_function_boundary()
    def dependency(self, request: Request) -> T:
        registry = getattr(request.app.state, "resource_registry", None)
        if registry is None:
            raise self._not_available()
        try:
            return cast(T, registry.require(self.name))
        except KeyError as exc:
            raise self._not_available() from exc

    @log_function_boundary()
    def _not_available(self) -> HTTPException:
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Managed resource '{self.name}' is not available",
        )


@dataclass(frozen=True)
class ManagedResource(Generic[T]):
    name: str | ResourceKey[T]
    factory: Callable[[FastAPI], T | Awaitable[T]]
    healthcheck: Callable[[T], object | Awaitable[object]] | None = None
    close: Callable[[T], None | Awaitable[None]] | None = None
    required: bool = True
    readiness_timeout_seconds: float | None = None
    redact_errors: bool = True


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


__all__ = ["ManagedResource", "ResourceKey", "ResourceRegistry"]
