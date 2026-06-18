from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
import inspect
from typing import Any

from fastapi import FastAPI

from fastapi_core.core.config import EnvConfig, ServiceSettings
from fastapi_core.dependencies.async_milvus import set_async_milvus_client
from fastapi_core.dependencies.auth import set_auth_provider
from fastapi_core.dependencies.database import set_db_engine
from fastapi_core.dependencies.langfuse import set_langfuse_client
from fastapi_core.dependencies.messaging import set_nats_client
from fastapi_core.dependencies.milvus import set_milvus_client
from fastapi_core.dependencies.ollama import set_ollama_client
from fastapi_core.dependencies.storage import set_minio_client
from fastapi_core.docmesh_bridge import (
    REGISTRY_SERVICE_SPECS,
    get_registry_service_spec,
    initialize_docmesh_registry as build_docmesh_registry,
)


@dataclass(slots=True)
class LifecyclePolicy:
    init_keycloak: bool
    init_database: bool
    init_minio: bool
    init_milvus: bool
    init_async_milvus: bool
    init_ollama: bool
    init_langfuse: bool
    init_nats: bool
    use_docmesh_registry: bool


def _resolve_optional(explicit: bool | None, derived: bool) -> bool:
    if explicit is None:
        return derived
    return explicit


def resolve_lifecycle_policy(settings: ServiceSettings) -> LifecyclePolicy:
    lifecycle = settings.lifecycle
    health = settings.health
    return LifecyclePolicy(
        init_keycloak=_resolve_optional(lifecycle.eager_keycloak, health.check_keycloak),
        init_database=_resolve_optional(lifecycle.eager_database, health.check_database),
        init_minio=_resolve_optional(lifecycle.eager_minio, health.check_minio),
        init_milvus=lifecycle.eager_milvus,
        init_async_milvus=lifecycle.eager_async_milvus,
        init_ollama=lifecycle.eager_ollama,
        init_langfuse=_resolve_optional(lifecycle.eager_langfuse, health.check_langfuse),
        init_nats=lifecycle.eager_nats,
        use_docmesh_registry=lifecycle.use_docmesh_registry,
    )


async def initialize_docmesh_registry(app: FastAPI, config: EnvConfig) -> None:
    if getattr(app.state, "docmesh_registry", None) is not None:
        return

    initialized = build_docmesh_registry(config=config)
    if initialized is None:
        raise RuntimeError("docmesh registry is required for supported services")
    docmesh_settings, registry = initialized
    app.state.docmesh_settings = docmesh_settings
    app.state.docmesh_registry = registry


def _unwrap_docmesh_client(client: Any) -> Any:
    wrapped_client = getattr(client, "client", None)
    if wrapped_client is not None:
        return wrapped_client
    return client


def _get_docmesh_registry(app: FastAPI) -> Any | None:
    return getattr(app.state, "docmesh_registry", None)


def _is_registry_service_enabled(policy: LifecyclePolicy, state_key: str) -> bool:
    return {
        "auth_provider": policy.init_keycloak,
        "db_engine": policy.init_database,
        "minio_client": policy.init_minio,
        "milvus_client": policy.init_milvus,
        "ollama_client": policy.init_ollama,
        "langfuse_client": policy.init_langfuse,
        "nats_client": policy.init_nats,
    }.get(state_key, False)


def _set_registry_managed_service(app: FastAPI, state_key: str, client: Any) -> None:
    if state_key == "auth_provider":
        set_auth_provider(app, provider=client)
        return
    if state_key == "db_engine":
        set_db_engine(app, engine=client)
        return
    if state_key == "minio_client":
        set_minio_client(app, client=client)
        return
    if state_key == "milvus_client":
        set_milvus_client(app, client=client)
        return
    if state_key == "ollama_client":
        set_ollama_client(app, client=client)
        return
    if state_key == "langfuse_client":
        set_langfuse_client(app, client=client)
        return
    raise KeyError(f"Unsupported registry-managed state key: {state_key}")


