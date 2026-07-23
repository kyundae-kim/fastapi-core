from __future__ import annotations

import logging
import os

import pytest
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.testclient import TestClient

import fastapi_core.factory as factory_module
from fastapi_core import (
    DomainModule,
    ErrorMapperSpec,
    ErrorMapping,
    ManagedResource,
    ReadinessCheckSpec,
    create_app,
)
from fastapi_core.config import AppConfig, load_app_config
from fastapi_core.docmesh_settings import load_docmesh_settings
from fastapi_core.testing import (
    assert_module_contract,
    assert_openapi_contract,
    create_empty_runtime,
    test_environment,
)


def test_create_app_registers_direct_router():
    router = APIRouter(prefix="/direct", tags=["direct"])

    @router.get("/items", operation_id="list_direct_items")
    async def list_items():
        return {"items": []}

    app = create_app(runtime=create_empty_runtime(), routers=[router])

    with TestClient(app) as client:
        response = client.get("/direct/items")

    assert response.status_code == 200
    assert response.json() == {"items": []}
    operation = app.openapi()["paths"]["/direct/items"]["get"]
    assert operation["tags"] == ["direct"]
    assert operation["operationId"] == "list_direct_items"


def test_domain_module_applies_dependencies_only_to_its_routers():
    calls: list[str] = []

    def authorize():
        calls.append("authorized")

    router = APIRouter(prefix="/documents")

    @router.get("")
    async def list_documents():
        return []

    module = DomainModule(
        name="documents",
        routers=(router,),
        dependencies=(Depends(authorize),),
    )
    app = create_app(runtime=create_empty_runtime(), modules=[module])

    with TestClient(app) as client:
        assert client.get("/documents").status_code == 200
        assert client.get("/health/liveness").status_code == 200

    assert calls == ["authorized"]


def test_domain_module_composes_resource_readiness_and_error_mapper():
    class DomainError(Exception):
        pass

    router = APIRouter(prefix="/domain")

    @router.get("/failure")
    async def failure():
        raise DomainError("domain failed")

    resource = ManagedResource(
        name="domain-store",
        factory=lambda _app: object(),
        healthcheck=lambda _value: True,
    )
    module = DomainModule(
        name="domain",
        routers=(router,),
        resources=(resource,),
        readiness_checks=(
            ReadinessCheckSpec(name="domain-policy", check=lambda: True),
        ),
        error_mappers=(
            ErrorMapperSpec(
                DomainError,
                lambda _request, exc: ErrorMapping(409, str(exc)),
            ),
        ),
    )
    app = create_app(runtime=create_empty_runtime(), modules=[module])

    with TestClient(app, raise_server_exceptions=False) as client:
        assert client.get("/domain/failure").status_code == 409
        readiness = client.get("/health/readiness")

    assert readiness.status_code == 200
    assert set(readiness.json()["details"]) == {"domain-policy", "domain-store"}


def test_domain_module_rejects_duplicate_readiness_before_startup():
    first = DomainModule(
        name="first",
        readiness_checks=(ReadinessCheckSpec("duplicate", lambda: True),),
    )
    second = DomainModule(
        name="second",
        readiness_checks=(ReadinessCheckSpec("duplicate", lambda: True),),
    )

    with pytest.raises(ValueError, match="duplicate"):
        create_app(runtime=create_empty_runtime(), modules=[first, second])


def test_domain_module_rejects_invalid_router_before_app_registration():
    module = DomainModule(name="invalid", routers=(object(),))

    with pytest.raises(TypeError, match="APIRouter"):
        create_app(runtime=create_empty_runtime(), modules=[module])


def test_declarative_error_mappers_are_installed_in_batch():
    class DomainError(Exception):
        pass

    router = APIRouter()

    @router.get("/failure")
    async def failure():
        raise DomainError("token=secret")

    app = create_app(
        runtime=create_empty_runtime(),
        routers=[router],
        error_mappers=[
            ErrorMapperSpec(
                DomainError,
                lambda _request, exc: ErrorMapping(418, str(exc)),
            )
        ],
    )

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/failure")

    assert response.status_code == 418
    assert response.json()["detail"] == "token=***"


def test_declarative_error_mapper_rejects_non_callable_mapper():
    class DomainError(Exception):
        pass

    with pytest.raises(TypeError, match="callable"):
        create_app(
            runtime=create_empty_runtime(),
            error_mappers=[ErrorMapperSpec(DomainError, None)],
        )


def test_duplicate_route_contract_is_rejected():
    first = APIRouter()
    second = APIRouter()

    @first.get("/duplicate")
    async def first_route():
        return None

    @second.get("/duplicate")
    async def second_route():
        return None

    with pytest.raises(ValueError, match="GET /duplicate"):
        create_app(runtime=create_empty_runtime(), routers=[first, second])


