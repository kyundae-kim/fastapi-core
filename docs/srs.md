# fastapi-core 소프트웨어 요구사항 명세서 (SRS)

> 문서 리비전: 2026-08-02
>
> 기준 릴리스: `fastapi-core 0.6.0`
>
> 상태: current-implementation
>
> 기준: 현재 `fastapi_core` 소스와 `test_fastapi_core` 회귀 계약

---

## 1. 문서 목적

이 문서는 DocMesh Py Core 기반 서비스를 FastAPI로 실행·노출하는 `fastapi-core`가 충족해야 하는 소프트웨어 요구사항을 정의한다. 제품 capability와 사용자 가치는 `docs/prd.md`가 소유하며, 이 문서는 구현 가능한 인터페이스, 동작, 오류, 수명주기 및 검증 기준을 소유한다.

### 1.1 요구사항 해석

- `해야 한다`는 현재 릴리스가 반드시 충족해야 하는 요구사항을 뜻한다.
- 각 요구사항은 고유한 `SRS-<영역>-<번호>` 식별자를 갖는다.
- 표와 코드 표기는 요구사항의 일부이며 공개 계약을 구체화한다.

### 1.2 시스템 경계

- **SRS-SYS-001** `fastapi-core`는 FastAPI 앱 조립, router 등록, dependency 제공, HTTP middleware, 오류 응답 및 lifespan 통합을 소유해야 한다.
- **SRS-SYS-002** `docmesh-py-core`는 서비스 설정, `RuntimePlan`, `ServiceRuntime`, 서비스 client 조립·점검·종료 및 민감 정보 마스킹을 소유해야 한다.
- **SRS-SYS-003** 소비 애플리케이션은 도메인 router와 schema, 사용자 정의 lifespan, 서비스 고유 자원 및 도메인 오류 매핑을 소유해야 한다.
- **SRS-SYS-004** `fastapi-core`는 Python `>=3.11`과 프로젝트가 선언한 FastAPI 및 DocMesh Py Core 버전 범위에서 동작해야 한다.

---

## 2. 공개 API 및 애플리케이션 조립 요구사항

### 2.1 패키지 공개 표면

- **SRS-API-001** `fastapi_core.__all__`은 `create_app`, `DomainModule`, `DomainModuleProvider`, `ErrorMapperSpec`, `ManagedResource`, `ResourceBinding`, `ResourceKey`, `ReadinessCheckSpec`, `HealthOutcome`, `HealthResultAdapter`, `register_readiness_check`, `ErrorMapping`, `ErrorRenderer`, `ExceptionMappingTable`, `create_error_renderer`, `register_error_mapper`, `TransportPolicy`, `ManagedStreamingResponse`, `invoke_resource`를 공개해야 한다.
- **SRS-API-002** `fastapi_core.dependencies.__all__`은 인증·설정·서비스·자원 dependency를 명시적으로 공개해야 한다.
- **SRS-API-003** `fastapi_core.schemas.__all__`은 `HealthResponse`, `HealthServiceDetail`, `ProblemDetail`, `TokenResponse`, `UserInfo`를 공개해야 한다.
- **SRS-API-004** `fastapi_core.testing.__all__`은 10절에 정의된 소비사 테스트 helper만 공개해야 한다.

### 2.2 앱 팩토리

- **SRS-APP-001** 앱 팩토리는 다음 signature와 반환 타입을 유지해야 한다.

```python
create_app(
    config: AppConfig | None = None,
    *,
    runtime: ServiceRuntime | None = None,
    lifespan: Callable | None = None,
    include_auth_router: bool = False,
    routers: Sequence[APIRouter] = (),
    modules: Sequence[DomainModule] = (),
    resources: Sequence[ManagedResource[Any] | ResourceBinding[Any]] = (),
    error_mappers: Sequence[ErrorMapperSpec] = (),
    error_renderer: ErrorRenderer | None = None,
    auth_provider: Any | None = None,
    transport_policy: TransportPolicy | None = None,
    error_mapping_table: ExceptionMappingTable | None = None,
) -> FastAPI
```

