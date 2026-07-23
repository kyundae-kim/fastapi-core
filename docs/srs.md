# fastapi-core 소프트웨어 요구사항 명세서 (SRS)

> 문서 리비전: 2026-07-23
>
> 기준 릴리스: `fastapi-core 0.6.0`
>
> 상태: current-implementation
>
> 기준: 현재 `fastapi_core` 소스와 `test_fastapi_core` 회귀 계약

---

## 1. 목적과 범위

이 문서는 DocMesh Py Core 기반 서비스를 FastAPI로 실행·노출하는 `fastapi-core`의 구현 계약을 정의한다. PRD의 capability를 앱 팩토리, router, dependency, schema, runtime, readiness, 자원 lifecycle, 오류 처리 및 테스트 지원 API 단위로 구체화한다.

### 1.1 시스템 경계

- `fastapi-core`는 FastAPI 앱 조립과 HTTP·dependency·lifespan 통합을 소유한다.
- `docmesh-py-core`는 서비스 설정, `RuntimePlan`, `ServiceRuntime`, 서비스 client 조립·점검·종료 및 민감 정보 마스킹을 소유한다.
- 서비스 애플리케이션은 도메인 router, 도메인 schema, 사용자 정의 lifespan, 관리 자원 및 도메인 오류 매핑을 소유한다.

### 1.2 용어

- **runtime**: DocMesh 서비스 설정·client·readiness check·종료 책임을 보유하는 `ServiceRuntime`.
- **managed resource**: 서비스 앱이 선언하고 framework lifespan이 생성·점검·종료하는 사용자 정의 자원.
- **required check**: 실패 시 앱 readiness를 오류로 만드는 점검.
- **optional check**: 실패 시 앱 readiness를 저하 상태로 만드는 점검.
- **current implementation**: 이 문서와 동일 revision의 저장소 소스에 구현되고 테스트되는 계약.

---

## 2. 공개 표면

### 2.1 패키지 root export

**SRS-API-001** `fastapi_core.__all__`은 다음 심벌을 제공해야 한다.

- `create_app`
- `DomainModule`, `ErrorMapperSpec`
- `ManagedResource`, `ResourceKey`
- `ReadinessCheckSpec`, `register_readiness_check`
- `ErrorMapping`, `ErrorRenderer`, `register_error_mapper`

**SRS-API-002** dependency와 schema는 각각 `fastapi_core.dependencies.__all__`, `fastapi_core.schemas.__all__`에서 명시적으로 관리해야 한다.

### 2.2 앱 팩토리

**SRS-APP-001** 앱 팩토리 signature는 다음 계약을 유지해야 한다.

```python
create_app(
    config: AppConfig | None = None,
    *,
    runtime: ServiceRuntime | None = None,
    lifespan: Callable | None = None,
    include_auth_router: bool = False,
    routers: Sequence[APIRouter] = (),
    modules: Sequence[DomainModule] = (),
    resources: Sequence[ManagedResource[Any]] = (),
    error_mappers: Sequence[ErrorMapperSpec] = (),
    error_renderer: ErrorRenderer | None = None,
    auth_provider: Any | None = None,
) -> FastAPI
```

**SRS-APP-002** `config`가 없으면 cache된 `load_app_config()` 결과를 사용해야 한다.

**SRS-APP-003** `runtime`이 없고 활성 서비스가 있으면 앱 생성 시 `RuntimePlan`을 검증·생성하고, lifespan startup에서 환경 기반 runtime을 조립해야 한다.

**SRS-APP-004** `runtime`이 없고 활성 서비스도 없으면 lifespan startup에서 외부 client가 없는 canonical runtime을 생성해야 한다.

**SRS-APP-005** 명시적 `runtime`은 재조립하지 않고 동일 객체를 앱 상태, readiness 및 lifecycle에 연결해야 한다. 이 경로에서는 앱 설정의 활성 서비스 목록보다 주입한 runtime이 권위 있는 서비스 상태여야 한다.

**SRS-APP-006** 생성된 앱에는 다음 공통 구성을 적용해야 한다.

- `root_path` 반영
- CORS middleware
- correlation ID middleware
- 표준 오류 handler와 선택적 custom renderer
- health router 기본 포함
- `include_auth_router=True`일 때만 auth router 포함
- 앱별 OAuth2 password scheme 및 OpenAPI token URL

