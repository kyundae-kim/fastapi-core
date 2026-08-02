from __future__ import annotations

from contextlib import asynccontextmanager
import json
import logging
import os

import pytest
from docmesh_config import (
    HealthcheckPolicy,
    InvalidRuntimePlanError,
    RuntimePlan,
    Service,
    StartupFailureMode,
    UnknownServiceError,
)
from docmesh_py_core import (
    HealthCheckError,
    RuntimeHealthDescriptorError,
    ServiceCloseError,
    ServiceClientWrapper,
    ServiceRuntime,
    create_keycloak_client,
    create_sqlite_client,
)
from fastapi.testclient import TestClient

import fastapi_core.factory as factory_module
import fastapi_core.runtime as runtime_module
from fastapi_core.config import AppConfig, load_app_config
from fastapi_core.docmesh_settings import load_docmesh_settings
from fastapi_core.factory import create_app
from fastapi_core.readiness import register_readiness_check
from fastapi_core.runtime import configure_service_runtime


def _service_handle(service: Service, client, *, healthcheck=None):
    return ServiceClientWrapper(
        client=client,
        healthcheck=healthcheck or client.check,
        service_name=service.value,
    )


def test_create_app_defaults_to_service_free_health_only_app(monkeypatch):
    for name in tuple(os.environ):
        if name.startswith(
            ("DOCMESH_", "KEYCLOAK_", "POSTGRES_", "NATS_", "READINESS_")
        ):
            monkeypatch.delenv(name, raising=False)
    load_app_config.cache_clear()

    app = create_app()

    with TestClient(app) as client:
        liveness = client.get("/health/liveness")
        readiness = client.get("/health/readiness")
        user = client.get("/user")
        token = client.post("/token")

    assert liveness.status_code == 200
    assert readiness.status_code == 200
    assert readiness.json() == {"status": "ok", "details": None}
    assert user.status_code == 404
    assert token.status_code == 404
    assert app.state.service_runtime.selected_services == frozenset()
    assert app.state.service_runtime.required_services == frozenset()
    assert app.state.service_runtime.clients == {}
    load_app_config.cache_clear()


def test_create_app_includes_auth_routes_when_enabled(empty_runtime):
    config = AppConfig(
        enabled_services=["keycloak"],
        required_services=["keycloak"],
    )
    app = create_app(
        config=config,
        runtime=empty_runtime,
        include_auth_router=True,
        auth_provider=object(),
    )

    with TestClient(app) as client:
        response = client.get("/health/liveness")
        user_response = client.get("/user")
        token_response = client.post("/token")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "details": None}
    assert user_response.status_code != 404
    assert token_response.status_code != 404
    assert app.state.service_runtime.configs is empty_runtime.configs
    assert app.state.config.token_url.endswith("token")
    assert app.state.service_runtime.clients == {}
    assert app.state.root_logger is not None
    assert app.state.readiness_registry.specs == {}


def test_create_app_applies_configured_token_url_to_openapi(empty_runtime):
    config = AppConfig(token_url="/api/v1/auth/token")

    app = create_app(
        config=config,
        runtime=empty_runtime,
        include_auth_router=True,
        auth_provider=object(),
    )

    security_scheme = app.openapi()["components"]["securitySchemes"]["OAuth2PasswordBearer"]
    assert security_scheme["flows"]["password"]["tokenUrl"] == "/api/v1/auth/token"


def test_create_app_keeps_oauth2_scheme_isolated_per_app(runtime_factory):
    first_app = create_app(
        config=AppConfig(token_url="/first/token"),
        runtime=runtime_factory(),
        include_auth_router=True,
        auth_provider=object(),
    )
    second_app = create_app(
        config=AppConfig(token_url="/second/token"),
        runtime=runtime_factory(),
        include_auth_router=True,
        auth_provider=object(),
    )

    first_scheme = first_app.openapi()["components"]["securitySchemes"]["OAuth2PasswordBearer"]
    second_scheme = second_app.openapi()["components"]["securitySchemes"]["OAuth2PasswordBearer"]

    assert first_scheme["flows"]["password"]["tokenUrl"] == "/first/token"
    assert second_scheme["flows"]["password"]["tokenUrl"] == "/second/token"
    assert first_app.state.oauth2_scheme is not second_app.state.oauth2_scheme