def test_access_log_records_safe_request_completion(caplog):
    router = APIRouter()

    @router.get("/logged/{item_id}")
    async def logged(item_id: str):
        return {"item_id": item_id}

    app = create_app(runtime=create_empty_runtime(), routers=[router])

    with caplog.at_level(logging.INFO, logger="fastapi_core.access"):
        with TestClient(app) as client:
            response = client.get(
                "/logged/123?token=query-secret",
                headers={"Authorization": "Bearer header-secret"},
            )
            client.get("/health/liveness")

    assert response.status_code == 200
    records = [record for record in caplog.records if record.getMessage() == "http_access"]
    assert len(records) == 1
    event = records[0].event
    assert event["method"] == "GET"
    assert event["route"] == "/logged/{item_id}"
    assert event["status_code"] == 200
    assert event["outcome"] == "success"
    assert event["correlation_id"] == response.headers["X-Correlation-ID"]
    assert event["duration_ms"] >= 0
    assert "query-secret" not in str(event)
    assert "header-secret" not in str(event)


def test_access_log_is_emitted_with_default_application_log_level(caplog):
    router = APIRouter()

    @router.get("/default-access-log")
    async def default_access_log():
        return None

    app = create_app(
        config=AppConfig(
            enabled_services=[],
            required_services=[],
            log_level="WARNING",
        ),
        runtime=create_empty_runtime(),
        routers=[router],
    )

    with TestClient(app) as client:
        client.get("/default-access-log")

    assert any(record.getMessage() == "http_access" for record in caplog.records)


def test_access_log_records_stream_completion_once(caplog):
    router = APIRouter()

    @router.get("/stream")
    async def stream():
        async def chunks():
            yield b"one"
            yield b"two"

        return StreamingResponse(chunks())

    app = create_app(runtime=create_empty_runtime(), routers=[router])

    with caplog.at_level(logging.INFO, logger="fastapi_core.access"):
        with TestClient(app) as client:
            assert client.get("/stream").content == b"onetwo"

    records = [record for record in caplog.records if record.getMessage() == "http_access"]
    assert len(records) == 1


def test_test_environment_restores_environment_and_configuration_caches(monkeypatch):
    monkeypatch.setenv("ROOT_PATH", "/before")
    load_app_config.cache_clear()
    load_docmesh_settings.cache_clear()
    assert load_app_config().root_path == "/before"
    before_settings = load_docmesh_settings(())

    with test_environment(
        {
            "ROOT_PATH": "/inside",
            "DOCMESH_SERVICES": "",
            "READINESS_REQUIRED_SERVICES": "",
        }
    ):
        assert os.environ["ROOT_PATH"] == "/inside"
        assert load_app_config().root_path == "/inside"
        assert load_docmesh_settings(()) is not before_settings

    assert os.environ["ROOT_PATH"] == "/before"
    assert load_app_config().root_path == "/before"


def test_auth_router_rejects_runtime_without_auth_provider():
    with pytest.raises(ValueError, match="auth router requires"):
        create_app(
            runtime=create_empty_runtime(),
            include_auth_router=True,
        )


def test_auth_router_diagnoses_automatic_runtime_before_assembly(monkeypatch):
    calls = []

    class Diagnosis:
        ok = False

        def to_dict(self):
            return {"issues": [{"key": "KEYCLOAK_URL"}]}

    def diagnose_services(*, plan):
        calls.append(plan)
        return Diagnosis()

    monkeypatch.setattr(factory_module, "diagnose_services", diagnose_services)
    config = AppConfig(
        enabled_services=["keycloak"],
        required_services=["keycloak"],
    )

    with pytest.raises(ValueError, match="KEYCLOAK_URL"):
        create_app(config=config, include_auth_router=True)

    assert len(calls) == 1


def test_explicit_auth_provider_is_a_supported_test_and_customization_seam():
    class Provider:
        pass

    provider = Provider()
    app = create_app(
        runtime=create_empty_runtime(),
        include_auth_router=True,
        auth_provider=provider,
    )

    assert app.state.auth_provider is provider


def test_module_and_openapi_contract_assertions_check_semantic_contracts():
    router = APIRouter(prefix="/contracts")

    @router.get("", operation_id="list_contracts")
    async def list_contracts():
        return []

    module = DomainModule(name="contracts", routers=(router,))
    app = create_app(runtime=create_empty_runtime(), modules=[module])

    assert_module_contract(app, module)
    assert_openapi_contract(
        app,
        expected_paths={"/contracts": {"GET"}},
        expected_security_schemes=(),
    )


def test_openapi_contract_assertion_reports_missing_path():
    app = create_app(runtime=create_empty_runtime())

    with pytest.raises(AssertionError, match="/missing"):
        assert_openapi_contract(app, expected_paths={"/missing": {"GET"}})
