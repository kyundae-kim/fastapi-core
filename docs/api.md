# 공개 API 명세

> 이 문서는 현재 소스코드 기준의 공개 인터페이스를 정리합니다.
> 설정 키와 기본값은 [config.md](config.md)를, 테스트 구성은 [test.md](test.md)를 참조하세요.

---

## 패키지 루트 재수출(`fastapi_core.__all__`)

패키지 루트는 **curated subset만** 재수출합니다.

> `KeycloakConfig` 는 fastapi-core 전용 로컬 모델이 아니라 `docmesh_py_core.config.KeycloakConfig` 의 재수출입니다. FastAPI 전용 `manage_url` 은 `KeycloakOverlayConfig` 로 분리됩니다.

```python
from fastapi_core import (
    AuthError,
    DatabaseConfig,
    EnvConfig,
    HealthResponse,
    KeycloakAuthProvider,
    KeycloakConfig,
    KeycloakOverlayConfig,
    LangfuseConfig,
    LifecycleSettings,
    MilvusConfig,
    MinIOConfig,
    OllamaConfig,
    ServiceSettings,
    TokenResponse,
    UserInfo,
    check_langfuse_connection,
    create_async_milvus_client,
    create_app,
    create_milvus_client,
    get_langfuse_client,
)
```

다음 helper는 모듈 경로로는 존재하지만 루트에서는 재수출되지 않습니다.

- `run_in_transaction`
- `check_milvus_connection`, `check_async_milvus_connection`
- `list_collection_names`, `list_async_collection_names`
- `ensure_collection_exists`, `ensure_async_collection_exists`
- `check_ollama_connection`, `list_model_names`, `generate_text`
- `generate_presigned_get_url`, `generate_presigned_put_url`

---

## FastAPI dependency 정책

- dependency는 모두 **함수형 API**입니다.
- `Get*Dependency` callable class와 `get_* = Get*Dependency()` 형태의 alias는 공개 API가 아닙니다.
- 대부분의 FastAPI dependency getter/setter는 `docmesh_bridge`를 통해 registry-backed 서비스 해석을 사용합니다.
- 예외적으로 `async_milvus_client`는 dependency 계층에서도 `create_async_milvus_client(config.milvus)`를 직접 사용합니다.

주요 state 키:

| state 키 | 타입 | 등록 함수 | 조회 함수 |
| --- | --- | --- | --- |
| `app.state.config` | `EnvConfig` | `set_config` | `get_config` |
| `app.state.settings` | `ServiceSettings` | `set_settings` | `get_settings` |
| `app.state.auth_provider` | Keycloak provider/adapter | `set_auth_provider` | `get_auth_provider` |
| `app.state.db_engine` | `Engine` | `set_db_engine` | `get_db_engine` |
| `app.state.minio_client` | `Minio` | `set_minio_client` | `get_minio_client` |
| `app.state.milvus_client` | `MilvusClient` | `set_milvus_client` | `get_milvus_client` |
| `app.state.async_milvus_client` | `AsyncMilvusClient` | `set_async_milvus_client` | `get_async_milvus_client` |
| `app.state.ollama_client` | `ollama.Client` | `set_ollama_client` | `get_ollama_client` |
| `app.state.langfuse_client` | `Any` | `set_langfuse_client` | `get_langfuse_client` |
| `app.state.nats_client` | `nats.aio.client.Client` | `set_nats_client` | `get_nats_client` |

---

## 스키마

### `UserInfo` — `fastapi_core.schemas.user`

```python
class UserInfo(BaseModel):
    sub: str
    username: str
    email: str | None = None
    name: str | None = None
    roles: list[str] = []
    scopes: list[str] = []
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
    status: str
```

---

## 인증

### `KeycloakAuthProvider` — `fastapi_core.core.auth`

```python
class KeycloakAuthProvider:
    def __init__(
        self,
        http_url: str,
        realm: str,
        client_id: str,
        client_secret: str | None = None,
    ) -> None: ...
```

생성 시 검증:

