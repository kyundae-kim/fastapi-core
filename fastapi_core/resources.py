from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from functools import partial
from typing import Any, Generic, TypeVar, cast

from fastapi_core.function_logging import log_function_boundary
from fastapi import FastAPI, HTTPException, Request, status

from fastapi_core.invocation import invoke_resource
from fastapi_core.readiness import (
    HealthResultAdapter,
    ReadinessCheckSpec,
    ReadinessRegistry,
)

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
    health_result_adapter: HealthResultAdapter | None = None

    @log_function_boundary()
    def bind(self) -> ResourceBinding[T]:
        if isinstance(self.name, str) and not self.name.strip():
            raise ValueError("resource name must not be empty")
        return ResourceBinding(
            self.name,
            factory=self.factory,
            healthcheck=self.healthcheck,
            close=self.close,
            required=self.required,
            readiness_timeout_seconds=self.readiness_timeout_seconds,
            redact_errors=self.redact_errors,
            health_result_adapter=self.health_result_adapter,
        )


@dataclass(frozen=True)
class ResourceBinding(Generic[T]):
    """Typed resource descriptor shared by registration and dependencies."""

    key: ResourceKey[T] | str
    factory: Callable[[FastAPI], T | Awaitable[T]]
    healthcheck: Callable[[T], object | Awaitable[object]] | None = None
    close: Callable[[T], None | Awaitable[None]] | None = None
    required: bool = True
    readiness_timeout_seconds: float | None = None
    redact_errors: bool = True
    health_result_adapter: HealthResultAdapter | None = None

    @log_function_boundary()
    def __post_init__(self) -> None:
        key = self.key if isinstance(self.key, ResourceKey) else ResourceKey[T](self.key)
        object.__setattr__(self, "key", key)

    @property
    @log_function_boundary()
    def name(self) -> str:
        return self.key.name

    @property
    @log_function_boundary()
    def managed_resource(self) -> ManagedResource[T]:
        return ManagedResource(
            name=self.key,
            factory=self.factory,
            healthcheck=self.healthcheck,
            close=self.close,
            required=self.required,
            readiness_timeout_seconds=self.readiness_timeout_seconds,
            redact_errors=self.redact_errors,
            health_result_adapter=self.health_result_adapter,
        )

    @log_function_boundary()
    def dependency(self, request: Request) -> T:
        return self.key.dependency(request)

    @log_function_boundary()
    async def call(
        self,
        method: Callable[..., Any] | str,
        *args: Any,
        instance: T | None = None,
        timeout_seconds: float | None = None,
        **kwargs: Any,
    ) -> Any:
        if isinstance(method, str):
            if instance is None:
                raise ValueError("resource method name requires a typed instance")
            method = cast(Callable[..., Any], getattr(instance, method))
        return await invoke_resource(
            method,
            *args,
            timeout_seconds=timeout_seconds,
            **kwargs,
        )


class ResourceRegistry:
    @log_function_boundary()
    def __init__(
        self,
        resources: Sequence[ManagedResource[Any] | ResourceBinding[Any]],
        readiness: ReadinessRegistry,
        *,
        reserved_names: set[str] | frozenset[str] = _RESERVED_RESOURCE_NAMES,
    ) -> None:
        self.bindings = tuple(
            resource if isinstance(resource, ResourceBinding) else resource.bind()
            for resource in resources
        )
        self.resources = tuple(binding.managed_resource for binding in self.bindings)
        self.readiness = readiness
        self.instances: dict[str, Any] = {}
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
                value = await invoke_resource(resource.factory, app)
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
                            health_result_adapter=resource.health_result_adapter,
                        )
                    )
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
    def require(self, name: str | ResourceKey[Any] | ResourceBinding[Any]) -> Any:
        return self.instances[self._name(name)]

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
                spec = self.readiness.specs.get(name)
                if (
                    spec is not None
                    and isinstance(spec.check, partial)
                    and spec.check.func is resource.healthcheck
                    and len(spec.check.args) == 1
                    and spec.check.args[0] is value
                ):
                    self.readiness.unregister(name)
        if failures:
            raise BaseExceptionGroup("managed resource shutdown failed", failures)

    @log_function_boundary()
    async def _close_resource(
        self,
        resource: ManagedResource[Any],
        value: Any,
    ) -> None:
        if resource.close is not None:
            await invoke_resource(resource.close, value)
            return
        elif callable(getattr(value, "aclose", None)):
            await invoke_resource(value.aclose)
            return
        elif callable(getattr(value, "close", None)):
            await invoke_resource(value.close)
            return
        else:
            return


__all__ = ["ManagedResource", "ResourceBinding", "ResourceKey", "ResourceRegistry"]
