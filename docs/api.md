# fastapi-core API Reference

> 문서 목적: `fastapi-core`의 **현재 구현된 FastAPI 공개 표면**을 문서화한다.
> 기준 문서: `docs/prd.md`, `docs/srs.md`
> 문서 상태: 구현 반영본(fastapi-core v0.4)

---

## 1. 문서 개요

이 문서는 계획 문서가 아니라 현재 저장소 코드와 테스트를 기준으로 정리한 **실구현 API 문서**다.
외부 서비스 SDK 래퍼보다, FastAPI 서비스 작성자가 직접 사용하는 공개 표면을 우선 설명한다.

- 작성일: `2026-07-03`
- 작성자: `Hermes Agent`
- 문서 리비전: `v0.7`
- 대상 릴리스: `v0.4`
- 상태: `implemented-surface`

핵심 범주:
- app factory
- router
- dependency
- schema
- config / settings loader
- `app.state` 기반 통합 지점

---

## 2. Entry point

`pyproject.toml` 기준 FastAPI entrypoint:

```toml
[tool.fastapi]
entrypoint = "fastapi_core.factory:create_app"
```

패키지 루트에서 보장하는 공개 re-export는 다음과 같다.

```python
from fastapi_core import (
    ErrorMapping,
    ManagedResource,
    ReadinessCheckSpec,
    create_app,
    register_error_mapper,
    register_readiness_check,
)
```

---

## 3. App factory API

### 3.1 `create_app(config=None, settings=None, lifespan=None, include_auth_router=True, resources=()) -> FastAPI`

공통 FastAPI 애플리케이션을 생성한다.

#### 입력
- `config: AppConfig | None`
- `settings: docmesh_py_core.ServiceConfigs | None`
- `lifespan: Callable | None`
- `include_auth_router: bool = True`
- `resources: Sequence[ManagedResource[Any]] = ()`

#### 현재 구현 동작
- `config is None`이면 `load_app_config()`를 사용한다.
- `_configure_application_logging(config)`로 앱 로깅을 초기화한다.
- `settings is None`이면 lifespan startup에서 `assemble_service_runtime(...)`을 호출해 설정 탐색, required 검증, client 생성, 선택적 startup healthcheck를 수행한다.
- `settings`가 명시되면 direct factory로 client를 만들고 `ServiceRuntime`에 담는 테스트/특수 실행용 주입 경로를 사용한다.
- `FastAPI(root_path=config.root_path, lifespan=_build_lifespan(...))` 인스턴스를 생성한다.
- `app.state`에 아래 값을 저장한다.
  - `config`
  - `root_logger`
  - `service_runtime`
  - `settings`
  - `service_clients`
  - `auth_provider` (keycloak client가 구성된 경우)
  - `oauth2_scheme`
  - `readiness_parallel`
  - `readiness_timeout_seconds`
  - `readiness_overall_timeout_seconds`
  - `readiness_checks`
  - `readiness_services`
  - `required_services`
  - `readiness_registry`
  - `resource_registry`
- `config.token_url`로 앱 전용 OAuth2 scheme을 만들고 dependency override와 OpenAPI password flow에 반영한다. module-global scheme model은 변경하지 않는다.
- CORS middleware를 등록한다.
- correlation ID middleware와 표준 problem-details exception handler를 등록한다.
- health router를 기본 포함한다.
- `include_auth_router=True`일 때 auth router를 포함한다.
- managed resource를 선언 순서로 생성하고 생성의 역순으로 정리한다.
- resource startup 실패 시 이미 생성한 resource를 역순 rollback한다.

#### readiness 기본 구성
기본 `create_app()` 경로는 `config.enabled_services`를 기준으로 `service_clients` 기반 readiness check를 자동 생성한다.

- `app.state.readiness_checks[service_name] = service client wrapper의 check callable`
- `app.state.readiness_services[service_name] = {"enabled": True, "required": ...}`
- `app.state.required_services = set(config.required_services)`

기본 `AppConfig`에서는 `enabled_services == ["keycloak"]`, `required_services == ["keycloak"]`다.

