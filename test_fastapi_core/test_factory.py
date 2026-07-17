from __future__ import annotations

from contextlib import asynccontextmanager
import json
import logging

import pytest
from docmesh_py_core import (
    ConfigError,
    HealthCheckError,
    HealthcheckPolicy,
    RuntimePlan,
    Service,
    ServiceCloseError,
    ServiceRuntime,
    assemble_service_runtime,
)
from fastapi.testclient import TestClient

import fastapi_core.factory as factory_module
from fastapi_core.config import AppConfig
from fastapi_core.docmesh_settings import load_docmesh_settings
from fastapi_core.factory import (
    _build_service_clients,
    _configure_service_runtime,
    create_app,
)


def _patch_injected_client(monkeypatch, client, service="keycloak"):
    monkeypatch.setattr(
        factory_module,
        "_build_service_clients",
        lambda _settings, _services: {Service.parse(service): client},
    )


def test_create_app_includes_default_routes(settings):
    config = AppConfig(
        enabled_services=["keycloak"],
        required_services=["keycloak"],
    )
    app = create_app(config=config, settings=settings)

    with TestClient(app) as client:
        response = client.get("/health/liveness")
        user_response = client.get("/user")
        token_response = client.post("/token")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "details": None}
    assert user_response.status_code != 404
    assert token_response.status_code != 404
    assert app.state.settings is settings
    assert app.state.config.token_url.endswith("token")
    assert sorted(app.state.service_clients) == ["keycloak"]
    assert app.state.auth_provider is app.state.service_clients["keycloak"].client
    assert app.state.root_logger is not None
    assert sorted(app.state.readiness_registry.specs) == ["keycloak"]
    assert app.state.readiness_registry.specs["keycloak"].required is True


def test_create_app_applies_configured_token_url_to_openapi(settings):
    config = AppConfig(token_url="/api/v1/auth/token")

    app = create_app(config=config, settings=settings)

    security_scheme = app.openapi()["components"]["securitySchemes"]["OAuth2PasswordBearer"]
    assert security_scheme["flows"]["password"]["tokenUrl"] == "/api/v1/auth/token"


def test_create_app_keeps_oauth2_scheme_isolated_per_app(settings):
    first_app = create_app(
        config=AppConfig(token_url="/first/token"),
        settings=settings,
    )
    second_app = create_app(
        config=AppConfig(token_url="/second/token"),
        settings=settings,
    )

    first_scheme = first_app.openapi()["components"]["securitySchemes"]["OAuth2PasswordBearer"]
    second_scheme = second_app.openapi()["components"]["securitySchemes"]["OAuth2PasswordBearer"]

    assert first_scheme["flows"]["password"]["tokenUrl"] == "/first/token"
    assert second_scheme["flows"]["password"]["tokenUrl"] == "/second/token"
    assert first_app.state.oauth2_scheme is not second_app.state.oauth2_scheme


def test_create_app_can_exclude_auth_router(settings):
    app = create_app(settings=settings, include_auth_router=False)

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
    assert app.state.service_clients == {}


def test_create_app_runs_custom_lifespan(settings):
    events: list[str] = []

    @asynccontextmanager
    async def lifespan(app):
        app.state.started_by_lifespan = True
        events.append("startup")
        yield
        events.append("shutdown")

    app = create_app(settings=settings, lifespan=lifespan)

    with TestClient(app):
        assert app.state.started_by_lifespan is True
        assert events == ["startup"]

    assert events == ["startup", "shutdown"]


def test_create_app_uses_selected_services_for_readiness_and_settings():
    config = AppConfig(
        enabled_services=["sqlite"],
        required_services=["sqlite"],
    )

    settings = load_docmesh_settings(("sqlite",))
    app = create_app(config=config, settings=settings, include_auth_router=False)

    assert app.state.settings.sqlite is not None
    assert app.state.settings.keycloak is None
    assert sorted(app.state.readiness_registry.specs) == ["sqlite"]
    assert sorted(app.state.service_clients) == ["sqlite"]
    assert app.state.readiness_registry.specs["sqlite"].required is True


def test_build_service_clients_resolves_factory_at_call_time(monkeypatch, settings):
    sentinel = object()
    monkeypatch.setattr(
        factory_module,
        "create_sqlite_client",
        lambda _config: sentinel,
    )

    clients = _build_service_clients(settings, ["sqlite"])

    assert clients == {"sqlite": sentinel}


@pytest.mark.asyncio
async def test_configure_service_runtime_preserves_async_checks(settings):
    events: list[str] = []

    class AsyncClient:
        async def check(self):
            events.append("checked")

    app = create_app(
        config=AppConfig(enabled_services=[], required_services=[]),
        settings=settings,
        include_auth_router=False,
    )
    runtime = ServiceRuntime(
        configs=settings,
        clients={Service.NATS: AsyncClient()},
        selected_services=frozenset({Service.NATS}),
    )
    _configure_service_runtime(app, runtime)

    await app.state.readiness_registry.specs["nats"].check()

    assert events == ["checked"]


def test_configure_service_runtime_rejects_client_without_check(settings):
    app = create_app(
        config=AppConfig(enabled_services=[], required_services=[]),
        settings=settings,
        include_auth_router=False,
    )
    runtime = ServiceRuntime(
        configs=settings,
        clients={Service.KEYCLOAK: object()},
        selected_services=frozenset({Service.KEYCLOAK}),
        required_services=frozenset({Service.KEYCLOAK}),
    )

    with pytest.raises(AttributeError):
        _configure_service_runtime(app, runtime)


def test_create_app_awaits_async_service_client_close(monkeypatch, settings):
    events: list[str] = []

    class AsyncClient:
        async def check(self):
            return None

        async def close(self):
            events.append("closed")

    _patch_injected_client(monkeypatch, AsyncClient(), "nats")
    app = create_app(settings=settings, include_auth_router=False)

    with TestClient(app):
        pass

    assert events == ["closed"]