**SRS-APP-007** 앱 생성 직후 다음 상태를 제공해야 한다.

- `app.state.config`
- `app.state.root_logger`
- `app.state.service_runtime` (`runtime` 자동 조립 전에는 `None` 가능)
- `app.state.readiness_registry`
- `app.state.resource_registry`
- `app.state.oauth2_scheme`
- `app.state.error_renderer`
- `app.state.error_mapper_types`
- `app.state.domain_modules`

Keycloak provider가 구성된 뒤에는 `app.state.auth_provider`를 제공해야 한다.

**SRS-APP-008** 앱별 OAuth2 scheme은 객체와 OpenAPI token URL이 다른 앱과 격리되어야 한다. `AppConfig.token_url`은 OpenAPI password flow URL을 변경하지만 내장 `POST /token` 경로를 이동시키지 않는다.

---

## 3. 설정 및 runtime 조립

### 3.1 앱 설정

**SRS-CFG-001** `AppConfig`는 다음 필드와 기본값을 제공해야 한다.

| 필드 | 타입 | 기본값 |
|---|---|---|
| `root_path` | `str` | `""` |
| `token_url` | `str` | `"/token"` |
| `cors_origins` | `list[str]` | `["*"]` |
| `cors_credentials` | `bool` | `False` |
| `readiness_parallel` | `bool` | `False` |
| `readiness_timeout_seconds` | `float \| None` | `None` |
| `readiness_overall_timeout_seconds` | `float \| None` | `None` |
| `service_alternatives` | `list[list[str]]` | `[]` |
| `startup_healthcheck` | `bool` | `False` |
| `startup_failure_mode` | `StartupFailureMode` | `FAIL` |
| `startup_healthcheck_attempts` | `int` | `1` |
| `startup_healthcheck_retry_delay_seconds` | `float` | `0` |
| `log_level` | `str \| None` | `"WARNING"` |
| `log_path` | `str \| None` | `None` |
| `log_json` | `bool` | `True` |
| `log_force` | `bool` | `False` |
| `access_log_enabled` | `bool` | `True` |
| `access_log_health_enabled` | `bool` | `False` |
| `enabled_services` | `list[str]` | `[]` |
| `required_services` | `list[str]` | `[]` |

**SRS-CFG-002** `required_services`는 모두 `enabled_services`에 포함되어야 하며, 위반 시 설정 검증 오류를 발생시켜야 한다.

**SRS-CFG-003** readiness timeout은 양수, startup healthcheck 시도 횟수는 1 이상, 재시도 간격은 0 이상이어야 한다.

**SRS-CFG-004** CORS origin, 활성 서비스 및 필수 서비스 환경변수는 CSV를 지원해야 하며 환경변수의 빈 문자열은 빈 목록으로 해석해야 한다. Python 생성자에 직접 전달한 빈 문자열은 허용하지 않는다.

**SRS-CFG-005** 대체 서비스 그룹 환경변수는 세미콜론으로 그룹을, 쉼표로 그룹 내 서비스를 구분해야 한다.

### 3.2 RuntimePlan

**SRS-RUN-001** `build_runtime_plan(config)`는 활성 서비스를 required 또는 optional `Service` specification으로 변환해야 한다.

**SRS-RUN-002** `service_alternatives`의 각 그룹은 `RuntimePlan.one_of`로 전달되어야 하며, 알 수 없는 서비스, 중복 서비스, 비어 있거나 충족 불가능한 그룹은 runtime 조립 전에 검증 오류가 발생해야 한다.

**SRS-RUN-003** startup healthcheck의 병렬 실행, 서비스별 timeout, 전체 timeout, 실패 모드, 시도 횟수 및 재시도 간격을 `HealthcheckPolicy`에 반영해야 한다.

**SRS-RUN-004** runtime의 모든 선택 서비스는 호출 가능한 readiness check를 제공해야 한다. 누락 시 앱 구성을 실패시켜야 한다.

**SRS-RUN-005** runtime 설정 후 각 서비스 check를 앱별 readiness registry에 등록하고 runtime의 required 집합을 반영해야 한다. Keycloak wrapper가 실제 `KeycloakAuthService`를 보유하면 허용 알고리즘을 `RS256`으로 제한하고 인증 provider로 연결해야 한다.

