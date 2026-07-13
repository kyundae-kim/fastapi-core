# 코드 크기 축소 중심 리팩토링 방안

## 1. 목적

현재 동작과 핵심 공개 API를 가능한 한 유지하면서 `fastapi-core`의 구현 및 테스트 코드를 줄인다. 단순히 코드를 다른 파일로 이동하거나 과도한 helper를 추가해 파일별 줄 수만 줄이는 방식은 제외한다.

## 2. 현재 기준선

`pygount` 기준 Python code LOC:

| 구분 | 파일 수 | Code LOC |
|---|---:|---:|
| `fastapi_core/` | 18 | 1,272 |
| `test_fastapi_core/` | 13 | 1,581 |
| 합계 | 31 | 2,853 |

프로덕션 코드 상위 모듈:

| 모듈 | Code LOC | 관찰 |
|---|---:|---|
| `fastapi_core/factory.py` | 282 | 서비스 조립, readiness 연결, lifecycle, 앱 초기화가 집중됨 |
| `fastapi_core/extensions.py` | 246 | typed registry와 legacy state 호환 자료구조를 동시에 유지함 |
| `fastapi_core/routers/health.py` | 150 | registry 경로와 legacy state 경로가 함께 존재함 |
| `fastapi_core/http.py` | 128 | HTTP 오류 정규화와 correlation ID 처리 |
| `fastapi_core/config.py` | 114 | 환경변수 alias/파싱/검증 |

테스트 코드 상위 모듈:

| 모듈 | Code LOC |
|---|---:|
| `test_fastapi_core/test_factory.py` | 307 |
| `test_fastapi_core/test_extensions.py` | 209 |
| `test_fastapi_core/test_dependencies.py` | 178 |
| `test_fastapi_core/test_health_router.py` | 155 |
| `test_fastapi_core/test_config.py` | 128 |

기준 동작은 `uv run pytest -q` 실행에서 `90 passed`다.

## 3. 핵심 판단

가장 큰 축소 지점은 작은 함수의 문법 단축이 아니라 다음 두 개의 **중복 계약 제거**다.

1. readiness의 typed registry 계약과 legacy `app.state` dict/set 계약이 동시에 유지되는 구조
2. `docmesh_py_core`와 `fastapi_core`가 각각 보유한 서비스 클라이언트 조립 분기

테스트에서는 동일한 앱 생성, provider 실패, readiness 상태 조립을 테스트마다 반복하는 것이 가장 큰 축소 지점이다.

## 4. 권장 리팩토링

### P0. 축소 기준과 보호 계약 고정

**대상**
- `docs/srs.md`
- `docs/api.md`
- 전체 테스트

**방안**
- 공개 보호 대상은 `create_app`, router endpoint, 공개 dependency, schema, `ManagedResource`, `ReadinessCheckSpec`, `register_readiness_check`, `ErrorMapping`, `register_error_mapper`로 고정한다.
- 내부 `app.state.readiness_checks`, `readiness_services`, `required_services` 직접 수정은 제거 가능한 호환 경로로 분류한다. 이는 이미 `docs/srs.md:196`에서 내부 구현 세부로 정의돼 있다.
- 변경 전후에 `pygount`와 전체 pytest 결과를 기록한다.

**예상 효과**
- 직접 LOC 절감 없음.
- 이후 단계가 공개 API 제거가 아닌 내부 중복 제거임을 보장한다.

---

### P1. 공개·legacy 계약을 유지한 즉시 축소

이 단계는 breaking change 없이 먼저 적용할 수 있는 묶음이다.

#### P1-1. health 응답 조립 단일 순회

**근거**
- `fastapi_core/routers/health.py:20-35`의 `_build_service_detail()`은 `service_name`을 받지만 바로 버린다.
- `fastapi_core/routers/health.py:92-110`은 `request.app.state`를 반복 조회한다.
- `fastapi_core/routers/health.py:156-195`는 details 생성 후 필수 실패, 선택 실패, 로그 대상을 각각 다시 순회한다.

**방안**
- `state = request.app.state`로 기준 객체를 한 번만 잡는다.
- 사용하지 않는 `service_name` 인자를 제거한다.
- 실패 detail 목록을 한 번 만들고 상태 결정과 로그에 함께 사용한다.
- `HealthResponse`를 한 번 생성하고 `503`일 때만 `JSONResponse`로 감싼다.

