# fastapi-core 소비사 앱 조립 부담 개선 구현 계획

## 1. 목표

소비사가 별도 외부 인프라 없이 앱을 생성하고, 필요한 경우에만 `ServiceRuntime`과 `ManagedResource`를 명시적으로 주입하도록 소스 코드의 기본 계약을 정리한다.

핵심 목표는 다음 세 가지다.

1. `create_app()`이 외부 서비스 설정 없이 실제 lifespan에 진입한다.
2. `create_app(config=..., runtime=...)`를 유일한 앱 factory 계약으로 유지한다.
3. runtime/resource/readiness/error 접근은 공개 dependency와 descriptor를 통해 수행하며 소비사가 `app.state` 키를 알 필요가 없게 한다.

## 2. 구현 원칙

- `create_app` 외에 동급 앱 factory를 여러 개 추가하지 않는다.
- 제거된 `settings=` 주입 경로를 다시 도입하지 않는다.
- `ServiceRuntime`은 DocMesh 서비스 설정, client, healthcheck, close의 유일한 소유자로 유지한다.
- `ManagedResource`는 애플리케이션 고유 SDK의 factory, readiness, close 소유권을 선언하는 표준 descriptor로 유지한다.
- resource 객체의 메서드 이름을 암묵적으로 탐색해 readiness를 등록하지 않는다. `healthcheck=`를 명시적으로 선언한다.
- `dms-core` 같은 소비사 SDK를 `fastapi-core`의 필수 또는 선택적 런타임 의존성으로 추가하지 않는다.
- 각 단계는 테스트를 먼저 추가한 뒤 최소 소스 변경으로 통과시킨다.
- 각 PR의 마지막 검증은 `uv run pytest -q` 전체 suite로 수행한다.

## 3. 실행 순서

### 단계 0. 현재 공개 계약 characterization 강화

목적은 이후 기본값 변경이 의도하지 않은 API 파손으로 이어지지 않도록 현재 경계를 먼저 고정하는 것이다.

대상 파일:

- `test_fastapi_core/test_public_api.py`
- `test_fastapi_core/test_factory.py`
- `test_fastapi_core/test_dependencies.py`
- `test_fastapi_core/test_extensions.py`
- `test_fastapi_core/test_http.py`

추가·정리할 테스트:

1. package-root export와 dependency export 집합을 고정한다.
2. `create_app(config=None, *, runtime=None, lifespan=None, include_auth_router=..., resources=(), error_renderer=None)` 시그니처를 고정한다.
3. 명시적 runtime은 재조립하지 않고 동일 객체를 lifecycle에서 닫는지 검증한다.
4. managed resource 생성 순서, 역순 종료, 부분 startup rollback, 종료 오류 집계를 고정한다.
5. required/optional readiness의 `503 error`와 `200 degraded` 계약을 고정한다.
6. 기본 Problem Details 및 custom mapper/renderer 계약을 고정한다.

완료 조건:

- 이후 단계에서 의도적으로 변경할 기본값 외의 공개 계약이 테스트로 보호된다.
- 전체 suite가 통과한다.

---

### 단계 1. `create_app()`을 외부 의존성 없는 기본 앱으로 변경

이 단계가 최우선 소스 변경이다.

대상 파일:

- `fastapi_core/config.py`
- `fastapi_core/factory.py`
- `fastapi_core/runtime.py`
- `fastapi_core/lifecycle.py`
- `test_fastapi_core/test_config.py`
- `test_fastapi_core/test_factory.py`
- `test_fastapi_core/test_health_router.py`
- `test_fastapi_core/test_public_api.py`

테스트를 먼저 추가한다.

1. 환경변수를 제공하지 않은 `create_app()`이 `TestClient` lifespan에 진입한다.
2. 기본 앱의 `/health/liveness`가 `200 + status=ok`를 반환한다.
3. 기본 앱의 `/health/readiness`가 `200 + status=ok`를 반환한다.
4. 기본 runtime의 `selected_services`, `required_services`, `clients`가 비어 있다.
5. 기본 startup에서 Keycloak, PostgreSQL, NATS 등 서비스 설정 loader나 client factory가 호출되지 않는다.
6. 기본 앱 종료 시 빈 runtime close가 정상 완료된다.