- **SRS-APP-002** `config`가 없으면 cache된 `load_app_config()` 결과를 사용해야 한다.
- **SRS-APP-003** 생성된 앱은 설정의 `root_path`, CORS, correlation ID, 선택적 access log, 표준 오류 handler 및 앱별 OAuth2 scheme을 적용해야 한다.
- **SRS-APP-004** health router는 항상 포함하고 auth router는 `include_auth_router=True`일 때만 포함해야 한다.
- **SRS-APP-005** 내장 router, 직접 전달된 router, module router는 각각 선언 순서를 보존하여 등록해야 한다. 직접 전달된 router의 prefix, tag, dependency, response 및 OpenAPI metadata를 변경하지 않아야 한다.
- **SRS-APP-006** 동일 HTTP method와 path의 중복 또는 operation ID 중복은 OpenAPI 생성 전에 구성 오류로 거부해야 한다.
- **SRS-APP-007** 앱 생성 직후 `app.state.config`, `root_logger`, `service_runtime`, `readiness_registry`, `resource_registry`, `oauth2_scheme`, `error_renderer`, `error_mapper_types`, `domain_modules`를 제공해야 한다. 자동 runtime 조립 전 `service_runtime`은 `None`일 수 있다.
- **SRS-APP-008** 인증 provider가 명시적으로 주입되거나 runtime에서 구성된 경우 `app.state.auth_provider`를 제공해야 한다.
- **SRS-APP-009** 앱별 OAuth2 scheme 객체와 OpenAPI token URL은 다른 앱과 격리되어야 한다. `AppConfig.token_url`은 OpenAPI password flow URL만 변경하며 내장 token endpoint 경로를 이동시키지 않아야 한다.
- **SRS-APP-010** 기본 설정에서 외부 서비스가 활성화되지 않은 앱은 외부 인프라 없이 lifespan에 진입할 수 있어야 한다.
- **SRS-APP-011** 생성된 앱은 effective `transport_policy`, route별 `transport_policies`, `error_mapping_table` 및 `resource_bindings`를 app state에서 제공해야 하며, runtime handler와 OpenAPI는 이 상태에서 파생된 동일 계약을 사용해야 한다.

### 2.3 도메인 모듈

- **SRS-MOD-001** `DomainModule`은 `name`, `routers`, `dependencies`, `resources`, `readiness_checks`, `error_mappers`, `transport_policy`를 갖는 불변 선언 타입이어야 한다. `resources`는 `ManagedResource` 또는 `ResourceBinding`을 받을 수 있다.
- **SRS-MOD-002** module 이름은 공백일 수 없고 한 앱에서 고유해야 한다.
- **SRS-MOD-003** module dependency는 해당 module의 모든 router에 추가하되 router 자체 dependency를 대체하지 않아야 한다.
- **SRS-MOD-004** module dependency는 내장 health·auth router 또는 다른 module로 전파되지 않아야 한다.
- **SRS-MOD-005** framework는 module 등록 전에 module 이름, router 타입과 충돌, resource·readiness 이름 충돌 및 error mapper 계약을 검증해야 한다. 검증 실패 시 부분 등록 없이 앱 생성을 실패시켜야 한다.
- **SRS-MOD-006** module resource와 readiness는 각각 공통 `ResourceRegistry`와 `ReadinessRegistry`가 관리해야 하며 별도 runtime 또는 lifecycle container를 만들지 않아야 한다.
- **SRS-MOD-007** DocMesh 서비스 client의 소유권과 종료 책임은 `ServiceRuntime`에 유지해야 한다. module이 직접 생성한 자원은 명시된 managed resource 종료 계약을 따라야 한다.
- **SRS-MOD-008** `DomainModuleProvider`는 `build_*_module(...) -> DomainModule` callable convention을 표현해야 하며, framework는 plugin discovery나 implicit import를 수행하지 않아야 한다.

---

## 3. 설정 및 Runtime 요구사항

### 3.1 애플리케이션 설정

- **SRS-CFG-001** `AppConfig`는 다음 필드와 기본값을 제공해야 한다.

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

- **SRS-CFG-002** `required_services`의 모든 항목은 `enabled_services`에 포함되어야 하며 위반 시 설정 검증 오류를 발생시켜야 한다.
- **SRS-CFG-003** 개별·전체 readiness timeout은 지정 시 양수, startup healthcheck 시도 횟수는 1 이상, 재시도 간격은 0 이상이어야 한다.
- **SRS-CFG-004** CORS origin, 활성 서비스 및 필수 서비스 환경변수는 CSV를 지원해야 한다. 환경변수의 빈 문자열은 빈 목록으로 해석하되 Python 생성자에 직접 전달한 빈 문자열은 거부해야 한다.
- **SRS-CFG-005** 대체 서비스 그룹 환경변수는 세미콜론으로 그룹을, 쉼표로 그룹 내 서비스를 구분해야 하며 빈 그룹과 빈 항목은 제거해야 한다.