**예상 절감:** 프로덕션 25~35 LOC

#### P1-2. readiness adapter와 중간 dict 제거

**근거**
- `fastapi_core/factory.py:130-154`는 Keycloak 인자 고정 closure와 client→check 중간 dict를 만든다.
- `fastapi_core/factory.py:198-206`은 이 dict를 다시 registry spec으로 변환한다.
- upstream `ServiceRuntime.checks`는 일반 서비스 check mapping을 이미 제공한다.

**방안**
- Keycloak만 `functools.partial()` adapter를 유지한다.
- 일반 서비스는 `runtime.checks`를 사용하고 registry에 바로 등록한다.
- `FASTAPI_CORE_TEST_SCOPE`의 앱 구성 시점 snapshot, async callable, `redact_errors=False`는 그대로 유지한다.

**예상 절감:** 프로덕션 15~25 LOC

#### P1-3. managed resource healthcheck 바인딩 축소

**근거**
- `fastapi_core/extensions.py:215-233`은 sync/async healthcheck별 closure를 따로 만든다.
- `_invoke_check()`가 이미 coroutine function과 반환된 awaitable을 모두 처리한다.

**방안**
- `_bind_healthcheck()`는 `functools.partial(healthcheck, value)`를 반환한다.
- async check가 thread로 넘어가지 않고 sync check는 계속 `asyncio.to_thread()`에서 실행되는지 회귀 테스트한다.

**예상 절감:** 프로덕션 12~18 LOC

#### P1-4. 작은 선언 반복 축소

- `factory.py:80-106`: settings 주입 경로의 서비스 factory 분기를 명시적 module-level mapping으로 바꾸면 8~14 LOC 절감할 수 있다. Keycloak, Langfuse `None`, NATS 타입의 특수 의미는 유지한다.
- `config.py:54-107`: `AliasChoices(field_name, ENV_NAME)` 생성 helper로 8~14 LOC 절감할 수 있다.
- 동적 함수 생성이나 숨은 registration은 사용하지 않는다.

**P1 묶음 예상 순절감:** 프로덕션 약 60~100 LOC

---

### P2. breaking release에서 readiness를 `ReadinessRegistry` 단일 경로로 통합

**근거**
- `fastapi_core/extensions.py:68-154`는 `specs` 외에도 `checks`, `services`, `required_services`를 중복 저장한다.
- `fastapi_core/extensions.py:100-118`의 `owns_legacy_state()`는 이 중복 자료구조의 동일성을 판별하기 위한 코드다.
- `fastapi_core/routers/health.py:91-136`은 registry 경로와 legacy state 경로를 선택해 같은 집계를 두 방식으로 실행한다.
- `fastapi_core/factory.py:324-326`은 registry 내부 자료구조를 legacy state 이름으로 다시 노출한다.
- `docs/srs.md:196`은 v0.3부터 공개 확장 계약을 `register_readiness_check(...)`와 `ReadinessCheckSpec`으로 규정한다.

**방안**
1. `ReadinessRegistry`를 단일 source of truth로 만든다.
2. `checks`, `services`, `required_services`, `owns_legacy_state()`를 제거하고 `specs`에서 필요한 check/metadata/required 집합을 계산한다.
3. health router는 `request.app.state.readiness_registry`만 읽고 `registry.check(...)`를 호출한다.
4. 공통 timeout/parallel 설정은 별도 state 복제 대신 `AppConfig` 또는 registry 설정에서 읽는다.
5. `test_health_router.py`의 직접 state 교체 테스트는 제거하거나 `register_readiness_check(...)` 기반 계약 테스트로 이동한다.
6. 문서에서 legacy state 직접 수정 예제를 제거한다.

**예상 절감**
- 프로덕션: 약 60~85 LOC
- 테스트: 약 60~100 LOC

**위험**
- `app.state.readiness_*`를 직접 수정하는 외부 소비자가 있다면 호환성이 깨진다.
- 따라서 minor release에서는 deprecation warning을 먼저 추가하고, 다음 breaking release에서 제거하거나, 현재 SRS의 내부 계약 판정을 근거로 즉시 제거할지 결정해야 한다.

**검증**
- 필수 실패 `503`, 선택 실패 `200/degraded`, 전체 timeout `503`, per-check timeout, error redaction, sync/async check 테스트를 유지한다.
- managed resource가 등록한 check도 동일 registry에서 동작하는지 검증한다.

