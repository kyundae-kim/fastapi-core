from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

from docmesh_py_core import KeycloakAuthService, NatsConnectionBuilder, ServiceClientWrapper
from fastapi import HTTPException, Request, status
from langfuse import Langfuse
from minio import Minio
from ollama import Client as OllamaClient
from pymilvus import MilvusClient
from sqlalchemy.engine import Engine


ServiceClientDependency = Callable[[Request], Any]
ResourceDependency = Callable[[Request], Any]


def _service_not_enabled(service_name: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=f"Service client '{service_name}' is not enabled",
    )


def _service_type_mismatch(service_name: str, expected_type: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Service client '{service_name}' is not a {expected_type}",
    )


def _resolve_service_client(request: Request, service_name: str) -> ServiceClientWrapper | NatsConnectionBuilder:
    service_clients = getattr(request.app.state, "service_clients", None)
    if service_clients is None or service_name not in service_clients:
        raise _service_not_enabled(service_name)
    return service_clients[service_name]


def _resolve_wrapped_service_client(request: Request, service_name: str) -> ServiceClientWrapper:
    client = _resolve_service_client(request, service_name)
    if not isinstance(client, ServiceClientWrapper):
        raise _service_type_mismatch(service_name, "wrapped service client")
    return client


def get_service_client(service_name: str) -> ServiceClientDependency:
    def dependency(request: Request) -> ServiceClientWrapper | NatsConnectionBuilder:
        return _resolve_service_client(request, service_name)

    return dependency


def get_resource(name: str) -> ResourceDependency:
    def dependency(request: Request) -> Any:
        registry = getattr(request.app.state, "resource_registry", None)
        if registry is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Managed resource '{name}' is not available",
            )
        try:
            return registry.require(name)
        except KeyError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Managed resource '{name}' is not available",
            ) from exc

    return dependency


def get_keycloak_auth_service(request: Request) -> KeycloakAuthService:
    wrapper = _resolve_wrapped_service_client(request, "keycloak")
    return cast(KeycloakAuthService, wrapper.client)


def get_postgres_engine(request: Request) -> Engine:
    wrapper = _resolve_wrapped_service_client(request, "postgres")
    return cast(Engine, wrapper.client)


def get_sqlite_engine(request: Request) -> Engine:
    wrapper = _resolve_wrapped_service_client(request, "sqlite")
    return cast(Engine, wrapper.client)


def get_minio_client(request: Request) -> Minio:
    wrapper = _resolve_wrapped_service_client(request, "minio")
    return cast(Minio, wrapper.client)


def get_milvus_client(request: Request) -> MilvusClient:
    wrapper = _resolve_wrapped_service_client(request, "milvus")
    return cast(MilvusClient, wrapper.client)


def get_ollama_client(request: Request) -> OllamaClient:
    wrapper = _resolve_wrapped_service_client(request, "ollama")
    return cast(OllamaClient, wrapper.client)


def get_langfuse_client(request: Request) -> Langfuse:
    wrapper = _resolve_wrapped_service_client(request, "langfuse")
    return cast(Langfuse, wrapper.client)


def get_nats_connection_builder(request: Request) -> NatsConnectionBuilder:
    client = _resolve_service_client(request, "nats")
    if not isinstance(client, NatsConnectionBuilder):
        raise _service_type_mismatch("nats", "NatsConnectionBuilder")
    return client
