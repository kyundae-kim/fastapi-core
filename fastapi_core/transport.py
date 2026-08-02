from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from fastapi.params import Depends

from fastapi_core.function_logging import log_function_boundary

_DEFAULT_COMMON_ERROR_STATUSES = (400, 401, 403, 404, 409, 422, 500, 502, 503)
_CONTRACT_FIELDS = (
    "validation_status",
    "validation_response_model",
    "common_error_response_model",
    "fallback_response_model",
    "common_error_statuses",
    "include_synthetic_422",
    "responses",
    "error_renderer",
)


@dataclass(frozen=True, slots=True)
class TransportPolicy:
    """Shared route policy used for runtime errors and generated OpenAPI."""

    dependencies: Sequence[Depends] = ()
    validation_status: int | None = None
    validation_response_model: Any | None = None
    common_error_response_model: Any | None = None
    fallback_response_model: Any | None = None
    common_error_statuses: Sequence[int] = ()
    include_synthetic_422: bool | None = None
    responses: Mapping[int, Mapping[str, Any]] = field(default_factory=dict)
    error_renderer: Any | None = None

    @log_function_boundary()
    def __post_init__(self) -> None:
        if self.validation_status is not None and not 400 <= self.validation_status <= 599:
            raise ValueError("transport policy validation_status must be between 400 and 599")
        statuses = tuple(self.common_error_statuses)
        if any(not 400 <= status <= 599 for status in statuses):
            raise ValueError("transport policy common error statuses must be HTTP error codes")
        object.__setattr__(self, "dependencies", tuple(self.dependencies))
        object.__setattr__(self, "common_error_statuses", statuses)
        object.__setattr__(self, "responses", MappingProxyType(dict(self.responses)))

    @property
    @log_function_boundary()
    def effective_validation_status(self) -> int:
        return self.validation_status or 422

    @property
    @log_function_boundary()
    def effective_include_synthetic_422(self) -> bool:
        if self.include_synthetic_422 is not None:
            return self.include_synthetic_422
        return self.effective_validation_status == 422

    @property
    @log_function_boundary()
    def effective_common_error_statuses(self) -> tuple[int, ...]:
        return self.common_error_statuses or _DEFAULT_COMMON_ERROR_STATUSES

    @log_function_boundary()
    def response_definitions(self) -> dict[int, dict[str, Any]]:
        responses = {status: dict(value) for status, value in self.responses.items()}
        validation = {"description": "Request validation error"}
        if self.validation_response_model is not None:
            validation["model"] = self.validation_response_model
        responses.setdefault(self.effective_validation_status, validation)
        if self.common_error_response_model is not None:
            for status in self.effective_common_error_statuses:
                responses.setdefault(
                    status,
                    {
                        "description": "Common error response",
                        "model": self.common_error_response_model,
                    },
                )
        if self.fallback_response_model is not None:
            responses.setdefault(
                500,
                {
                    "description": "Fallback error response",
                    "model": self.fallback_response_model,
                },
            )
        return responses

    @classmethod
    @log_function_boundary()
    def resolve(
        cls,
        base: TransportPolicy | None,
        override: TransportPolicy | None,
    ) -> TransportPolicy:
        base = base or cls()
        override = override or cls()
        values: dict[str, Any] = {}
        for name in _CONTRACT_FIELDS:
            override_value = getattr(override, name)
            base_value = getattr(base, name)
            if name == "responses":
                merged = dict(base_value)
                merged.update(override_value)
                values[name] = merged
            elif override_value is not None and override_value != ():
                values[name] = override_value
            else:
                values[name] = base_value
        values["dependencies"] = tuple(base.dependencies) + tuple(override.dependencies)
        return cls(**values)

    @classmethod
    @log_function_boundary()
    def validate_module_conflicts(cls, policies: Sequence[TransportPolicy]) -> None:
        for field_name in _CONTRACT_FIELDS:
            values: list[Any] = []
            for policy in policies:
                value = getattr(policy, field_name)
                if field_name == "responses":
                    value = tuple(sorted(value.items(), key=lambda item: item[0]))
                if value is None or value == () or value == {}:
                    continue
                if not any(value == existing for existing in values):
                    values.append(value)
            if len(values) > 1:
                raise ValueError(f"transport policy field '{field_name}' conflicts across modules")


__all__ = ["TransportPolicy"]
