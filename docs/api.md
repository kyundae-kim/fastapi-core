# fastapi-core API Reference

> 기준 릴리스: `fastapi-core 0.7.0`
>
> 상태: current-implementation
>
> 구체 수용 기준은 [`docs/srs.md`](srs.md), capability 기준은 [`docs/prd.md`](prd.md)에서 관리한다.

## 1. 애플리케이션 조립

```python
from fastapi_core import create_app

app = create_app(
    routers=(),
    modules=(),
    resources=(),
    transport_policy=None,
    error_mapping_table=None,
)
```

`create_app`은 다음 확장 입력을 지원한다.

- `resources`: `ManagedResource[T]` 또는 `ResourceBinding[T]`의 순서 있는 목록
- `modules`: `DomainModule`의 순서 있는 목록
- `transport_policy`: 직접 전달한 router에 적용할 앱 기본 transport policy
- `error_mapping_table`: table-driven exception mapping
- `error_renderer`: 앱 기본 error renderer

앱 생성 시 다음 상태를 확인할 수 있다.

- `app.state.resource_registry`
- `app.state.resource_bindings`
- `app.state.readiness_registry`
- `app.state.transport_policy`
- `app.state.transport_policies`
- `app.state.error_mapping_table`
- `app.state.domain_modules`

health와 auth router에는 domain module policy가 자동 전파되지 않는다.

## 2. ResourceBinding

`ResourceBinding[T]`는 자원 이름, factory, dependency, readiness, close 및 health result adapter를 하나의 선언으로 묶는다.

```python
from typing import Any
from fastapi_core import ResourceBinding

class DocumentStore:
    def search(self, query: str) -> list[dict[str, Any]]:
        ...

    def close(self) -> None:
        ...


document_store = ResourceBinding(
    "document-store",
    factory=lambda _app: DocumentStore(),
    healthcheck=lambda store: store.ping(),
    required=True,
)
```

binding은 기존 `ResourceKey` dependency와 같은 typed dependency를 제공한다.

```python
from fastapi import APIRouter, Depends

router = APIRouter()

@router.get("/documents")
async def list_documents(
    store: DocumentStore = Depends(document_store.dependency),
):
    return store.search("*")
```

기존 소비자는 `ManagedResource(...).bind()`로 migration할 수 있다. `create_app(resources=[...])`는 두 타입을 모두 받고, lifecycle 종료 시 `aclose()`를 우선하고 없으면 `close()`를 호출한다.

### Health result

- `True`, `None`: 성공
- `False`: 실패
- `HealthCheckResult`: 기존 하위 service 결과로 확장
- `HealthOutcome` 또는 `ok` attribute를 가진 SDK 결과: `ok`를 기준으로 정규화
- SDK가 별도 형식을 사용하면 `health_result_adapter`를 제공

opaque legacy sentinel은 기존 0.6.0 호환을 위해 허용된다. 엄격한 해석이 필요하면 adapter가 `False`를 반환하도록 선언한다.

## 3. Resource invocation

`invoke_resource`와 `ResourceBinding.call`은 coroutine을 직접 await하고 sync callable을 worker thread에서 실행한다.

```python
result = await document_store.call(
    "search",
    "invoice",
    instance=store,
    timeout_seconds=2.0,
)
```

sync 함수가 awaitable을 반환하는 경우도 자동으로 완료까지 await한다. timeout은 `asyncio.TimeoutError`로 전달되고, caller cancellation과 원래 예외는 숨기지 않는다.

## 4. DomainModule과 TransportPolicy

```python
from fastapi import APIRouter, Depends
from fastapi_core import DomainModule, TransportPolicy

router = APIRouter(prefix="/documents", tags=["documents"])

policy = TransportPolicy(
    dependencies=(Depends(require_document_scope),),
    validation_status=400,
    include_synthetic_422=False,
    common_error_response_model=ProblemDetail,
)

module = DomainModule(
    name="documents",
    routers=(router,),
    resources=(document_store,),
    transport_policy=policy,
)
```

`TransportPolicy`의 주요 필드:

- `dependencies`: module route에만 적용되는 공통 security/auth dependency
- `validation_status`, `validation_response_model`: request validation 오류 계약
- `common_error_response_model`, `common_error_statuses`: 공통 오류 OpenAPI 응답
- `fallback_response_model`: fallback 오류 응답 모델
- `responses`: 추가 FastAPI response metadata
- `error_renderer`: 해당 route의 renderer
- `include_synthetic_422`: OpenAPI synthetic 422 유지 여부

동일 policy는 route dependency/handler와 OpenAPI response 생성에 함께 사용된다. 위 설정은 invalid request를 400으로 반환하고 해당 operation의 synthetic 422를 제거한다. policy를 생략하면 기존 422 기본 계약이 유지된다.

module provider는 명시적 callable convention으로 작성한다.

```python
from fastapi_core import DomainModule

def build_documents_module(settings) -> DomainModule:
    return DomainModule(name="documents")
```

framework는 provider를 자동 discovery하지 않는다.

## 5. Error mapping과 renderer

```python
from fastapi_core import ErrorMapping, ExceptionMappingTable, create_app

class DocumentNotFound(Exception):
    pass

error_table = ExceptionMappingTable(
    {
        DocumentNotFound: ErrorMapping(
            status_code=404,
            detail="Document not found",
            code="document_not_found",
        ),
    },
    fallback=ErrorMapping(status_code=500, detail="Request failed", code="request_failed"),
)

app = create_app(error_mapping_table=error_table)
```

예외 table은 예외 class MRO에서 가장 구체적인 mapping을 선택한다. mapping의 `headers`와 `extensions`는 renderer까지 보존된다. 중복 선언과 fallback에 도달할 수 없는 `Exception` mapping은 생성 시 거부된다.

표준 renderer는 조합 가능한 factory로 만들 수 있다.

```python
from fastapi_core import create_error_renderer

renderer = create_error_renderer(
    problem_details=False,
    fallback_codes={404: "not_found", 500: "internal_error"},
)
app = create_app(error_renderer=renderer)
```

renderer는 correlation ID를 body와 `X-Correlation-ID` response header에 모두 제공한다. 기본 모드는 `application/problem+json`이며, envelope mode에서는 안전한 `error` 객체를 반환한다.

## 6. ManagedStreamingResponse

```python
from fastapi_core import ManagedStreamingResponse

async def stream_documents():
    yield b"document-1\n"
    yield b"document-2\n"

response = ManagedStreamingResponse(
    stream_documents(),
    resource=store,
    media_type="application/x-ndjson",
)
```

응답은 sync/async iterator와 기존 `StreamingResponse`의 status, headers, media type, background task metadata를 보존한다. producer 정상 종료, producer exception, client disconnect 및 cancellation에서도 resource를 한 번만 닫는다. sync close는 worker thread에서 실행한다.

## 7. Contract testing

```python
from fastapi_core.testing import (
    ApplicationContractProfile,
    assert_application_contract,
)

profile = ApplicationContractProfile(
    module_names=("documents",),
    expected_paths={"/documents": {"GET"}},
    expected_responses={("/documents", "GET"): (400, 500)},
    validation_status=400,
    include_synthetic_422=False,
)

assert_application_contract(app, profile)
```

profile assertion은 health, auth router inclusion, module router/resource/readiness/error mapper, OpenAPI path/method/status/security scheme, operation ID와 schema reference를 의미 기반으로 검증한다. 전체 OpenAPI JSON snapshot을 요구하지 않는다.
