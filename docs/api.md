# 공개 API 명세 (Public Interface)

> 이 문서는 `fastapi-core` SDK가 외부에 공개하는 모든 심볼의 시그니처, 동작, 에러 처리를 정의합니다.  
> 설정 값(환경 변수, YAML 키)은 [config.md](config.md)를 참조하세요.

---

## 스키마 (Pydantic 모델)

### `UserInfo` — `fastapi_core.schemas.user`

```python
class UserInfo(BaseModel):
    sub: str                        # JWT subject (Keycloak user ID)
    username: str                   # preferred_username 클레임
    email: str | None = None        # email 클레임
    name: str | None = None         # name 클레임
    roles: list[str] = []           # realm_access.roles 클레임
    scopes: list[str] = []          # scope 문자열 또는 scp 리스트
```

### `TokenResponse` — `fastapi_core.schemas.token`

```python
class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
```

### `HealthResponse` — `fastapi_core.schemas.health`

```python
class HealthResponse(BaseModel):
    status: str    # "ok"
```

---

## 인증 (Authentication)

### `KeycloakAuthProvider` — `fastapi_core.core.auth`

Keycloak과 통신하는 인증 프로바이더. 직접 생성하거나 `set_auth_provider(app, config=config)`를 통해 등록한다.

```python
class KeycloakAuthProvider:
    def __init__(
        self,
        http_url: str,       # Keycloak base URL (예: "http://keycloak:8080/"), 반드시 "/" 로 끝나야 함
        realm: str,          # Realm 이름
        client_id: str,      # client_id (JWT audience)
        client_secret: str | None = None,  # Confidential 클라이언트 secret
    ) -> None: ...
```

**생성 시 ValueError 조건**: `http_url`, `realm`, `client_id` 중 하나라도 빈 문자열이면 `ValueError`.

내부에서 다음 URL을 자동 조합한다:

| 속성 | 값 |
|---|---|
| `token_url` | `{http_url}/realms/{realm}/protocol/openid-connect/token` |
| `jwks_url` | `{http_url}/realms/{realm}/protocol/openid-connect/certs` |
| `issuer` | `{http_url}/realms/{realm}` |

#### 메서드

```python
def authenticate(self, username: str, password: str) -> dict[str, Any]:
    """Password Grant로 Keycloak에서 토큰 발급. HTTP 오류 시 httpx.HTTPStatusError."""
```

```python
def refresh_access_token(self, refresh_token: str) -> dict[str, Any]:
    """Refresh Token Grant로 액세스 토큰 갱신. HTTP 오류 시 httpx.HTTPStatusError."""
```

```python
def decode_token(self, token: str) -> dict[str, Any]:
    """RS256 서명 검증 후 JWT payload 반환. 검증 실패 시 ValueError."""
```

```python
def decode_token_insecure(self, token: str) -> dict[str, Any]:
    """서명 검증 없이 JWT payload 반환 (개발 환경용). 파싱 실패 시 ValueError."""
```

```python
def to_user(self, payload: dict[str, Any]) -> UserInfo:
    """JWT payload → UserInfo 모델 변환."""
```

#### 클레임 파싱 유틸리티

```python
def extract_roles(payload: dict[str, Any]) -> list[str]:
    """payload['realm_access']['roles'] 추출. 키 없으면 []."""

def extract_scopes(payload: dict[str, Any]) -> list[str]:
    """'scp' 키(리스트) 또는 'scope' 키(공백 구분 문자열) 추출. 없으면 []."""
```

---

### `set_auth_provider` — `fastapi_core.dependencies.auth`

```python
def set_auth_provider(
    app: FastAPI,
    provider: KeycloakAuthProvider | None = None,
    *,
    config: EnvConfig | None = None,
) -> None:
```

- `provider` 직접 전달 → `app.state.auth_provider`에 할당
- `config` 전달 → `KeycloakAuthProvider` 내부 생성 후 할당
- 둘 다 `None` → `ValueError`

### `get_auth_provider` — `fastapi_core.dependencies.auth`

```python
def get_auth_provider(
    request: Request,
    config: EnvConfig = Depends(get_config),
) -> KeycloakAuthProvider:
```

- `app.state.auth_provider` 존재 시 반환 (싱글톤)
- `AttributeError` 시 `EnvConfig`로 생성 후 `app.state.auth_provider`에 저장 (fallback lazy singleton)