#### lifespan 동작
기본 경로에서는 lifespan startup이 `assemble_service_runtime(...)`을 await한 뒤 `app.state.service_runtime/settings/service_clients/readiness_checks`를 설치한다. enabled/required와 함께 `one_of`, 병렬 실행, per-service/overall timeout을 전달한다. `startup_healthcheck=True`이면 assembly 단계에서 동일한 timeout 정책으로 startup healthcheck를 수행하고, 명시적 `settings` 주입 경로에서는 생성된 runtime의 `check()`를 호출한다.

사용자가 전달한 custom lifespan은 service runtime과 managed resource 준비 뒤 실행된다. startup check 실패 시 생성된 client/resource를 rollback한다. custom lifespan shutdown 뒤 managed resource를 역순으로 정리하고, 마지막으로 service runtime을 닫는다. service runtime 종료 실패는 `service_runtime_close_failed` 구조화 로그를 남긴 뒤 `ServiceCloseError`로 전파한다.

#### 반환값
- `FastAPI`

#### 예시

```python
from fastapi_core import create_app

app = create_app()
```

```python
app = create_app(include_auth_router=False)
```

### 3.2 Runtime extension API

#### `ManagedResource`

서비스 SDK나 연결 객체의 생성, readiness, 종료 정책을 하나로 선언한다.

주요 필드:
- `name`
- `factory(app)` — sync/async 반환 지원
- `healthcheck(resource)` — 선택, sync/async 지원
- `close(resource)` — 선택, sync/async 지원
- `required=True`
- `readiness_timeout_seconds=None`
- `redact_errors=True`

명시적 `close`가 없으면 `aclose()`, `close()` 순서로 자동 정리 프로토콜을 찾는다. 여러 resource는 선언 순서로 생성되고 역순으로 정리된다.

#### `register_readiness_check(app, name, check, *, required=True, timeout_seconds=None, redact_errors=True)`

사용자 정의 sync/async readiness check를 앱별 registry에 등록한다. 중복 이름과 빈 이름은 `ValueError`다. check별 timeout이 없으면 앱의 `readiness_timeout_seconds`를 사용한다. `redact_errors=True`이면 외부 응답 오류를 안정된 일반 메시지로 대체한다.

#### `ReadinessCheckSpec`

registry가 보관하는 typed readiness 선언이다. 현재 public helper는 동일 필드를 개별 인자로 받아 이 spec을 생성한다.

#### `get_resource(name)`

정의 위치: `fastapi_core.dependencies`

managed resource를 route에 주입하는 dependency factory다. lifecycle 안에서는 생성된 동일 객체를 반환하며, 등록되지 않았거나 사용할 수 없으면 `503`을 반환한다.

---

### 3.3 HTTP contract API

#### Correlation ID

모든 HTTP 요청은 `X-Correlation-ID`를 응답 header와 `request.state.correlation_id`에서 사용할 수 있다. 입력값은 영문자, 숫자, `.`, `_`, `:`, `-`로 구성된 1~128자만 신뢰한다. 값이 없거나 유효하지 않으면 32자리 hexadecimal UUID를 생성한다.

#### `ErrorMapping`

package root에서 import할 수 있는 immutable 오류 매핑 선언이다.

- `status_code: int`
- `detail: str`
- `title: str | None = None`
- `type_uri: str = "about:blank"`
- `headers: dict[str, str] | None = None`

#### `register_error_mapper(app, exception_type, mapper)`

서비스별 domain 예외를 공통 problem-details 응답으로 변환한다. mapper는 `(Request, Exception)`을 받고 `ErrorMapping` 또는 awaitable을 반환한다. detail은 응답 전에 공통 민감정보 마스킹을 거친다.

#### 기본 오류 변환

- `HTTPException`: 기존 status/detail/header를 유지하고 problem-details envelope로 변환
- `RequestValidationError`: `422`, `Request validation failed`
- 미처리 `Exception`: `500`, `Internal Server Error`; 원문 예외는 응답에 포함하지 않음
- media type: `application/problem+json`