**SRS-RUN-006** runtime 연결은 원자적으로 수행해야 한다. 선택 서비스의 callable check가 누락되거나 기존 readiness 이름과 충돌하면 현재 `app.state.service_runtime`과 readiness registry를 변경하지 않고 오류를 발생시켜야 한다.

---

## 4. Lifespan 및 관리 자원

### 4.1 실행 순서

**SRS-LIFE-001** framework lifespan startup 순서는 다음과 같아야 한다.

1. runtime이 없으면 runtime 조립 및 앱 연결
2. 명시적 runtime이고 startup healthcheck가 활성화된 경우 runtime 점검
3. managed resource를 선언 순서대로 생성하고 readiness check 등록
4. startup healthcheck가 활성화된 경우 required managed resource 점검
5. 사용자 정의 lifespan 진입

자동 조립 runtime의 startup healthcheck는 `RuntimePlan` 정책에 의해 수행되어야 한다.

**SRS-LIFE-002** shutdown은 사용자 정의 lifespan 종료 후 managed resource를 역순으로 닫고, 마지막으로 runtime을 닫아야 한다.

**SRS-LIFE-003** startup, 사용자 lifespan 또는 request serving 단계의 예외와 관계없이 framework 소유 정리는 `finally`에서 실행되어야 한다.

**SRS-LIFE-004** managed resource startup이 부분 실패하면 이미 생성된 자원을 역순으로 rollback해야 한다. rollback 실패는 원래 예외에 note로 남기고 원래 startup 실패를 유지해야 한다.

**SRS-LIFE-005** managed resource 종료 실패는 가능한 모든 자원의 종료 시도 후 `BaseExceptionGroup`으로 보고해야 한다. runtime 종료 실패는 `ServiceCloseError`로 기록하고 전파해야 한다.

### 4.2 ManagedResource와 ResourceKey

**SRS-RES-001** `ManagedResource`는 다음 계약을 제공해야 한다.

```python
ManagedResource(
    name: str | ResourceKey[T],
    factory: Callable[[FastAPI], T | Awaitable[T]],
    healthcheck: Callable[[T], object | Awaitable[object]] | None = None,
    close: Callable[[T], None | Awaitable[None]] | None = None,
    required: bool = True,
    readiness_timeout_seconds: float | None = None,
    redact_errors: bool = True,
)
```

**SRS-RES-002** resource 이름은 공백일 수 없고, 중복 이름과 framework 예약 이름을 거부해야 하며, readiness timeout은 지정 시 양수여야 한다.

**SRS-RES-003** factory, healthcheck 및 close callback은 동기·비동기 결과를 모두 지원해야 한다.

**SRS-RES-004** 명시적 close callback이 없으면 자원의 `aclose()`, 그 다음 `close()`를 탐색해야 한다.

**SRS-RES-005** `ResourceKey[T].dependency`와 `get_resource(name)`는 생성 완료된 자원을 반환하고, registry 또는 자원이 준비되지 않았으면 `503 Service Unavailable`을 발생시켜야 한다.

**SRS-RES-006** resource 종료 시 해당 인스턴스에 결합된 readiness check를 제거해야 한다.

---

## 5. Readiness와 health router

### 5.1 Readiness registry

**SRS-READY-001** `ReadinessCheckSpec`은 `name`, `check`, `required=True`, `timeout_seconds=None`, `redact_errors=True` 필드를 제공해야 한다.

**SRS-READY-002** `register_readiness_check(...)`는 앱별 registry에 동기 또는 비동기 check를 등록해야 하며, 빈 이름·중복 이름·0 이하 timeout을 거부해야 한다.

**SRS-READY-003** 동기 check는 이벤트 루프를 차단하지 않도록 worker thread에서 실행하고, 동기 함수가 awaitable을 반환하는 경우에도 await해야 한다.

**SRS-READY-004** check가 `False`를 반환하거나 예외·timeout이 발생하면 실패로 처리해야 한다. `HealthCheckResult`를 반환하면 하위 결과를 `<parent>.<child>` 이름으로 펼치고 required 정책을 상속해야 한다.

**SRS-READY-005** 하위 이름과 동일한 spec이 있으면 exact match를 우선하고, 없을 때 최상위 parent spec으로 정책을 해석해야 한다.

**SRS-READY-006** 필수 check 실패 시에도 완료된 선택·성공 check의 결과를 보존해야 한다.

### 5.2 HTTP health 계약

