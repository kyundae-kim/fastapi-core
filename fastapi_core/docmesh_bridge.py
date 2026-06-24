from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import importlib
import os
from typing import TYPE_CHECKING, Any, Literal

from fastapi import FastAPI

if TYPE_CHECKING:
    from fastapi_core.core.config import EnvConfig, MilvusConfig


DOCMESH_MODULE_NAME = "docmesh_py_core"


@dataclass(frozen=True, slots=True)
class RegistryServiceSpec:
    registry_name: str
    state_key: str
    mode: Literal["sync", "async_builder"]


REGISTRY_SERVICE_SPECS: dict[str, RegistryServiceSpec] = {
    "auth_provider": RegistryServiceSpec(
        registry_name="keycloak",
        state_key="auth_provider",
        mode="sync",
    ),
    "db_engine": RegistryServiceSpec(
        registry_name="postgres",
        state_key="db_engine",
        mode="sync",
    ),
    "minio_client": RegistryServiceSpec(
        registry_name="minio",
        state_key="minio_client",
        mode="sync",
    ),
    "milvus_client": RegistryServiceSpec(
        registry_name="milvus",
        state_key="milvus_client",
        mode="sync",
    ),
    "ollama_client": RegistryServiceSpec(
        registry_name="ollama",
        state_key="ollama_client",
        mode="sync",
    ),
    "langfuse_client": RegistryServiceSpec(
        registry_name="langfuse",
        state_key="langfuse_client",
        mode="sync",
    ),
    "nats_client": RegistryServiceSpec(
        registry_name="nats",
        state_key="nats_client",
        mode="async_builder",
    ),
}


def get_registry_service_spec(state_key: str) -> RegistryServiceSpec | None:
    return REGISTRY_SERVICE_SPECS.get(state_key)


def _load_docmesh_module() -> Any:
    return importlib.import_module(DOCMESH_MODULE_NAME)


def is_docmesh_available() -> bool:
    try:
        _load_docmesh_module()
    except ImportError:
        return False
    return True


def _bool_string(value: bool) -> str:
    return "true" if value else "false"


def _docmesh_env_name(env: str) -> str:
    return {
        "dev": "development",
        "stage": "stage",
        "prod": "production",
    }.get(env, env)


def build_docmesh_keycloak_config(config: EnvConfig) -> Any:
    docmesh_config_module = importlib.import_module(f"{DOCMESH_MODULE_NAME}.config")
    docmesh_keycloak_config = getattr(docmesh_config_module, "KeycloakConfig")
    return docmesh_keycloak_config(
        url=str(config.keycloak.http_url),
        realm=config.keycloak.realm,
        client_id=config.keycloak.client_id,
        client_secret=config.keycloak.client_secret,
        verify_ssl=str(config.keycloak.http_url).startswith("https://"),
        client_public=config.keycloak.client_secret is None,
    )


def build_docmesh_env(config: EnvConfig) -> dict[str, str]:
    keycloak_config = build_docmesh_keycloak_config(config)
    env: dict[str, str] = {
        "DOCMESH_ENV": _docmesh_env_name(config.env.value),
        "DOCMESH_HEALTHCHECK_ENABLED": "true",
        "KEYCLOAK_URL": keycloak_config.url,
        "KEYCLOAK_REALM": keycloak_config.realm,
        "KEYCLOAK_CLIENT_ID": keycloak_config.client_id,
        "KEYCLOAK_VERIFY_SSL": _bool_string(keycloak_config.verify_ssl),
        "POSTGRES_DSN": config.db.sqlalchemy_database_url,
        "MINIO_ENDPOINT": config.minio.endpoint,
        "MINIO_ACCESS_KEY": config.minio.access_key,
        "MINIO_SECRET_KEY": config.minio.secret_key,
        "MINIO_SECURE": _bool_string(config.minio.secure),
        "MINIO_BUCKET": config.minio.bucket,
        "MILVUS_URI": config.milvus.uri,
        "MILVUS_DB_NAME": config.milvus.db_name or "default",
        "MILVUS_SECURE": _bool_string(config.milvus.uri.startswith("https://")),
        "OLLAMA_HOST": config.ollama.host,
        "OLLAMA_GENERATION_MODEL": config.ollama.model,
        "OLLAMA_REQUEST_TIMEOUT_SECONDS": str(int(config.ollama.timeout)),
        "NATS_SERVERS": config.nats.servers,
        "NATS_NAME": config.nats.name,
        "NATS_CONNECT_TIMEOUT_SECONDS": str(config.nats.connect_timeout),
        "NATS_MAX_RECONNECT_ATTEMPTS": str(config.nats.max_reconnect_attempts),
    }

    if keycloak_config.client_secret:
        env["KEYCLOAK_CLIENT_SECRET"] = keycloak_config.client_secret
    else:
        env["KEYCLOAK_CLIENT_PUBLIC"] = "true"

    langfuse_enabled = bool(
        config.langfuse.tracing_enabled
        and config.langfuse.public_key
        and config.langfuse.secret_key
    )
    env["LANGFUSE_ENABLED"] = _bool_string(langfuse_enabled)
    if langfuse_enabled:
        env["LANGFUSE_HOST"] = config.langfuse.host
        env["LANGFUSE_PUBLIC_KEY"] = config.langfuse.public_key or ""
        env["LANGFUSE_SECRET_KEY"] = config.langfuse.secret_key or ""
        env["LANGFUSE_REQUEST_TIMEOUT_SECONDS"] = str(config.langfuse.timeout)
        if config.langfuse.environment:
            env["LANGFUSE_ENVIRONMENT"] = config.langfuse.environment
        if config.langfuse.release:
            env["LANGFUSE_RELEASE"] = config.langfuse.release

    return env