### 3.2 Runtime 계획과 연결

- **SRS-RUN-001** runtime이 없고 활성 서비스가 있으면 앱 생성 중 `RuntimePlan`을 만들고 lifespan startup에서 환경 기반 `ServiceRuntime`을 조립해야 한다.
- **SRS-RUN-002** runtime이 없고 활성 서비스도 없으면 lifespan startup에서 선택·필수 서비스와 client가 없는 canonical runtime을 생성해야 한다.
- **SRS-RUN-003** 명시적 runtime은 재조립하지 않고 동일 객체를 앱 상태, readiness 및 lifecycle에 연결해야 한다. 이 경로에서는 주입된 runtime이 앱 설정의 활성 서비스 목록보다 권위 있어야 한다.
- **SRS-RUN-004** `build_runtime_plan(config)`는 활성 서비스를 required 또는 optional service specification으로 변환하고 대체 서비스 그룹을 `RuntimePlan.one_of`에 반영해야 한다.
- **SRS-RUN-005** 알 수 없는 서비스, 중복 서비스, 비어 있거나 충족 불가능한 대체 그룹은 runtime 조립 전에 거부해야 한다.
- **SRS-RUN-006** startup 점검의 병렬 실행, 개별·전체 timeout, 실패 모드, 시도 횟수 및 재시도 간격을 `HealthcheckPolicy`에 반영해야 한다.
- **SRS-RUN-007** 선택된 모든 runtime 서비스는 호출 가능한 readiness check를 제공해야 하며 누락 시 runtime 연결을 실패시켜야 한다.
- **SRS-RUN-008** runtime 서비스 check는 앱별 readiness registry에 서비스 이름으로 등록하고 runtime의 required 집합을 반영해야 한다.
- **SRS-RUN-009** runtime 연결 중 check 누락 또는 readiness 이름 충돌이 발견되면 기존 `app.state.service_runtime`과 readiness registry를 변경하지 않고 실패해야 한다.
- **SRS-RUN-010** runtime의 Keycloak wrapper가 `KeycloakAuthService`를 보유하면 허용 알고리즘을 `RS256`으로 제한하고 앱 인증 provider로 연결해야 한다.

---

## 4. Lifespan 및 관리 자원 요구사항

### 4.1 Lifespan 실행과 정리

- **SRS-LIFE-001** framework startup은 다음 순서로 실행해야 한다.
  1. runtime이 없으면 runtime 조립 및 앱 연결
  2. 명시적 runtime이고 startup healthcheck가 활성화된 경우 runtime 점검
  3. 인증 provider 필수 조건 검증
  4. managed resource를 선언 순서대로 생성하고 readiness check 등록
  5. startup healthcheck가 활성화된 경우 required managed resource 점검
  6. 사용자 정의 lifespan 진입
- **SRS-LIFE-002** 자동 조립 runtime의 startup 점검은 `RuntimePlan`의 healthcheck 정책을 따라야 한다.
- **SRS-LIFE-003** startup 점검이 실패하고 실패 모드가 `REPORT`이면 결과를 보존하고 기동을 계속해야 하며, 그 외에는 마지막 점검 오류를 전파해야 한다.
- **SRS-LIFE-004** shutdown은 사용자 정의 lifespan 종료 후 managed resource를 역순으로 닫고 마지막으로 runtime을 닫아야 한다.
- **SRS-LIFE-005** startup, 사용자 lifespan 또는 request serving 중 예외가 발생해도 framework 소유 정리를 `finally` 경로에서 시도해야 한다.
- **SRS-LIFE-006** managed resource startup이 부분 실패하면 이미 생성된 자원을 역순으로 rollback해야 한다. rollback 실패는 원래 예외의 note로 남기고 원래 startup 실패를 유지해야 한다.
- **SRS-LIFE-007** managed resource 종료 실패 시 가능한 모든 자원의 종료를 시도한 뒤 `BaseExceptionGroup`으로 보고해야 한다.
- **SRS-LIFE-008** runtime 종료 실패는 구조화 로그를 기록하고 `ServiceCloseError`를 전파해야 한다.

### 4.2 Managed resource

