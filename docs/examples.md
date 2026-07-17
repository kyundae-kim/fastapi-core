# fastapi-core 예제 문서

> 문서 목적: `fastapi-core`의 **현재 구현된 공개 표면을 바로 사용할 수 있는 예제**로 정리한다.
> 기준 문서: `docs/prd.md`, `docs/srs.md`, `docs/api.md`, `docs/config.md`, `docs/messaging.md`, `docs/test.md`
> 문서 상태: 구현 반영본

---

## 1. 문서 개요

이 문서는 개념 설명보다 **실제로 붙여 넣어 시작할 수 있는 사용 예제**를 제공한다.
예제는 현재 저장소의 구현과 테스트에서 확인된 패턴만 다룬다.

- 작성일: `2026-07-03`
- 작성자: `Hermes Agent`
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
- 내부 lifecycle state에 config, settings, `ServiceRuntime`과 client map 저장; 애플리케이션 route는 공개 dependency로 접근
- keycloak이 활성화되면 `app.state.auth_provider` 저장
- 앱별 typed readiness/resource registry 초기화
- CORS middleware 등록
- `X-Correlation-ID` 전파와 problem-details 오류 handler 등록

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
from fastapi_core import create_app
from fastapi_core.dependencies.auth import get_current_user
from fastapi_core.schemas.user import UserInfo

router = APIRouter()

@router.get("/me", response_model=UserInfo)
async def me(user: UserInfo = Depends(get_current_user)) -> UserInfo:
    return user


app = create_app()
app.include_router(router)
```

현재 구현 기준 동작:
- `Authorization` 헤더에 bearer token이 없으면 `401`
- 응답 헤더에 `WWW-Authenticate: Bearer` 포함
- provider의 `extract_user_info(token)` 결과를 `UserInfo`로 변환
- `username = preferred_username or sub`
- `roles = realm_roles + client_roles[*]` 중복 제거
- `scopes = claims["scope"]`를 공백 기준 분리

---

## 5. 선언적 role/scope/permission 검사

`require_roles`, `require_scopes`, `require_permissions`는 각각 role, scope, 두 집합을 합친 permission을 검사한다.

```python
from fastapi import APIRouter, Depends
from fastapi_core import create_app
from fastapi_core.dependencies import require_roles, require_scopes
from fastapi_core.schemas.user import UserInfo

router = APIRouter()

@router.get("/documents")
async def documents(
    role_user: UserInfo = Depends(require_roles("editor")),
    scope_user: UserInfo = Depends(require_scopes("document:read")),
) -> dict[str, bool]:
    return {"ok": True}


app = create_app()
app.include_router(router)
```

현재 구현 기준 동작:
- `require_roles`는 현재 사용자 `roles`, `require_scopes`는 `scopes`를 검사한다.
- `require_permissions`는 role과 scope의 합집합을 검사한다.
- 하나라도 없으면 `403 Forbidden`
- 통과 시 현재 `UserInfo`를 그대로 재사용 가능
- `require_scopes`의 요구 scope는 OpenAPI security requirement에 노출됨

---

## 6. token endpoint 호출 예시

`POST /token`은 `OAuth2PasswordRequestForm` 형식 입력을 받는다.
현재 구현은 `username`, `password`, `scope`를 provider의 `fetch_access_token(...)`에 직접 전달한다.

### 6.1 curl 예시

이 요청이 실제로 성공하려면 Keycloak 서버가 도달 가능해야 하며, `KEYCLOAK_URL`, `KEYCLOAK_REALM`, `KEYCLOAK_CLIENT_ID`, `KEYCLOAK_CLIENT_SECRET`와 유효한 사용자 credential이 준비되어야 한다. 로컬 app 실행과 환경변수 설정은 [설정 문서](config.md)를 따른다.

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
- generic integration code만 `get_service_runtime()`을 사용하고, 일반 route는 구체 타입 dependency를 우선한다.
- `app.state.service_runtime`이나 `app.state.service_clients`를 애플리케이션 코드에서 직접 읽지 않는다.

---

## 7. AppConfig를 코드로 직접 주입

앱 조립 방식과 readiness 기본 대상을 코드에서 명시하고 싶다면 `AppConfig`를 직접 전달할 수 있다.

```python
from fastapi_core.config import AppConfig
from fastapi_core.factory import create_app