async def _resolve_registry_service(registry: Any, state_key: str) -> Any:
    spec = get_registry_service_spec(state_key)
    if spec is None:
        raise KeyError(f"Unsupported registry-managed state key: {state_key}")

    service = registry.create_client(spec.registry_name)
    if spec.mode == "async_builder":
        connect = getattr(service, "connect", None)
        if callable(connect):
            return await connect()
    return _unwrap_docmesh_client(service)


async def _initialize_docmesh_managed_services(
    app: FastAPI,
    policy: LifecyclePolicy,
) -> None:
    registry = _get_docmesh_registry(app)
    if registry is None:
        return

    managed_services: set[str] = set()

    for state_key, spec in REGISTRY_SERVICE_SPECS.items():
        if not _is_registry_service_enabled(policy, state_key):
            continue

        client = await _resolve_registry_service(registry, state_key)
        if spec.mode == "async_builder":
            await set_nats_client(app, client=client)
        else:
            _set_registry_managed_service(app, state_key, client)
        managed_services.add(state_key)

    app.state.docmesh_managed_services = managed_services


async def initialize_app_services(
    app: FastAPI,
    config: EnvConfig,
    settings: ServiceSettings | None = None,
    *,
    init_auth: bool | None = None,
    init_database: bool | None = None,
    init_minio: bool | None = None,
    init_milvus: bool | None = None,
    init_async_milvus: bool | None = None,
    init_ollama: bool | None = None,
    init_langfuse: bool | None = None,
    init_nats: bool | None = None,
    use_docmesh_registry: bool | None = None,
) -> None:
    if settings is None:
        settings = ServiceSettings()

    policy = resolve_lifecycle_policy(settings)
    if init_auth is not None:
        policy.init_keycloak = init_auth
    if init_database is not None:
        policy.init_database = init_database
    if init_minio is not None:
        policy.init_minio = init_minio
    if init_milvus is not None:
        policy.init_milvus = init_milvus
    if init_async_milvus is not None:
        policy.init_async_milvus = init_async_milvus
    if init_ollama is not None:
        policy.init_ollama = init_ollama
    if init_langfuse is not None:
        policy.init_langfuse = init_langfuse
    if init_nats is not None:
        policy.init_nats = init_nats
    if use_docmesh_registry is not None:
        policy.use_docmesh_registry = use_docmesh_registry

    requires_registry_services = any(
        _is_registry_service_enabled(policy, state_key)
        for state_key in REGISTRY_SERVICE_SPECS
    )
    should_initialize_registry = policy.use_docmesh_registry or requires_registry_services

    if should_initialize_registry:
        await initialize_docmesh_registry(app, config)
        await _initialize_docmesh_managed_services(app, policy)

    if policy.init_async_milvus:
        await set_async_milvus_client(app, config=config)


async def _call_maybe_async(method: Callable[[], Any]) -> None:
    result = method()
    if inspect.isawaitable(result):
        await result


async def shutdown_app_services(app: FastAPI) -> None:
    docmesh_managed_services: set[str] = getattr(app.state, "docmesh_managed_services", set())

    for state_key, method_name in (
        ("docmesh_registry", "close_all"),
        ("nats_client", "drain"),
        ("async_milvus_client", "close"),
        ("milvus_client", "close"),
        ("db_engine", "dispose"),
        ("langfuse_client", "flush"),
    ):
        if state_key in docmesh_managed_services:
            continue
        resource = getattr(app.state, state_key, None)
        if resource is None:
            continue
        method = getattr(resource, method_name, None)
        if method is None:
            continue
        await _call_maybe_async(method)


def create_managed_lifespan(
    config: EnvConfig,
    settings: ServiceSettings,
) -> Callable[[FastAPI], AsyncIterator[None]]:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        await initialize_app_services(app, config, settings)
        try:
            yield
        finally:
            await shutdown_app_services(app)

    return lifespan
