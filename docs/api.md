# fastapi-core API Reference

> 문서 목적: `fastapi-core`의 **현재 구현된 FastAPI 공개 표면**을 문서화한다.
> 기준 문서: `docs/prd.md`, `docs/srs.md`
> 문서 상태: 구현 반영본(v0.5)

---

## 1. 문서 개요

이 문서는 계획 문서가 아니라 현재 저장소 코드와 테스트를 기준으로 정리한 **실구현 API 문서**다.
외부 서비스 SDK 래퍼보다, FastAPI 서비스 작성자가 직접 사용하는 공개 표면을 우선 설명한다.

- 작성일: `2026-07-03`
- 작성자: `Hermes Agent`
- 버전: `v0.5`
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

패키지 루트에서 보장하는 공개 re-export는 현재 `create_app` 하나다.

```python
from fastapi_core import create_app
```

---

## 3. App factory API

### 3.1 `create_app(config=None, settings=None, lifespan=None, include_auth_router=True) -> FastAPI`

공통 FastAPI 애플리케이션을 생성한다.

#### 입력
- `config: AppConfig | None`
- `settings: docmesh_py_core.ServiceConfigs | None`
- `lifespan: Callable | None`
- `include_auth_router: bool = True`

#### 현재 구현 동작
- `config is None`이면 `load_app_config()`를 사용한다.
- `settings is None`이면 `load_docmesh_settings(tuple(config.enabled_services))`를 사용한다.
- `_configure_application_logging(config)`로 앱 로깅을 초기화한다.
- `_build_service_clients(settings, config.enabled_services)`로 서비스 클라이언트 맵을 생성한다.
- `FastAPI(root_path=config.root_path, lifespan=_build_lifespan(lifespan, service_clients))` 인스턴스를 생성한다.
- `app.state`에 아래 값을 저장한다.
  - `config`
  - `root_logger`
  - `settings`
  - `service_clients`
  - `auth_provider` (keycloak client가 구성된 경우)
  - `readiness_parallel`
  - `readiness_checks`
  - `readiness_services`
  - `required_services`
- `set_oauth2_token_url(config.token_url)`을 호출해 OpenAPI password flow의 token URL을 반영한다.
- CORS middleware를 등록한다.
- health router를 기본 포함한다.
- `include_auth_router=True`일 때 auth router를 포함한다.

#### readiness 기본 구성
기본 `create_app()` 경로는 `config.enabled_services`를 기준으로 `service_clients` 기반 readiness check를 자동 생성한다.

- `app.state.readiness_checks[service_name] = service client wrapper의 check callable`
- `app.state.readiness_services[service_name] = {"enabled": True, "required": ...}`
- `app.state.required_services = set(config.required_services)`

기본 `AppConfig`에서는 `enabled_services == ["keycloak"]`, `required_services == ["keycloak"]`다.

#### lifespan 동작
내부 lifespan wrapper는 사용자가 전달한 custom lifespan을 먼저 실행하고, 종료 시 항상 `close_service_clients(service_clients.values())`를 호출한다.

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

---

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
- `app.state.readiness_checks`에서 서비스명 → check callable 매핑을 읽는다.
- `app.state.readiness_services`에서 서비스별 메타데이터(`required`, `enabled`)를 읽는다.
- `app.state.required_services`에서 필수 서비스 집합을 읽는다.
- `app.state.readiness_parallel`에서 병렬 실행 여부를 읽는다.
- readiness check가 비어 있으면 `{"status": "ok", "details": null}`을 반환한다.
- readiness check가 있으면 `docmesh_py_core.check_all_services(...)`로 집계한다.
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
- `request.app.state.settings`가 있으면 그것을 반환한다.
- 없으면 `load_docmesh_settings(tuple(config.enabled_services))`를 사용한다.
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
- `OAuth2PasswordBearer(tokenUrl="/token", auto_error=False)`를 사용한다.
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

### 5.6 `require_permissions(*roles) -> dependency`

정의 위치: `fastapi_core.dependencies.auth`

역할 검사용 dependency factory.

#### 동작
- `get_current_user()` 결과의 `roles`에 요구 role이 모두 있어야 한다.
- 하나라도 없으면 403 `Forbidden`
- 통과 시 현재 `UserInfo` 반환

#### 예시

```python
from fastapi import APIRouter, Depends
from fastapi_core.dependencies.auth import require_permissions
from fastapi_core.schemas.user import UserInfo

router = APIRouter()

@router.get("/admin")
async def admin_only(user: UserInfo = Depends(require_permissions("admin"))):
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
- 빈 문자열은 기본값 처리로 넘긴다.
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

내부 기본값 보강 컨텍스트를 적용한 뒤 `docmesh_py_core.load_service_configs(...)`를 호출한다.

#### 동작
- `enabled_services`가 주어지면 해당 서비스 집합만 선택적으로 로딩한다.
- 예: `("sqlite",)`를 넘기면 `settings.sqlite`는 채워지고 `settings.keycloak`은 `None`일 수 있다.
- 함수는 `lru_cache(maxsize=1)`로 캐시된다.

---

## 8. Lifespan / integration points

`create_app(..., lifespan=...)`는 외부 의존성 초기화를 FastAPI 수명주기와 연결하는 핵심 진입점이다.

현재 코드의 통합 포인트:
- startup 이전에 service_clients / logging / readiness metadata가 app assembly 단계에서 준비된다.
- custom lifespan이 있으면 내부 wrapper가 이를 감싼다.
- 종료 시 service client 자원 정리를 보장한다.

권장 통합 지점:
- startup에서 추가 연결 객체를 `app.state`에 저장
- 필요 시 `app.state.readiness_checks`, `app.state.readiness_services`, `app.state.required_services`를 덮어써 서비스 정책을 세밀화
- shutdown에서 custom 자원 정리

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
- auth 전용 exception handler 등록 API
- secure/insecure decode 분기나 introspection 모드 선택 API
- `get_nats_connection` 같은 메시징 전용 FastAPI dependency
- NATS 연결 상태 객체를 바로 주입하는 기본 dependency/route 세트

참고로 실제 외부 서비스 연동은 `test_fastapi_core/integration/`의 live integration 테스트에서 별도로 검증된다.

따라서 실제 사용 계약은 이 문서를 우선 참고하되, 공통 lookup은 `get_service_client(...)`, 타입이 중요한 사용처는 전용 dependency(`get_keycloak_auth_service`, `get_postgres_engine`, `get_sqlite_engine`, `get_minio_client`, `get_milvus_client`, `get_ollama_client`, `get_langfuse_client`, `get_nats_connection_builder`)를 우선 사용하고, 연결 상태나 세션 수명주기까지 커스터마이즈해야 하는 경우에만 custom lifespan과 `app.state` 확장을 보완적으로 사용하는 것이 현재 코드 구조와 맞다.