소스 변경:

1. `AppConfig.enabled_services` 기본값을 빈 목록으로 변경한다.
2. `AppConfig.required_services` 기본값을 빈 목록으로 변경한다.
3. 빈 서비스 선택에서는 `RuntimePlan`이나 upstream 자동 탐색 경로를 거치지 않고 현재의 명시적 빈 `ServiceRuntime` 경로를 사용한다.
4. `include_auth_router` 기본값은 다음 기준으로 결정한다.
   - auth endpoint 자체도 opt-in 계약으로 볼 경우 `False`로 변경한다.
   - route 존재는 유지하되 미설정 시 `503`을 반환하는 계약을 유지할 경우 `True`를 유지한다.
5. 기본 앱의 목표가 “최소 서비스 앱”인 만큼 권장안은 `include_auth_router=False`이며, 이 경우 시그니처 계약 테스트도 의도적으로 갱신한다.

완료 조건:

- 깨끗한 프로세스 환경에서 `create_app()`만으로 두 health endpoint가 동작한다.
- 외부 설정 누락 오류가 발생하지 않는다.
- 명시적으로 서비스를 활성화한 기존 경로는 유지된다.

---

### 단계 2. 선택 서비스만 조립한다는 runtime 경계 검증

현재 기본 앱 실행에서 의도하지 않은 PostgreSQL 설정까지 요구될 수 있으므로, 서비스 선택과 upstream 설정 탐색 범위를 분리해 검증한다.

대상 파일:

- `fastapi_core/runtime.py`
- `fastapi_core/docmesh_settings.py`
- `test_fastapi_core/test_config.py`
- `test_fastapi_core/test_factory.py`
- `test_fastapi_core/integration/conftest.py`

테스트를 먼저 추가한다.

1. `enabled_services=["keycloak"]`이면 Keycloak 설정만 요구한다.
2. `enabled_services=["sqlite"]`이면 SQLite 설정만 로드한다.
3. 빈 선택이면 어떤 서비스 설정도 로드하지 않는다.
4. `required_services`가 `enabled_services`에 포함되지 않으면 app 생성 시 검증 오류가 발생한다.
5. 명시적 runtime 주입 시 process environment와 `AppConfig.enabled_services`를 이용해 runtime을 다시 만들지 않는다.

소스 변경:

1. `build_runtime_plan()`의 서비스 목록이 upstream assembly에 정확히 전달되는지 확인한다.
2. upstream v0.4.0 assembly가 plan 외 서비스를 탐색한다면 public API 범위에서 선택 서비스만 로드하는 안전한 조립 경로를 구성한다.
3. silent fallback으로 다른 서비스 설정을 탐색하지 않는다.
4. upstream 계약으로 해결할 수 없는 경우 명확한 `ConfigError` 또는 app-level validation error를 발생시킨다.

완료 조건:

- 활성화하지 않은 서비스의 환경변수 누락이 startup을 막지 않는다.
- 자동 조립, 빈 서비스 모드, prebuilt runtime 주입 세 경로의 책임이 분리된다.

---

### 단계 3. 단일 앱 조립 계약을 소스 수준에서 고정

새 factory를 추가하기보다 현재 `create_app`의 두 조립 모드를 명확히 고정한다.

대상 파일:

- `fastapi_core/factory.py`
- `fastapi_core/lifecycle.py`
- `fastapi_core/runtime.py`
- `fastapi_core/__init__.py`
- `test_fastapi_core/test_factory.py`
- `test_fastapi_core/test_public_api.py`

고정할 계약:

1. `runtime is None`
   - lifespan startup에서 환경 기반 runtime을 한 번 조립한다.
   - runtime을 app에 설치한 뒤 readiness를 등록한다.
   - framework lifespan이 runtime close를 소유한다.