- **SRS-RES-001** `ManagedResource`는 이름 또는 `ResourceKey`, factory, 선택적 healthcheck와 close, required 여부, readiness timeout 및 오류 redaction 정책을 표현해야 한다.
- **SRS-RES-002** resource 이름은 공백일 수 없고 앱 내에서 고유해야 하며 framework 예약 이름과 충돌하지 않아야 한다.
- **SRS-RES-003** resource readiness timeout은 지정 시 양수여야 한다.
- **SRS-RES-004** factory, healthcheck 및 close callback은 동기·비동기 결과를 모두 지원해야 한다.
- **SRS-RES-005** 명시적 close callback이 없으면 자원의 `aclose()`, 그 다음 `close()`를 탐색하여 호출해야 한다.
- **SRS-RES-006** `ResourceKey[T].dependency`와 `get_resource(name)`는 생성 완료된 자원을 반환해야 한다. registry 또는 자원이 준비되지 않았으면 `503 Service Unavailable`을 발생시켜야 한다.
- **SRS-RES-007** resource 종료 시 해당 인스턴스에 결합된 readiness check를 제거해야 한다.
- **SRS-RES-008** `ResourceBinding[T]`는 `ResourceKey[T]`, factory, dependency, lifecycle callback, health check 및 `HealthResultAdapter`를 하나의 typed 선언으로 제공해야 한다. `ManagedResource.bind()`는 기존 선언을 binding으로 승격하는 호환 경로여야 한다.
- **SRS-RES-009** binding의 `call()`과 `invoke_resource()`는 coroutine 함수를 직접 await하고 sync callable을 worker thread에서 실행해야 하며, sync callable이 awaitable을 반환하는 경우도 완료까지 await해야 한다.
- **SRS-RES-010** resource invocation은 선택적 timeout을 지원하고 caller cancellation과 예외를 숨기지 않아야 하며, `ResourceRegistry`의 sync factory와 close callback에도 같은 executor 정책을 적용해야 한다.

---

## 5. Readiness 및 Health 요구사항

### 5.1 Readiness registry

- **SRS-READY-001** `ReadinessCheckSpec`은 `name`, `check`, `required=True`, `timeout_seconds=None`, `redact_errors=True`를 제공해야 한다.
- **SRS-READY-002** `register_readiness_check(...)`는 앱별 registry에 check를 등록해야 하며 빈 이름, 중복 이름 및 0 이하 timeout을 거부해야 한다.
- **SRS-READY-003** 동기 check는 worker thread에서 실행하여 event loop를 차단하지 않아야 하며 동기 함수가 awaitable을 반환하면 그 결과도 await해야 한다.
- **SRS-READY-004** check가 `False`를 반환하거나 예외 또는 timeout이 발생하면 실패로 처리해야 한다.
- **SRS-READY-005** check가 `HealthCheckResult`를 반환하면 하위 결과를 `<parent>.<child>` 이름으로 펼치고 parent의 required 정책을 상속해야 한다.
- **SRS-READY-006** 하위 이름과 동일한 spec이 있으면 exact match를 우선하고, 없으면 최상위 parent spec으로 required·timeout·redaction 정책을 해석해야 한다.
- **SRS-READY-007** 필수 check가 실패해도 완료된 선택·성공 check 결과를 보존해야 한다.
- **SRS-READY-008** registry는 설정에 따라 순차 또는 병렬 실행과 전체 timeout을 지원해야 한다.
- **SRS-READY-009** `HealthOutcome` protocol 또는 명시적 adapter는 `bool`, 기존 `HealthCheckResult`, `ok`·`detail`·`error`를 가진 SDK health 결과를 공통 readiness 결과로 정규화해야 한다. adapter가 없는 opaque legacy sentinel은 0.6.0 호환을 위해 성공 sentinel로 허용한다.
- **SRS-READY-010** sync·async check와 adapter는 동일한 timeout·redaction·required 정책을 사용해야 하며, `ok=False` 결과는 예외와 같은 readiness failure로 처리해야 한다.

### 5.2 HTTP health 계약

- **SRS-HEALTH-001** `GET /health/liveness`는 HTTP `200`과 `{"status":"ok","details":null}`을 반환해야 한다.
- **SRS-HEALTH-002** `GET /health/readiness`는 등록된 check가 없으면 HTTP `200`과 `ok` 상태를 반환해야 한다.
- **SRS-HEALTH-003** readiness 응답 상태는 다음 규칙을 따라야 한다.

| 조건 | HTTP status | 응답 `status` |
|---|---:|---|
| 모든 check 성공 | 200 | `ok` |
| optional check만 실패 | 200 | `degraded` |
| required check 실패 | 503 | `error` |
| 전체 timeout | 503 | `error` |