---

### P3. 서비스 runtime 조립을 `docmesh_py_core`에 위임

**근거**
- `fastapi_core/factory.py:80-106`의 `_build_service_clients()`는 서비스 이름별 create 함수 분기를 직접 보유한다.
- 설치된 `docmesh_py_core`의 `assemble_services()`도 동일한 서비스별 create 분기를 보유한다.
- 기본 경로는 이미 `fastapi_core/factory.py:224-236`에서 `assemble_service_runtime(...)`에 위임한다.
- 중복은 명시적 `settings` 주입 경로(`factory.py:157-172`)를 지원하기 위해 남아 있다.

**권장 방안**
- `docmesh_py_core`에 설정 객체를 입력받는 공개 조립 API를 먼저 추가한다. 예: `assemble_service_runtime_from_configs(configs, *, services, required, one_of, ...)`.
- `fastapi_core`는 기본 환경변수 경로와 명시적 settings 경로 모두 upstream 조립 API만 호출한다.
- upstream API가 준비되면 다음을 삭제한다.
  - 서비스별 `create_*_client` import
  - `_build_service_clients()`
  - `_build_injected_service_runtime()`의 직접 validation/runtime 생성

**예상 절감**
- 이 저장소 프로덕션: 약 35~50 LOC
- 테스트: 약 20~35 LOC

**위험**
- 현재 설치된 `docmesh_py_core` 공개 API에는 설정 객체 기반 runtime 조립 함수가 없다.
- upstream 변경 없이 로컬 registry/dict로 if/elif만 치환하면 줄 수 감소는 작고, 특수 처리(Keycloak, Langfuse, NATS)가 숨겨져 오히려 읽기 어려워질 수 있다.
- 따라서 upstream 지원 전에는 현재 분기를 유지하는 편이 낫다.

**검증**
- 환경 기반 조립과 settings 주입 조립에서 동일한 `selected_services`, `required_services`, client 타입, startup check, rollback, shutdown 결과를 검증한다.

---

### P4. 반복 테스트를 fixture와 parametrize로 통합

#### P4-1. auth 실패 매핑 table-driven 테스트

**근거**
- `test_fastapi_core/test_auth_router.py:78-147`은 인증/설정/일시 장애가 동일한 준비·요청·로그 검증 구조를 반복한다.
- `fastapi_core/routers/auth.py:47-67`도 예외 타입별 status/detail/outcome을 if/elif로 반복한다.

**방안**
- `(exception, status_code, detail, outcome)`을 테스트 parameter로 만든다.
- 구현은 typed mapping tuple 또는 작은 immutable mapping으로 표현하되, unknown 예외 fallback은 별도로 유지한다.

**예상 절감**
- 프로덕션: 약 5~10 LOC
- 테스트: 약 30~45 LOC

#### P4-2. 공통 앱 fixture 제공

**근거**
- `create_app(settings=settings, include_auth_router=False)`와 empty service `AppConfig`가 여러 테스트 파일에서 반복된다.
- readiness 테스트는 check dict와 service metadata dict를 매번 함께 조립한다.

**방안**
- `test_fastapi_core/conftest.py`에 다음처럼 의미가 명확한 fixture/factory만 둔다.
  - `empty_app_factory(...)`
  - `auth_app_factory(provider=...)`
  - `register_check(app, name, check, required=..., timeout=..., redact=...)`
- endpoint별 결과 assertion은 각 테스트에 남겨 과도한 test DSL을 피한다.
- 비동기 단위 테스트는 기존 선호대로 `pytest.mark.asyncio` 함수와 `await`를 유지한다.
- `test_health_router.py`의 상태 설정 및 timeout 사례는 helper/parametrize로 47~60 LOC를 줄일 수 있다.
- `integration/test_readiness_with_live_services.py`는 서비스별 app fixture와 필수 서비스 사례를 factory/parametrize로 묶어 50~65 LOC를 줄일 수 있다. 복수 서비스 및 unreachable NATS 시나리오는 별도로 유지한다.
- `test_extensions.py`의 empty app 생성은 20~28 LOC, `test_dependencies.py`의 auth app 준비는 15~22 LOC 절감 후보다.

**예상 절감**
- 테스트: 겹치는 fixture 도입 비용을 포함해 약 120~160 LOC