**SRS-HEALTH-001** `GET /health/liveness`는 `200`과 `{"status":"ok","details":null}` 계약을 반환해야 한다.

**SRS-HEALTH-002** `GET /health/readiness`는 등록 check가 없으면 `200`과 `ok`를 반환해야 한다.

**SRS-HEALTH-003** readiness 결과는 다음 상태 계약을 따라야 한다.

| 조건 | HTTP | `status` |
|---|---:|---|
| 모두 성공 | 200 | `ok` |
| 선택 check만 실패 | 200 | `degraded` |
| 필수 check 실패 | 503 | `error` |
| 전체 timeout | 503 | `error` |

**SRS-HEALTH-004** 개별 결과는 `ok`, `latency_ms`, `error`, `required`, `enabled`를 제공해야 한다. 전체 timeout에서는 `details`가 `null`일 수 있다.

**SRS-HEALTH-005** `redact_errors=True`인 실패는 외부 응답에 원문 오류를 노출하지 않아야 한다. readiness 실패 로그도 DocMesh 마스킹 정책을 적용해야 한다.

---

## 6. 인증·인가

### 6.1 Auth router

**SRS-AUTH-001** auth router를 포함한 앱은 다음 경로를 제공해야 한다.

- `POST /token`: `OAuth2PasswordRequestForm` 입력, `TokenResponse` 출력
- `GET /user`: bearer token 입력, `UserInfo` 출력

**SRS-AUTH-002** token 발급은 form의 username, password 및 공백 구분 scope를 provider에 전달하고 token type을 소문자로 정규화해야 한다. 동기 provider 호출은 worker thread로 위임하여 event loop를 차단하지 않아야 한다.

**SRS-AUTH-003** token 발급 실패는 다음과 같이 매핑하고 `WWW-Authenticate: Bearer`를 포함해야 한다.

| 오류 | HTTP | detail |
|---|---:|---|
| 인증 실패 | 401 | `Authentication failed` |
| provider 구성 오류 | 500 | `Authentication service misconfigured` |
| 일시적 provider 오류 | 503 | `Authentication service unavailable` |
| 일반 upstream 오류 | 502 | `Authentication service error` |
| 예상하지 못한 오류 | 500 | `Authentication service error` |

**SRS-AUTH-004** `get_current_user()`는 token 누락과 검증 실패를 `401`로 처리하고 `WWW-Authenticate: Bearer`를 포함해야 하며, 성공 시 provider의 `AuthenticatedUser`를 정보 손실 없이 반환해야 한다.

**SRS-AUTH-005** `/user`에서만 `AuthenticatedUser`를 `UserInfo(sub, username, email, name, roles, scopes)`로 변환해야 한다. username이 없으면 subject를 사용해야 한다.

### 6.2 권한 dependency

**SRS-AUTH-006** `require_roles`, `require_scopes`, `require_permissions`는 모든 요청 항목이 사용자에게 부여되어야 통과하는 AND semantics를 사용하고 실패 시 `403`을 발생시켜야 한다.

**SRS-AUTH-007** role은 realm role과 모든 client role의 중복 제거 합집합, scope는 token claim의 공백 구분 `scope` 문자열에서 계산해야 한다.

**SRS-AUTH-008** permission 검사는 role과 scope의 합집합을 대상으로 하며, 성공한 dependency는 같은 `AuthenticatedUser`를 반환해야 한다.

---

## 7. 서비스 dependency

**SRS-DEP-001** 다음 dependency를 공개해야 한다.

- 공통: `get_service_runtime`, `get_settings`, `get_service_client(name)`
- typed: `get_keycloak_auth_service`, `get_postgres_engine`, `get_sqlite_engine`, `get_minio_client`, `get_milvus_client`, `get_ollama_client`, `get_langfuse_client`, `get_nats_connection_builder`
- resource: `get_resource(name)`

**SRS-DEP-002** `get_settings`는 별도 전역 설정이 아니라 현재 앱 runtime의 `ServiceConfigs`를 반환해야 한다.

**SRS-DEP-003** runtime이 아직 없거나 서비스가 활성화되지 않았으면 `503`을 발생시켜야 한다.

**SRS-DEP-004** wrapper 종류 또는 unwrap한 client의 실제 타입이 typed dependency 계약과 다르면 `500`을 발생시켜 조립 오류와 가용성 오류를 구분해야 한다.