- **SRS-HEALTH-004** 개별 상세 결과는 `ok`, `latency_ms`, `error`, `required`, `enabled`를 제공해야 한다. 전체 timeout 응답의 `details`는 `null`일 수 있다.
- **SRS-HEALTH-005** `redact_errors=True`인 실패는 외부 응답에 원문 오류를 노출하지 않아야 한다.
- **SRS-HEALTH-006** 개별 readiness 실패는 서비스명, 결과, 지연 시간 및 required 여부를 포함하는 구조화 로그로 기록해야 한다. 전체 timeout은 timeout 범위를 식별하는 구조화 로그로 기록해야 하며 두 로그 모두 DocMesh 민감 정보 마스킹 정책을 적용해야 한다.

---

## 6. 인증 및 인가 요구사항

### 6.1 인증 조립

- **SRS-AUTH-001** 자동 runtime 조립 경로에서 auth router를 활성화하면 Keycloak이 활성·필수 서비스로 선택되어야 한다. framework는 Keycloak을 암묵적으로 활성화하지 않아야 한다.
- **SRS-AUTH-002** 자동 조립 전에 auth 요구사항이 포함된 동일 `RuntimePlan`으로 `diagnose_services(plan=...)`를 실행해야 한다. 진단 실패 시 네트워크 연결 전에 secret-safe 구성 오류를 발생시켜야 한다.
- **SRS-AUTH-003** 명시적 runtime 경로에서 auth router가 활성화되고 별도 `auth_provider`가 없으면 runtime에 유효한 Keycloak provider가 있어야 한다. 없으면 request serving 전에 구성 오류를 발생시켜야 한다.
- **SRS-AUTH-004** `auth_provider` 입력은 테스트 또는 사용자 정의 provider를 위한 명시적 조립 경로여야 한다. auth router가 비활성화된 앱은 Keycloak 설정 또는 provider를 요구하지 않아야 한다.

### 6.2 Auth router와 사용자 계약

- **SRS-AUTH-005** auth router를 포함한 앱은 `POST /token`과 `GET /user`를 제공해야 한다.
- **SRS-AUTH-006** `POST /token`은 `OAuth2PasswordRequestForm`의 username, password 및 공백 구분 scope를 provider에 전달하고 `TokenResponse`를 반환해야 한다.
- **SRS-AUTH-007** 동기 token provider 호출은 worker thread에서 실행해야 하며 반환 token type은 소문자로 정규화해야 한다.
- **SRS-AUTH-008** token 발급 오류는 `WWW-Authenticate: Bearer`를 포함하고 다음과 같이 매핑해야 한다.

| 오류 | HTTP status | `detail` |
|---|---:|---|
| 인증 실패 | 401 | `Authentication failed` |
| provider 구성 오류 | 500 | `Authentication service misconfigured` |
| 일시적 provider 오류 | 503 | `Authentication service unavailable` |
| 일반 upstream 오류 | 502 | `Authentication service error` |
| 예상하지 못한 오류 | 500 | `Authentication service error` |

- **SRS-AUTH-009** `get_current_user()`는 token 누락과 검증 실패를 `401`로 처리하고 `WWW-Authenticate: Bearer`를 포함해야 한다.
- **SRS-AUTH-010** 인증 성공 시 dependency는 provider의 `AuthenticatedUser`를 정보 손실 없이 반환해야 하며 `/user` endpoint에서만 `UserInfo`로 변환해야 한다.
- **SRS-AUTH-011** `UserInfo.username`은 preferred username을 우선하고 없으면 subject를 사용해야 한다.

### 6.3 인가 dependency

- **SRS-AUTH-012** `require_roles`, `require_scopes`, `require_permissions`는 요청된 모든 항목이 부여되어야 통과하는 AND semantics를 사용하고 실패 시 `403`을 발생시켜야 한다.
- **SRS-AUTH-013** role은 realm role과 모든 client role의 중복 제거 합집합으로 계산해야 한다.
- **SRS-AUTH-014** scope는 token claim의 공백 구분 `scope` 문자열로 계산해야 한다.
- **SRS-AUTH-015** permission은 role과 scope의 합집합을 대상으로 검사해야 하며 성공한 dependency는 동일한 `AuthenticatedUser`를 반환해야 한다.

---

## 7. 서비스 Dependency 요구사항