def load_docmesh_settings(config: EnvConfig | None = None) -> Any:
    initialized = initialize_docmesh_registry(config=config)
    if initialized is None:
        raise RuntimeError("docmesh registry is unavailable")
    settings, _ = initialized
    return settings


def _adapt_docmesh_milvus_config(docmesh_milvus: Any) -> MilvusConfig:
    from fastapi_core.core.config import MilvusConfig

    fallback = MilvusConfig()
    return MilvusConfig(
        uri=str(getattr(docmesh_milvus, "uri", fallback.uri)),
        db_name=str(getattr(docmesh_milvus, "db_name", fallback.db_name)),
        token=(getattr(docmesh_milvus, "token", fallback.token) or ""),
        timeout=getattr(docmesh_milvus, "request_timeout_seconds", None),
    )


def resolve_milvus_config(
    config: EnvConfig,
    *,
    docmesh_settings: Any | None = None,
) -> MilvusConfig:
    resolved_docmesh_settings = docmesh_settings
    if resolved_docmesh_settings is not None:
        docmesh_milvus = getattr(resolved_docmesh_settings, "milvus", None)
        if docmesh_milvus is not None:
            return _adapt_docmesh_milvus_config(docmesh_milvus)
    return config.milvus


def unwrap_docmesh_client(client: Any) -> Any:
    wrapped_client = getattr(client, "client", None)
    if wrapped_client is not None:
        return wrapped_client
    return client


def get_docmesh_registry(app: FastAPI) -> Any | None:
    return getattr(app.state, "docmesh_registry", None)


def ensure_docmesh_registry(app: FastAPI, config: EnvConfig) -> Any:
    registry = get_docmesh_registry(app)
    if registry is not None:
        return registry

    initialized = initialize_docmesh_registry(config=config)
    if initialized is None:
        raise RuntimeError("docmesh registry is required for supported services")

    settings, registry = initialized
    app.state.docmesh_settings = settings
    app.state.docmesh_registry = registry
    return registry


def get_docmesh_service(app: FastAPI, service_name: str) -> Any | None:
    registry = get_docmesh_registry(app)
    if registry is None:
        return None
    return unwrap_docmesh_client(registry.create_client(service_name))


def get_required_docmesh_service(
    app: FastAPI,
    state_key: str,
    *,
    config: EnvConfig,
) -> Any:
    spec = get_registry_service_spec(state_key)
    if spec is None:
        raise KeyError(f"Unsupported registry-managed state key: {state_key}")
    registry = ensure_docmesh_registry(app, config)
    return unwrap_docmesh_client(registry.create_client(spec.registry_name))


def check_docmesh_service_connection(app: FastAPI, state_key: str) -> bool | None:
    spec = get_registry_service_spec(state_key)
    if spec is None:
        return None

    registry = get_docmesh_registry(app)
    if registry is None:
        return None

    service = registry.create_client(spec.registry_name)
    check = getattr(service, "check", None)
    if not callable(check):
        return None

    try:
        result = check()
    except Exception:
        return False

    ok = getattr(result, "ok", result)
    return bool(ok)


async def get_docmesh_service_async(app: FastAPI, service_name: str) -> Any | None:
    registry = get_docmesh_registry(app)
    if registry is None:
        return None
    service = registry.create_client(service_name)
    connect = getattr(service, "connect", None)
    if callable(connect):
        return await connect()
    return unwrap_docmesh_client(service)


async def get_required_docmesh_service_async(
    app: FastAPI,
    state_key: str,
    *,
    config: EnvConfig,
) -> Any:
    spec = get_registry_service_spec(state_key)
    if spec is None:
        raise KeyError(f"Unsupported registry-managed state key: {state_key}")

    registry = ensure_docmesh_registry(app, config)
    service = registry.create_client(spec.registry_name)
    if spec.mode == "async_builder":
        connect = getattr(service, "connect", None)
        if callable(connect):
            return await connect()
    return unwrap_docmesh_client(service)


def initialize_docmesh_registry(
    config: EnvConfig | None = None,
    env: Mapping[str, str] | None = None,
) -> tuple[object, object] | None:
    try:
        module = _load_docmesh_module()
    except ImportError:
        return None

    if env is not None:
        source_env = dict(env)
    elif config is not None:
        source_env = build_docmesh_env(config)
    else:
        source_env = dict(os.environ)

    settings = module.load_settings(source_env)
    registry = module.ServiceFactoryRegistry(settings)
    return settings, registry


def run_docmesh_healthchecks(
    service_checks: Mapping[str, Any],
    *,
    required_services: set[str] | None = None,
) -> bool:
    try:
        module = _load_docmesh_module()
    except ImportError:
        return False

    result = module.check_all_services(
        dict(service_checks),
        required_services=required_services,
    )
    return bool(getattr(result, "ok", False))