**SRS-DEP-005** NATS는 `NatsConnectionBuilder`를 직접 반환하고, 그 외 typed 서비스는 `ServiceClientWrapper`에서 실제 client를 unwrap해야 한다.

**SRS-DEP-006** dependency 구현은 `app.state.settings` 또는 `app.state.service_clients`와 같은 폐기된 상태를 fallback으로 사용하지 않아야 한다.

---

## 8. HTTP 오류와 요청 추적

### 8.1 Correlation ID

**SRS-HTTP-001** 모든 HTTP 요청은 `X-Correlation-ID`를 request state와 response header에 제공해야 한다.

**SRS-HTTP-002** 입력 ID는 영문자, 숫자, `.`, `_`, `:`, `-`만 포함한 1~128자일 때만 수용하고, 그 외에는 새로운 32자리 hex ID로 교체해야 한다.

### 8.2 오류 응답

**SRS-ERR-001** 기본 renderer는 HTTP 예외, request validation 오류 및 미처리 오류를 `application/problem+json`의 `ProblemDetail`로 반환해야 한다.

**SRS-ERR-002** `ProblemDetail`은 `type`, `title`, `status`, `detail`, `instance`, `correlation_id`를 포함해야 한다.

**SRS-ERR-003** validation 오류 detail은 `Request validation failed`, 미처리 오류 detail은 `Internal Server Error`로 고정하여 내부 정보를 노출하지 않아야 한다.

**SRS-ERR-004** `register_error_mapper(app, exception_type, mapper)`는 동기·비동기 mapper가 반환한 `ErrorMapping`을 동일한 sanitize·render 흐름으로 처리해야 한다.

**SRS-ERR-005** `create_app(error_renderer=...)`는 기본 problem envelope 대신 동기·비동기 custom renderer를 사용할 수 있어야 한다. custom renderer에도 민감 정보가 제거된 `ErrorMapping`을 전달해야 한다.

**SRS-ERR-006** `ErrorMapping`은 status code와 detail 외에 title, type URI, headers, domain code 및 extension metadata를 표현할 수 있어야 한다.

---

## 9. 로깅 및 비기능 요구사항

**SRS-NFR-001** 앱 로깅은 DocMesh 공통 logging 설정을 사용하고, JSON 모드에서 timestamp, logger, level, message와 선택적 function/event/exception 정보를 구조화해야 한다.

**SRS-NFR-002** 주요 함수 경계는 시작·성공·예외 이벤트를 기록하되 함수 signature와 sync/async 호출 semantics를 보존해야 한다.

**SRS-NFR-003** token 발급, readiness 및 미처리 request 오류 로그에 credential 또는 token 원문을 기록하지 않아야 한다.

**SRS-NFR-004** sync readiness check는 event loop를 차단하지 않아야 하며, 병렬 실행 설정과 timeout을 준수해야 한다.

**SRS-NFR-005** Python `>=3.11`과 프로젝트가 선언한 FastAPI 및 DocMesh Py Core 버전 범위에서 동작해야 한다.

---

## 10. 테스트 지원 계약

**SRS-TEST-001** `fastapi_core.testing.__all__`은 다음 소비사 contract helper만 제공해야 한다.

- `create_empty_runtime`
- `ResourceLifecycleProbe`
- `assert_health_contract`
- `assert_auth_router_contract`
- `assert_module_contract`
- `assert_openapi_contract`
- `test_environment`

**SRS-TEST-002** `create_empty_runtime()`은 선택·필수 서비스와 client가 없는 canonical `ServiceRuntime`을 반환하고 production runtime helper와 동일 객체를 사용해야 한다.

**SRS-TEST-003** `ResourceLifecycleProbe`는 실제 managed resource를 생성하여 create, check, close 이벤트 순서를 기록해야 한다.

**SRS-TEST-004** health assertion은 liveness와 readiness 성공 계약을, auth assertion은 router opt-in 여부를 실제 HTTP 요청으로 검증해야 한다.

**SRS-TEST-005** async 동작을 검증하는 테스트는 `pytest-asyncio` async test 함수에서 직접 `await`해야 한다.

---

## 11. 검증 및 추적성