### `get_current_user` — `fastapi_core.dependencies.auth`

```python
def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    provider: KeycloakAuthProvider = Depends(get_auth_provider),
    settings: ServiceSettings = Depends(get_settings),
) -> UserInfo:
```

| 조건 | 결과 |
|---|---|
| `Authorization: Bearer <token>` 헤더 없음 | `401 Not authenticated` |
| 토큰 검증 실패 (`ValueError`) | `401 <오류 메시지>` |
| `settings.auth.verify_jwt = True` | `provider.decode_token()` (RS256 서명 검증) |
| `settings.auth.verify_jwt = False` | `provider.decode_token_insecure()` (서명 검증 생략) |

### `require_permissions` — `fastapi_core.dependencies.auth`

```python
def require_permissions(*roles: str) -> Callable:
    """지정한 역할을 모두 보유해야 통과하는 Depends 팩토리."""
```

```python
# 사용 예
@router.get("/admin")
def admin_only(user: UserInfo = Depends(require_permissions("admin"))):
    ...
```

| 조건 | 결과 |
|---|---|
| 필요 역할 중 하나라도 `user.roles`에 없음 | `403 Missing required role: {role}` |
| 모든 역할 보유 | `UserInfo` 반환 |

---

## 데이터베이스 (Database)

### `create_db_engine` — `fastapi_core.core.database`

```python
def create_db_engine(config: DatabaseConfig) -> Engine:
    """SQLAlchemy Engine 생성. config.sqlalchemy_database_url 과 config.echo 사용."""
```

### `check_database_connection` — `fastapi_core.core.database`

```python
def check_database_connection(engine: Engine) -> bool:
    """SELECT 1 실행. 성공 시 True, 예외 시 False."""
```

### `get_database_version` — `fastapi_core.core.database`

```python
def get_database_version(engine: Engine) -> str:
    """SELECT version() 결과 문자열 반환."""
```

### `set_db_engine` — `fastapi_core.dependencies.database`

```python
def set_db_engine(
    app: FastAPI,
    engine: Engine | None = None,
    *,
    config: EnvConfig | None = None,
) -> None:
```

- `engine` 직접 전달 → `app.state.db_engine`에 할당
- `config` 전달 → `create_db_engine(config.db)` 내부 호출 후 할당
- 둘 다 `None` → `ValueError`

### `get_db_engine` — `fastapi_core.dependencies.database`

```python
def get_db_engine(
    request: Request,
    config: EnvConfig = Depends(get_config),
) -> Engine:
```

- `app.state.db_engine` 존재 시 반환 (싱글톤)
- `AttributeError` 시 `create_db_engine(config.db)` 호출 후 `app.state.db_engine`에 저장 (fallback lazy singleton)

### `get_db_session` — `fastapi_core.dependencies.database` *(추가 예정)*

```python
def get_db_session(
    engine: Engine = Depends(get_db_engine),
) -> Generator[Session, None, None]:
```

- SQLAlchemy `Session`을 생성해 요청 스코프에서 제공
- 정상/예외 종료와 관계없이 `session.close()` 보장

### `run_in_transaction` — `fastapi_core.core.database` *(추가 예정)*

```python
def run_in_transaction(
    engine: Engine,
    fn: Callable[[Session], T],
) -> T:
```

- 내부에서 세션/트랜잭션 경계를 생성해 `fn(session)` 실행
- 성공 시 `commit`, 실패 시 `rollback` 후 예외 재전파

---

## 스토리지 (Storage / MinIO)

### `create_minio_client` — `fastapi_core.core.storage`

```python
def create_minio_client(config: MinIOConfig) -> Minio:
    """MinIOConfig로 minio.Minio 클라이언트 생성."""
```

### `ensure_bucket_exists` — `fastapi_core.core.storage`

```python
def ensure_bucket_exists(client: Minio, bucket: str) -> None:
    """버킷이 없으면 생성. 이미 존재하면 아무 작업 안 함."""
```

### `list_buckets` — `fastapi_core.core.storage`

```python
def list_buckets(client: Minio) -> list[str]:
    """버킷 이름 목록 반환."""
```

### `check_minio_connection` — `fastapi_core.core.storage`

```python
def check_minio_connection(client: Minio, bucket: str) -> bool:
    """bucket_exists() 호출 성공 시 True, 예외 시 False."""
```