## 4. Router API

### 4.1 Auth router

정의 위치: `fastapi_core.routers.auth`

- prefix 없음
- tag: `auth`

#### `POST /token`

`OAuth2PasswordRequestForm`을 입력으로 받아 token provider 결과를 `TokenResponse`로 변환한다.

##### 입력
- form field: `username`
- form field: `password`
- form field: `scope`

##### 현재 구현 세부사항
- `scope = " ".join(form_data.scopes) or None`
- provider의 `fetch_access_token(scope=scope, username=form_data.username, password=form_data.password)`를 호출한다.
- 실패 시 route 내부에서 예외 유형별 HTTP 상태 코드와 메시지를 매핑한다.

##### 실패 매핑
- `KeycloakTokenAuthenticationError` → `401 Authentication failed`
- `KeycloakTokenConfigurationError` → `500 Authentication service misconfigured`
- `KeycloakTokenTemporaryError` → `503 Authentication service unavailable`
- `KeycloakTokenError` → `502 Authentication service error`
- 기타 예외 → `500 Authentication service error`

모든 실패 응답에는 `WWW-Authenticate: Bearer` 헤더가 포함된다.
로그는 `token_issue_failed` 메시지와 구조화 `event` payload로 남는다.

##### 응답 모델
- `TokenResponse`

##### 성공 응답 예시

```json
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "bearer"
}
```

#### `GET /user`

현재 인증된 사용자 정보를 반환한다.

##### 응답 모델
- `UserInfo`

##### 동작
- 내부적으로 `get_current_user()` dependency를 사용한다.

---

### 4.2 Health router

정의 위치: `fastapi_core.routers.health`

- prefix: `/health`
- tag: `health`

#### `GET /health/liveness`

프로세스 생존 여부를 확인한다.

##### 응답 모델
- `HealthResponse`

##### 현재 응답 예시

```json
{
  "status": "ok",
  "details": null
}
```

#### `GET /health/readiness`

외부 의존성 준비 상태를 확인한다.

##### 응답 모델
- `HealthResponse`

##### 현재 구현 동작
- 기본 경로는 앱별 `ReadinessRegistry`에 등록된 typed check를 실행한다.
- legacy state 객체가 교체된 경우 기존 테스트/호환 경로로 아래 state 구조를 집계한다.
- `app.state.readiness_checks`에서 서비스명 → check callable 매핑을 읽는다.
- `app.state.readiness_services`에서 서비스별 메타데이터(`required`, `enabled`)를 읽는다.
- `app.state.required_services`에서 필수 서비스 집합을 읽는다.
- `app.state.readiness_parallel`에서 병렬 실행 여부를 읽는다.
- `app.state.readiness_timeout_seconds`에서 서비스별 제한 시간을 읽는다.
- `app.state.readiness_overall_timeout_seconds`에서 전체 제한 시간을 읽는다.
- readiness check가 비어 있으면 `{"status": "ok", "details": null}`을 반환한다.
- readiness check가 있으면 `docmesh_py_core.async_check_all_services(...)`로 집계한다.
- 서비스별 timeout은 해당 서비스 실패로 집계하며 빈 timeout 오류 문자열은 `health check timed out`으로 정규화한다.
- typed check별 timeout이 있으면 앱 공통 timeout보다 우선하며, 생략하면 앱 공통 timeout을 fallback으로 사용한다.
- `redact_errors=True`인 typed check의 외부 오류는 `readiness check failed`로 정규화한다.
- overall timeout은 `503 + status="error" + details=null`로 반환하고 `readiness_check_timeout` 경고 로그를 남긴다.
- 필수 서비스 실패 시 `503 + status="error"`를 반환한다.
- 선택 서비스만 실패 시 `200 + status="degraded"`를 반환한다.
- 모두 성공 시 `200 + status="ok"`를 반환한다.

##### 세부 응답 형식
성공/실패 공통으로 `details`는 서비스별 `HealthServiceDetail` 구조를 가진다.

