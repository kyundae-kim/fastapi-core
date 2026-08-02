from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from fastapi import APIRouter
from fastapi.params import Depends

from fastapi_core.function_logging import log_function_boundary
from fastapi_core.http import ErrorMapper
from fastapi_core.readiness import ReadinessCheckSpec
from fastapi_core.resources import ManagedResource, ResourceBinding
from fastapi_core.transport import TransportPolicy


@dataclass(frozen=True, slots=True)
class ErrorMapperSpec:
    exception_type: type[Exception]
    mapper: ErrorMapper


@runtime_checkable
class DomainModuleProvider(Protocol):
    @log_function_boundary()
    def __call__(self, *args: Any, **kwargs: Any) -> DomainModule: ...


@dataclass(frozen=True, slots=True)
class DomainModule:
    name: str
    routers: Sequence[APIRouter] = ()
    dependencies: Sequence[Depends] = ()
    resources: Sequence[ManagedResource[Any] | ResourceBinding[Any]] = ()
    readiness_checks: Sequence[ReadinessCheckSpec] = ()
    error_mappers: Sequence[ErrorMapperSpec] = ()
    transport_policy: TransportPolicy | None = None

    @log_function_boundary()
    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("domain module name must not be empty")


__all__ = ["DomainModule", "DomainModuleProvider", "ErrorMapperSpec"]