2. `runtime is not None`
   - 전달된 runtime을 그대로 설치한다.
   - 재조립하거나 재설정하지 않는다.
   - runtime의 required-service metadata를 readiness에 반영한다.
   - framework lifespan이 동일 runtime close를 소유한다.
3. `config`
   - FastAPI 조립, auth router, CORS, logging, readiness/startup 정책만 소유한다.
4. `runtime`
   - 서비스 설정, client, healthcheck, close를 소유한다.

추가하지 않을 API:

- `create_test_app()`
- `create_runtime_from_environment()`의 성급한 package-root export
- `settings=` compatibility layer

환경 기반 runtime을 앱 외부에서 미리 진단해야 하는 실제 소비사 요구가 확인될 때만 별도 async assembly API 공개를 검토한다.

완료 조건:

- package root와 type hint가 하나의 `create_app` 계약만 노출한다.
- 자동 조립과 runtime 주입 경로의 lifecycle/readiness parity 테스트가 통과한다.

---

### 단계 4. resource/readiness를 공식 SDK 통합 계약으로 강화

현재 `ManagedResource`와 `ResourceKey`를 유지하면서 빠진 경계만 보강한다.

대상 파일:

- `fastapi_core/resources.py`
- `fastapi_core/readiness.py`
- `fastapi_core/schemas/health.py`
- `fastapi_core/extensions.py`
- `fastapi_core/__init__.py`
- `test_fastapi_core/test_extensions.py`
- `test_fastapi_core/test_health_router.py`

검증 및 필요한 최소 변경:

1. sync factory와 async factory를 모두 지원한다.
2. 명시적 `close=`, `aclose()`, `close()` 우선순위를 고정한다.
3. sync/async close 반환값이 awaitable이면 반드시 await한다.
4. startup 실패 시 생성 완료된 resource만 역순 rollback한다.
5. 여러 종료 실패는 `BaseExceptionGroup`으로 집계한다.
6. `healthcheck=`가 있으면 readiness가 자동 등록되고 종료 시 해제된다.
7. bool 및 `HealthCheckResult` 반환을 지원한다.
8. structured child detail은 `resource.child` 이름으로 namespace 처리한다.
9. parent resource의 required/redaction 정책이 child detail에도 적용된다.
10. startup healthcheck가 활성화된 경우 required managed resource만 startup blocker가 된다.
11. `ResourceKey[T]` 하나를 registration과 typed dependency에서 함께 사용한다.

새 Protocol이나 adapter class는 위 계약으로 표현할 수 없는 실제 SDK가 확인될 때만 추가한다. 단순히 `factory/healthcheck/close`를 다시 감싸는 중복 abstraction은 만들지 않는다.

완료 조건:

- 일반 SDK lifecycle/readiness 통합에 소비사 자체 registry 또는 `app.state` 조작이 필요하지 않다.
- 기존 public dataclass field/default 계약을 불필요하게 변경하지 않는다.

---

### 단계 5. 공개 dependency로 app state 접근 완전 캡슐화

대상 파일:

- `fastapi_core/dependencies/services.py`
- `fastapi_core/dependencies/config.py`
- `fastapi_core/dependencies/__init__.py`
- `fastapi_core/resources.py`
- `fastapi_core/readiness.py`
- `test_fastapi_core/test_dependencies.py`
- `test_fastapi_core/test_public_api.py`

구현 내용:

1. `get_service_runtime()`을 runtime 접근의 유일한 공개 dependency로 유지한다.
2. `get_service_client(name)`을 generic service client 접근 경로로 유지한다.
3. 서비스별 typed dependency는 실제 반환 타입을 보존한다.
4. `get_resource(name)`과 `ResourceKey[T].dependency`를 managed resource 접근 경로로 유지한다.
5. runtime/resource 미준비는 `503`, 타입 불일치는 `500`으로 고정한다.
6. 새 공개 기능이 readiness registry 자체를 요구하지 않는 한 `app.state.readiness_registry`를 반환하는 공개 dependency는 추가하지 않는다.
7. 내부 state key 조회는 각 소유 모듈의 accessor로 한정해 키 문자열이 여러 모듈에 중복되지 않게 한다.

