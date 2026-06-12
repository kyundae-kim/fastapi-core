from __future__ import annotations

from collections.abc import Mapping
import importlib
import os
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from fastapi_core.core.config import EnvConfig


DOCMESH_MODULE_NAME = "docmesh_py_core"


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


def build_docmesh_env(config: EnvConfig) -> dict[str, str]:
    env: dict[str, str] = {
        "DOCMESH_ENV": _docmesh_env_name(config.env.value),
        "DOCMESH_HEALTHCHECK_ENABLED": "true",
        "KEYCLOAK_URL": str(config.keycloak.http_url),
        "KEYCLOAK_REALM": config.keycloak.realm,
        "KEYCLOAK_CLIENT_ID": config.keycloak.client_id,
        "KEYCLOAK_VERIFY_SSL": _bool_string(
            str(config.keycloak.http_url).startswith("https://")
        ),
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

    if config.keycloak.client_secret:
        env["KEYCLOAK_CLIENT_SECRET"] = config.keycloak.client_secret
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
