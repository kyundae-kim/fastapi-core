from __future__ import annotations

import asyncio
import threading
import time
from dataclasses import dataclass

import pytest
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from pydantic import BaseModel

from fastapi_core import (
    DomainModule,
    DomainModuleProvider,
    ErrorMapping,
    ExceptionMappingTable,
    ManagedResource,
    ManagedStreamingResponse,
    ResourceBinding,
    TransportPolicy,
    create_app,
    create_error_renderer,
    invoke_resource,
)
from fastapi_core.runtime import create_empty_runtime
from fastapi_core.testing import (
    ApplicationContractProfile,
    assert_application_contract,
)


class Resource:
    def __init__(self) -> None:
        self.value = "ready"


class ErrorResponse(BaseModel):
    code: str
    message: str


@dataclass
class HealthStatus:
    ok: bool


class DomainError(Exception):
    pass


class ChildDomainError(DomainError):
    pass


def test_resource_binding_unifies_registration_and_typed_dependency():
    binding = ResourceBinding(
        "document-store",
        factory=lambda _app: Resource(),
        healthcheck=lambda _resource: True,
    )
    app = create_app(runtime=create_empty_runtime(), resources=[binding])

    @app.get("/resource")
    async def resource_route(resource: Resource = Depends(binding.dependency)):
        return {"value": resource.value}

    with TestClient(app) as client:
        response = client.get("/resource")

    assert response.status_code == 200
    assert response.json() == {"value": "ready"}
    assert app.state.resource_registry.bindings == (binding,)



def test_managed_resource_bind_returns_canonical_binding():
    resource = ManagedResource(
        "document-store",
        factory=lambda _app: Resource(),
    )

    binding = resource.bind()

    assert isinstance(binding, ResourceBinding)
    assert binding.key.name == "document-store"
    assert binding.managed_resource.name.name == "document-store"



def test_health_outcome_protocol_is_normalized_without_consumer_lambda():
    binding = ResourceBinding(
        "document-store",
        factory=lambda _app: Resource(),
        healthcheck=lambda _resource: HealthStatus(ok=False),
    )
    app = create_app(runtime=create_empty_runtime(), resources=[binding])

    with TestClient(app) as client:
        response = client.get("/health/readiness")

    assert response.status_code == 503
    assert response.json()["details"]["document-store"]["ok"] is False



def test_health_result_adapter_can_reject_an_opaque_sdk_result():
    binding = ResourceBinding(
        "document-store",
        factory=lambda _app: Resource(),
        healthcheck=lambda _resource: object(),
        health_result_adapter=lambda _result: False,
    )
    app = create_app(runtime=create_empty_runtime(), resources=[binding])

    with TestClient(app) as client:
        response = client.get("/health/readiness")

    assert response.status_code == 503



def test_transport_policy_applies_auth_validation_and_openapi_together():
    calls: list[str] = []

    def authorize() -> None:
        calls.append("authorized")

    router = APIRouter(prefix="/documents")

    @router.get("", response_model=list[str])
    async def list_documents(limit: int):
        return [str(limit)]

    policy = TransportPolicy(
        dependencies=(Depends(authorize),),
        validation_status=400,
        include_synthetic_422=False,
        common_error_response_model=ErrorResponse,
        fallback_response_model=ErrorResponse,
    )
    module = DomainModule(
        name="documents",
        routers=(router,),
        transport_policy=policy,
    )
    app = create_app(runtime=create_empty_runtime(), modules=[module])

    with TestClient(app) as client:
        response = client.get("/documents")
        health = client.get("/health/liveness")

    operation = app.openapi()["paths"]["/documents"]["get"]
    assert response.status_code == 400
    assert response.json()["detail"] == "Request validation failed"
    assert health.status_code == 200
    assert calls == ["authorized"]
    assert "422" not in operation["responses"]
    assert "400" in operation["responses"]
    assert "500" in operation["responses"]



