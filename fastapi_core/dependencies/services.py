from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

from docmesh_py_core.function_logging import log_function_boundary
from docmesh_py_core import (
    KeycloakAuthService,
    NatsConnectionBuilder,
    ServiceClientWrapper,
    ServiceRuntime,
)
from fastapi import HTTPException, Request, status
from langfuse import Langfuse
from minio import Minio
from ollama import Client as OllamaClient
from pymilvus import MilvusClient
from sqlalchemy.engine import Engine

from fastapi_core.resources import ResourceKey


ServiceClientDependency = Callable[[Request], Any]
ResourceDependency = Callable[[Request], Any]


@log_function_boundary()
def _service_not_enabled(service_name: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=f"Service client '{service_name}' is not enabled",
    )


@log_function_boundary()
def _service_type_mismatch(service_name: str, expected_type: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Service client '{service_name}' is not a {expected_type}",
    )


@log_function_boundary()
def _resolve_service_client(request: Request, service_name: str) -> ServiceClientWrapper | NatsConnectionBuilder:
    client = get_service_runtime(request).get(service_name)
    if client is None:
        raise _service_not_enabled(service_name)
    return client


@log_function_boundary()
def _resolve_wrapped_service_client(request: Request, service_name: str) -> ServiceClientWrapper:
    client = _resolve_service_client(request, service_name)
    if not isinstance(client, ServiceClientWrapper):
        raise _service_type_mismatch(service_name, "wrapped service client")
    return client


@log_function_boundary()
def _unwrap_service_client(request: Request, service_name: str) -> Any:
    return _resolve_wrapped_service_client(request, service_name).client


@log_function_boundary()
def get_service_client(service_name: str) -> ServiceClientDependency:
    @log_function_boundary()
    def dependency(request: Request) -> ServiceClientWrapper | NatsConnectionBuilder:
        return _resolve_service_client(request, service_name)

    return dependency


@log_function_boundary()
def get_service_runtime(request: Request) -> ServiceRuntime:
    runtime = getattr(request.app.state, "service_runtime", None)
    if runtime is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service runtime is not available",
        )
    return runtime


@log_function_boundary()
def get_resource(name: str) -> ResourceDependency:
    return ResourceKey[Any](name).dependency


@log_function_boundary()
def get_keycloak_auth_service(request: Request) -> KeycloakAuthService:
    return cast(KeycloakAuthService, _unwrap_service_client(request, "keycloak"))


@log_function_boundary()
def get_postgres_engine(request: Request) -> Engine:
    return cast(Engine, _unwrap_service_client(request, "postgres"))


@log_function_boundary()
def get_sqlite_engine(request: Request) -> Engine:
    return cast(Engine, _unwrap_service_client(request, "sqlite"))


@log_function_boundary()
def get_minio_client(request: Request) -> Minio:
    return cast(Minio, _unwrap_service_client(request, "minio"))


@log_function_boundary()
def get_milvus_client(request: Request) -> MilvusClient:
    return cast(MilvusClient, _unwrap_service_client(request, "milvus"))


@log_function_boundary()
def get_ollama_client(request: Request) -> OllamaClient:
    return cast(OllamaClient, _unwrap_service_client(request, "ollama"))


@log_function_boundary()
def get_langfuse_client(request: Request) -> Langfuse:
    return cast(Langfuse, _unwrap_service_client(request, "langfuse"))


@log_function_boundary()
def get_nats_connection_builder(request: Request) -> NatsConnectionBuilder:
    client = _resolve_service_client(request, "nats")
    if not isinstance(client, NatsConnectionBuilder):
        raise _service_type_mismatch("nats", "NatsConnectionBuilder")
    return client
