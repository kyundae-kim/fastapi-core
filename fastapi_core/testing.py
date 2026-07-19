from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

from fastapi_core.function_logging import log_function_boundary
from fastapi_core.resources import ManagedResource
from fastapi_core.runtime import create_empty_runtime

T = TypeVar("T")


@dataclass
class ResourceLifecycleProbe(Generic[T]):
    """Build a managed resource that records create, check, and close events."""

    value: T
    health_result: object = True
    events: list[str] = field(default_factory=list)

    @log_function_boundary()
    def managed_resource(
        self,
        name: str,
        *,
        required: bool = True,
        readiness_timeout_seconds: float | None = None,
    ) -> ManagedResource[T]:
        @log_function_boundary()
        async def factory(_app: Any) -> T:
            self.events.append(f"create:{name}")
            return self.value

        @log_function_boundary()
        async def healthcheck(value: T) -> object:
            if value is not self.value:
                raise AssertionError(
                    "managed resource probe received an unexpected value"
                )
            self.events.append(f"check:{name}")
            return self.health_result

        @log_function_boundary()
        async def close(value: T) -> None:
            if value is not self.value:
                raise AssertionError(
                    "managed resource probe received an unexpected value"
                )
            self.events.append(f"close:{name}")

        return ManagedResource(
            name=name,
            factory=factory,
            healthcheck=healthcheck,
            close=close,
            required=required,
            readiness_timeout_seconds=readiness_timeout_seconds,
        )


@log_function_boundary()
def assert_health_contract(client: Any) -> None:
    """Assert the built-in liveness and readiness success contract."""
    liveness = client.get("/health/liveness")
    readiness = client.get("/health/readiness")
    assert liveness.status_code == 200
    assert liveness.json()["status"] == "ok"
    assert readiness.status_code == 200
    assert readiness.json()["status"] == "ok"


@log_function_boundary()
def assert_auth_router_contract(client: Any, *, included: bool) -> None:
    """Assert whether the built-in authentication routes are installed."""
    user = client.get("/user")
    token = client.post("/token")
    if included:
        assert user.status_code != 404
        assert token.status_code != 404
    else:
        assert user.status_code == 404
        assert token.status_code == 404


__all__ = [
    "ResourceLifecycleProbe",
    "assert_auth_router_contract",
    "assert_health_contract",
    "create_empty_runtime",
]