config = AppConfig(
    root_path="/api",
    token_url="/api/auth/token",
    cors_origins=["https://app.example.com"],
    cors_credentials=True,
    readiness_parallel=True,
    readiness_timeout_seconds=5,
    readiness_overall_timeout_seconds=15,
    service_alternatives=[["postgres", "sqlite"]],
    startup_healthcheck=True,
    enabled_services=["keycloak", "postgres", "sqlite", "nats"],
    required_services=["keycloak"],
)

app = create_app(config=config)
```

이 예제의 현재 의미:
- OpenAPI password flow의 `tokenUrl`이 `/api/auth/token`으로 반영됨
- readiness 기본 체크 대상은 `keycloak`, `postgres`, `sqlite`, `nats`
- `keycloak`만 필수 서비스로 간주
- PostgreSQL 또는 SQLite 중 적어도 하나의 설정이 필요
- startup과 readiness endpoint 모두 서비스별 5초, 전체 15초 제한 적용
- `nats` 실패는 degraded 후보, `keycloak` 실패는 error 후보

---

## 8. 환경변수 기반 설정 예시

`load_app_config()`는 환경변수에서 `AppConfig`를 읽는다.

```env
ROOT_PATH=/api
TOKEN_URL=/api/auth/token
CORS_ORIGINS=https://app.example.com,https://admin.example.com
CORS_CREDENTIALS=true
READINESS_PARALLEL=true
READINESS_TIMEOUT_SECONDS=5
READINESS_OVERALL_TIMEOUT_SECONDS=15
DOCMESH_SERVICE_ALTERNATIVES=postgres,sqlite
DOCMESH_HEALTHCHECK_ENABLED=true
DOCMESH_LOG_LEVEL=INFO
APP_LOG_PATH=/tmp/app.log
APP_LOG_JSON=true
APP_LOG_FORCE=true
DOCMESH_SERVICES=keycloak,postgres,sqlite,nats
READINESS_REQUIRED_SERVICES=keycloak

# PostgreSQL: 권장 개별 접속 항목
POSTGRES_HOST=postgres.example.com
POSTGRES_PORT=5432
POSTGRES_DB=docmesh
POSTGRES_USER=docmesh
POSTGRES_PASSWORD=change-me
```

현재 구현 기준 해석:
- `DOCMESH_SERVICES` → readiness 기본 활성 서비스 목록
- `READINESS_REQUIRED_SERVICES` → readiness 실패 시 `503`을 유발하는 필수 서비스 목록
- `DOCMESH_SERVICE_ALTERNATIVES` → 세미콜론/쉼표 형식의 `one_of` 서비스 그룹
- timeout 값 → startup healthcheck와 readiness endpoint에 공통 적용
- `APP_LOG_*`, `DOCMESH_LOG_LEVEL` → 앱 로깅 초기화에 사용
- PostgreSQL은 개별 접속 환경변수를 권장하며, deprecated 호환 경로로 `POSTGRES_DSN` 하나를 사용할 수 있음

```env
POSTGRES_HOST=postgres.example.com
POSTGRES_PORT=5432
POSTGRES_DB=docmesh
POSTGRES_USER=docmesh
POSTGRES_PASSWORD=change-me
POSTGRES_SSLMODE=require
POSTGRES_CONNECT_TIMEOUT_SECONDS=10
POSTGRES_POOL_SIZE=5
POSTGRES_MAX_OVERFLOW=10
```

`POSTGRES_DSN`과 개별 접속 항목은 함께 설정할 수 없다. 실제 비밀번호와 DSN은 secret으로 주입하고 문서나 저장소에 커밋하지 않는다.

---

## 9. readiness 기본 동작 예시

현재 `create_app()`는 `enabled_services`를 기준으로 readiness check를 자동 구성한다.
기본값은 `keycloak`만 활성/필수다.

```python
from fastapi.testclient import TestClient
from fastapi_core import create_app

