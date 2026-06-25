# fastapi-core API Reference

> 문서 목적: `fastapi-core`의 **현재 구현된 FastAPI 공개 표면**을 문서화한다.
> 기준 문서: `docs/prd.md`, `docs/srs.md`
> 문서 상태: 구현 반영본(v0.3)

---

## 1. 문서 개요

이 문서는 계획 문서가 아니라 현재 저장소에 구현된 FastAPI API를 기준으로 정리한다.
외부 서비스 SDK 래퍼보다, FastAPI 서비스 작성자가 직접 사용하는 공개 표면을 우선 설명한다.

- 작성일: `2026-06-25`
- 작성자: `Hermes Agent`
- 버전: `v0.3`
- 상태: `implemented-surface`

핵심 범주:
- app factory
- router
- dependency
- schema
- `app.state` 기반 통합 지점

---

## 2. Entry point

`pyproject.toml` 기준 FastAPI entrypoint:

```toml
[tool.fastapi]
entrypoint = "fastapi_core.factory:create_app"
```

패키지 루트에서 보장하는 공개 re-export는 현재 `create_app`이다.

---

## 3. App factory API

### 3.1 `create_app(config=None, settings=None, lifespan=None, include_auth_router=True) -> FastAPI`

공통 FastAPI 애플리케이션을 생성한다.

#### 입력
- `config: AppConfig | None`
- `settings: docmesh_py_core.Settings | None`
- `lifespan: Callable | None`
- `include_auth_router: bool`

#### 현재 구현 동작
- `config is None`이면 `load_app_config()`를 사용한다.
- `settings is None`이면 `load_default_settings()`를 사용한다.
- `FastAPI(root_path=config.root_path, lifespan=lifespan)` 인스턴스를 생성한다.
- `app.state.config`, `app.state.settings`를 저장한다.
- `app.state.readiness_parallel`을 저장한다.
- CORS middleware를 등록한다.
- health router를 기본 포함한다.
- `include_auth_router=True`일 때 auth router를 포함한다.

#### 현재 구현에 없는 것
- logging 초기화
- auth 전용 exception handler 등록
- startup 단계의 기본 Keycloak/NATS readiness check 자동 등록

#### 반환값
- `FastAPI`

#### 예시

```python
from fastapi_core.factory import create_app

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
- `OAuth2PasswordRequestForm`

##### 현재 구현 세부사항
- 현재 구현은 `form_data.scopes`를 공백으로 join한 값을 `provider.fetch_access_token(scope=...)`에 전달한다.
- `username`, `password` 필드는 폼에서 받지만 provider 호출 인자로 직접 넘기지 않는다.
- provider 예외 발생 시 `401 Unauthorized`와 `WWW-Authenticate: Bearer`를 반환한다.

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
- `app.state.required_services`에서 필수 서비스 집합을 읽는다.
- `app.state.readiness_parallel`에서 병렬 실행 여부를 읽는다.
- readiness check가 비어 있으면 `{"status": "ok", "details": null}`을 반환한다.
- readiness check가 있으면 `docmesh_py_core.check_all_services(...)`로 집계한다.
- 필수 서비스 실패 시 `503 Service Unavailable`을 반환한다.

##### 세부 응답 형식
성공 시 `details`는 서비스별 구조를 가진다.

```json
{
  "status": "ok",
  "details": {
    "keycloak": {
      "ok": true,
      "latency_ms": 3,
      "error": null
    }
  }
}
```

실패 시 `details`는 `HealthCheckError` 또는 집계 결과를 그대로 반영한다.
에러 메시지는 `docmesh_py_core`의 마스킹 정책 영향을 받을 수 있다.

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

### 5.2 `get_settings(request: Request, config: AppConfig = Depends(get_config)) -> Settings`

정의 위치: `fastapi_core.dependencies.config`

#### 동작
- `request.app.state.settings`가 있으면 그것을 반환한다.
- 없으면 `load_default_settings()`를 사용한다.
- 현재 `config` 인자는 dependency wiring 목적이며 함수 본문에서는 직접 사용하지 않는다.

### 5.3 `get_auth_provider(request: Request, settings: Settings = Depends(get_settings)) -> KeycloakAuthService`

정의 위치: `fastapi_core.dependencies.auth`

#### 동작
- `app.state.auth_provider`가 있으면 재사용한다.
- 없으면 `KeycloakAuthService(settings)`를 생성해 `app.state.auth_provider`에 저장한다.

### 5.4 `get_current_user(token=Depends(oauth2_scheme), provider=Depends(get_auth_provider), settings=Depends(get_settings)) -> UserInfo`

정의 위치: `fastapi_core.dependencies.auth`

#### 동작
- `OAuth2PasswordBearer(tokenUrl="/token", auto_error=False)`를 사용한다.
- bearer token이 없으면 401과 `WWW-Authenticate: Bearer`를 반환한다.
- provider의 `extract_user_info(token)`을 호출한다.
- `docmesh_py_core.TokenValidationError`를 401로 매핑한다.
- 결과 `AuthenticatedUser`를 `UserInfo`로 변환한다.

#### 현재 변환 규칙
- `username = preferred_username or sub`
- `roles = realm_roles + client_roles[*]` 중복 제거
- `scopes = claims["scope"]` 공백 분리

#### 현재 구현에 없는 것
- secure/insecure decode 분기 설정
- introspection 모드 분기

### 5.5 `require_permissions(*roles) -> dependency`

정의 위치: `fastapi_core.dependencies.auth`

역할 검사용 dependency factory.

#### 동작
- `get_current_user()` 결과의 `roles`에 요구 role이 모두 있어야 한다.
- 하나라도 없으면 403 `Forbidden`
- 통과 시 현재 `UserInfo` 반환

#### 예시

```python
from fastapi import Depends
from fastapi import APIRouter
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

