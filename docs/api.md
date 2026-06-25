# fastapi-core API Reference

> 문서 목적: `fastapi-core`의 **FastAPI 공개 표면**을 문서화한다.
> 기준 문서: `docs/prd.md`, `docs/srs.md`
> 문서 상태: 초안(v0.2)

---

## 1. 문서 개요

이 문서는 외부 서비스 SDK 래퍼보다, FastAPI 서비스 작성자가 직접 사용하는 API를 우선 설명한다.

핵심 범주는 다음과 같다.

- app factory
- router
- dependency
- schema
- 설정/인증/메시징과의 통합 지점

---

## 2. Entry point

`pyproject.toml` 기준 FastAPI entrypoint:

```toml
[tool.fastapi]
entrypoint = "fastapi_core.factory:create_app"
```

즉, 이 패키지의 1차 공개 표면은 `create_app`이다.

---

## 3. App factory API

## 3.1 `create_app(config=None, settings=None, lifespan=None, include_auth_router=True) -> FastAPI`

공통 FastAPI 애플리케이션을 생성한다.

### 입력
- `config`: 환경/런타임 설정 객체 또는 None
- `settings`: 서비스 설정 객체 또는 None
- `lifespan`: 사용자 정의 FastAPI lifespan 또는 None
- `include_auth_router`: auth router 포함 여부

### 기본 동작
- 설정이 없으면 기본 설정 객체를 생성한다.
- logging을 초기화한다.
- `FastAPI(root_path=..., lifespan=...)` 인스턴스를 만든다.
- CORS middleware를 등록한다.
- auth 예외 핸들러를 등록한다.
- health router를 포함한다.
- 옵션에 따라 auth router를 포함한다.

### 반환값
- `FastAPI`

### 예시

```python
from fastapi_core.factory import create_app

app = create_app()
```

---

## 4. Router API

## 4.1 Auth router

태그: `auth`

### `POST /token`

사용자명/비밀번호 폼을 받아 access token을 발급한다.

#### 입력
- `OAuth2PasswordRequestForm`

#### 응답 모델
- `TokenResponse`

#### 성공 응답 예시

```json
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "bearer"
}
```

#### 실패
- 401 Unauthorized
- `WWW-Authenticate: Bearer`

### `GET /user`

현재 인증된 사용자 정보를 반환한다.

#### 응답 모델
- `UserInfo`

---

## 4.2 Health router

prefix: `/health`
tag: `health`

### `GET /health/liveness`

프로세스 생존 여부를 확인한다.

#### 응답 모델
- `HealthResponse`

#### 예시

```json
{
  "status": "ok"
}
```

### `GET /health/readiness`

외부 의존성 준비 상태를 확인한다.

#### 응답 모델
- `HealthResponse`

#### 실패
- 503 Service Unavailable

---

## 5. Dependency API

## 5.1 `get_config()`

캐시 가능한 환경 설정 객체를 반환한다.

### 특징
- FastAPI dependency로 사용 가능
- 요청 간 재사용 가능

## 5.2 `get_settings(config: EnvConfig | None = None)`

서비스 설정 객체를 반환한다.

## 5.3 `get_auth_provider(request, config=Depends(get_config))`

auth provider를 반환한다.

### 동작
- `app.state`에 provider가 있으면 그것을 사용한다.
- 없으면 설정 기반 기본 provider를 생성한다.

## 5.4 `get_current_user(token=Depends(oauth2_scheme), provider=Depends(get_auth_provider), settings=Depends(get_settings))`

현재 사용자 정보를 반환한다.

### 동작
- bearer token이 없으면 401
- 설정에 따라 secure/insecure decode 분기
- decode 결과를 `UserInfo`로 변환

### 반환값
- `UserInfo`

## 5.5 `require_permissions(*roles)`

역할 검사용 dependency factory.

### 동작
- 지정한 role이 없으면 403
- 있으면 현재 user 반환

### 예시

```python
from fastapi import Depends
from fastapi_core.dependencies.auth import require_permissions

@router.get("/admin")
def admin_only(user=Depends(require_permissions("admin"))):
    return {"ok": True}
```

---

## 6. Schema API

## 6.1 `TokenResponse`

```python
class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
```

## 6.2 `UserInfo`

```python
class UserInfo(BaseModel):
    sub: str
    username: str
    email: str | None = None
    name: str | None = None
    roles: list[str] = []
    scopes: list[str] = []
```

## 6.3 `HealthResponse`

```python
class HealthResponse(BaseModel):
    status: str
```

---

## 7. FastAPI security model

- OAuth2 bearer 기반
- `OAuth2PasswordBearer(tokenUrl="/token", auto_error=False)` 사용
- token 미제공: 401
- 권한 부족: 403
- auth router와 dependency 계층이 동일한 user/auth 모델을 공유

---

## 8. Lifespan / integration points

`create_app(..., lifespan=...)`는 외부 의존성 초기화를 FastAPI 수명주기와 연결하는 핵심 진입점이다.

대표 용도:
- startup에서 NATS 연결
- shutdown에서 외부 자원 정리
- app.state에 provider/registry 주입

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
def me(user: UserInfo = Depends(get_current_user)):
    return user
```

---

## 10. 참고 문서

- `docs/prd.md`
- `docs/srs.md`
- `docs/config.md`
- `docs/messaging.md`
- `pyproject.toml`

---

## 부록 A. 문서 상태 메모

이 문서는 배포 산출물에 포함된 FastAPI 계층(`factory.py`, `routers`, `dependencies`, `schemas`)을 기준으로 다시 작성했다. 서비스 클라이언트 레지스트리보다 FastAPI app surface를 우선 공개 API로 취급한다.