app = create_app(include_auth_router=False)

# 기본 runtime과 readiness spec은 lifespan startup에서 구성된다.
with TestClient(app):
    spec = app.state.readiness_registry.specs["keycloak"]
    assert spec.required is True
```

즉, 현재 구현은 예전 문서 초안처럼 “readiness check가 비어 있으면 단순 ok”에만 머물지 않고,
`enabled_services`를 바탕으로 기본 readiness 체크를 등록한다.

---

## 10. typed readiness 체크 등록 예시

서비스별 정책을 더 세밀하게 제어하려면 public registration API를 사용한다.

```python
from fastapi_core import create_app, register_readiness_check

app = create_app(include_auth_router=False)
register_readiness_check(
    app,
    "domain-sdk",
    lambda: None,
    required=False,
    timeout_seconds=5,
    redact_errors=True,
)
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
    "domain-sdk": {
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
- `domain-sdk` 실패
- HTTP 상태 코드는 `200`
- 본문 `status`는 `degraded`

필수 서비스 실패 예시 개념:
- 같은 check를 `required=True`로 등록한 상태에서 실패
- HTTP 상태 코드는 `503`
- 본문 `status`는 `error`

---

## 11. managed resource 연계 예시

서비스 고유 SDK나 연결 객체는 managed resource로 등록한다.

```python
from fastapi import Depends, FastAPI
from fastapi_core import ManagedResource, ResourceKey, create_app


class DomainSDK:
    async def check(self) -> None: ...
    async def aclose(self) -> None: ...


async def create_sdk(_app: FastAPI) -> DomainSDK:
    return DomainSDK()


domain_sdk = ResourceKey[DomainSDK]("domain-sdk")


app = create_app(
    resources=[
        ManagedResource(
            domain_sdk,
            factory=create_sdk,
            healthcheck=lambda sdk: sdk.check(),
            required=True,
        )
    ]
)


@app.get("/sdk-status")
async def sdk_status(sdk: DomainSDK = Depends(domain_sdk.dependency)):
    return {"ready": sdk is not None}
```

현재 구현 기준 보장되는 점:
- resource는 선언 순서로 생성되고 역순으로 종료된다.
- 일부 factory 또는 startup healthcheck가 실패하면 이미 생성된 resource를 rollback한다.
- healthcheck가 있으면 readiness registry에 자동 등록된다.
- 명시적 close callback이 없으면 `aclose()`, `close()` 순서로 자동 정리한다.
- `get_resource(name)`은 lifecycle에서 생성된 동일 객체를 route에 주입한다.
- `ResourceKey[T]`를 등록과 `Depends(key.dependency)`에 함께 사용하면 반환 타입을 유지하고 resource 이름 문자열을 한 곳에서 관리한다.
- healthcheck의 `None`/`True`는 성공, `False`는 실패다. `HealthCheckResult`를 반환하면 하위 상태가 `domain-sdk.<service>` details로 보존된다.
- `runtime`과 deprecated `settings`를 생략한 기본 경로는 custom lifespan보다 먼저 `assemble_service_runtime(...)`으로 외부 서비스 runtime을 준비한다.
- 준비된 runtime은 `app.state.service_runtime`에 저장되고 clients/settings도 기존 state 키로 노출된다.
- custom lifespan startup/shutdown이 호출된다.
- 내부 `service_clients`는 lifespan 종료 시 `await service_runtime.close()`를 통해 정리된다.
- custom lifespan shutdown이 예외를 발생시켜도 내부 client 정리는 `finally` 경로에서 실행된다.
- sync/async `close()`를 모두 지원하므로 NATS builder의 비동기 종료도 await된다.
- startup healthcheck 실패 시 custom lifespan 진입 전에 생성된 client를 rollback한다.
- runtime close 실패 시 `service_runtime_close_failed` 이벤트를 남기고 `ServiceCloseError`를 전파한다.

- custom lifespan은 managed resource startup 뒤 진입하고, custom shutdown 뒤 managed resource가 정리된다.

---

## 12. 선택 서비스만 로딩하는 예시

기본 assembly 경로에서도 서비스 선택을 필요한 범위로 제한할 수 있다.

```python
from fastapi_core.config import AppConfig
from fastapi_core.factory import create_app

config = AppConfig(
    enabled_services=["sqlite"],
    required_services=["sqlite"],
)
app = create_app(
    config=config,
    include_auth_router=False,
)
```

lifespan startup 이후 확인되는 결과:
- `app.state.settings.sqlite is not None`
- `app.state.settings.keycloak is None`
- readiness 기본 대상도 `sqlite`만 사용

테스트나 외부 조립 코드가 이미 완성된 `ServiceRuntime`을 보유한 경우에는 `create_app(runtime=runtime)`으로 동일 객체를 주입한다. `settings=`는 deprecated 호환 경로이며 `runtime=`과 동시에 전달할 수 없다.

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

## 14. domain 오류와 correlation ID 연계

```python
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi_core import ErrorMapping, create_app, register_error_mapper


class DomainSDKError(Exception):
    pass


def render_error(request: Request, mapping: ErrorMapping) -> JSONResponse:
    return JSONResponse(
        status_code=mapping.status_code,
        content={
            "error": {
                "code": mapping.code,
                "message": mapping.detail,
                "correlation_id": request.state.correlation_id,
            }
        },
    )


app = create_app(error_renderer=render_error)
register_error_mapper(
    app,
    DomainSDKError,
    lambda _request, exc: ErrorMapping(
        status_code=502,
        title="Domain service error",
        detail=str(exc),
        code="DOMAIN_SERVICE_ERROR",
        type_uri="https://errors.example/domain-service",
    ),
)
```

모든 정상/오류 응답에는 `X-Correlation-ID`가 설정된다. 유효한 입력 ID는 `request.state.correlation_id`와 응답에 그대로 전파되고, 유효하지 않은 값은 새 UUID로 교체된다. custom renderer는 HTTP/validation/unhandled 오류와 위 domain mapper에 공통 적용되며, renderer 호출 전 `detail` 마스킹이 완료된다. `error_renderer`를 생략하면 기본 `application/problem+json` 응답을 사용한다.

## 15. 예제 선택 가이드

원하는 사용 패턴별로 다음 예제를 먼저 보면 된다.

- 가장 빨리 시작: [2. 가장 작은 시작 예제](#2-가장-작은-시작-예제)
- 인증 없는 내부 서비스: [3. auth router를 제외한 앱 생성](#3-auth-router를-제외한-앱-생성)
- 보호된 API 작성: [4. 보호된 endpoint 추가](#4-보호된-endpoint-추가)
- role/scope 기반 접근 제어: [5. 선언적 role/scope/permission 검사](#5-선언적-rolescopepermission-검사)
- 배포 설정 반영: [7. AppConfig를 코드로 직접 주입](#7-appconfig를-코드로-직접-주입), [8. 환경변수 기반 설정 예시](#8-환경변수-기반-설정-예시)
- readiness 정책 커스터마이징: [10. readiness 체크를 직접 주입하는 예시](#10-readiness-체크를-직접-주입하는-예시)
- 외부 자원 lifecycle 연계: [11. custom lifespan 연계 예시](#11-custom-lifespan-연계-예시)
- 표준 domain 오류 매핑: [14. domain 오류와 correlation ID 연계](#14-domain-오류와-correlation-id-연계)

---

## 16. 참고 문서

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