### `generate_presigned_get_url` — `fastapi_core.core.storage` *(추가 예정)*

```python
def generate_presigned_get_url(
    client: Minio,
    bucket: str,
    object_name: str,
    expires: timedelta = timedelta(minutes=15),
) -> str:
```

- 지정 객체 다운로드용 presigned GET URL 반환

### `generate_presigned_put_url` — `fastapi_core.core.storage` *(추가 예정)*

```python
def generate_presigned_put_url(
    client: Minio,
    bucket: str,
    object_name: str,
    expires: timedelta = timedelta(minutes=15),
) -> str:
```

- 지정 객체 업로드용 presigned PUT URL 반환

### `set_minio_client` — `fastapi_core.dependencies.storage`

```python
def set_minio_client(
    app: FastAPI,
    client: Minio | None = None,
    *,
    config: EnvConfig | None = None,
) -> None:
```

- `client` 직접 전달 → `app.state.minio_client`에 할당
- `config` 전달 → `create_minio_client(config.minio)` 내부 호출 후 할당
- 둘 다 `None` → `ValueError`

### `get_minio_client` — `fastapi_core.dependencies.storage`

```python
def get_minio_client(
    request: Request,
    config: EnvConfig = Depends(get_config),
) -> Minio:
```

- `app.state.minio_client` 존재 시 반환 (싱글톤)
- `AttributeError` 시 `create_minio_client(config.minio)` 호출 후 `app.state.minio_client`에 저장 (fallback lazy singleton)

---

## 메시징 (NATS) *(추가 예정)*

### `create_nats_client` — `fastapi_core.core.messaging`

```python
async def create_nats_client(config: NatsConfig) -> nats.aio.client.Client:
    """NATS 서버에 연결된 클라이언트를 생성한다."""
```

### `publish_json` — `fastapi_core.core.messaging`

```python
async def publish_json(
    client: nats.aio.client.Client,
    subject: str,
    payload: dict[str, Any],
) -> None:
    """JSON payload를 UTF-8 bytes로 직렬화하여 subject로 발행한다."""
```

### `subscribe_json` — `fastapi_core.core.messaging`

```python
async def subscribe_json(
    client: nats.aio.client.Client,
    subject: str,
    cb: Callable[[dict[str, Any]], Awaitable[None]],
    queue: str | None = None,
) -> None:
    """subject를 구독하고 수신 메시지를 JSON으로 역직렬화하여 콜백에 전달한다."""
```

### `set_nats_client` — `fastapi_core.dependencies.messaging`

```python
async def set_nats_client(
    app: FastAPI,
    client: nats.aio.client.Client | None = None,
    *,
    config: EnvConfig | None = None,
) -> None:
```

- `client` 직접 전달 → `app.state.nats_client`에 할당
- `config` 전달 → `create_nats_client(config.nats)` 내부 호출 후 할당
- 둘 다 `None` → `ValueError`

### `get_nats_client` — `fastapi_core.dependencies.messaging`

```python
async def get_nats_client(
    request: Request,
    config: EnvConfig = Depends(get_config),
) -> nats.aio.client.Client:
```

- `app.state.nats_client` 존재 시 반환 (싱글톤)
- 미등록 시 `create_nats_client(config.nats)` 호출 후 `app.state.nats_client`에 저장 (fallback lazy singleton)

---

## 설정 (Config)

### `get_config` — `fastapi_core.dependencies.config`

```python
def get_config() -> EnvConfig:
    """EnvConfig() 인스턴스 반환 (환경 변수 / .env 파일 로드)."""
```

### `get_settings` — `fastapi_core.dependencies.config`

```python
def get_settings(config: EnvConfig = Depends(get_config)) -> ServiceSettings:
    """ServiceSettings.from_yaml(config.config_path) 반환."""
```

---

## 앱 팩토리 (Factory)

### `create_app` — `fastapi_core.factory`

```python
def create_app(
    config: EnvConfig | None = None,
    settings: ServiceSettings | None = None,
    lifespan: Callable[[FastAPI], AsyncIterator] | None = None,
    include_auth_router: bool = True,
) -> FastAPI:
```

| 인자 | 설명 |
|---|---|
| `config` | `None`이면 `EnvConfig()` 자동 생성 |
| `settings` | `None`이면 `ServiceSettings.from_yaml(config.config_path)` 자동 로드 |
| `lifespan` | FastAPI lifespan 컨텍스트 매니저. `None`이면 lifespan 없이 생성 |
| `include_auth_router` | `True`이면 `/token`, `/user` 라우터 포함 |