- `http_url`이 비어 있으면 `ValueError("http_url must not be empty")`
- `realm`이 비어 있으면 `ValueError("realm must not be empty")`
- `client_id`가 비어 있으면 `ValueError("client_id must not be empty")`

파생 속성:

| 속성 | 값 |
| --- | --- |
| `token_url` | `{base}/realms/{realm}/protocol/openid-connect/token` |
| `introspection_url` | `{token_url}/introspect` |
| `jwks_url` | `{base}/realms/{realm}/protocol/openid-connect/certs` |
| `issuer` | `{base}/realms/{realm}` |

#### 메서드

```python
def authenticate(self, username: str, password: str) -> dict[str, Any]:
```

- password grant 토큰 발급
- 실패 시 내부 `httpx` 예외(`HTTPStatusError`)가 그대로 전파될 수 있음

```python
def refresh_access_token(self, refresh_token: str) -> dict[str, Any]:
```

```python
def decode_token(self, token: str) -> dict[str, Any]:
```

- RS256 + audience + issuer 검증
- 실패 시 `ValueError("Invalid token: ...")`

```python
def decode_token_insecure(self, token: str) -> dict[str, Any]:
```

- 서명 검증 없이 decode
- 실패 시 `ValueError("Invalid token: ...")`

```python
def introspect_token(self, token: str) -> dict[str, Any]:
```

```python
def to_user(self, payload: dict[str, Any]) -> UserInfo:
```

### `set_auth_provider` — `fastapi_core.dependencies.auth`

```python
def set_auth_provider(
    app: FastAPI,
    provider: KeycloakAuthProvider | None = None,
    *,
    config: EnvConfig | None = None,
) -> None:
```

동작:

- `provider=` 직접 전달 시 그대로 저장
- `config=` 전달 시 `get_required_docmesh_service(app, "auth_provider", config=config)` 결과를 adapter로 감싸 저장
- 둘 다 없으면 `ValueError("Either provider or config must be provided")`

### `get_auth_provider`

```python
def get_auth_provider(
    request: Request,
    config: EnvConfig | DependsParam = Depends(get_config),
) -> KeycloakAuthProvider:
```

- state 캐시 우선
- 없으면 registry-backed 서비스 해석 후 state에 저장

### `get_current_user`

```python
def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    provider: KeycloakAuthProvider = Depends(get_auth_provider),
    settings: ServiceSettings = Depends(get_settings),
) -> UserInfo:
```

분기 규칙:

| 조건 | 동작 |
| --- | --- |
| 토큰 없음 | `401 Not authenticated` |
| `settings.auth.use_introspection` | `provider.introspect_token()` |
| `settings.auth.verify_jwt` | `provider.decode_token()` |
| `settings.auth.allow_insecure_jwt_decode` | `provider.decode_token_insecure()` |
| 모두 아니면 | `401 JWT verification is disabled but insecure decode is not allowed` |

예외는 `HTTPException(401, detail=..., WWW-Authenticate=Bearer)`로 변환됩니다.

### `require_permissions`

```python
def require_permissions(*roles: str):
```

- 반환값은 내부 dependency 함수
- 지정 역할이 하나라도 없으면 `403 Missing required role: {role}`

---

## 설정 dependency

### `set_config` / `set_settings` — `fastapi_core.dependencies.config`

```python
def set_config(app: FastAPI, config: EnvConfig) -> None:
def set_settings(app: FastAPI, settings: ServiceSettings) -> None:
```

### `get_config`

```python
def get_config(request: Request) -> EnvConfig:
```

- `app.state.config`가 없으면 `EnvConfig()`를 생성 후 저장

### `get_settings`

```python
def get_settings(
    request: Request,
    config: EnvConfig | DependsParam = Depends(get_config),
) -> ServiceSettings:
```

- `app.state.settings`가 없으면 `ServiceSettings.from_yaml(config.config_path)` 결과를 저장
- 설정 로딩 책임은 `fastapi_core.core.config` 에 있고, docmesh registry/settings 적응 책임은 `fastapi_core.docmesh_bridge` 에 있습니다.
- Keycloak readiness용 관리 URL은 `EnvConfig.keycloak_overlay.manage_url` 로 읽고, docmesh canonical Keycloak 적응은 `build_docmesh_keycloak_config()` 가 담당합니다.

