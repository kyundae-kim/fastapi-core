# fastapi-core 예제 문서

> 문서 목적: `fastapi-core`의 **현재 구현된 공개 표면을 바로 사용할 수 있는 예제**로 정리한다.
> 기준 문서: `docs/prd.md`, `docs/srs.md`, `docs/api.md`, `docs/config.md`, `docs/messaging.md`, `docs/test.md`
> 문서 상태: 구현 반영본(v0.1)

---

## 1. 문서 개요

이 문서는 개념 설명보다 **실제로 붙여 넣어 시작할 수 있는 사용 예제**를 제공한다.
예제는 현재 저장소의 구현과 테스트에서 확인된 패턴만 다룬다.

- 작성일: `2026-06-29`
- 작성자: `Hermes Agent`
- 버전: `v0.1`
- 상태: `implemented-surface`

다루는 범위:
- 기본 앱 생성
- auth router 포함/제외
- 현재 사용자 주입 및 권한 검사
- readiness 체크 주입
- 환경변수 기반 설정
- token endpoint 호출 예시
- custom lifespan 연계

---

## 2. 가장 작은 시작 예제

패키지 루트 공개 진입점은 `create_app`이다.

```python
from fastapi_core import create_app

app = create_app()
```

현재 기본 동작:
- `/health/liveness` 포함
- `/health/readiness` 포함
- `/token`, `/user` 포함
- `app.state.config`, `app.state.settings`, `app.state.service_clients` 저장
- `app.state.readiness_checks`, `app.state.readiness_services`, `app.state.required_services` 초기화
- CORS middleware 등록

---

## 3. auth router를 제외한 앱 생성

인증 endpoint를 직접 노출하지 않는 서비스는 auth router를 제외하고 시작할 수 있다.

```python
from fastapi_core import create_app

app = create_app(include_auth_router=False)
```

이 경우 현재 테스트 기준 기대 동작:
- `GET /health/liveness` → `200`
- `GET /user` → `404`
- `POST /token` → `404`

---

## 4. 보호된 endpoint 추가

`get_current_user()` dependency를 사용하면 bearer token을 `UserInfo`로 변환해 주입할 수 있다.

```python
from fastapi import APIRouter, Depends
from fastapi_core.dependencies.auth import get_current_user
from fastapi_core.schemas.user import UserInfo

router = APIRouter()

@router.get("/me", response_model=UserInfo)
async def me(user: UserInfo = Depends(get_current_user)) -> UserInfo:
    return user
```

현재 구현 기준 동작:
- `Authorization: Bearer <token>` 헤더가 없으면 `401`
- 응답 헤더에 `WWW-Authenticate: Bearer` 포함
- provider의 `extract_user_info(token)` 결과를 `UserInfo`로 변환
- `username = preferred_username or sub`
- `roles = realm_roles + client_roles[*]` 중복 제거
- `scopes = claims["scope"]`를 공백 기준 분리

---

## 5. 역할 기반 권한 검사

`require_permissions(*roles)`는 role 검사용 dependency factory다.

```python
from fastapi import APIRouter, Depends
from fastapi_core.dependencies.auth import require_permissions
from fastapi_core.schemas.user import UserInfo

router = APIRouter()

@router.get("/admin")
async def admin_only(
    user: UserInfo = Depends(require_permissions("admin")),
) -> dict[str, bool]:
    return {"ok": True}
```

현재 구현 기준 동작:
- 현재 사용자 `roles`에 요구 role이 모두 있으면 통과
- 하나라도 없으면 `403 Forbidden`
- 통과 시 현재 `UserInfo`를 그대로 재사용 가능

---

## 6. token endpoint 호출 예시

`POST /token`은 `OAuth2PasswordRequestForm` 형식 입력을 받는다.
현재 구현은 `username`, `password`, `scope`를 provider의 `fetch_access_token(...)`에 직접 전달한다.

### 6.1 curl 예시

```bash
curl -X POST http://localhost:8000/token \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=alice&password=secret&scope=openid profile'
```

성공 응답 예시:

```json
{
  "access_token": "access-token",
  "refresh_token": "refresh-token",
  "token_type": "bearer"
}
```

현재 구현의 오류 매핑:
- 인증 실패 → `401 Authentication failed`
- 인증 서비스 설정 오류 → `500 Authentication service misconfigured`
- 인증 서비스 일시 장애 → `503 Authentication service unavailable`
- 기타 upstream/auth 오류 → `502` 또는 `500`

모든 실패 응답에는 `WWW-Authenticate: Bearer` 헤더가 포함된다.

