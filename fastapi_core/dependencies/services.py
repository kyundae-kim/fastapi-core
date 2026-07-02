from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import HTTPException, Request, status


ServiceClientDependency = Callable[[Request], Any]


def get_service_client(service_name: str) -> ServiceClientDependency:
    def dependency(request: Request) -> Any:
        service_clients = getattr(request.app.state, "service_clients", None)
        if service_clients is None or service_name not in service_clients:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Service client '{service_name}' is not enabled",
            )
        return service_clients[service_name]

    return dependency