| 요구사항 영역 | 대표 소스 | 대표 테스트 |
|---|---|---|
| 공개 API·앱 팩토리 | `fastapi_core/__init__.py`, `factory.py` | `test_public_api.py`, `test_factory.py` |
| 설정·runtime | `config.py`, `runtime.py`, `docmesh_settings.py` | `test_config.py`, `test_settings_compatibility.py`, `test_factory.py` |
| lifespan·자원 | `lifecycle.py`, `resources.py` | `test_factory.py`, `test_extensions.py` |
| readiness·health | `readiness.py`, `routers/health.py` | `test_extensions.py`, `test_health_router.py` |
| 인증·인가 | `routers/auth.py`, `dependencies/auth.py` | `test_auth_router.py`, `test_dependencies.py` |
| 서비스 dependency | `dependencies/services.py`, `dependencies/config.py` | `test_dependencies.py`, integration runtime tests |
| HTTP 오류·추적 | `http.py`, `schemas/error.py` | `test_http.py` |
| 로깅 | `logging.py`, `function_logging.py` | `test_function_logging.py`, auth/health tests |
| 소비사 contract helper | `testing.py` | `test_testing.py` |

### 11.1 완료 검증

- 기본 회귀 명령: `uv run --frozen pytest -q`
- non-integration 회귀: `uv run --frozen pytest -q -m "not integration"`
- integration test는 필요한 외부 서비스와 credential이 제공된 환경에서 별도로 실행한다.
- 문서 Markdown fence, 내부 링크, requirement ID 중복 및 `git diff --check`를 검사한다.

### 11.2 구현 상태

- 1~12절은 모두 `fastapi-core 0.6.0` 현재 구현 계약을 기술한다.
- 12절은 0.6.0에서 확장된 도메인 조립, 기동 진단, access logging 및 소비사 검증 계약을 상세화한다.
- 구체 API가 변경되면 소스·공개 API 테스트와 이 문서를 같은 변경에서 갱신해야 한다.
- `docs/prd.md`는 제품 capability와 결과를, 이 문서는 구현 가능한 계약과 검증 기준을 소유한다.

---

## 12. 0.6.0 확장 구현 계약

이 절은 0.6.0에서 추가된 계약을 기능 영역별로 상세화한다. 모든 항목은 현재 소스에 구현되어 있으며 회귀 테스트의 검증 대상이다.

### 12.1 P0-1 — auth router와 서비스 설정의 startup 진단

**SRS-AUTH-009** 내장 auth router가 활성화된 자동 runtime 조립 경로는 Keycloak을 선택된 필수 서비스로 요구해야 한다. framework는 선택되지 않은 Keycloak을 암묵적으로 활성화하지 않고 앱 생성 단계에서 구성 오류를 발생시켜야 한다.

**SRS-AUTH-010** framework는 자동 runtime을 조립하기 전에 auth 요구사항을 포함한 동일 `RuntimePlan`으로 `diagnose_services(plan=...)`를 호출해야 한다. 진단의 `ok`가 거짓이면 네트워크 연결을 시도하지 않고 secret-safe한 startup configuration error를 발생시켜야 한다.

**SRS-AUTH-011** 명시적 `runtime`이 주입된 경로에서는 `AppConfig.enabled_services`가 아니라 주입된 runtime이 권위 있어야 한다. 명시적 `auth_provider`가 없고 auth router가 활성화됐지만 runtime에 Keycloak 서비스가 없거나 unwrap한 provider가 `KeycloakAuthService`가 아니면 앱 생성 중 구성 오류를 발생시켜야 한다.

**SRS-AUTH-012** 자동 조립 경로는 runtime 연결 직후 `app.state.auth_provider`가 유효한 `KeycloakAuthService`인지 검증하고, 사용자 lifespan과 request serving 전에 실패해야 한다. 진단 오류는 누락된 서비스·환경변수 key·remediation을 제공할 수 있지만 credential 값과 token을 포함하지 않아야 한다.

**SRS-AUTH-013** auth router가 비활성화된 앱은 Keycloak 설정 또는 provider를 요구하지 않아야 한다. `create_app(auth_provider=...)`는 테스트 또는 명시적 사용자 정의 provider를 위한 조립 seam이며, 단순한 `app.state.auth_provider` 사후 변경은 지원되는 조립 방식으로 간주하지 않는다.

### 12.2 P0-2 — DomainModule 선언과 원자적 등록

**SRS-MOD-001** 패키지 root는 다음 불변 선언 타입을 공개해야 한다.