### 6.3 `HealthResponse`

정의 위치: `fastapi_core.schemas.health`

```python
class HealthResponse(BaseModel):
    status: str
    details: dict[str, Any] | None = None
```

`details`는 선택 필드다. 현재 구현에서는 readiness 성공 시 서비스별 상세 구조를, 실패 시 오류 구조를 담을 수 있다.

---

## 7. Config API

### 7.1 `AppConfig`

정의 위치: `fastapi_core.config`

```python
class AppConfig(BaseModel):
    root_path: str = ""
    cors_origins: list[str] = ["*"]
    cors_credentials: bool = False
    readiness_parallel: bool = False
```

### 7.2 `load_app_config() -> AppConfig`

환경변수 기반 앱 설정 로더.

읽는 환경변수:
- `ROOT_PATH`
- `CORS_ORIGINS`
- `CORS_CREDENTIALS`
- `READINESS_PARALLEL`

### 7.3 `load_default_settings() -> docmesh_py_core.Settings`

`docmesh_py_core.load_settings(...)`를 감싸는 기본 설정 로더.
현재 구현은 로컬 개발/테스트를 위해 여러 필수 환경변수에 dev 기본값을 넣는다.

대표 기본값 예:
- `KEYCLOAK_URL=http://keycloak.local`
- `SQLITE_PATH=:memory:`
- `MINIO_ENDPOINT=minio.local:9000`
- `MILVUS_URI=http://milvus.local:19530`
- `OLLAMA_HOST=http://ollama.local:11434`
- `LANGFUSE_HOST=http://langfuse.local:3000`
- `NATS_SERVERS=nats://nats.local:4222`

---

## 8. Lifespan / integration points

`create_app(..., lifespan=...)`는 외부 의존성 초기화를 FastAPI 수명주기와 연결하는 핵심 진입점이다.

현재 코드에서 기본 제공되는 startup/shutdown orchestration은 없고, 사용자가 custom lifespan을 주입하는 방식으로 확장한다.
권장 통합 지점은 다음과 같다.

- startup에서 registry / builder / connection 생성
- `app.state.auth_provider`, `app.state.readiness_checks`, `app.state.required_services` 주입
- shutdown에서 외부 자원 정리

---

## 9. Minimal usage examples

### 9.1 기본 앱 생성

```python
from fastapi_core.factory import create_app

app = create_app()
```

### 9.2 auth router 제외

```python
app = create_app(include_auth_router=False)
```

### 9.3 현재 사용자 주입

```python
from fastapi import APIRouter, Depends
from fastapi_core.dependencies.auth import get_current_user
from fastapi_core.schemas.user import UserInfo

router = APIRouter()

@router.get("/me")
async def me(user: UserInfo = Depends(get_current_user)) -> UserInfo:
    return user
```

### 9.4 readiness check 주입

```python
from fastapi_core.factory import create_app

app = create_app(include_auth_router=False)
app.state.readiness_checks = {
    "keycloak": lambda: None,
}
app.state.required_services = {"keycloak"}
```

---

## 10. 코드-문서 차이 요약

현재 구현은 PRD/SRS의 핵심 공개 표면 일부를 충족하지만, 아직 다음 항목은 미구현 또는 부분 구현이다.

- logging 초기화
- auth exception handler 등록
- `get_current_user()`의 secure/insecure decode 분기
- 기본 readiness check 자동 구성
- `/token`의 사용자명/비밀번호 기반 직접 provider 연계

따라서 PRD/SRS는 목표 문서로 읽고, 실제 사용 계약은 이 API 문서를 우선 참고해야 한다.