def test_conflicting_module_transport_policies_fail_before_registration():
    first = DomainModule(
        name="first",
        transport_policy=TransportPolicy(validation_status=400),
    )
    second = DomainModule(
        name="second",
        transport_policy=TransportPolicy(validation_status=422),
    )

    with pytest.raises(ValueError, match="transport policy"):
        create_app(runtime=create_empty_runtime(), modules=[first, second])



def test_managed_streaming_response_closes_sync_resource_once():
    events: list[tuple[str, int]] = []
    response_thread = threading.get_ident()

    class StreamResource:
        def close(self) -> None:
            events.append(("close", threading.get_ident()))

    async def chunks():
        yield b"one"
        yield b"two"

    router = APIRouter()

    @router.get("/stream")
    async def stream():
        return ManagedStreamingResponse(
            chunks(),
            resource=StreamResource(),
            media_type="text/plain",
            headers={"X-Stream": "yes"},
        )

    app = create_app(runtime=create_empty_runtime(), routers=[router])
    with TestClient(app) as client:
        response = client.get("/stream")

    assert response.status_code == 200
    assert response.content == b"onetwo"
    assert response.headers["X-Stream"] == "yes"
    assert [name for name, _thread in events] == ["close"]
    assert events[0][1] != response_thread



def test_managed_streaming_response_closes_resource_when_producer_fails():
    events: list[str] = []

    class StreamResource:
        async def aclose(self) -> None:
            events.append("close")

    async def chunks():
        yield b"one"
        raise RuntimeError("producer failed")

    router = APIRouter()

    @router.get("/failing-stream")
    async def failing_stream():
        return ManagedStreamingResponse(chunks(), resource=StreamResource())

    app = create_app(runtime=create_empty_runtime(), routers=[router])
    with TestClient(app, raise_server_exceptions=False) as client:
        client.get("/failing-stream")

    assert events == ["close"]


@pytest.mark.asyncio
async def test_managed_streaming_response_closes_once_when_cancelled():
    events: list[str] = []
    started = asyncio.Event()
    release = asyncio.Event()

    class StreamResource:
        async def aclose(self) -> None:
            events.append("close")

    async def chunks():
        started.set()
        await release.wait()
        yield b"never-reached"

    async def receive():
        await asyncio.sleep(0.01)
        return {"type": "http.request"}

    async def send(_message):
        return None

    response = ManagedStreamingResponse(chunks(), resource=StreamResource())
    task = asyncio.create_task(
        response(
            {"type": "http", "method": "GET", "path": "/stream", "headers": []},
            receive,
            send,
        )
    )
    await asyncio.wait_for(started.wait(), timeout=1)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert events == ["close"]


def test_exception_mapping_table_uses_most_specific_mapping_and_fallback():
    table = ExceptionMappingTable(
        mappings={
            DomainError: ErrorMapping(409, "domain", code="domain_error"),
            ChildDomainError: ErrorMapping(
                410,
                "child",
                code="child_error",
                headers={"X-Domain": "child"},
                extensions={"scope": "document"},
            ),
        },
        fallback=ErrorMapping(500, "fallback", code="fallback_error"),
    )
    router = APIRouter()

    @router.get("/failure")
    async def failure():
        raise ChildDomainError("secret")

    app = create_app(
        runtime=create_empty_runtime(),
        routers=[router],
        error_mapping_table=table,
        error_renderer=create_error_renderer(problem_details=False),
    )

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/failure")

    assert response.status_code == 410
    assert response.headers["X-Domain"] == "child"
    assert response.json() == {
        "error": {
            "code": "child_error",
            "message": "child",
            "correlation_id": response.headers["X-Correlation-ID"],
            "metadata": {"scope": "document"},
        }
    }