def test_create_app_closes_service_clients_when_custom_shutdown_fails(
    monkeypatch,
    settings,
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

    _patch_injected_client(monkeypatch, AsyncClient(), "nats")
    app = create_app(
        settings=settings,
        lifespan=lifespan,
        include_auth_router=False,
    )

    with pytest.raises(RuntimeError, match="custom shutdown failed"):
        with TestClient(app):
            pass

    assert events == ["closed"]


def test_configure_service_runtime_passes_keycloak_healthcheck_credentials(
    monkeypatch,
    settings,
):
    calls: list[tuple[str | None, str | None, str | None]] = []

    class KeycloakClient:
        def check(self):
            raise AssertionError("keycloak readiness should call healthcheck directly")

        def healthcheck(self, *, username=None, password=None, scope=None):
            calls.append((username, password, scope))

    monkeypatch.setenv("KEYCLOAK_TOKEN_USERNAME", "tester")
    monkeypatch.setenv("KEYCLOAK_TOKEN_PASSWORD", "secret")
    monkeypatch.setenv("FASTAPI_CORE_TEST_SCOPE", "openid profile")

    app = create_app(
        config=AppConfig(enabled_services=[], required_services=[]),
        settings=settings,
        include_auth_router=False,
    )
    runtime = ServiceRuntime(
        configs=settings,
        clients={Service.KEYCLOAK: KeycloakClient()},
        selected_services=frozenset({Service.KEYCLOAK}),
    )
    _configure_service_runtime(app, runtime)
    monkeypatch.setenv("KEYCLOAK_TOKEN_PASSWORD", "changed")
    check = app.state.readiness_registry.specs["keycloak"].check
    check()

    assert calls == [("tester", "secret", "openid profile")]
    assert "secret" not in repr(check)


def test_create_app_uses_rs256_for_keycloak_auth_provider(settings):
    app = create_app(settings=settings, include_auth_router=False)

    assert app.state.auth_provider.allowed_algorithms == ["RS256"]


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
        clients={Service.SQLITE: SqliteClient()},
        selected_services=frozenset({Service.SQLITE}),
        required_services=frozenset({Service.SQLITE}),
    )

    async def fake_assemble_service_runtime(env, **kwargs):
        calls["env"] = env
        calls.update(kwargs)
        return runtime

    monkeypatch.setattr(
        factory_module,
        "assemble_service_runtime",
        fake_assemble_service_runtime,
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
    )
    app = create_app(config=config, include_auth_router=False)

    with TestClient(app):
        assert app.state.service_runtime is runtime
        assert app.state.settings is settings
        assert app.state.service_clients is runtime.clients
        assert sorted(app.state.readiness_registry.specs) == ["sqlite"]

    assert calls["plan"] == RuntimePlan(
        services=(Service.SQLITE.required(), Service.POSTGRES.optional()),
        one_of=((Service.SQLITE, Service.POSTGRES),),
        healthcheck=HealthcheckPolicy(
            on_startup=True,
            parallel=True,
            timeout_seconds=0.25,
            overall_timeout_seconds=1.5,
        ),
    )
    assert set(calls) == {"env", "plan"}
    assert calls["env"]["SQLITE_PATH"] == ":memory:"
    assert events == ["closed"]


def test_create_app_checks_injected_runtime_on_startup(monkeypatch, settings):
    events: list[str] = []

    class Client:
        def check(self):
            events.append("checked")

        def close(self):
            events.append("closed")

    _patch_injected_client(monkeypatch, Client())
    config = AppConfig(startup_healthcheck=True)
    app = create_app(
        config=config,
        settings=settings,
        include_auth_router=False,
    )

    with TestClient(app):
        assert events == ["checked"]

    assert events == ["checked", "closed"]


def test_create_app_validates_service_alternatives_for_injected_settings():
    settings = load_docmesh_settings(("sqlite",))
    config = AppConfig(
        enabled_services=["sqlite"],
        required_services=[],
        service_alternatives=[["minio", "milvus"]],
    )

    with pytest.raises(ConfigError, match="At least one service must be configured"):
        create_app(
            config=config,
            settings=settings,
            include_auth_router=False,
        )


def test_create_app_rolls_back_runtime_when_startup_healthcheck_fails(monkeypatch):
    events: list[str] = []

    class Client:
        async def check(self):
            events.append("checked")
            raise RuntimeError("sqlite unavailable")

        async def close(self):
            events.append("closed")

    async def assemble_with_failing_client(env, **kwargs):
        return await assemble_service_runtime(
            env,
            factory_overrides={"sqlite": lambda _config: Client()},
            **kwargs,
        )

    @asynccontextmanager
    async def lifespan(_app):
        events.append("custom-startup")
        yield

    monkeypatch.setattr(
        factory_module,
        "assemble_service_runtime",
        assemble_with_failing_client,
    )
    app = create_app(
        config=AppConfig(
            enabled_services=["sqlite"],
            required_services=["sqlite"],
            startup_healthcheck=True,
        ),
        lifespan=lifespan,
        include_auth_router=False,
    )

    with pytest.raises(HealthCheckError, match="Required service health check failed"):
        with TestClient(app):
            pass

    assert events == ["checked", "closed"]


def test_create_app_logs_service_runtime_close_failures(monkeypatch, settings, caplog):
    class Client:
        def check(self):
            return None

        def close(self):
            raise RuntimeError("close failed token=secret-token")

    _patch_injected_client(monkeypatch, Client())
    app = create_app(settings=settings, include_auth_router=False)

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

    app = create_app(config=config, settings=settings, include_auth_router=False)
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
