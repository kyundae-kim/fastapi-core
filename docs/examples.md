# fastapi-core 사용 예제

이 문서는 현재 구현된 `fastapi-core 0.6.0` API를 기준으로 한다. 전체 API surface는 [`api.md`](api.md), 수용 기준은 [`srs.md`](srs.md)를 참조한다.

## ResourceBinding과 module

```python
from fastapi import APIRouter, Depends
from fastapi_core import DomainModule, ResourceBinding, TransportPolicy, create_app

class SearchClient:
    async def search(self, query: str) -> list[dict[str, str]]:
        return [{"query": query}]

    async def aclose(self) -> None:
        pass

search_client = ResourceBinding(
    "search-client",
    factory=lambda _app: SearchClient(),
    healthcheck=lambda client: True,
)

router = APIRouter(prefix="/documents", tags=["documents"])

@router.get("")
async def search(
    query: str,
    client: SearchClient = Depends(search_client.dependency),
):
    return await client.search(query)

module = DomainModule(
    name="documents",
    routers=(router,),
    resources=(search_client,),
    transport_policy=TransportPolicy(validation_status=400),
)

app = create_app(modules=(module,))
```

`ResourceBinding`은 `create_app(resources=[...])`의 최상위 입력으로도 사용할 수 있다. module에 포함한 자원은 같은 앱 registry와 lifespan을 공유한다.

## SDK health 결과 정규화

`ok` 필드를 가진 SDK 결과는 별도 lambda 없이 사용할 수 있다.

```python
from dataclasses import dataclass

@dataclass
class HealthStatus:
    ok: bool
    detail: str | None = None

client = ResourceBinding(
    "search-client",
    factory=lambda _app: SearchClient(),
    healthcheck=lambda value: HealthStatus(ok=True, detail="connected"),
)
```

SDK 결과가 `ok`를 제공하지 않으면 adapter를 명시한다.

```python
client = ResourceBinding(
    "search-client",
    factory=lambda _app: SearchClient(),
    healthcheck=lambda value: value.health(),
    health_result_adapter=lambda result: result.status == "ready",
)
```

## Module transport policy

공통 인증 dependency와 validation/OpenAPI 응답을 module에 함께 선언한다.

```python
from fastapi import Depends
from fastapi_core import TransportPolicy
from fastapi_core.schemas.error import ProblemDetail

policy = TransportPolicy(
    dependencies=(Depends(require_document_scope),),
    validation_status=400,
    include_synthetic_422=False,
    common_error_response_model=ProblemDetail,
    common_error_statuses=(400, 401, 403, 500),
)
```

이 policy는 health/auth router가 아니라 module route에만 적용된다. validation handler와 OpenAPI 모두 같은 status 정책을 사용한다.

## ExceptionMappingTable과 renderer

```python
from fastapi_core import ErrorMapping, ExceptionMappingTable

class SearchUnavailable(Exception):
    pass

errors = ExceptionMappingTable(
    {
        SearchUnavailable: ErrorMapping(
            status_code=503,
            detail="Search service unavailable",
            code="search_unavailable",
            headers={"Retry-After": "5"},
            extensions={"retryable": True},
        ),
    },
    fallback=ErrorMapping(
        status_code=500,
        detail="Internal server error",
        code="internal_error",
    ),
)

app = create_app(error_mapping_table=errors)
```

custom envelope가 필요하면 다음처럼 renderer를 선택한다.

```python
from fastapi_core import create_error_renderer

app = create_app(
    error_mapping_table=errors,
    error_renderer=create_error_renderer(
        problem_details=False,
        fallback_codes={503: "service_unavailable", 500: "internal_error"},
    ),
)
```

## Streaming과 자원 정리

```python
from fastapi_core import ManagedStreamingResponse

@router.get("/export")
async def export():
    export_resource = await create_export_resource()

    async def produce():
        try:
            async for chunk in export_resource.chunks():
                yield chunk
        finally:
            # 응답 helper가 resource close를 담당하므로 여기서 중복 close하지 않는다.
            pass

    return ManagedStreamingResponse(
        produce(),
        resource=export_resource,
        media_type="application/octet-stream",
    )
```

response가 정상 완료되거나 producer 오류, cancellation, disconnect로 종료되어도 `aclose()` 또는 `close()`는 한 번만 호출된다.

## ApplicationContractProfile

```python
from fastapi_core.testing import ApplicationContractProfile, assert_application_contract

profile = ApplicationContractProfile(
    module_names=("documents",),
    expected_paths={"/documents": {"GET"}},
    expected_responses={("/documents", "GET"): (400, 500)},
    validation_status=400,
    include_synthetic_422=False,
    expected_resource_names={"documents": ("search-client",)},
    expected_security_dependency_counts={"documents": 1},
)

assert_application_contract(app, profile)
```

profile은 실제 TestClient 요청으로 health와 auth inclusion을 확인하고, 생성된 OpenAPI에서 path/method/status/security/schema reference를 검사한다.
