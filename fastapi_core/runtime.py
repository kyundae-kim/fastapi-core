from __future__ import annotations

from docmesh_config import (
    HealthcheckPolicy,
    RuntimePlan,
    Service,
)
from docmesh_py_core import (
    KeycloakAuthService,
    ServiceClientWrapper,
    ServiceRuntime,
    assemble_service_runtime,
    create_empty_service_runtime,
)
from fastapi_core.function_logging import log_function_boundary
from fastapi import FastAPI

from fastapi_core.config import AppConfig
from fastapi_core.readiness import ReadinessCheckSpec, get_readiness_registry


@log_function_boundary()
def _build_healthcheck_policy(config: AppConfig) -> HealthcheckPolicy:
    return HealthcheckPolicy(
        on_startup=config.startup_healthcheck,
        parallel=config.readiness_parallel,
        timeout_seconds=config.readiness_timeout_seconds,
        overall_timeout_seconds=config.readiness_overall_timeout_seconds,
        failure_mode=config.startup_failure_mode,
        attempts=config.startup_healthcheck_attempts,
        retry_delay_seconds=config.startup_healthcheck_retry_delay_seconds,
    )


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
        healthcheck=_build_healthcheck_policy(config),
    )


@log_function_boundary()
def configure_keycloak_provider(provider: KeycloakAuthService) -> None:
    provider.allowed_algorithms = ["RS256"]


@log_function_boundary()
def create_empty_runtime() -> ServiceRuntime:
    """Create the canonical runtime that owns no external service clients."""
    return create_empty_service_runtime()


@log_function_boundary()
async def assemble_runtime(plan: RuntimePlan | None) -> ServiceRuntime:
    if plan is not None:
        return await assemble_service_runtime(plan=plan)
    return create_empty_runtime()


@log_function_boundary()
def configure_service_runtime(app: FastAPI, runtime: ServiceRuntime) -> None:
    readiness_registry = get_readiness_registry(app)
    required_services = runtime.required_services
    checks = runtime.checks
    missing_checks = runtime.selected_services.difference(checks)
    if missing_checks:
        names = ", ".join(
            sorted(service.value for service in missing_checks)
        )
        raise AttributeError(f"Runtime services do not expose callable checks: {names}")
    readiness_specs = tuple(
        ReadinessCheckSpec(
            name=service.value,
            check=check,
            required=service in required_services,
            redact_errors=True,
        )
        for service, check in checks.items()
    )
    duplicate_names = {
        spec.name for spec in readiness_specs if spec.name in readiness_registry.specs
    }
    if duplicate_names:
        name = sorted(duplicate_names)[0]
        raise ValueError(f"readiness check '{name}' is already registered")

    for spec in readiness_specs:
        readiness_registry.register(spec)

    keycloak_client = runtime.get(Service.KEYCLOAK)
    if isinstance(keycloak_client, ServiceClientWrapper):
        provider = keycloak_client.unwrap()
        if isinstance(provider, KeycloakAuthService):
            configure_keycloak_provider(provider)
            app.state.auth_provider = provider
    app.state.service_runtime = runtime


__all__ = [
    "assemble_runtime",
    "build_runtime_plan",
    "configure_service_runtime",
]