- **SRS-DEP-001** 공통 dependency로 `get_service_runtime`, `get_settings`, `get_service_client(name)`, `get_resource(name)`를 공개해야 한다.
- **SRS-DEP-002** typed dependency로 `get_keycloak_auth_service`, `get_postgres_engine`, `get_sqlite_engine`, `get_minio_client`, `get_milvus_client`, `get_ollama_client`, `get_langfuse_client`, `get_nats_connection_builder`를 공개해야 한다.
- **SRS-DEP-003** `get_settings`는 별도 전역 설정이 아니라 현재 앱 runtime의 `ServiceConfigs`를 반환해야 한다.
- **SRS-DEP-004** runtime이 준비되지 않았거나 요청한 서비스가 활성화되지 않았으면 `503 Service Unavailable`을 발생시켜야 한다.
- **SRS-DEP-005** wrapper 종류 또는 unwrap한 client 실제 타입이 typed dependency 계약과 다르면 `500 Internal Server Error`를 발생시켜 조립 오류와 가용성 오류를 구분해야 한다.
- **SRS-DEP-006** NATS dependency는 `NatsConnectionBuilder`를 직접 반환하고 나머지 typed 서비스 dependency는 `ServiceClientWrapper`에서 실제 client를 unwrap해야 한다.
- **SRS-DEP-007** dependency 구현은 `app.state.settings` 또는 `app.state.service_clients`와 같은 폐기된 상태를 fallback으로 사용하지 않아야 한다.

---

## 8. HTTP, 오류 및 관측성 요구사항

### 8.1 요청 추적

- **SRS-HTTP-001** 모든 HTTP 요청은 `X-Correlation-ID`를 request state와 response header에 제공해야 한다.
- **SRS-HTTP-002** 입력 correlation ID는 영문자, 숫자, `.`, `_`, `:`, `-`만 포함한 1~128자일 때 수용해야 한다. 그 외에는 새로운 32자리 hex ID로 교체해야 한다.

### 8.2 오류 응답과 확장

- **SRS-ERR-001** 기본 renderer는 HTTP 예외, request validation 오류 및 미처리 오류를 `application/problem+json`의 `ProblemDetail`로 반환해야 한다.
- **SRS-ERR-002** `ProblemDetail`은 `type`, `title`, `status`, `detail`, `instance`, `correlation_id`를 포함해야 한다.
- **SRS-ERR-003** validation 오류 detail은 `Request validation failed`, 미처리 오류 detail은 `Internal Server Error`로 고정하여 내부 정보를 노출하지 않아야 한다.
- **SRS-ERR-004** `ErrorMapping`은 status code, detail, title, type URI, header, domain code 및 extension metadata를 표현할 수 있어야 한다.
- **SRS-ERR-005** `register_error_mapper()`와 선언형 `ErrorMapperSpec`은 동기·비동기 mapper 결과를 동일한 sanitize·render 흐름으로 처리해야 한다.
- **SRS-ERR-006** 앱 수준과 module 수준 error mapper는 일괄 검증해야 하며 동일 예외 타입의 중복을 override하지 않고 거부해야 한다.
- **SRS-ERR-007** 앱 생성 후 `register_error_mapper()`로 동일 예외 타입을 다시 등록하는 경우에도 오류를 발생시켜야 한다.
- **SRS-ERR-008** `error_renderer`가 제공되면 기본 problem envelope 대신 동기·비동기 custom renderer를 사용하되 민감 정보가 제거된 `ErrorMapping`만 전달해야 한다.
- **SRS-ERR-009** `ExceptionMappingTable`은 예외 유형의 MRO에서 most-specific mapping을 선택하고 명시적 fallback을 지원해야 하며, duplicate mapping과 fallback에 도달할 수 없는 `Exception` mapping을 생성 시 거부해야 한다.
- **SRS-ERR-010** table mapping은 response status, headers, domain code 및 extensions를 보존하고 sync·async mapping callable을 동일한 rendering 흐름으로 처리해야 한다.
- **SRS-ERR-011** `create_error_renderer()`는 correlation ID extractor, status별 fallback code, 안전한 envelope builder 및 optional Problem Details mode를 조합할 수 있어야 한다. renderer는 body correlation ID와 `X-Correlation-ID` response header를 일관되게 제공해야 한다.

### 8.3 Module transport policy 및 streaming