```python
@dataclass(frozen=True, slots=True)
class DomainModule:
    name: str
    routers: Sequence[APIRouter] = ()
    dependencies: Sequence[params.Depends] = ()
    resources: Sequence[ManagedResource[Any]] = ()
    readiness_checks: Sequence[ReadinessCheckSpec] = ()
    error_mappers: Sequence[ErrorMapperSpec] = ()
```

**SRS-MOD-002** module 이름은 공백일 수 없고 한 앱에서 고유해야 한다. module이 선언한 resource와 readiness 이름은 기존 registry, 다른 module 및 framework 예약 이름과 충돌하지 않아야 한다.

**SRS-MOD-003** framework는 모든 module의 이름, router, dependency, resource, readiness 및 error mapper를 먼저 검증한 뒤 등록해야 한다. 검증 실패 시 router table, exception handler, resource registry 및 readiness registry 중 어느 것도 변경하지 않아야 한다.

**SRS-MOD-004** module resource는 기존 `ResourceRegistry`와 framework lifespan이 소유하고, module readiness는 기존 `ReadinessRegistry`가 소유해야 한다. module은 별도의 lifecycle 또는 runtime container를 만들지 않아야 한다.

**SRS-MOD-005** DocMesh 서비스 client와 그 종료는 `ServiceRuntime`이 계속 소유한다. module resource는 서비스 앱이 직접 생성한 자원에 사용하며, NATS builder로 생성한 지속 연결처럼 runtime이 종료하지 않는 자원은 명시적 close callback으로 `drain()` 등 필요한 정리를 수행해야 한다.

### 12.3 P1-1 — router 직접 등록과 공통 인증 dependency

**SRS-APP-009** 앱 팩토리는 다음 입력을 제공해야 한다.

```python
create_app(
    config: AppConfig | None = None,
    *,
    runtime: ServiceRuntime | None = None,
    lifespan: Callable | None = None,
    include_auth_router: bool = False,
    routers: Sequence[APIRouter] = (),
    modules: Sequence[DomainModule] = (),
    resources: Sequence[ManagedResource[Any]] = (),
    error_mappers: Sequence[ErrorMapperSpec] = (),
    error_renderer: ErrorRenderer | None = None,
    auth_provider: Any | None = None,
) -> FastAPI
```

**SRS-APP-010** `routers`는 전달 순서대로 직접 등록하고 각 `APIRouter`가 선언한 prefix, tag, dependency, response 및 OpenAPI metadata를 보존해야 한다. framework는 전달받은 router 객체 자체를 변경하지 않아야 한다.

**SRS-APP-011** 내장 health router는 항상 등록하고 내장 auth router는 opt-in으로 등록한 뒤 사용자 router와 module router를 선언 순서대로 등록해야 한다. 동일 path와 HTTP method 또는 operation ID 충돌은 OpenAPI 생성 전 진단 가능한 구성 오류로 처리해야 한다.

**SRS-AUTH-014** router 수준 공통 인증·인가 정책은 FastAPI `APIRouter`의 dependency 계약을 사용해야 한다. module의 `dependencies`는 해당 module의 모든 router에 추가 적용하되 router 자체 dependency를 대체하지 않아야 한다.

**SRS-AUTH-015** module dependency는 내장 health/auth router와 다른 module에 전파되지 않아야 한다. token 발급 endpoint에 현재 사용자 인증 dependency가 순환 적용되지 않도록 적용 범위를 module 경계로 제한해야 한다.

### 12.4 P1-2 — declarative error mapper 일괄 등록

**SRS-ERR-007** 패키지 root는 다음 불변 선언 타입을 공개해야 한다.

```python
@dataclass(frozen=True, slots=True)
class ErrorMapperSpec:
    exception_type: type[Exception]
    mapper: ErrorMapper
```

**SRS-ERR-008** 앱 수준 `error_mappers`와 각 `DomainModule.error_mappers`를 하나의 검증 단계에서 평탄화해야 한다. 같은 예외 타입이 둘 이상 선언되면 등록 순서에 따른 override 없이 구성 오류를 발생시켜야 한다.

**SRS-ERR-009** 선언형 mapper는 기존 `register_error_mapper()`와 같은 동기·비동기 실행, `ErrorMapping` sanitize 및 `ErrorRenderer` 흐름을 사용해야 한다. mapper 등록 실패는 다른 module 요소를 부분 등록하지 않아야 한다.