def test_create_app_can_exclude_auth_router(empty_runtime):
    app = create_app(runtime=empty_runtime, include_auth_router=False)

    with TestClient(app) as client:
        liveness_response = client.get("/health/liveness")
        user_response = client.get("/user")
        token_response = client.post("/token")

    assert liveness_response.status_code == 200
    assert user_response.status_code == 404
    assert token_response.status_code == 404


def test_create_app_supports_explicitly_empty_service_selection():
    app = create_app(
        config=AppConfig(enabled_services=[], required_services=[]),
        include_auth_router=False,
    )

    with TestClient(app) as client:
        response = client.get("/health/readiness")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "details": None}
    assert app.state.service_runtime.clients == {}


@pytest.mark.parametrize(
    ("config", "error_type"),
    [
        (
            AppConfig(enabled_services=["unknown"], required_services=[]),
            UnknownServiceError,
        ),
        (
            AppConfig(
                enabled_services=["sqlite", "sqlite"],
                required_services=[],
            ),
            InvalidRuntimePlanError,
        ),
        (
            AppConfig(
                enabled_services=["sqlite"],
                required_services=[],
                service_alternatives=[["postgres"]],
            ),
            InvalidRuntimePlanError,
        ),
        (
            AppConfig(
                enabled_services=["sqlite"],
                required_services=[],
                service_alternatives=[[]],
            ),
            InvalidRuntimePlanError,
        ),
    ],
)
def test_create_app_validates_runtime_plan_before_lifespan(config, error_type):
    with pytest.raises(error_type):
        create_app(config=config, include_auth_router=False)


def test_create_app_does_not_build_runtime_plan_for_injected_runtime(
    monkeypatch,
    empty_runtime,
):
    def fail_build_runtime_plan(_config):
        raise AssertionError("injected runtime must remain authoritative")

    monkeypatch.setattr(
        factory_module,
        "build_runtime_plan",
        fail_build_runtime_plan,
        raising=False,
    )

    app = create_app(
        config=AppConfig(enabled_services=["sqlite"], required_services=[]),
        runtime=empty_runtime,
        include_auth_router=False,
    )

    with TestClient(app):
        assert app.state.service_runtime is empty_runtime


def test_create_app_accepts_prebuilt_service_runtime(settings):
    events: list[str] = []

    class SqliteClient:
        def check(self):
            events.append("checked")

        def close(self):
            events.append("closed")

    runtime = ServiceRuntime(
        configs=settings,
        clients={Service.SQLITE: _service_handle(Service.SQLITE, SqliteClient())},
        selected_services=frozenset({Service.SQLITE}),
        required_services=frozenset({Service.SQLITE}),
    )

    app = create_app(
        config=AppConfig(
            enabled_services=[],
            required_services=[],
            startup_healthcheck=True,
        ),
        runtime=runtime,
        include_auth_router=False,
    )

    with TestClient(app):
        assert app.state.service_runtime is runtime
        assert app.state.service_runtime.configs is settings
        assert app.state.service_runtime.clients is runtime.clients
        assert app.state.readiness_registry.specs["sqlite"].required is True
        assert events == ["checked"]

    assert events == ["checked", "closed"]


def test_create_app_runs_custom_lifespan(empty_runtime):
    events: list[str] = []

    @asynccontextmanager
    async def lifespan(app):
        app.state.started_by_lifespan = True
        events.append("startup")
        yield
        events.append("shutdown")

    app = create_app(runtime=empty_runtime, lifespan=lifespan)

    with TestClient(app):
        assert app.state.started_by_lifespan is True
        assert events == ["startup"]

    assert events == ["startup", "shutdown"]


def test_create_app_binds_prebuilt_runtime_services(
    settings,
    runtime_factory,
):
    config = AppConfig(
        enabled_services=["sqlite"],
        required_services=["sqlite"],
    )

    runtime = runtime_factory(
        clients={"sqlite": create_sqlite_client(settings.sqlite)},
        required=("sqlite",),
    )
    app = create_app(config=config, runtime=runtime, include_auth_router=False)

    assert app.state.service_runtime.configs is settings
    assert sorted(app.state.readiness_registry.specs) == ["sqlite"]
    assert sorted(app.state.service_runtime.clients) == ["sqlite"]
    assert app.state.readiness_registry.specs["sqlite"].required is True