완료 조건:

- 소비사 route 예제를 `app.state` 직접 접근 없이 작성할 수 있다.
- 폐기된 `app.state.settings`와 `app.state.service_clients` fallback이 재도입되지 않는다.

---

### 단계 6. 기본 오류 매핑 표면 보강

대상 파일:

- `fastapi_core/http.py`
- `fastapi_core/schemas/error.py`
- `fastapi_core/__init__.py`
- `test_fastapi_core/test_http.py`
- `test_fastapi_core/test_public_api.py`

구현 내용:

1. HTTP exception, validation error, unhandled exception에 대한 현재 Problem Details 기본 동작을 유지한다.
2. correlation ID와 민감정보 masking을 모든 mapper 결과에 적용한다.
3. `register_error_mapper()`의 sync/async mapper 지원을 유지한다.
4. DocMesh 공통 exception 중 HTTP 의미가 안정적인 유형만 built-in mapping 후보로 검토한다.
5. DMS 도메인 exception은 core에 직접 결합하지 않고 DMS adapter/example에서 mapper 집합으로 제공한다.
6. 기본 renderer를 외부에서 직접 참조해야 하는 소비사 요구가 확인되면 private `_problem_renderer`를 안정적인 공개 이름으로 승격하고 export/signature 테스트를 추가한다. 자동 설치만 필요한 현재 경로에서는 불필요한 export를 늘리지 않는다.

완료 조건:

- 기본 앱은 별도 renderer 설정 없이 RFC 7807 응답을 제공한다.
- domain adapter는 renderer를 다시 구현하지 않고 `ErrorMapping`만 반환할 수 있다.

---

### 단계 7. 소비사 contract test helper 추가

대상 파일:

- 신규 `fastapi_core/testing.py`
- `fastapi_core/__init__.py` 또는 별도 `fastapi_core.testing` 공개 모듈
- 신규 `test_fastapi_core/test_testing.py`
- `test_fastapi_core/test_public_api.py`

1차 제공 범위:

1. 외부 서비스가 없는 빈 `ServiceRuntime` 생성 helper
2. sync/async close 여부를 기록하는 managed-resource probe
3. readiness 성공/필수 실패/선택 실패 결과 assertion helper
4. app lifespan 진입과 cleanup 검증에 사용할 context helper
5. auth router opt-in/out contract assertion helper

설계 원칙:

- pytest 자체를 runtime dependency로 추가하지 않는다.
- 처음에는 framework-neutral helper를 제공한다.
- 실제 소비사 반복 사용이 확인된 뒤 pytest fixture/plugin으로 확장한다.
- test helper가 production app의 별도 조립 경로를 만들지 않게 한다.

완료 조건:

- 소비사가 자체적으로 빈 runtime과 cleanup probe를 반복 구현하지 않아도 된다.
- helper로 검증한 앱도 실제 `create_app()` lifespan을 사용한다.

---

### 단계 8. dms-core reference integration으로 계약 검증

이 단계의 목적은 새 core abstraction을 추가하는 것이 아니라 단계 4~7의 공개 계약이 실제 SDK 통합을 충분히 표현하는지 검증하는 것이다.

대상 경로:

- 신규 `examples/dms_service/` 또는 별도 integration test 경로
- 신규 `test_fastapi_core/integration/test_dms_resource.py`
- 필요 시 최소한의 `fastapi_core` source 보완

검증할 통합 경로:

1. `ManagedResource`로 DMS SDK 생성
2. `ResourceKey[DmsSdk]`로 route dependency 주입
3. SDK health 결과를 readiness에 연결
4. SDK sync/async 종료 보장
5. upload/download stream의 정상·예외 경로 close 보장
6. HTTP 응답에서 공개 metadata DTO만 반환
7. 내부 storage key 비노출
8. 삭제 문서 read 경계 검증
9. DMS domain error를 `ErrorMapping`으로 변환

제약:

