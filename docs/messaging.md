# fastapi-core 메시징 정의서

> 문서 목적: `fastapi-core`에서 메시징을 **현재 구현된 FastAPI lifecycle / service_clients / readiness 구조에 맞춰** 설명한다.
> 기준 문서: `docs/prd.md`, `docs/srs.md`, `docs/api.md`, `docs/config.md`
> 문서 상태: 구현 반영본(v0.7)

---

## 1. 문서 개요

이 문서는 NATS 자체의 일반론보다, `fastapi-core`가 **현재 코드에서 메시징 같은 외부 서비스를 어떤 위치에 두는지**에 초점을 둔다.

- 작성일: `2026-07-03`
- 작성자: `Hermes Agent`
- 버전: `v0.7`
- 상태: `implemented-surface`

핵심 질문은 다음과 같다.
- NATS 같은 서비스는 앱 조립 시 어디에서 선택되는가?
- readiness는 어떻게 연결되는가?
- startup / shutdown과 어떤 관계를 가지는가?
- 무엇이 1차 공개 API이고, 무엇이 확장 지점인가?

---

## 2. 현재 구현에서 메시징의 위치

`fastapi-core`에서 메시징은 독립 FastAPI 공개 API라기보다 **service_clients와 readiness 체계에 연결되는 외부 서비스 범주**다.

현재 코드 흐름:
1. 기본 `create_app(...)` 경로는 lifespan startup에서 `assemble_service_runtime(...)`으로 `ServiceRuntime`과 client map을 만든다.
2. `AppConfig.enabled_services`와 `required_services`를 assembly/runtime 및 readiness 정책에 전달한다.
3. 종료 시 내부 lifespan wrapper가 `await service_runtime.close()`를 호출한다.
4. 공통 서비스 접근용 `get_service_client(service_name)`와 NATS 전용 `get_nats_connection_builder()` dependency는 제공하지만, publisher/subscriber helper나 route는 현재 패키지에서 직접 제공하지 않는다.

즉, 현재 `fastapi-core`에서 메시징은:
- **1차 공개 FastAPI API**: 아님
- **앱 조립 시 선택 가능한 외부 서비스**: 맞음
- **readiness 및 lifecycle과 연결되는 확장 지점**: 맞음

---

## 3. 공개 표면과 확장 지점 구분

### 3.1 1차 공개 FastAPI 표면

현재 문서 세트에서 1차 공개 표면으로 보는 항목:
- `create_app(...)`
- auth / health router
- dependency (`get_config`, `get_settings`, `get_auth_provider`, `get_service_client`, `get_nats_connection_builder`, `get_current_user`, `require_permissions`)
- schema (`TokenResponse`, `UserInfo`, `HealthResponse`, `HealthServiceDetail`)

### 3.2 메시징 관련 확장 지점

메시징 쪽에서 현재 활용 가능한 확장 지점:
- `AppConfig.enabled_services`
- `AppConfig.required_services`
- `AppConfig.service_alternatives`
- `AppConfig.readiness_timeout_seconds`
- `AppConfig.readiness_overall_timeout_seconds`
- `load_docmesh_settings(...)`
- `app.state.service_runtime`
- `app.state.service_clients`
- `app.state.readiness_checks`
- `app.state.readiness_services`
- `app.state.required_services`
- custom lifespan

### 3.3 아직 직접 제공하지 않는 것

현재 `fastapi-core`가 직접 제공하지 않는 메시징 API:
- `get_nats_connection(request)` 같은 연결 상태 전용 FastAPI dependency
- NATS publisher/subscriber helper
- startup에서 연결 객체를 `app.state.nats`로 저장하는 기본 동작
- 연결 상태 객체를 노출하는 메시징 전용 기본 route/helper 세트

참고로 실제 NATS 연동은 `test_fastapi_core/integration/test_readiness_with_live_services.py`, `test_fastapi_core/integration/test_nats_lifespan.py`에서 별도로 검증된다.

---

## 4. 서비스 선택과 readiness 연결

메시징이 현재 코드에 반영되는 가장 직접적인 경로는 `enabled_services` / `required_services`다.

예시:

```python
from fastapi_core.config import AppConfig
from fastapi_core.factory import create_app

config = AppConfig(
    enabled_services=["keycloak", "nats"],
    required_services=["keycloak"],
)
app = create_app(config=config)
```

이 예시의 의미:
- `load_docmesh_settings(("keycloak", "nats"))` 경로를 사용할 수 있다.
- readiness 기본 체크는 `keycloak`, `nats` 두 서비스에 대해 구성된다.
- `keycloak` 실패는 `503 + error` 대상이다.
- `nats` 실패는 선택 서비스 실패이므로 `200 + degraded` 대상이 될 수 있다.

---

## 5. 현재 readiness 계약에서 메시징

`/health/readiness`는 메시징 상태를 직접 환경변수에서 읽지 않는다.
대신 app assembly에서 준비된 아래 state를 사용한다.

