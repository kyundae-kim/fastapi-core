from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
import inspect
from typing import Any

from fastapi import FastAPI

from fastapi_core.bootstrap import set_state_value
from fastapi_core.core.config import EnvConfig, ServiceSettings
from fastapi_core.core.langfuse import get_langfuse_client
from fastapi_core.dependencies.async_milvus import set_async_milvus_client
from fastapi_core.dependencies.auth import set_auth_provider
from fastapi_core.dependencies.database import set_db_engine
from fastapi_core.dependencies.messaging import set_nats_client
from fastapi_core.dependencies.milvus import set_milvus_client
from fastapi_core.dependencies.ollama import set_ollama_client
from fastapi_core.dependencies.storage import set_minio_client
from fastapi_core.docmesh_bridge import initialize_docmesh_registry as build_docmesh_registry


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
    initialized = build_docmesh_registry(config=config)
    if initialized is None:
        return
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


async def _initialize_docmesh_managed_services(
    app: FastAPI,
    policy: LifecyclePolicy,
) -> None:
    registry = _get_docmesh_registry(app)
    if registry is None:
        return

    managed_services: set[str] = set()

    if policy.init_keycloak:
        provider = _unwrap_docmesh_client(registry.create_client("keycloak"))
        set_auth_provider(app, provider=provider)
        managed_services.add("auth_provider")
    if policy.init_database:
        engine = _unwrap_docmesh_client(registry.create_client("postgres"))
        set_db_engine(app, engine=engine)
        managed_services.add("db_engine")
    if policy.init_minio:
        minio_client = _unwrap_docmesh_client(registry.create_client("minio"))
        set_minio_client(app, client=minio_client)
        managed_services.add("minio_client")
    if policy.init_milvus:
        milvus_client = _unwrap_docmesh_client(registry.create_client("milvus"))
        set_milvus_client(app, client=milvus_client)
        managed_services.add("milvus_client")
    if policy.init_ollama:
        ollama_client = _unwrap_docmesh_client(registry.create_client("ollama"))
        set_ollama_client(app, client=ollama_client)
        managed_services.add("ollama_client")
    if policy.init_langfuse:
        langfuse_client = _unwrap_docmesh_client(registry.create_client("langfuse"))
        set_state_value(app, "langfuse_client", langfuse_client)
        managed_services.add("langfuse_client")
    if policy.init_nats:
        nats_builder = registry.create_client("nats")
        connect = getattr(nats_builder, "connect", None)
        nats_client = await connect() if callable(connect) else _unwrap_docmesh_client(nats_builder)
        await set_nats_client(app, client=nats_client)
        managed_services.add("nats_client")

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

    if policy.use_docmesh_registry:
        await initialize_docmesh_registry(app, config)
        await _initialize_docmesh_managed_services(app, policy)

    registry = _get_docmesh_registry(app)
    use_docmesh_registry_clients = policy.use_docmesh_registry and registry is not None

    if policy.init_keycloak and not use_docmesh_registry_clients:
        set_auth_provider(app, config=config)
    if policy.init_database and not use_docmesh_registry_clients:
        set_db_engine(app, config=config)
    if policy.init_minio and not use_docmesh_registry_clients:
        set_minio_client(app, config=config)
    if policy.init_milvus and not use_docmesh_registry_clients:
        set_milvus_client(app, config=config)
    if policy.init_async_milvus:
        await set_async_milvus_client(app, config=config)
    if policy.init_ollama and not use_docmesh_registry_clients:
        set_ollama_client(app, config=config)
    if policy.init_langfuse and not use_docmesh_registry_clients:
        set_state_value(app, "langfuse_client", get_langfuse_client(config.langfuse))
    if policy.init_nats and not use_docmesh_registry_clients:
        await set_nats_client(app, config=config)


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