---

## 데이터베이스

### Core helper — `fastapi_core.core.database`

```python
def create_db_engine(config: DatabaseConfig) -> Engine:
```

- `config.sqlalchemy_database_url`
- `echo`, `pool_size`, `max_overflow`, `pool_timeout`, `pool_recycle`

```python
def check_database_connection(engine: Engine) -> bool:
```

- `SELECT 1` 성공 시 `True`, 예외 시 `False`

```python
def get_database_version(engine: Engine) -> str | None:
```

- `SELECT version()` 결과 문자열
- 실패 시 `None`

```python
@contextmanager
def run_in_transaction(
    engine: Engine,
    *,
    session_factory: Callable[[Engine], Session] = Session,
) -> Iterator[Session]:
```

- 성공 시 `commit()`
- 예외 시 `rollback()` 후 재전파
- 항상 `close()` 보장

### FastAPI dependency — `fastapi_core.dependencies.database`

```python
def set_db_engine(
    app: FastAPI,
    engine: Engine | None = None,
    *,
    config: EnvConfig | None = None,
) -> None:
```

- `config=` 사용 시 현재 구현은 `create_db_engine()`이 아니라 registry-backed `get_required_docmesh_service(..., "db_engine", ...)` 경로를 사용

```python
def get_db_engine(
    request: Request,
    config: EnvConfig | DependsParam = Depends(get_config),
) -> Engine:
```

```python
def get_db_session(engine: Engine = Depends(get_db_engine)) -> Iterator[Session]:
```

- 요청 범위 세션 제공
- 종료 시 `session.close()` 보장

---

## MinIO

### Core helper — `fastapi_core.core.storage`

```python
def create_minio_client(config: MinIOConfig) -> Minio:
```

```python
def check_minio_connection(client: Minio, bucket: str) -> bool:
```

- `bucket_exists(bucket)` 성공 시 `True`

```python
def ensure_bucket_exists(client: Minio, bucket: str) -> bool:
```

- 이미 있으면 `False`
- 새로 만들면 `True`

```python
def list_bucket_names(client: Minio) -> list[str]:
```

```python
def generate_presigned_get_url(
    client: Minio,
    config: MinIOConfig,
    bucket: str,
    object_name: str,
) -> str:
```

```python
def generate_presigned_put_url(
    client: Minio,
    config: MinIOConfig,
    bucket: str,
    object_name: str,
) -> str:
```

- 둘 다 `config.presigned_expires_sec`를 `timedelta(seconds=...)`로 변환

### FastAPI dependency — `fastapi_core.dependencies.storage`

```python
def set_minio_client(
    app: FastAPI,
    client: Minio | None = None,
    *,
    config: EnvConfig | None = None,
) -> None:
```

```python
def get_minio_client(
    request: Request,
    config: EnvConfig | DependsParam = Depends(get_config),
) -> Minio:
```

- `config=` 경로는 registry-backed `minio_client` 해석 사용

---

## Milvus

### Core helper — `fastapi_core.core.milvus`

```python
def create_milvus_client(config: MilvusConfig) -> MilvusClient:
def create_async_milvus_client(config: MilvusConfig) -> AsyncMilvusClient:
```

전달 파라미터:

- `uri`
- `db_name`
- `timeout`
- `token` (`config.token is not None`이면 포함)

```python
def check_milvus_connection(client: MilvusClient) -> bool:
async def check_async_milvus_connection(client: AsyncMilvusClient) -> bool:
```

```python
def list_collection_names(client: MilvusClient) -> list[str]:
async def list_async_collection_names(client: AsyncMilvusClient) -> list[str]:
```

```python
def ensure_collection_exists(
    client: MilvusClient,
    collection_name: str,
    *,
    dimension: int,
) -> bool:
```

```python
async def ensure_async_collection_exists(
    client: AsyncMilvusClient,
    collection_name: str,
    *,
    dimension: int,
) -> bool:
```

