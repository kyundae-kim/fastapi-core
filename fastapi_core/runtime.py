from __future__ import annotations

import os

from docmesh_py_core import (
    HealthcheckPolicy,
    RuntimePlan,
    Service,
    ServiceClientWrapper,
    ServiceRuntime,
    assemble_service_runtime,
    load_service_configs,
)
from docmesh_py_core.function_logging import log_function_boundary
from fastapi import FastAPI

from fastapi_core.config import AppConfig
from fastapi_core.docmesh_settings import build_docmesh_env_overlay
from fastapi_core.readiness import ReadinessCheckSpec, ReadinessRegistry


@log_function_boundary()
def build_runtime_plan(config: AppConfig) -> RuntimePlan:
    required_services = set(config.required_services)
    return RuntimePlan(
        services=tuple(
            Service.parse(service_name).required()
            if service_name in required_services
            else Service.parse(service_name).optional()
            for service_name in config.enabled_services
        ),
        one_of=tuple(
            tuple(Service.parse(service_name) for service_name in group)
            for group in config.service_alternatives
        ),
        healthcheck=HealthcheckPolicy(
            on_startup=config.startup_healthcheck,
            parallel=config.readiness_parallel,
            timeout_seconds=config.readiness_timeout_seconds,
            overall_timeout_seconds=config.readiness_overall_timeout_seconds,
        ),
    )


@log_function_boundary()
def build_keycloak_check_kwargs() -> dict[str, str]:
    values = {
        "username": os.getenv("KEYCLOAK_TOKEN_USERNAME"),
        "password": os.getenv("KEYCLOAK_TOKEN_PASSWORD"),
        "scope": os.getenv("FASTAPI_CORE_TEST_SCOPE", "").strip(),
    }
    return {name: value for name, value in values.items() if value}


@log_function_boundary()
def configure_keycloak_provider(client: ServiceClientWrapper) -> None:
    provider = getattr(client, "client", None)
    if provider is None or not hasattr(provider, "allowed_algorithms"):
        return
    provider.allowed_algorithms = ["RS256"]


@log_function_boundary()
async def assemble_runtime(config: AppConfig) -> ServiceRuntime:
    env = build_docmesh_env_overlay()
    if config.enabled_services:
        return await assemble_service_runtime(
            env,
            plan=build_runtime_plan(config),
        )
    return ServiceRuntime(
        configs=load_service_configs(env, services=set()),
        clients={},
        selected_services=frozenset(),
    )


@log_function_boundary()
def configure_service_runtime(app: FastAPI, runtime: ServiceRuntime) -> None:
    app.state.service_runtime = runtime
    readiness_registry: ReadinessRegistry = app.state.readiness_registry
    required_services = {
        Service.parse(service).value for service in runtime.required_services
    }
    for service, client in runtime.clients.items():
        service_name = Service.parse(service).value
        check = client.check
        if service_name == "keycloak":
            healthcheck = getattr(client, "healthcheck", check)
            kwargs = build_keycloak_check_kwargs()

            @log_function_boundary()
            def keycloak_check(healthcheck=healthcheck, kwargs=kwargs) -> object:
                return healthcheck(**kwargs)

            check = keycloak_check
        readiness_registry.register(
            ReadinessCheckSpec(
                name=service_name,
                check=check,
                required=service_name in required_services,
                redact_errors=True,
            )
        )
    keycloak_client = runtime.clients.get(Service.KEYCLOAK)
    if keycloak_client is not None:
        configure_keycloak_provider(keycloak_client)
        if hasattr(keycloak_client, "client"):
            app.state.auth_provider = keycloak_client.client


__all__ = [
    "assemble_runtime",
    "build_runtime_plan",
    "configure_service_runtime",
]