```json
{
  "status": "degraded",
  "details": {
    "keycloak": {
      "ok": true,
      "latency_ms": 3,
      "error": null,
      "required": true,
      "enabled": true
    },
    "nats": {
      "ok": false,
      "latency_ms": null,
      "error": "masked error",
      "required": false,
      "enabled": true
    }
  }
}
```

##### 로깅
- 실패한 서비스마다 `readiness_check_failed` 경고 로그를 남긴다.
- 구조화 `event`에는 `service`, `operation`, `outcome`, `required`, `enabled`, `latency_ms`, `error` 등이 들어간다.
- `error` 값은 `docmesh_py_core`의 마스킹 정책 영향을 받을 수 있다.

---

## 5. Dependency API

### 5.1 `get_config(request: Request) -> AppConfig`

정의 위치: `fastapi_core.dependencies.config`

#### 동작
- `request.app.state.config`가 있으면 그것을 반환한다.
- 없으면 `load_app_config()`를 사용한다.

#### 참고
- 요청 없는 독립 호출용 helper가 아니라 FastAPI dependency 형태를 기준으로 구현되어 있다.
- 실제 캐시는 `load_app_config()`의 `lru_cache`에 있다.

### 5.2 `get_settings(request: Request, config: AppConfig = Depends(get_config)) -> ServiceConfigs`

정의 위치: `fastapi_core.dependencies.config`

#### 동작
- `request.app.state.settings`가 `None`이 아니면 그것을 반환한다.
- state가 없거나 기본 runtime startup 전이라 값이 `None`이면 `load_docmesh_settings(tuple(config.enabled_services))`를 사용한다.
- 현재 `config` 인자는 dependency wiring 목적이며 함수 본문에서는 `enabled_services` 계산 외 직접 사용하지 않는다.

### 5.3 `get_auth_provider(request: Request, settings: ServiceConfigs = Depends(get_settings)) -> KeycloakAuthService`

정의 위치: `fastapi_core.dependencies.auth`

#### 동작
- `app.state.auth_provider`가 있으면 재사용한다.
- 없으면 `app.state.service_clients`를 확인한다.
- `service_clients["keycloak"]`가 있으면 해당 wrapper의 `.client`를 provider로 사용하고 `app.state.auth_provider`에 저장한다.
- 없으면 `settings.keycloak`을 사용해 `KeycloakAuthService(settings.keycloak, allowed_algorithms=["RS256"])`를 직접 생성하고 `app.state.auth_provider`에 저장한다.

### 5.4 서비스 클라이언트 접근 표면

#### `get_service_client(service_name: str) -> dependency`

정의 위치: `fastapi_core.dependencies.services`

서비스 이름을 받아 `app.state.service_clients`에서 해당 클라이언트를 꺼내 주는 dependency factory다.

#### 동작
- `create_app(...)`가 저장한 `app.state.service_clients`를 조회한다.
- 요청한 `service_name`이 존재하면 같은 앱 인스턴스에서 초기화된 클라이언트 객체를 그대로 반환한다.
- `service_clients`가 없거나 해당 서비스가 활성화되지 않았으면 `503 Service Unavailable`과 `Service client '<name>' is not enabled`를 반환한다.

#### 예시

```python
from fastapi import APIRouter, Depends
from fastapi_core.dependencies import get_service_client

router = APIRouter()

@router.get("/sqlite-health")
async def sqlite_health(sqlite_client=Depends(get_service_client("sqlite"))):
    return {"has_check": hasattr(sqlite_client, "check")}
```

#### 범위와 한계
- 반환 타입은 서비스별로 다를 수 있으므로 이 함수는 **통합 관점의 공통 lookup**에 초점을 둔다.

#### 전용 서비스 dependency

반환 타입 구체화가 필요하면 아래 전용 dependency를 사용한다.

