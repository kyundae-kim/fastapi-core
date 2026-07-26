from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter
from fastapi.params import Depends

from fastapi_core.function_logging import log_function_boundary
from fastapi_core.http import ErrorMapper
from fastapi_core.readiness import ReadinessCheckSpec
from fastapi_core.resources import ManagedResource


@dataclass(frozen=True, slots=True)
class ErrorMapperSpec:
    exception_type: type[Exception]
    mapper: ErrorMapper


@dataclass(frozen=True, slots=True)
class DomainModule:
    name: str
    routers: Sequence[APIRouter] = ()
    dependencies: Sequence[Depends] = ()
    resources: Sequence[ManagedResource[Any]] = ()
    readiness_checks: Sequence[ReadinessCheckSpec] = ()
    error_mappers: Sequence[ErrorMapperSpec] = ()

    @log_function_boundary()
    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("domain module name must not be empty")


__all__ = ["DomainModule", "ErrorMapperSpec"]