- `app.state.readiness_checks`
- `app.state.readiness_services`
- `app.state.required_services`
- `app.state.readiness_parallel`

기본 `create_app()` 경로에서는:
- `enabled_services`를 기준으로 service client 기반 check를 자동 생성한다.
- NATS 설정이 존재하고 `create_nats_client()`가 client를 생성하면 NATS check가 readiness 대상에 들어간다.
- `async_check_all_services(...)`가 sync/async check를 await 가능한 한 경로에서 집계한다.
- 필수 서비스 실패 시에도 `HealthCheckError.result`를 사용해 성공한 선택 서비스를 포함한 전체 details를 보존한다.
- `enabled_services` metadata와 실제 readiness check 등록은 별개다. 지원되지 않거나 settings에서 `None`인 서비스는 metadata에는 남아도 client/check가 생성되지 않는다.

상태 판정 규칙:
- 모든 서비스 성공 → `200`, `status="ok"`
- 선택 서비스만 실패 → `200`, `status="degraded"`
- 필수 서비스 실패 → `503`, `status="error"`

즉, 현재 메시징 문서에서 중요한 점은 **NATS가 readiness에 포함되는지 여부는 환경변수 이름 그 자체보다 `enabled_services` / `required_services`와 app.state 구성에 의해 결정된다**는 점이다.

---

## 6. lifecycle 연결 방식

### 6.1 현재 코드가 직접 보장하는 것

- 기본 `create_app()`는 lifespan startup에서 `assemble_service_runtime(...)`으로 NATS를 포함한 runtime/client를 구성한다.
- 명시적 `settings` 주입은 direct factory client를 동일한 `ServiceRuntime` lifecycle로 감싼다.
- 내부 lifespan wrapper는 사용자가 준 custom lifespan을 감싼다.
- custom lifespan은 runtime과 `app.state.service_runtime/service_clients`가 준비된 뒤 실행된다.
- lifespan 종료 시 `service_runtime.close()`를 await해 sync/async client를 모두 정리한다.
- client 정리는 `finally`에 있으므로 custom lifespan의 startup 또는 shutdown에서 예외가 발생해도 실행된다.
- NATS builder의 async `close()`도 await되며, 이전 동기 close helper 사용 시 발생하던 unawaited-coroutine 경고는 제거됐다.
- startup healthcheck 실패 시 조립된 NATS 등 client는 custom lifespan 진입 전에 rollback된다.
- close 실패는 client/error 원문을 구조화 payload에 넣지 않고 실패 개수만 기록한 `service_runtime_close_failed` 이벤트와 `ServiceCloseError`로 처리된다.

즉, `service_clients`가 관리하는 서비스 자원 정리는 shutdown 경로에 연결돼 있다.

### 6.2 사용자가 확장해야 하는 것

아래 패턴은 여전히 사용자 custom lifespan이 맡는다.
- 특정 메시징 연결 객체를 startup에서 생성
- `app.state.nats` 같은 이름으로 저장
- route/service layer에서 참조
- shutdown에서 세밀한 정리 로직 수행

권장 예시:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi_core import create_app

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 필요 시 메시징 연결/래퍼를 생성해 app.state에 저장
    yield
    # 필요 시 custom 정리

app = create_app(lifespan=lifespan)
```

---

## 7. dependency / handler integration

메시징 사용 방식은 현재 코드 기준으로 두 층으로 생각하면 된다.

### 방식 A. service_clients/readiness 중심
- `create_app()`가 만든 `app.state.service_clients`를 기반으로 서비스 client를 재사용
- readiness는 service client 기반 check를 사용
- 현재 기본 구현이 이 방식에 가깝다

### 방식 B. app.state 또는 custom dependency 확장
- startup/custom lifespan에서 `app.state.nats` 같은 객체 저장
- 필요 시 `get_nats_connection_builder()` 위에 프로젝트별 `get_nats_connection(request)` dependency를 별도로 정의
- endpoint/service layer가 이를 사용

현재 `fastapi-core`는 A를 기본 제공하고, B는 서비스별 확장 지점으로 남겨둔다.

개발 시 바로 참고할 수 있는 최소 패턴 예시:

```python
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi_core import create_app


def get_nats_connection(request: Request):
    return request.app.state.nats


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.nats = object()  # 실제 NATS client/wrapper로 교체
    try:
        yield
    finally:
        app.state.nats = None


app = create_app(lifespan=lifespan)


@app.get("/internal/nats-status")
async def nats_status(conn=Depends(get_nats_connection)):
    return {"configured": conn is not None}