#### P4-3. factory lifecycle 테스트 준비 코드 축소

**근거**
- `test_factory.py`에서 `events`를 기록하는 fake client/runtime/lifespan 클래스가 반복된다.

**방안**
- `_build_service_clients` monkeypatch 설치만 파일 로컬 helper로 묶는다.
- sync/async `check()`·`close()`가 각 테스트의 검증 대상이므로 작은 Client 클래스와 이벤트 assertion은 유지한다.
- startup 실패, custom shutdown 실패, async close를 configurable fake 하나로 합치지 않는다. 예외 우선순위와 rollback 의미가 흐려질 수 있다.

**예상 절감**
- 테스트: 약 8~12 LOC

---

### P5. 작은 축소는 동작 경계를 유지하는 범위에서만 수행

#### 유지 권장

- `fastapi_core/dependencies/services.py`의 typed getter들은 반복처럼 보이지만 IDE/type checker와 문서화된 공개 API를 제공한다. 동적 함수 생성으로 줄이지 않는다.
- `ManagedResource`의 sync/async 호출 및 역순 종료 로직은 오류·rollback 의미가 다르므로 무리하게 하나의 generic invoke helper로 합치지 않는다.
- `create_app()`의 state 초기화를 dataclass/builder로 옮기는 것은 총 LOC를 줄이지 못하고 간접 호출만 늘릴 가능성이 높다.
- 한 줄 comprehension, 중첩 lambda, 동적 registry로 물리적 줄 수만 줄이지 않는다.

#### 선택적 후보

- `dependencies/auth.py:15-37`의 role 중복 제거는 순서 보존 helper로 5~8 LOC 줄일 수 있으나 현재 코드가 더 명시적이므로 우선순위가 낮다.
- `dependencies/services.py:73-105`의 wrapped client getter 공통화는 공개 return type을 유지하면서 8~12 LOC 줄일 수 있을 때만 적용한다.
- JSON logging formatter를 `docmesh_py_core`의 공통 기능으로 올릴 수 있다면 `factory.py:48-77` 일부를 위임할 수 있으나, 한 저장소에서 다른 저장소로 코드를 이동하는 것만으로는 전체 시스템 크기 축소가 아니다.

## 5. 권장 실행 순서

1. **P4 테스트 중복 축소**: 동작 변경 없이 보호망을 간결하게 만든다.
2. **P1 즉시 축소**: health 조립, readiness adapter, resource binding을 legacy 호환 상태로 단순화한다.
3. 전체 pytest 및 LOC 재측정.
4. breaking release 범위가 확정되면 **P2 legacy readiness 제거**를 적용한다. minor release에서는 deprecation을 먼저 적용한다.
5. **P3 upstream runtime API 추가**: `docmesh_py_core` 변경과 릴리스를 먼저 완료한다.
6. `fastapi_core`에서 로컬 service factory 분기를 제거한다.
7. **P5 작은 축소**를 적용하되, 각 변경이 실제 순감소인지 diff로 확인한다.
8. API/설정/예제/테스트 문서를 현재 계약에 맞게 동기화한다.

## 6. 목표치

공개 기능을 유지하는 현실적인 1차 목표:

| 구분 | 현재 | 목표 | 예상 감소 |
|---|---:|---:|---:|
| 프로덕션 Code LOC | 1,272 | 1,122~1,162 | 110~150 (8.6~11.8%) |
| 테스트 Code LOC | 1,581 | 1,361~1,401 | 180~220 (11.4~13.9%) |
| 합계 | 2,853 | 2,483~2,563 | 290~370 (10.2~13.0%) |

P2 breaking 변경과 P3 upstream 변경을 제외하고 이 저장소만 먼저 정리하면 프로덕션 절감 폭은 약 60~100 LOC로 보는 것이 안전하다.

## 7. 완료 조건

- `uv run pytest -q` 전체 통과
- 공개 import/API 및 OpenAPI endpoint 계약 유지
- readiness 상태/HTTP status/error redaction/lifecycle rollback 회귀 없음
- `pygount` 기준 Code LOC가 단계별로 순감소
- 새 helper/fixture의 LOC를 포함한 **저장소 전체 순감소** 확인
- legacy readiness state를 제거할 경우 SRS/API/config/examples/test 문서 동기화
- upstream 위임 시 `docmesh_py_core` 최소 지원 버전 또는 git revision 갱신