- DMS SDK를 `fastapi-core` 기본 dependency로 추가하지 않는다.
- DMS SDK가 없는 환경에서는 integration test만 명시적으로 skip한다.
- 통합 과정에서 공통적으로 필요한 기능이 확인될 때만 `ManagedResource`, dependency 또는 error mapping API를 확장한다.

완료 조건:

- DMS 예제가 private app state나 private fastapi-core 모듈을 사용하지 않는다.
- stream과 SDK resource가 정상·오류 경로 모두에서 닫힌다.

## 4. 권장 PR 분할

### PR 1 — 서비스 없는 기본 앱

- 단계 0 characterization 보강
- `AppConfig`의 빈 서비스 기본값
- 기본 auth router 정책 변경 여부 반영
- clean-environment lifespan 및 health 테스트

### PR 2 — 선택 서비스 runtime 조립 경계

- 활성 서비스 외 설정 탐색 방지
- 자동 조립/빈 runtime/prebuilt runtime parity 테스트
- startup 및 close 회귀 검증

### PR 3 — SDK resource와 state dependency 경계

- managed resource edge case 보강
- public dependency를 통한 state 캡슐화
- readiness structured result 회귀 테스트

### PR 4 — 오류 adapter와 contract test helper

- 공통 오류 mapping 후보
- `fastapi_core.testing` helper
- public export/signature 테스트

### PR 5 — dms-core reference integration

- lifecycle/readiness/error/streaming E2E 예제
- 실제 SDK integration 테스트
- 검증 중 확인된 최소 core API 보완

## 5. 단계별 검증 명령

각 단계의 focused 테스트 후 항상 전체 suite를 마지막에 실행한다.

```bash
uv run pytest -q test_fastapi_core/test_factory.py test_fastapi_core/test_config.py
uv run pytest -q test_fastapi_core/test_extensions.py test_fastapi_core/test_health_router.py
uv run pytest -q test_fastapi_core/test_dependencies.py test_fastapi_core/test_http.py
uv run pytest -q test_fastapi_core/test_public_api.py
uv run pytest -q -m "not integration"
uv run pytest -q
```

DMS 및 live service가 준비된 경우:

```bash
uv run pytest -q -m integration
```

추가 검증:

```bash
uv run python - <<'PY'
from fastapi.testclient import TestClient
from fastapi_core import create_app

app = create_app()
with TestClient(app) as client:
    assert client.get('/health/liveness').status_code == 200
    assert client.get('/health/readiness').status_code == 200
PY
```

## 6. 완료 기준

- 환경변수 없는 `create_app()`이 실제 lifespan에 진입한다.
- 기본 앱은 외부 client를 생성하지 않는다.
- `create_app(config=..., runtime=...)`가 유일한 앱 factory 계약이다.
- 자동 조립 runtime과 주입 runtime의 readiness/startup/close 정책이 일치한다.
- 활성화하지 않은 서비스 설정은 요구되지 않는다.
- managed resource가 sync/async create, healthcheck, rollback, close를 일관되게 처리한다.
- 소비사 route가 `app.state`를 직접 참조하지 않는다.
- 기본 Problem Details와 domain mapper 확장 경로가 동작한다.
- 소비사 contract helper로 health, cleanup, readiness, auth opt-in/out을 검증할 수 있다.
- DMS reference integration이 lifecycle, readiness, streaming close, 공개 DTO, 오류 mapping을 검증한다.
- 최종 `uv run pytest -q`가 통과한다.

## 7. 이번 계획에서 제외하는 작업

- 여러 동급 app factory 추가
- `settings=` compatibility layer 복원
- resource method-name 기반 암묵적 readiness 탐색
- dms-core의 runtime/optional dependency 편입
- private `app.state` 키를 공개 API로 고정
- 운영 배포 템플릿 및 문서 전체 재작성

문서와 migration guide 동기화는 각 소스 변경 PR에 필요한 범위로 수행하되, 본 계획의 중심은 소스 코드 계약과 실행 가능한 회귀 테스트다.