- **SRS-HTTP-003** `TransportPolicy`는 공통 security dependency, validation status/response model, common error response model, fallback response model, custom responses, renderer 및 synthetic 422 유지 여부를 선언해야 한다.
- **SRS-HTTP-004** app/module transport policy는 route 등록 시 dependency와 response metadata에 적용되고, 같은 policy 객체의 규칙을 runtime validation handler와 OpenAPI 생성에 함께 사용해야 한다.
- **SRS-HTTP-005** `validation_status=400`과 `include_synthetic_422=False`를 선언한 route는 validation 오류를 400으로 반환하고 OpenAPI에서 synthetic 422를 제거해야 한다. 기본 policy는 기존 422 계약을 유지해야 한다.
- **SRS-HTTP-006** module policy의 공통 renderer·response·validation 선언이 서로 충돌하면 silent override 없이 앱 생성 전에 실패해야 하며, module-local dependency는 해당 module route에만 적용되어야 한다.
- **SRS-HTTP-007** `ManagedStreamingResponse`는 sync/async iterator와 기존 `StreamingResponse` metadata를 보존하고, 정상 완료·producer exception·disconnect·cancellation에서 resource close/aclose를 정확히 한 번 실행해야 한다. sync close는 worker thread에서 실행해야 한다.

### 8.4 로깅과 access log

- **SRS-OBS-001** 앱 로깅은 DocMesh 공통 logging 설정을 사용하고 JSON 모드에서 timestamp, logger, level, message와 선택적 function·event·exception 정보를 구조화해야 한다.
- **SRS-OBS-002** access logging이 활성화되면 각 HTTP 요청 완료 시 method, route template 또는 안전한 path, status code, duration, outcome 및 correlation ID를 포함하는 event를 정확히 한 번 기록해야 한다.
- **SRS-OBS-003** access log는 query string, Authorization·Cookie header, request·response body 및 credential·token 원문을 기록하지 않아야 한다. route가 확정되지 않은 요청은 query를 제외한 path만 기록할 수 있다.
- **SRS-OBS-004** 정상 응답, framework 오류, 미처리 예외 및 streaming 응답에 같은 완료 event 계약을 적용해야 한다. streaming 응답은 마지막 body 전송 또는 전송 실패 시점을 완료로 계산해야 한다.
- **SRS-OBS-005** health access log는 기본적으로 제외하고 `access_log_health_enabled=True`일 때만 기록해야 한다.
- **SRS-OBS-006** access logging 활성 여부와 관계없이 correlation ID 응답 계약을 유지해야 한다.
- **SRS-OBS-007** token 발급, readiness 및 미처리 요청 오류 로그에 credential 또는 token 원문을 기록하지 않아야 한다.

---

## 9. Schema 요구사항

- **SRS-SCHEMA-001** `HealthResponse`는 `status: "ok" | "degraded" | "error"`와 선택적 `details`를 제공해야 한다.
- **SRS-SCHEMA-002** `HealthServiceDetail`은 `ok`, `latency_ms`, `error`, `required=False`, `enabled=True`를 제공해야 한다.
- **SRS-SCHEMA-003** `TokenResponse`는 `access_token`, 선택적 `refresh_token`, 기본값이 `bearer`인 `token_type`을 제공해야 한다.
- **SRS-SCHEMA-004** `UserInfo`는 `sub`, `username`, 선택적 `email`과 `name`, 기본 빈 목록인 `roles`와 `scopes`를 제공해야 한다.
- **SRS-SCHEMA-005** `ProblemDetail`은 8.2절의 오류 응답 필드를 직렬화해야 한다.

---

## 10. 테스트 지원 요구사항