- `get_keycloak_auth_service(request) -> KeycloakAuthService`
- `get_postgres_engine(request) -> sqlalchemy.engine.Engine`
- `get_sqlite_engine(request) -> sqlalchemy.engine.Engine`
- `get_minio_client(request) -> minio.Minio`
- `get_milvus_client(request) -> pymilvus.MilvusClient`
- `get_ollama_client(request) -> ollama.Client`
- `get_langfuse_client(request) -> langfuse.Langfuse`
- `get_nats_connection_builder(request) -> docmesh_py_core.NatsConnectionBuilder`

이 함수들은 모두 `app.state.service_clients`를 재사용하며, wrapper 기반 서비스는 내부 `.client`를 꺼내 concrete client를 반환한다. NATS만 예외적으로 wrapper가 아니라 builder 객체 자체를 반환한다.

#### 전용 dependency 예시

```python
from fastapi import APIRouter, Depends
from fastapi_core.dependencies import get_keycloak_auth_service, get_sqlite_engine
from sqlalchemy.engine import Engine
from docmesh_py_core import KeycloakAuthService

router = APIRouter()

@router.get("/diagnostics")
async def diagnostics(
    sqlite_engine: Engine = Depends(get_sqlite_engine),
    keycloak_auth_service: KeycloakAuthService = Depends(get_keycloak_auth_service),
):
    return {
        "sqlite_connect": hasattr(sqlite_engine, "connect"),
        "keycloak_extract_user_info": hasattr(keycloak_auth_service, "extract_user_info"),
    }
```

#### 범위와 한계
- `get_auth_provider()`는 여전히 keycloak wrapper의 `.client`를 꺼내 auth provider를 구성하는 전용 경로를 유지한다.
- `get_nats_connection` 같은 **연결 상태/세션을 직접 보장하는 커스텀 dependency**는 아직 기본 제공하지 않는다.

### 5.5 `get_current_user(token=Depends(oauth2_scheme), provider=Depends(get_auth_provider), settings=Depends(get_settings)) -> UserInfo`

정의 위치: `fastapi_core.dependencies.auth`

#### 동작
- module-global OAuth2 dependency key를 사용하되, 각 앱은 자신의 `token_url`로 생성한 `app.state.oauth2_scheme`을 dependency override로 사용한다.
- bearer token이 없으면 401과 `WWW-Authenticate: Bearer`를 반환한다.
- provider의 `extract_user_info(token)`을 호출한다.
- `docmesh_py_core.TokenValidationError`를 401 `Invalid token`으로 매핑한다.
- 결과 `AuthenticatedUser`를 `UserInfo`로 변환한다.

#### 현재 변환 규칙
- `username = preferred_username or sub`
- `roles = realm_roles + client_roles[*]` 중복 제거
- `scopes = claims["scope"]` 공백 분리

#### 현재 구현에 없는 것
- secure/insecure decode 분기 설정
- introspection 모드 분기

### 5.6 Authorization dependency factories

정의 위치: `fastapi_core.dependencies.auth`

#### `require_roles(*roles)`

`UserInfo.roles`에 요구 role이 모두 있는지 검사한다.

#### `require_scopes(*scopes)`

`UserInfo.scopes`에 요구 scope가 모두 있는지 검사하며 요구 scope를 OpenAPI operation security에 반영한다.

#### `require_permissions(*permissions)`

role과 scope의 합집합을 permission 집합으로 보고 요구 값이 모두 있는지 검사한다. 기존 role 기반 호출도 호환된다.

#### 동작
- 각 factory는 `get_current_user()` 결과를 사용한다.
- 하나라도 없으면 403 `Forbidden`
- 통과 시 현재 `UserInfo` 반환

#### 예시

```python
from fastapi import APIRouter, Depends
from fastapi_core.dependencies import require_scopes
from fastapi_core.schemas.user import UserInfo

router = APIRouter()

@router.get("/documents")
async def documents(user: UserInfo = Depends(require_scopes("document:read"))):
    return {"ok": True}
```

---

## 6. Schema API

### 6.1 `TokenResponse`

정의 위치: `fastapi_core.schemas.token`

```python
class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
```

### 6.2 `UserInfo`

정의 위치: `fastapi_core.schemas.user`