---

## 6A. 서비스별 전용 client dependency 예시

반환 타입을 명확히 쓰고 싶다면 공통 `get_service_client("...")` 대신 서비스별 전용 dependency를 사용할 수 있다.

```python
from fastapi import APIRouter, Depends
from docmesh_py_core import KeycloakAuthService
from sqlalchemy.engine import Engine

from fastapi_core.dependencies import get_keycloak_auth_service, get_sqlite_engine

router = APIRouter()

@router.get("/diagnostics")
async def diagnostics(
    sqlite_engine: Engine = Depends(get_sqlite_engine),
    keycloak_auth_service: KeycloakAuthService = Depends(get_keycloak_auth_service),
) -> dict[str, bool]:
    return {
        "sqlite_connect": hasattr(sqlite_engine, "connect"),
        "keycloak_extract_user_info": hasattr(keycloak_auth_service, "extract_user_info"),
    }
```

현재 구현 기준 해석:
- `get_sqlite_engine()`은 SQLAlchemy `Engine`을 반환한다.
- `get_keycloak_auth_service()`는 `KeycloakAuthService`를 반환한다.
- `get_nats_connection_builder()`는 `NatsConnectionBuilder`를 반환한다.

---

## 7. AppConfig를 코드로 직접 주입

앱 조립 방식과 readiness 기본 대상을 코드에서 명시하고 싶다면 `AppConfig`를 직접 전달할 수 있다.

```python
from fastapi_core.config import AppConfig
from fastapi_core.factory import create_app

config = AppConfig(
    root_path="/api",
    token_url="/api/v1/auth/token",
    cors_origins=["https://app.example.com"],
    cors_credentials=True,
    readiness_parallel=True,
    enabled_services=["keycloak", "nats"],
    required_services=["keycloak"],
)

app = create_app(config=config)
```

이 예제의 현재 의미:
- OpenAPI password flow의 `tokenUrl`이 `/api/v1/auth/token`으로 반영됨
- readiness 기본 체크 대상은 `keycloak`, `nats`
- `keycloak`만 필수 서비스로 간주
- `nats` 실패는 degraded 후보, `keycloak` 실패는 error 후보

---

## 8. 환경변수 기반 설정 예시

`load_app_config()`는 환경변수에서 `AppConfig`를 읽는다.

```env
ROOT_PATH=/api
TOKEN_URL=/api/v1/auth/token
CORS_ORIGINS=https://app.example.com,https://admin.example.com
CORS_CREDENTIALS=true
READINESS_PARALLEL=true
DOCMESH_LOG_LEVEL=INFO
APP_LOG_PATH=/tmp/app.log
APP_LOG_JSON=true
APP_LOG_FORCE=true
DOCMESH_SERVICES=keycloak,nats
READINESS_REQUIRED_SERVICES=keycloak
```

현재 구현 기준 해석:
- `DOCMESH_SERVICES` → readiness 기본 활성 서비스 목록
- `READINESS_REQUIRED_SERVICES` → readiness 실패 시 `503`을 유발하는 필수 서비스 목록
- `APP_LOG_*`, `DOCMESH_LOG_LEVEL` → 앱 로깅 초기화에 사용

---

## 9. readiness 기본 동작 예시

현재 `create_app()`는 `enabled_services`를 기준으로 readiness check를 자동 구성한다.
기본값은 `keycloak`만 활성/필수다.

```python
from fastapi_core import create_app

app = create_app(include_auth_router=False)
```

위와 같이 생성했을 때 앱 상태 예시는 다음과 같다.

```python
app.state.readiness_services == {
    "keycloak": {"enabled": True, "required": True}
}
app.state.required_services == {"keycloak"}
```

즉, 현재 구현은 예전 문서 초안처럼 “readiness check가 비어 있으면 단순 ok”에만 머물지 않고,
`enabled_services`를 바탕으로 기본 readiness 체크를 등록한다.

---

## 10. readiness 체크를 직접 주입하는 예시

서비스별 정책을 더 세밀하게 제어하려면 `app.state`를 직접 구성할 수 있다.

```python
from fastapi_core import create_app

app = create_app(include_auth_router=False)
app.state.readiness_checks = {
    "keycloak": lambda: None,
    "nats": lambda: None,
}
app.state.readiness_services = {
    "keycloak": {"required": True, "enabled": True},
    "nats": {"required": False, "enabled": True},
}
app.state.required_services = {"keycloak"}
```