**등록 순서**: `setup_logging` → `FastAPI(root_path=...)` → `CORSMiddleware` → `AuthError` 핸들러 → `/health` 라우터 → (선택) auth 라우터

---

## 내장 HTTP 엔드포인트

### `GET /health/liveness`

응답 `200 OK`:
```json
{ "status": "ok" }
```

### `GET /health/readiness`

Keycloak + PostgreSQL + MinIO 준비 상태를 종합 확인한다. *(추가 예정)*

| 조건 | 응답 |
|---|---|
| Keycloak + DB + MinIO 모두 정상 | `200 { "status": "ok" }` |
| Keycloak 비정상 응답 | `503 { "detail": "Keycloak not ready" }` |
| Keycloak 연결 불가 (`RequestError`) | `503 { "detail": "Keycloak unreachable: ..." }` |
| DB 연결 실패 | `503 { "detail": "Database not ready" }` |
| MinIO 연결 실패 | `503 { "detail": "MinIO not ready" }` |

### `POST /token`

**요청**: `application/x-www-form-urlencoded` (OAuth2PasswordRequestForm)

| 필드 | 설명 |
|---|---|
| `username` | Keycloak 사용자명 |
| `password` | 비밀번호 |
| `grant_type` | `"password"` (자동) |

**응답 `200`**: `TokenResponse`  
**응답 `401`**: `{ "detail": "<Keycloak 오류 메시지>" }` + `WWW-Authenticate: Bearer`

### `GET /user`

**요청**: `Authorization: Bearer <access_token>` 헤더 필요

**응답 `200`**: `UserInfo`  
**응답 `401`**: `{ "detail": "Not authenticated" }` 또는 `{ "detail": "<토큰 오류>" }` + `WWW-Authenticate: Bearer`

---

## 예외 처리

### `AuthError` — `fastapi_core.core.exceptions`

```python
class AuthError(Exception):
    def __init__(self, message: str, status_code: int = 401) -> None: ...
```

`create_app()`에 자동으로 전역 핸들러가 등록되며, 다음 형식으로 응답한다:

```json
{ "detail": "<message>" }
```

### HTTP 에러 응답 형식 요약

| 상황 | 상태 코드 | 응답 바디 |
|---|---|---|
| 토큰 없음 | `401` | `{"detail": "Not authenticated"}` |
| 토큰 검증 실패 | `401` | `{"detail": "<오류 메시지>"}` |
| 역할 부족 | `403` | `{"detail": "Missing required role: {role}"}` |
| Keycloak 미준비 | `503` | `{"detail": "Keycloak not ready"}` |
| Keycloak 연결 불가 | `503` | `{"detail": "Keycloak unreachable: ..."}` |
| DB 미준비 | `503` | `{"detail": "Database not ready"}` |
| MinIO 미준비 | `503` | `{"detail": "MinIO not ready"}` |

---

## `app.state` 속성 요약

| 속성명 (고정) | 타입 | 등록 함수 | 조회 Depends |
|---|---|---|---|
| `app.state.auth_provider` | `KeycloakAuthProvider` | `set_auth_provider` | `get_auth_provider` |
| `app.state.db_engine` | `Engine` | `set_db_engine` | `get_db_engine` |
| `app.state.minio_client` | `Minio` | `set_minio_client` | `get_minio_client` |
| `app.state.nats_client` | `nats.aio.client.Client` | `set_nats_client` | `get_nats_client` |

속성명은 SDK 내부에 하드코딩되어 있으며 사용자가 변경할 수 없다.

---

## 사용 예시 (lifespan 패턴)

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi_core.factory import create_app
from fastapi_core.core.config import EnvConfig
from fastapi_core.dependencies.auth import set_auth_provider
from fastapi_core.dependencies.database import set_db_engine
from fastapi_core.dependencies.storage import set_minio_client

config = EnvConfig()

@asynccontextmanager
async def lifespan(app: FastAPI):
    set_auth_provider(app, config=config)
    set_db_engine(app, config=config)
    set_minio_client(app, config=config)
    yield
    app.state.db_engine.dispose()

app = create_app(config=config, lifespan=lifespan)
```