```python
class UserInfo(BaseModel):
    sub: str
    username: str
    email: str | None = None
    name: str | None = None
    roles: list[str] = Field(default_factory=list)
    scopes: list[str] = Field(default_factory=list)
```

### 6.3 `HealthStatus`

정의 위치: `fastapi_core.schemas.health`

```python
HealthStatus = Literal["ok", "degraded", "error"]
```

### 6.4 `HealthServiceDetail`

정의 위치: `fastapi_core.schemas.health`

```python
class HealthServiceDetail(BaseModel):
    ok: bool
    latency_ms: int | None = None
    error: str | None = None
    required: bool = False
    enabled: bool = True
```

### 6.5 `HealthResponse`

정의 위치: `fastapi_core.schemas.health`

```python
class HealthResponse(BaseModel):
    status: HealthStatus
    details: dict[str, HealthServiceDetail] | None = None
```

### 6.6 `ProblemDetail`

정의 위치: `fastapi_core.schemas.error`; `fastapi_core.schemas`에서 re-export한다.

```python
class ProblemDetail(BaseModel):
    type: str = "about:blank"
    title: str
    status: int
    detail: str
    instance: str
    correlation_id: str
```

---

## 7. Config / settings API

### 7.1 `AppConfig`

정의 위치: `fastapi_core.config`

```python
class AppConfig(BaseSettings):
    root_path: str = ""
    token_url: str = "/token"
    cors_origins: list[str] = ["*"]
    cors_credentials: bool = False
    readiness_parallel: bool = False
    readiness_timeout_seconds: float | None = None
    readiness_overall_timeout_seconds: float | None = None
    service_alternatives: list[list[str]] = []
    startup_healthcheck: bool = False
    log_level: str | None = "WARNING"
    log_path: str | None = None
    log_json: bool = True
    log_force: bool = False
    enabled_services: list[str] = ["keycloak"]
    required_services: list[str] = ["keycloak"]
```

#### 관련 환경변수
- `ROOT_PATH`
- `TOKEN_URL`
- `CORS_ORIGINS`
- `CORS_CREDENTIALS`
- `READINESS_PARALLEL`
- `READINESS_TIMEOUT_SECONDS`
- `READINESS_OVERALL_TIMEOUT_SECONDS`
- `DOCMESH_SERVICE_ALTERNATIVES`
- `DOCMESH_HEALTHCHECK_ENABLED` (`startup_healthcheck` alias)
- `DOCMESH_LOG_LEVEL` (`log_level` alias)
- `APP_LOG_PATH` (`log_path` alias)
- `APP_LOG_JSON` (`log_json` alias)
- `APP_LOG_FORCE` (`log_force` alias)
- `DOCMESH_SERVICES` (`enabled_services` alias)
- `READINESS_REQUIRED_SERVICES` (`required_services` alias)

### 7.2 `load_app_config() -> AppConfig`

환경변수 기반 앱 설정 로더.

#### 파싱 규칙
- `cors_origins`, `enabled_services`, `required_services`는 CSV 문자열을 list로 파싱한다.
- 해당 환경변수의 빈 문자열은 빈 목록으로 해석하며, 미설정일 때만 기본값을 사용한다.
- 코드 생성자에서 list 필드에 빈 문자열을 직접 전달하면 validation error다.
- `required_services`는 `enabled_services`의 부분집합이어야 한다.
- 함수는 `lru_cache(maxsize=1)`로 캐시된다.

### 7.3 `build_docmesh_env_overlay() -> dict[str, str]`

정의 위치: `fastapi_core.docmesh_settings`

현재 환경변수를 복사한 뒤, `docmesh_py_core.load_service_configs(...)`가 실패하지 않도록 개발/테스트용 fallback 값을 채운다.