@pytest.mark.asyncio
async def test_configure_service_runtime_preserves_async_checks(settings, empty_runtime):
    events: list[str] = []

    class AsyncClient:
        async def check(self):
            events.append("checked")

    app = create_app(
        config=AppConfig(enabled_services=[], required_services=[]),
        runtime=empty_runtime,
        include_auth_router=False,
    )
    runtime = ServiceRuntime(
        configs=settings,
        clients={Service.NATS: _service_handle(Service.NATS, AsyncClient())},
        selected_services=frozenset({Service.NATS}),
    )
    configure_service_runtime(app, runtime)

    await app.state.readiness_registry.specs["nats"].check()

    assert events == ["checked"]


def test_configure_service_runtime_uses_runtime_checks_container_surface(
    monkeypatch,
    settings,
    empty_runtime,
):
    calls: list[str] = []

    class Client:
        @property
        def check(self):
            raise AssertionError("adapter must not extract checks from runtime.clients")

    def canonical_check():
        calls.append("checked")

    app = create_app(
        config=AppConfig(enabled_services=[], required_services=[]),
        runtime=empty_runtime,
        include_auth_router=False,
    )
    monkeypatch.setattr(
        ServiceRuntime,
        "checks",
        property(lambda _runtime: {Service.SQLITE: canonical_check}),
    )
    runtime = ServiceRuntime(
        configs=settings,
        clients={
            Service.SQLITE: _service_handle(
                Service.SQLITE,
                Client(),
                healthcheck=canonical_check,
            )
        },
        selected_services=frozenset({Service.SQLITE}),
    )
    configure_service_runtime(app, runtime)
    app.state.readiness_registry.specs["sqlite"].check()

    assert calls == ["checked"]


def test_configure_service_runtime_redacts_service_check_errors_by_default(
    settings,
    empty_runtime,
):
    class Client:
        def check(self):
            raise RuntimeError("postgresql://user:***@database.test/docmesh")

    app = create_app(
        config=AppConfig(enabled_services=[], required_services=[]),
        runtime=empty_runtime,
        include_auth_router=False,
    )
    runtime = ServiceRuntime(
        configs=settings,
        clients={Service.POSTGRES: _service_handle(Service.POSTGRES, Client())},
        selected_services=frozenset({Service.POSTGRES}),
    )

    configure_service_runtime(app, runtime)

    assert app.state.readiness_registry.specs["postgres"].redact_errors is True


def test_service_runtime_rejects_client_without_health_descriptor(settings):
    with pytest.raises(
        RuntimeHealthDescriptorError,
        match="missing a health descriptor: keycloak",
    ):
        ServiceRuntime(
            configs=settings,
            clients={Service.KEYCLOAK: object()},
            selected_services=frozenset({Service.KEYCLOAK}),
            required_services=frozenset({Service.KEYCLOAK}),
        )


def test_configure_service_runtime_is_atomic_on_readiness_name_collision(
    settings,
    empty_runtime,
):
    class Client:
        def check(self):
            return None

    app = create_app(
        config=AppConfig(enabled_services=[], required_services=[]),
        runtime=empty_runtime,
        include_auth_router=False,
    )
    register_readiness_check(app, "postgres", lambda: True)
    runtime = ServiceRuntime(
        configs=settings,
        clients={
            Service.SQLITE: _service_handle(Service.SQLITE, Client()),
            Service.POSTGRES: _service_handle(Service.POSTGRES, Client()),
        },
        selected_services=frozenset({Service.SQLITE, Service.POSTGRES}),
    )

    with pytest.raises(ValueError, match="postgres.*already registered"):
        configure_service_runtime(app, runtime)

    assert app.state.service_runtime is empty_runtime
    assert set(app.state.readiness_registry.specs) == {"postgres"}


def test_create_app_awaits_async_service_client_close(runtime_factory):
    events: list[str] = []

    class AsyncClient:
        async def check(self):
            return None

        async def close(self):
            events.append("closed")

    runtime = runtime_factory(clients={"nats": AsyncClient()})
    app = create_app(runtime=runtime, include_auth_router=False)

    with TestClient(app):
        pass

    assert events == ["closed"]