**SRS-ERR-010** 기존 `register_error_mapper(app, ...)`는 앱 생성 후 명시적으로 확장하는 imperative API로 유지하되, 이미 등록된 예외 타입을 덮어쓰려면 중복 정책을 명시적으로 위반하지 않는 별도 계약이 없는 한 오류를 발생시켜야 한다.

### 12.5 P1-3 — request access logging

**SRS-OBS-001** `AppConfig`는 `access_log_enabled: bool = True`와 `access_log_health_enabled: bool = False`를 제공해야 한다.

**SRS-OBS-002** access logging middleware는 각 HTTP 요청 완료 시 정확히 한 번 구조화 event를 기록해야 하며 최소한 method, route template 또는 안전한 path, status code, duration, outcome 및 correlation ID를 포함해야 한다.

**SRS-OBS-003** access log는 기본적으로 query string, Authorization·Cookie header, request/response body 및 credential·token 원문을 기록하지 않아야 한다. route가 확정되지 않은 404 요청은 query를 제외한 path만 기록할 수 있다.

**SRS-OBS-004** 정상 응답, framework 오류 응답, 미처리 예외 및 streaming 응답에도 동일한 완료 event 계약을 적용해야 한다. streaming 응답은 마지막 body 전송 또는 전송 실패 시점을 완료로 계산해야 한다.

**SRS-OBS-005** health probe access log는 기본 제외하고 `access_log_health_enabled=True`일 때만 기록해야 한다. access logging 비활성화 여부와 관계없이 correlation ID 응답 계약은 유지해야 한다.

### 12.6 P1-4 — 환경 override와 config cache test context

**SRS-TEST-006** `fastapi_core.testing`은 다음 context manager를 공개해야 한다.

```python
test_environment(
    overrides: Mapping[str, str | None],
) -> AbstractContextManager[None]
```

**SRS-TEST-007** context 진입 시 기존 환경값을 보존하고 `str` 값은 설정하며 `None` 값은 삭제한 뒤 `load_app_config()`와 `load_docmesh_settings()` 관련 cache를 초기화해야 한다.

**SRS-TEST-008** 정상 종료와 예외 종료 모두에서 환경을 정확히 원상복구하고 관련 cache를 다시 초기화해야 한다. 중첩 context는 각 진입 시점의 환경을 복원 기준으로 사용해야 한다.

**SRS-TEST-009** context는 process-global 환경을 변경하므로 여러 thread에서 동시에 사용하는 안전성을 보장하지 않아야 한다. helper의 repr, assertion 및 오류에는 override credential 값을 포함하지 않아야 한다.

### 12.7 P2 — module 및 생성 OpenAPI contract assertion

**SRS-TEST-010** `fastapi_core.testing`은 다음 assertion helper를 공개해야 한다.

```python
assert_module_contract(app: FastAPI, module: DomainModule) -> None

assert_openapi_contract(
    app: FastAPI,
    *,
    expected_paths: Mapping[str, Collection[str]],
    expected_security_schemes: Collection[str] = (),
) -> None
```

**SRS-TEST-011** module assertion은 module의 router operation, resource, readiness check 및 error mapper가 대상 앱에 등록됐는지 확인해야 하며 실제 resource 생성·종료를 대신 수행하지 않아야 한다.

**SRS-TEST-012** OpenAPI assertion은 schema 생성을 실제 호출하고 요구된 path·HTTP method, operation ID 고유성, security scheme 및 참조 가능한 component schema를 의미 기반으로 검사해야 한다.

**SRS-TEST-013** OpenAPI assertion은 FastAPI 또는 Pydantic의 비계약적 출력 순서·설명 문구까지 고정하는 전체 JSON 문자열 snapshot을 기본 방식으로 사용하지 않아야 한다.

### 12.8 구현 검증 순서

1. auth router의 자동 runtime 진단, 명시적 runtime 진단 및 secret redaction 테스트
2. module 전체 사전 검증과 등록 원자성 테스트
3. 직접 router 등록 순서·metadata·module dependency 격리 테스트
4. 앱/module error mapper 일괄 등록과 중복 거부 테스트
5. 정상·오류·streaming 요청 access log와 민감 정보 미기록 테스트
6. test environment 정상·예외·중첩 복원과 cache 격리 테스트
7. module 및 생성 OpenAPI 의미 계약 assertion 테스트

각 단계의 공개 계약과 회귀 테스트는 0.6.0 현재 구현에서 함께 검증한다.
