from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar, cast

from docmesh_py_core.function_logging import log_function_boundary
from fastapi import HTTPException, Request, status

T = TypeVar("T")


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