- 존재하면 `False`, 새로 만들면 `True`

### FastAPI dependency

```python
def set_milvus_client(...): ...
def get_milvus_client(...): ...
```

- sync Milvus는 registry-backed `milvus_client` 해석 사용
- native `EnvConfig.milvus` 와 docmesh settings 사이의 최종 선택은 `fastapi_core.docmesh_bridge.resolve_milvus_config(...)` 가 담당합니다.

```python
async def set_async_milvus_client(...): ...
async def get_async_milvus_client(...): ...
```

- async Milvus는 `create_async_milvus_client(config.milvus)` 직접 사용

---

## Ollama

### Core helper — `fastapi_core.core.ollama`

```python
def create_ollama_client(config: OllamaConfig) -> ollama.Client:
def check_ollama_connection(client: ollama.Client) -> bool:
def list_model_names(client: ollama.Client) -> list[str]:
```

```python
def generate_text(
    client: ollama.Client,
    config: OllamaConfig,
    prompt: str,
    *,
    model: str | None = None,
) -> str:
```

- 기본 모델은 `config.model`
- `model=`이 주어지면 override
- 응답의 `response` 문자열 반환

### FastAPI dependency — `fastapi_core.dependencies.ollama`

```python
def set_ollama_client(...): ...
def get_ollama_client(...): ...
```

- registry-backed `ollama_client` 해석 사용

---

## Langfuse

### Core helper — `fastapi_core.core.langfuse`

```python
def get_langfuse_client(config: LangfuseConfig | None = None) -> Langfuse:
```

동작:

- `config is None` → `langfuse.get_client()`
- `config`가 있으면 내부 `_create_langfuse_client(config)` 호출 후
  - `config.public_key`가 있으면 `langfuse.get_client(public_key=...)`
  - 없으면 `langfuse.get_client()`

```python
def check_langfuse_connection(config: LangfuseConfig) -> bool:
```

- `GET {host}/api/public/health`
- HTTP 성공 + JSON `status == "OK"`면 `True`
- 그 외 `False`

### FastAPI dependency — `fastapi_core.dependencies.langfuse`

```python
def set_langfuse_client(...): ...
def get_langfuse_client(...): ...
```

- registry-backed `langfuse_client` 해석 사용

---

## NATS 메시징

### Core helper — `fastapi_core.core.messaging`

```python
async def create_nats_client(config: NatsConfig) -> nats.aio.client.Client:
```

- `servers=config.server_list`
- `reconnect_time_wait=config.reconnect_time_wait_ms / 1000`

```python
def validate_event_subject(subject: str) -> bool:
def build_event_subject(domain: str, entity: str, action: str) -> str:
```

- 형식: `<domain>.<entity>.<action>`
- 각 segment는 소문자/숫자/하이픈만 허용
- `build_event_subject()`는 실패 시 `ValueError`

```python
async def publish_event(
    client: nats.aio.client.Client,
    subject: str,
    payload: Mapping[str, Any],
) -> None:
```

- payload를 compact JSON UTF-8 bytes로 인코딩하여 publish

```python
async def subscribe_event(
    client: nats.aio.client.Client,
    subject: str,
    handler: Callable[[str, dict[str, Any]], Awaitable[None] | None],
) -> Any:
```

```python
async def subscribe_queue_event(
    client: nats.aio.client.Client,
    subject: str,
    queue: str,
    handler: Callable[[str, dict[str, Any]], Awaitable[None] | None],
) -> Any:
```

### FastAPI dependency — `fastapi_core.dependencies.messaging`

```python
async def set_nats_client(...): ...
async def get_nats_client(...): ...
```

- registry-backed `nats_client` 해석 사용
- 함수형 dependency 정책 유지

---

## lifecycle / factory

### `resolve_lifecycle_policy` — `fastapi_core.lifecycle`

```python
def resolve_lifecycle_policy(settings: ServiceSettings) -> LifecyclePolicy:
```

- `eager_keycloak/database/minio/langfuse`가 `None`이면 대응 `health.check_*` 값을 상속

### `initialize_app_services`