대표 기본값 예:
- `KEYCLOAK_URL=http://keycloak.local`
- `KEYCLOAK_REALM=docmesh`
- `KEYCLOAK_CLIENT_ID=fastapi-core`
- `KEYCLOAK_CLIENT_SECRET=dev-secret`
- `SQLITE_PATH=:memory:`
- `MINIO_ENDPOINT=minio.local:9000`
- `MILVUS_URI=http://milvus.local:19530`
- `OLLAMA_HOST=http://ollama.local:11434`
- `LANGFUSE_HOST=http://langfuse.local:3000`
- `NATS_SERVERS=nats://nats.local:4222`
- `NATS_TOKEN=dev-token`

### 7.4 `load_docmesh_settings(enabled_services: tuple[str, ...] | None = None) -> ServiceConfigs`

정의 위치: `fastapi_core.docmesh_settings`

`build_docmesh_env_overlay()` mapping을 `docmesh_py_core.load_service_configs(env, ...)`에 직접 전달한다. 프로세스 `os.environ`은 변경하지 않는다.

#### 동작
- `enabled_services`가 주어지면 해당 서비스 집합만 선택적으로 로딩한다.
- 예: `("sqlite",)`를 넘기면 `settings.sqlite`는 채워지고 `settings.keycloak`은 `None`일 수 있다.
- 함수는 `lru_cache(maxsize=1)`로 캐시된다.

---

## 8. Lifespan / integration points

`create_app(..., lifespan=...)`는 외부 의존성 초기화를 FastAPI 수명주기와 연결하는 핵심 진입점이다.

현재 코드의 통합 포인트:
- logging과 readiness metadata는 app 생성 단계에서 준비되고, 기본 경로의 `ServiceRuntime` / settings / service_clients / checks는 lifespan startup에서 조립된다.
- custom lifespan이 있으면 runtime state를 설치한 뒤 내부 wrapper가 이를 실행한다.
- 종료 시 `ServiceRuntime.close()`로 sync/async service client 자원을 정리한다.
- custom lifespan shutdown 예외가 발생해도 내부 client 정리는 `finally`에서 실행된다.
- readiness router는 `async_check_all_services(...)`를 await하며 sync/async check를 native async 경로에서 집계한다.
- 필수 서비스 실패 시 `HealthCheckError.result`의 전체 서비스 상태를 응답 details에 보존한다.

권장 통합 지점:
- `ManagedResource` factory에서 추가 연결 객체 생성
- `healthcheck`로 typed readiness registry에 자동 연결
- `get_resource(name)`로 request dependency 주입
- managed resource의 명시적 close 또는 `aclose()`/`close()` 자동 정리 사용

---

## 9. Usage examples

- 기본 예제 모음: `docs/examples.md`
- 문서 교차 점검 기준: `docs/consistency-checklist.md`
- README quick start: `README.md`

대표 예시:

```python
from fastapi_core import create_app

app = create_app(include_auth_router=False)
```

```python
from fastapi_core.config import AppConfig
from fastapi_core.factory import create_app

config = AppConfig(
    token_url="/api/v1/auth/token",
    enabled_services=["keycloak", "nats"],
    required_services=["keycloak"],
)
app = create_app(config=config)
```

---

## 10. 현재 구현 기준 주의점

아직 `fastapi-core`가 직접 제공하지 않는 항목:
- secure/insecure decode 분기나 introspection 모드 선택 API
- `get_nats_connection` 같은 메시징 전용 FastAPI dependency
- NATS 연결 상태 객체를 바로 주입하는 기본 dependency/route 세트

참고로 실제 외부 서비스 연동은 `test_fastapi_core/integration/`의 live integration 테스트에서 별도로 검증된다.

따라서 실제 사용 계약은 이 문서를 우선 참고하되, 공통 lookup은 `get_service_client(...)`, 타입이 중요한 사용처는 전용 dependency(`get_keycloak_auth_service`, `get_postgres_engine`, `get_sqlite_engine`, `get_minio_client`, `get_milvus_client`, `get_ollama_client`, `get_langfuse_client`, `get_nats_connection_builder`)를 우선 사용하고, 연결 상태나 세션 수명주기까지 커스터마이즈해야 하는 경우에만 custom lifespan과 `app.state` 확장을 보완적으로 사용하는 것이 현재 코드 구조와 맞다.