def test_exception_mapping_table_rejects_duplicate_and_unreachable_entries():
    with pytest.raises(ValueError, match="already registered"):
        ExceptionMappingTable.from_specs(
            [
                (DomainError, ErrorMapping(409, "one")),
                (DomainError, ErrorMapping(409, "two")),
            ]
        )

    with pytest.raises(ValueError, match="unreachable"):
        ExceptionMappingTable(
            mappings={Exception: ErrorMapping(500, "catch-all")},
            fallback=ErrorMapping(500, "fallback"),
        )

    with pytest.raises(TypeError, match="Exception types"):
        ExceptionMappingTable(mappings={str: ErrorMapping(500, "invalid")})



def test_standard_error_renderer_uses_status_fallback_code():
    router = APIRouter()

    @router.get("/failure")
    async def failure():
        raise ValueError("token=secret")

    app = create_app(
        runtime=create_empty_runtime(),
        routers=[router],
        error_renderer=create_error_renderer(
            problem_details=False,
            fallback_codes={500: "internal_error"},
        ),
    )

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/failure")

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    assert response.json()["error"]["message"] == "Internal Server Error"
    assert "secret" not in response.text



@pytest.mark.asyncio
async def test_resource_binding_call_executes_sync_and_async_methods():
    binding = ResourceBinding("sdk", factory=lambda _app: Resource())
    events: list[str] = []
    event_loop_thread = threading.get_ident()

    def sync_call(value: str) -> str:
        events.append(f"sync:{threading.get_ident()}")
        return value

    async def async_call(value: str) -> str:
        events.append("async")
        await asyncio.sleep(0)
        return value

    assert await binding.call(sync_call, "one") == "one"
    assert await binding.call(async_call, "two") == "two"
    assert events[0] != f"sync:{event_loop_thread}"
    assert events[1] == "async"


@pytest.mark.asyncio
async def test_resource_executor_awaits_sync_awaitable_and_applies_timeout():
    binding = ResourceBinding("sdk", factory=lambda _app: Resource())

    async def delayed_result() -> str:
        await asyncio.sleep(0)
        return "awaited"

    def sync_returns_awaitable() -> object:
        return delayed_result()

    assert await binding.call(sync_returns_awaitable) == "awaited"

    def blocking_call() -> None:
        time.sleep(0.05)

    with pytest.raises(asyncio.TimeoutError):
        await binding.call(blocking_call, timeout_seconds=0.001)


@pytest.mark.asyncio
async def test_resource_executor_propagates_cancellation():
    started = asyncio.Event()

    async def slow_call() -> None:
        started.set()
        await asyncio.sleep(1)

    task = asyncio.create_task(invoke_resource(slow_call))
    await started.wait()
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task



def test_application_contract_profile_combines_runtime_and_openapi_assertions():
    router = APIRouter(prefix="/documents")

    def authorize() -> None:
        return None

    @router.get("", operation_id="list_documents")
    async def list_documents():
        return []

    policy = TransportPolicy(
        dependencies=(Depends(authorize),),
        common_error_response_model=ErrorResponse,
    )
    binding = ResourceBinding(
        "document-store",
        factory=lambda _app: Resource(),
    )
    module = DomainModule(
        name="documents",
        routers=(router,),
        resources=(binding,),
        transport_policy=policy,
    )
    app = create_app(runtime=create_empty_runtime(), modules=[module])
    profile = ApplicationContractProfile(
        module_names=("documents",),
        expected_paths={"/documents": {"GET"}},
        expected_security_schemes=(),
        auth_router_included=False,
        expected_transport_policies={"documents": policy},
        expected_security_dependency_counts={"documents": 1},
        expected_common_error_statuses={"documents": (400, 500)},
        expected_resource_names={"documents": ("document-store",)},
    )

    assert_application_contract(app, profile)


def test_domain_module_provider_is_an_explicit_callable_convention():
    def build_documents_module() -> DomainModule:
        return DomainModule(name="documents")

    assert isinstance(build_documents_module, DomainModuleProvider)
    assert build_documents_module().name == "documents"