```

이 예시는 현재 `fastapi-core`가 NATS builder 접근용 `get_nats_connection_builder()`는 제공하지만, 연결 상태 객체를 `app.state.nats`로 저장/관리하는 dependency는 기본 제공하지 않는다는 점을 전제로,
서비스 레이어에서 어떤 방식으로 `app.state` 확장을 붙여야 하는지 보여준다.

`get_nats_connection_builder()`의 현재 실패 계약:
- NATS가 활성화되지 않았거나 `app.state.service_clients`에 없으면 `503 Service Unavailable`과 `Service client 'nats' is not enabled`를 반환한다.
- 등록된 객체가 `NatsConnectionBuilder`가 아니면 `500 Internal Server Error`를 반환한다.

---

## 8. 설정 계약 요약

메시징 관련 대표 환경변수는 `docmesh_py_core.ServiceConfigs` 측에서 해석된다.
예:
- `NATS_SERVERS`
- `NATS_NAME`
- `NATS_CONNECT_TIMEOUT_SECONDS`
- `NATS_MAX_RECONNECT_ATTEMPTS`
- `NATS_USER`
- `NATS_PASSWORD`
- `NATS_TOKEN`
- `NATS_CREDS_FILE`

현재 `fastapi-core` 자체의 직접 연결점은 다음 두 수준이다.

1. **서비스 선택 수준**
   - `DOCMESH_SERVICES`
   - `READINESS_REQUIRED_SERVICES`

2. **settings fallback 수준**
   - `build_docmesh_env_overlay()`가 `NATS_SERVERS`, `NATS_TOKEN` 기본값을 채운다.

즉, `fastapi-core`는 메시징 세부 필드를 직접 해석하는 문서화보다, **서비스 선택과 readiness 정책에 어떻게 반영되는지**를 설명하는 것이 맞다.

---

## 9. 오류 처리 기준

현재 FastAPI 계층에서 메시징 관련 장애가 보이는 주요 경로는 readiness다.

원칙:
- 필수 서비스 실패는 `503 + error`
- 선택 서비스 실패는 `200 + degraded`
- 오류 문자열은 구조화 로그에 기록되며 마스킹 정책 영향을 받을 수 있다.

custom lifespan이나 route/service layer에서 별도 메시징 호출을 추가하는 경우에도:
- 민감정보 노출 금지
- startup 실패 정책 명시
- 선택/필수 서비스 구분 유지
를 따르는 것이 현재 구현과 맞다.

---

## 10. 테스트 포인트

기본 회귀(unit-like 테스트)에서는 메시징 자체가 직접 live 통합 검증되지는 않는다.
그러나 아래 관련 계약은 검증된다.

- 선택/필수 서비스 readiness 상태 분기 (`ok/degraded/error`)
- 필수 서비스 실패 시 성공한 선택 서비스를 포함한 전체 readiness details 보존
- 선택 서비스만 로딩하는 `load_docmesh_settings(("sqlite",))` 패턴
- async service client close await 및 custom shutdown 실패 시 cleanup 보장
- custom lifespan과 live NATS service client 공존
- `enabled_services=["nats"]`, `required_services=["nats"]` 구성에서 readiness `ok` 경로

아직 없는 테스트:
- custom `app.state.nats` dependency 패턴 테스트

---

## 11. 현재 권장 패턴

메시징을 현재 코드와 가장 잘 맞게 쓰는 방법은 다음과 같다.

1. `AppConfig.enabled_services`에 필요한 서비스를 선언한다.
2. readiness 필수 여부를 `required_services`로 결정한다.
3. 기본 service_clients/readiness 구성을 우선 활용한다.
4. 실제 연결 객체 주입이 필요하면 custom lifespan에서 `app.state`를 확장한다.
5. 메시징 전용 dependency/helper는 서비스 레이어에서 추가한다.

이 패턴은 현재 `fastapi-core`가 제공하는 public API와 확장 지점 경계를 가장 잘 보존한다.

---

## 12. 참고 문서

- `docs/prd.md`
- `docs/srs.md`
- `docs/api.md`
- `docs/config.md`
- `docs/examples.md`
- `fastapi_core/factory.py`
- `fastapi_core/docmesh_settings.py`
- `fastapi_core/routers/health.py`
- `test_fastapi_core/test_health_router.py`
- `test_fastapi_core/test_factory.py`

---

## 부록 A. 문서 상태 메모

이 문서는 기존의 NATS 일반론 중심 초안을, **현재 저장소 코드가 실제로 제공하는 service_clients/readiness/lifecycle 구조** 중심으로 다시 정렬한 것이다.
특히 메시징을 1차 공개 FastAPI API로 과장하지 않고, `enabled_services`, `required_services`, `app.state`, custom lifespan을 통한 확장 지점으로 명확히 구분했다.
v0.5에서는 native async readiness 집계, 전체 실패 결과 보존, async-aware shutdown cleanup과 예외 안전성을 반영했다.
v0.6에서는 기본 앱 경로의 assembly-first `ServiceRuntime`, required 검증, mapping 기반 설정, startup healthcheck 정책을 반영했다.
v0.7에서는 서비스 대안(`one_of`), per-service/overall timeout, startup rollback, runtime close 실패 로깅을 반영했다.