- **SRS-TEST-001** `fastapi_core.testing`은 `ApplicationContractProfile`, `create_empty_runtime`, `ResourceLifecycleProbe`, `assert_health_contract`, `assert_auth_router_contract`, `assert_application_contract`, `assert_module_contract`, `assert_openapi_contract`, `test_environment`를 공개해야 한다.
- **SRS-TEST-002** `create_empty_runtime()`은 production runtime helper와 동일한 canonical empty `ServiceRuntime`을 반환해야 한다.
- **SRS-TEST-003** `ResourceLifecycleProbe`는 실제 managed resource를 생성하여 create, check, close 이벤트 순서를 기록해야 한다.
- **SRS-TEST-004** health assertion은 liveness와 readiness 성공 계약을, auth assertion은 auth router 포함 여부를 실제 HTTP 요청으로 검증해야 한다.
- **SRS-TEST-005** `test_environment(overrides)`는 진입 시 환경값을 설정 또는 삭제하고 앱·DocMesh 설정 cache를 초기화해야 한다.
- **SRS-TEST-006** `test_environment`는 정상·예외 종료 모두에서 환경을 정확히 원상복구하고 cache를 다시 초기화해야 한다. 중첩 context는 각 진입 시점의 환경을 복원 기준으로 사용해야 한다.
- **SRS-TEST-007** `test_environment`는 process-global 환경을 변경하므로 thread-safe 동시 사용을 보장하지 않아야 하며 오류나 표현에 credential 값을 포함하지 않아야 한다.
- **SRS-TEST-008** module assertion은 module의 router operation, resource, readiness check 및 error mapper 등록 여부를 확인하되 resource lifecycle을 대신 실행하지 않아야 한다.
- **SRS-TEST-009** OpenAPI assertion은 실제 schema를 생성하고 요구된 path·method, operation ID 고유성, security scheme 및 component schema reference 유효성을 의미 기반으로 검사해야 한다.
- **SRS-TEST-010** OpenAPI 검증은 비계약적 출력 순서나 설명 문구까지 고정하는 전체 JSON 문자열 snapshot을 기본 방식으로 사용하지 않아야 한다.
- **SRS-TEST-011** async 동작을 검증하는 프로젝트 테스트는 `pytest-asyncio` async test 함수에서 직접 `await`해야 한다.
- **SRS-TEST-012** `ApplicationContractProfile`은 module 이름, expected route, security scheme, validation status, common response, resource/readiness/error mapper 및 transport policy assertion을 하나의 조합 가능한 typed profile로 제공해야 한다.

---

## 11. 검증 및 추적성

### 11.1 요구사항별 대표 근거

| 요구사항 영역 | 대표 소스 | 대표 테스트 |
|---|---|---|
| 공개 API·앱 조립 | `fastapi_core/__init__.py`, `factory.py`, `modules.py`, `transport.py` | `test_public_api.py`, `test_factory.py`, `test_target_contracts.py` |
| 설정·runtime | `config.py`, `runtime.py`, `docmesh_settings.py` | `test_config.py`, `test_settings_compatibility.py`, `test_factory.py` |
| lifespan·자원 | `lifecycle.py`, `resources.py`, `invocation.py`, `streaming.py` | `test_factory.py`, `test_extensions.py`, `test_target_contracts.py` |
| readiness·health | `readiness.py`, `routers/health.py` | `test_extensions.py`, `test_health_router.py`, `test_target_contracts.py` |
| 인증·인가 | `routers/auth.py`, `dependencies/auth.py` | `test_auth_router.py`, `test_dependencies.py`, `test_next_requirements.py` |
| 서비스 dependency | `dependencies/services.py`, `dependencies/config.py` | `test_dependencies.py`, integration runtime tests |
| HTTP 오류·관측성 | `http.py`, `schemas/error.py`, `streaming.py` | `test_http.py`, `test_next_requirements.py`, `test_target_contracts.py` |
| schema | `schemas/` | `test_schemas.py`, router tests |
| 소비사 테스트 helper | `testing.py` | `test_testing.py`, `test_next_requirements.py`, `test_target_contracts.py` |

### 11.2 검증 기준

- **SRS-VER-001** non-integration 회귀는 `uv run --frozen pytest -q -m "not integration"`로 검증해야 한다.
- **SRS-VER-002** 전체 회귀는 `uv run --frozen pytest -q`로 검증하고 외부 서비스나 credential이 없는 환경의 integration skip을 별도로 보고해야 한다.
- **SRS-VER-003** 요구사항 문서 변경은 requirement ID 중복, Markdown fence 균형, 직접 참조한 로컬 파일의 존재 및 `git diff --check`를 검사해야 한다.
- **SRS-VER-004** 공개 API 또는 동작 계약이 변경되면 구현, 대표 회귀 테스트 및 이 문서를 같은 변경에서 갱신해야 한다.

### 11.3 구현 상태

- 이 문서의 모든 요구사항은 `fastapi-core 0.6.0` 현재 구현 계약이며, 2026-08-02에 구현·회귀 검증된 promoted extension을 포함한다.
- 미래 기능, 우선순위 backlog 및 릴리스 이력은 현재 구현 요구사항과 혼합하지 않는다.
- 제품 수준 완료 조건은 `docs/prd.md`, 구체 소프트웨어 수용 기준은 이 문서를 기준으로 판정한다.