def test_create_app_closes_service_clients_when_custom_shutdown_fails(
    runtime_factory,
):
    events: list[str] = []

    class AsyncClient:
        async def check(self):
            return None

        async def close(self):
            events.append("closed")

    @asynccontextmanager
    async def lifespan(_app):
        yield
        raise RuntimeError("custom shutdown failed")

    runtime = runtime_factory(clients={"nats": AsyncClient()})
    app = create_app(
        runtime=runtime,
        lifespan=lifespan,
        include_auth_router=False,
    )

    with pytest.raises(RuntimeError, match="custom shutdown failed"):
        with TestClient(app):
            pass

    assert events == ["closed"]


def test_configure_service_runtime_uses_canonical_keycloak_wrapper_check(
    monkeypatch,
    settings,
    empty_runtime,
):
    calls: list[str] = []

    def healthcheck():
        calls.append("checked")

    monkeypatch.setenv("KEYCLOAK_TOKEN_USERNAME", "tester")
    monkeypatch.setenv("KEYCLOAK_TOKEN_PASSWORD", "secret")
    monkeypatch.setenv("FASTAPI_CORE_TEST_SCOPE", "openid profile")

    app = create_app(
        config=AppConfig(enabled_services=[], required_services=[]),
        runtime=empty_runtime,
        include_auth_router=False,
    )
    wrapper = ServiceClientWrapper(
        client=object(),
        healthcheck=healthcheck,
        service_name="keycloak",
    )
    runtime = ServiceRuntime(
        configs=settings,
        clients={Service.KEYCLOAK: wrapper},
        selected_services=frozenset({Service.KEYCLOAK}),
    )
    configure_service_runtime(app, runtime)
    monkeypatch.setenv("KEYCLOAK_TOKEN_PASSWORD", "changed")
    check = app.state.readiness_registry.specs["keycloak"].check
    check()

    assert calls == ["checked"]
    assert check.__self__ is wrapper
    assert check.__func__ is ServiceClientWrapper.check


def test_create_app_uses_rs256_for_keycloak_auth_provider(settings, runtime_factory):
    runtime = runtime_factory(
        clients={"keycloak": create_keycloak_client(settings.keycloak)},
        required=("keycloak",),
    )
    app = create_app(runtime=runtime, include_auth_router=False)

    assert app.state.auth_provider.allowed_algorithms == ["RS256"]


def test_configure_service_runtime_uses_runtime_lookup_for_keycloak_provider(
    settings,
    runtime_factory,
):
    wrapper = create_keycloak_client(settings.keycloak)
    runtime = runtime_factory(clients={"keycloak": wrapper})
    calls: list[Service] = []
    original_get = runtime.get

    def tracked_get(service):
        calls.append(service)
        return original_get(service)

    runtime.get = tracked_get

    app = create_app(runtime=runtime, include_auth_router=False)

    assert calls == [Service.KEYCLOAK]
    assert app.state.auth_provider is wrapper.unwrap()


def test_configure_service_runtime_does_not_bind_invalid_keycloak_provider(
    settings,
    empty_runtime,
):
    app = create_app(
        config=AppConfig(enabled_services=[], required_services=[]),
        runtime=empty_runtime,
        include_auth_router=False,
    )
    runtime = ServiceRuntime(
        configs=settings,
        clients={
            Service.KEYCLOAK: ServiceClientWrapper(
                client=object(),
                healthcheck=lambda: None,
                service_name="keycloak",
            )
        },
        selected_services=frozenset({Service.KEYCLOAK}),
    )

    configure_service_runtime(app, runtime)

    assert not hasattr(app.state, "auth_provider")


