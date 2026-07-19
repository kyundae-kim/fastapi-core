from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

from fastapi_core.function_logging import log_function_boundary
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
ClientT = TypeVar("ClientT")


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
    wrapper = _resolve_wrapped_service_client(request, "keycloak")
    return cast(KeycloakAuthService, wrapper.client)


@log_function_boundary()
def get_postgres_engine(request: Request) -> Engine:
    wrapper = _resolve_wrapped_service_client(request, "postgres")
    return cast(Engine, wrapper.client)


@log_function_boundary()
def get_sqlite_engine(request: Request) -> Engine:
    wrapper = _resolve_wrapped_service_client(request, "sqlite")
    return cast(Engine, wrapper.client)


@log_function_boundary()
def get_minio_client(request: Request) -> Minio:
    wrapper = _resolve_wrapped_service_client(request, "minio")
    return cast(Minio, wrapper.client)


@log_function_boundary()
def get_milvus_client(request: Request) -> MilvusClient:
    wrapper = _resolve_wrapped_service_client(request, "milvus")
    return cast(MilvusClient, wrapper.client)


@log_function_boundary()
def get_ollama_client(request: Request) -> OllamaClient:
    wrapper = _resolve_wrapped_service_client(request, "ollama")
    return cast(OllamaClient, wrapper.client)


@log_function_boundary()
def get_langfuse_client(request: Request) -> Langfuse:
    wrapper = _resolve_wrapped_service_client(request, "langfuse")
    return cast(Langfuse, wrapper.client)


@log_function_boundary()
def get_nats_connection_builder(request: Request) -> NatsConnectionBuilder:
    client = _resolve_service_client(request, "nats")
    if not isinstance(client, NatsConnectionBuilder):
        raise _service_type_mismatch("nats", "NatsConnectionBuilder")
    return client