현재 응답 정책:
- 모든 서비스 성공 → `200`, `status="ok"`
- 선택 서비스만 실패 → `200`, `status="degraded"`
- 필수 서비스 실패 → `503`, `status="error"`

성공 응답 예시:

```json
{
  "status": "ok",
  "details": {
    "keycloak": {
      "ok": true,
      "latency_ms": 1,
      "error": null,
      "required": true,
      "enabled": true
    },
    "nats": {
      "ok": true,
      "latency_ms": 1,
      "error": null,
      "required": false,
      "enabled": true
    }
  }
}
```

선택 서비스 실패 예시 개념:
- `nats` 실패, `keycloak` 성공
- HTTP 상태 코드는 `200`
- 본문 `status`는 `degraded`

필수 서비스 실패 예시 개념:
- `keycloak` 실패
- HTTP 상태 코드는 `503`
- 본문 `status`는 `error`

---

## 11. custom lifespan 연계 예시

외부 연결 수명주기를 직접 관리하려면 custom lifespan을 전달한다.

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi_core import create_app

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.started_by_lifespan = True
    # startup 작업
    yield
    # shutdown 작업

app = create_app(lifespan=lifespan)
```

현재 구현 기준 보장되는 점:
- custom lifespan startup/shutdown이 호출된다.
- 내부 `service_clients`는 lifespan 종료 뒤 `close_service_clients(service_clients.values())`로 정리된다.

메시징/NATS 같은 외부 자원은 이 지점에서 초기화/정리하는 패턴이 권장된다.

---

## 12. 선택 서비스만 로딩하는 예시

`docmesh_py_core.ServiceConfigs`도 서비스 선택에 맞춰 줄여서 로딩할 수 있다.

```python
from fastapi_core.config import AppConfig
from fastapi_core.docmesh_settings import load_docmesh_settings
from fastapi_core.factory import create_app

config = AppConfig(
    enabled_services=["sqlite"],
    required_services=["sqlite"],
)
settings = load_docmesh_settings(("sqlite",))

app = create_app(
    config=config,
    settings=settings,
    include_auth_router=False,
)
```

현재 테스트에서 확인된 결과:
- `app.state.settings.sqlite is not None`
- `app.state.settings.keycloak is None`
- readiness 기본 대상도 `sqlite`만 사용

---

## 13. 로깅 설정 예시

현재 `create_app()`는 앱 로거를 초기화하고, JSON 로그 파일 출력도 지원한다.

```python
from fastapi_core.config import AppConfig
from fastapi_core.factory import create_app

config = AppConfig(
    log_level="WARNING",
    log_path="/tmp/app.log",
    log_json=True,
    log_force=True,
    enabled_services=["sqlite"],
    required_services=["sqlite"],
)

app = create_app(config=config, include_auth_router=False)
```

현재 테스트 기준 확인된 동작:
- 로그 파일이 생성된다.
- 각 줄은 JSON 객체다.
- 기본 필드는 `timestamp`, `logger`, `level`, `message`
- `extra={"event": ...}`를 넘기면 구조화 이벤트가 함께 기록된다.

---

## 14. 예제 선택 가이드

원하는 사용 패턴별로 다음 예제를 먼저 보면 된다.

- 가장 빨리 시작: [2. 가장 작은 시작 예제](#2-가장-작은-시작-예제)
- 인증 없는 내부 서비스: [3. auth router를 제외한 앱 생성](#3-auth-router를-제외한-앱-생성)
- 보호된 API 작성: [4. 보호된 endpoint 추가](#4-보호된-endpoint-추가)
- role 기반 접근 제어: [5. 역할 기반 권한 검사](#5-역할-기반-권한-검사)
- 배포 설정 반영: [7. AppConfig를 코드로 직접 주입](#7-appconfig를-코드로-직접-주입), [8. 환경변수 기반 설정 예시](#8-환경변수-기반-설정-예시)
- readiness 정책 커스터마이징: [10. readiness 체크를 직접 주입하는 예시](#10-readiness-체크를-직접-주입하는-예시)
- 외부 자원 lifecycle 연계: [11. custom lifespan 연계 예시](#11-custom-lifespan-연계-예시)

---

## 15. 참고 문서

- `docs/prd.md`
- `docs/srs.md`
- `docs/api.md`
- `docs/config.md`
- `docs/messaging.md`
- `docs/test.md`
- `README.md`
- `fastapi_core/factory.py`
- `fastapi_core/config.py`
- `fastapi_core/dependencies/auth.py`
- `test_fastapi_core/test_factory.py`
- `test_fastapi_core/test_auth_router.py`
- `test_fastapi_core/test_health_router.py`