def test_create_app_assembles_default_runtime_during_lifespan(monkeypatch):
    calls: dict[str, object] = {}
    events: list[str] = []
    settings = load_docmesh_settings(("sqlite",))

    class SqliteClient:
        def check(self):
            events.append("checked")

        def close(self):
            events.append("closed")

    runtime = ServiceRuntime(
        configs=settings,
        clients={Service.SQLITE: _service_handle(Service.SQLITE, SqliteClient())},
        selected_services=frozenset({Service.SQLITE}),
        required_services=frozenset({Service.SQLITE}),
    )

    expected_plan = RuntimePlan(
        services=(Service.SQLITE.required(), Service.POSTGRES.optional()),
        one_of=((Service.SQLITE, Service.POSTGRES),),
        healthcheck=HealthcheckPolicy(
            on_startup=True,
            parallel=True,
            timeout_seconds=0.25,
            overall_timeout_seconds=1.5,
            failure_mode=StartupFailureMode.REPORT,
            attempts=3,
            retry_delay_seconds=0.25,
        ),
    )

    def fake_build_runtime_plan(_config):
        calls["build_count"] = int(calls.get("build_count", 0)) + 1
        return expected_plan

    async def fake_assemble_service_runtime(*, plan):
        calls["plan"] = plan
        return runtime

    monkeypatch.setattr(
        runtime_module,
        "assemble_service_runtime",
        fake_assemble_service_runtime,
        raising=False,
    )
    monkeypatch.setattr(
        factory_module,
        "build_runtime_plan",
        fake_build_runtime_plan,
        raising=False,
    )
    config = AppConfig(
        enabled_services=["sqlite", "postgres"],
        required_services=["sqlite"],
        startup_healthcheck=True,
        readiness_parallel=True,
        readiness_timeout_seconds=0.25,
        readiness_overall_timeout_seconds=1.5,
        service_alternatives=[["sqlite", "postgres"]],
        startup_failure_mode=StartupFailureMode.REPORT,
        startup_healthcheck_attempts=3,
        startup_healthcheck_retry_delay_seconds=0.25,
    )
    app = create_app(config=config, include_auth_router=False)

    with TestClient(app):
        assert app.state.service_runtime is runtime
        assert app.state.service_runtime.configs is settings
        assert app.state.service_runtime.clients is runtime.clients
        assert sorted(app.state.readiness_registry.specs) == ["sqlite"]

    assert calls["plan"] is expected_plan
    assert calls["build_count"] == 1
    assert set(calls) == {"build_count", "plan"}
    assert events == ["closed"]


def test_create_app_checks_injected_runtime_on_startup(runtime_factory):
    events: list[str] = []

    class Client:
        def check(self):
            events.append("checked")

        def close(self):
            events.append("closed")

    runtime = runtime_factory(
        clients={"keycloak": Client()},
        required=("keycloak",),
    )
    config = AppConfig(startup_healthcheck=True)
    app = create_app(
        config=config,
        runtime=runtime,
        include_auth_router=False,
    )

    with TestClient(app):
        assert events == ["checked"]

    assert events == ["checked", "closed"]


def test_create_app_delegates_injected_startup_policy_to_docmesh(runtime_factory):
    policies: list[HealthcheckPolicy] = []

    class Client:
        def check(self):
            return None

        def close(self):
            return None

    runtime = runtime_factory(
        clients={"keycloak": Client()},
        required=("keycloak",),
    )
    original_check_with_policy = runtime.check_with_policy

    async def tracked_check_with_policy(policy):
        policies.append(policy)
        return await original_check_with_policy(policy)

    runtime.check_with_policy = tracked_check_with_policy
    config = AppConfig(
        startup_healthcheck=True,
        readiness_parallel=True,
        readiness_timeout_seconds=0.25,
        readiness_overall_timeout_seconds=1.5,
        startup_failure_mode=StartupFailureMode.REPORT,
        startup_healthcheck_attempts=2,
        startup_healthcheck_retry_delay_seconds=0.1,
    )
    app = create_app(config=config, runtime=runtime, include_auth_router=False)

    with TestClient(app):
        pass

    assert len(policies) == 1
    assert policies[0] == HealthcheckPolicy(
        on_startup=True,
        parallel=True,
        timeout_seconds=0.25,
        overall_timeout_seconds=1.5,
        failure_mode=StartupFailureMode.REPORT,
        attempts=2,
        retry_delay_seconds=0.1,
    )