```python
async def initialize_app_services(
    app: FastAPI,
    config: EnvConfig,
    settings: ServiceSettings | None = None,
    *,
    init_auth: bool | None = None,
    init_database: bool | None = None,
    init_minio: bool | None = None,
    init_milvus: bool | None = None,
    init_async_milvus: bool | None = None,
    init_ollama: bool | None = None,
    init_langfuse: bool | None = None,
    init_nats: bool | None = None,
    use_docmesh_registry: bool | None = None,
) -> None:
```

- 정책에 따라 docmesh registry bootstrap
- registry-managed 서비스 eager init
- `async_milvus_client` 직접 초기화

### `shutdown_app_services`

```python
async def shutdown_app_services(app: FastAPI) -> None:
```

종료 시도 대상:

- `docmesh_registry.close_all()`
- `nats_client.drain()`
- `async_milvus_client.close()`
- `milvus_client.close()`
- `db_engine.dispose()`
- `langfuse_client.flush()`

### `create_managed_lifespan`

```python
def create_managed_lifespan(
    config: EnvConfig,
    settings: ServiceSettings,
) -> Callable[[FastAPI], AsyncIterator[None]]:
```

### `create_app` — `fastapi_core.factory`

```python
def create_app(
    config: EnvConfig | None = None,
    settings: ServiceSettings | None = None,
    lifespan: Callable[[FastAPI], AsyncIterator] | None = None,
    include_auth_router: bool = True,
) -> FastAPI:
```

동작 순서:

1. `config` 기본값 보정
2. `settings` 기본값 보정 (`ServiceSettings.from_yaml(config.config_path)`)
3. `lifespan` 기본값 보정 (`create_managed_lifespan(config, settings)`)
4. `setup_logging(config.logging.level)`
5. `FastAPI(root_path=config.root_path, lifespan=lifespan)` 생성
6. `config`, `settings`를 state에 저장
7. `CORSMiddleware` 등록
8. `AuthError` handler 등록
9. `health.router` 등록
10. `include_auth_router=True`면 `auth.router` 등록

---

## 내장 HTTP 엔드포인트

### `GET /health/liveness`

응답:

```json
{ "status": "ok" }
```

### `GET /health/readiness`

입력 dependency:

- `config = Depends(get_config)`
- `settings = Depends(get_settings)`

검사 규칙:

- `health.check_keycloak`가 켜져 있으면 `GET {manage_url}/health/ready`
- `health.check_database`가 켜져 있으면 `check_database_connection(get_db_engine(...))`
- `health.check_minio`가 켜져 있으면 `check_minio_connection(get_minio_client(...), config.minio.bucket)`
- `health.check_langfuse`가 켜져 있으면 registry check 또는 `check_langfuse_connection(config.langfuse)`
- `lifecycle.use_docmesh_healthchecks`가 켜져 있고 native checks가 있으면 `run_docmesh_healthchecks(...)`를 시도

주요 실패 응답:

| 조건 | 응답 |
| --- | --- |
| Keycloak not ready | `503 {"detail": "Keycloak not ready"}` |
| Keycloak unreachable | `503 {"detail": "Keycloak unreachable: ..."}` |
| Database not ready | `503 {"detail": "Database not ready"}` |
| MinIO not ready | `503 {"detail": "MinIO not ready"}` |
| Langfuse not ready | `503 {"detail": "Langfuse not ready"}` |

### `POST /token`

```python
@router.post("/token", response_model=TokenResponse)
```

- `OAuth2PasswordRequestForm` 입력
- `provider.authenticate(form.username, form.password)` 호출
- 실패 시 `401` + `WWW-Authenticate: Bearer`

### `GET /user`

```python
@router.get("/user", response_model=UserInfo)
```

- `Depends(get_current_user)` 결과 반환

---

## 예외 처리

### `AuthError` — `fastapi_core.core.exceptions`

```python
class AuthError(Exception):
    def __init__(self, message: str, status_code: int = 401) -> None: ...
```

`create_app()`는 `auth_error_handler`를 전역 handler로 등록합니다.
기본 응답 형식:

```json
{ "detail": "<message>" }
```