def test_create_app_retries_injected_runtime_startup_check(runtime_factory):
    events: list[str] = []

    class Client:
        def check(self):
            events.append("checked")
            if events.count("checked") < 3:
                raise RuntimeError("temporarily unavailable")

        def close(self):
            events.append("closed")

    runtime = runtime_factory(
        clients={"keycloak": Client()},
        required=("keycloak",),
    )
    app = create_app(
        config=AppConfig(
            startup_healthcheck=True,
            startup_healthcheck_attempts=3,
        ),
        runtime=runtime,
        include_auth_router=False,
    )

    with TestClient(app):
        assert events == ["checked", "checked", "checked"]
        assert runtime.startup_healthcheck_result is not None
        assert runtime.startup_healthcheck_result.ok is True

    assert events == ["checked", "checked", "checked", "closed"]


def test_create_app_reports_injected_runtime_startup_failure(runtime_factory):
    events: list[str] = []

    class Client:
        def check(self):
            events.append("checked")
            raise RuntimeError("still unavailable")

        def close(self):
            events.append("closed")

    runtime = runtime_factory(
        clients={"keycloak": Client()},
        required=("keycloak",),
    )
    app = create_app(
        config=AppConfig(
            startup_healthcheck=True,
            startup_failure_mode=StartupFailureMode.REPORT,
            startup_healthcheck_attempts=2,
        ),
        runtime=runtime,
        include_auth_router=False,
    )

    with TestClient(app):
        assert events == ["checked", "checked"]
        assert runtime.startup_healthcheck_result is not None
        assert runtime.startup_healthcheck_result.ok is False

    assert events == ["checked", "checked", "closed"]


def test_create_app_closes_injected_runtime_when_startup_healthcheck_fails(settings):
    events: list[str] = []

    class Client:
        async def check(self):
            events.append("checked")
            raise RuntimeError("sqlite unavailable")

        async def close(self):
            events.append("closed")

    runtime = ServiceRuntime(
        configs=settings,
        clients={
            Service.SQLITE: _service_handle(Service.SQLITE, Client()),
        },
        selected_services=frozenset({Service.SQLITE}),
        required_services=frozenset({Service.SQLITE}),
    )

    app = create_app(
        config=AppConfig(
            enabled_services=["sqlite"],
            required_services=["sqlite"],
            startup_healthcheck=True,
        ),
        runtime=runtime,
        include_auth_router=False,
    )

    with pytest.raises(HealthCheckError, match="Required service health check failed"):
        with TestClient(app):
            pass

    assert events == ["checked", "closed"]


def test_create_app_logs_service_runtime_close_failures(runtime_factory, caplog):
    class Client:
        def check(self):
            return None

        def close(self):
            raise RuntimeError("close failed token=secret-token")

    runtime = runtime_factory(clients={"keycloak": Client()})
    app = create_app(runtime=runtime, include_auth_router=False)

    with caplog.at_level(logging.ERROR):
        with pytest.raises(ServiceCloseError):
            with TestClient(app):
                pass

    records = [
        record
        for record in caplog.records
        if record.getMessage() == "service_runtime_close_failed"
    ]
    assert len(records) == 1
    assert records[0].event == {
        "operation": "service_runtime_close",
        "outcome": "error",
        "failure_count": 1,
    }
    assert records[0].exc_info is None
    assert "secret-token" not in str(records[0].event)


def test_create_app_configures_json_logging_to_file(tmp_path):
    log_path = tmp_path / "app.log"
    config = AppConfig(
        log_level="WARNING",
        log_path=str(log_path),
        log_force=True,
        enabled_services=["sqlite"],
        required_services=["sqlite"],
    )
    settings = load_docmesh_settings(("sqlite",))
    runtime = ServiceRuntime(
        configs=settings,
        clients={},
        selected_services=frozenset(),
    )

    app = create_app(config=config, runtime=runtime, include_auth_router=False)
    logger = logging.getLogger("fastapi_core.test")
    logger.warning("structured-log", extra={"event": {"service": "sqlite", "outcome": "ok"}})

    for handler in app.state.root_logger.handlers:
        handler.flush()

    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert lines
    payload = json.loads(lines[-1])
    assert payload["message"] == "structured-log"
    assert payload["level"] == "WARNING"
    assert payload["logger"] == "fastapi_core.test"
    assert payload["event"] == {"service": "sqlite", "outcome": "ok"}
