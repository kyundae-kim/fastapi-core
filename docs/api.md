# 공개 API 명세 (Public Interface)

> 이 문서는 `fastapi-core` SDK가 외부에 공개하는 모든 심볼의 시그니처, 동작, 에러 처리를 정의합니다.  
> 설정 값(환경 변수, YAML 키)은 [config.md](config.md)를 참조하세요.

---

## FastAPI 의존성 export 정책

- `get_config`, `get_settings`, `get_auth_provider`, `get_current_user`, `get_db_engine`, `get_db_session`, `get_minio_client`, `get_milvus_client`, `get_ollama_client`, `get_nats_client`는 모두 **함수형 dependency**로 export한다.
- `Get*Dependency` callable class와 `get_* = Get*Dependency()` 형태의 전역 인스턴스는 사용하지 않는다.
- 중복 dependency alias인 `config_schema`, `settings_schema`, `auth_provider_schema`, `current_user_schema`는 제공하지 않는다.
- 라우터와 테스트에서는 항상 `Depends(get_*)` 형태로 직접 참조한다.
- Langfuse는 SDK 자체 싱글톤을 중심으로 사용한다. 앱 코드에서는 `fastapi_core.core.langfuse.get_langfuse_client()`를 직접 호출하거나, FastAPI state가 필요하면 `fastapi_core.dependencies.langfuse.get_langfuse_client()`를 사용할 수 있다.

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
| `introspection_url` | `{http_url}/realms/{realm}/protocol/openid-connect/token/introspect` |
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
def introspect_token(self, token: str) -> dict[str, Any]:
    """Keycloak token introspection endpoint 호출 결과를 반환. HTTP 오류 시 httpx.HTTPStatusError."""
```

```python
def to_user(self, payload: dict[str, Any]) -> UserInfo:
    """JWT payload → UserInfo 모델 변환."""
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
    config: EnvConfig | DependsParam = Depends(get_config),
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
| `Authorization: Bearer ***` 헤더 없음 | `401 Not authenticated` |
| 토큰 검증 실패 (`ValueError`) | `401 <오류 메시지>` |
| `settings.auth.use_introspection = True` | `provider.introspect_token()` |
| `settings.auth.use_introspection = False` 이고 `settings.auth.verify_jwt = True` | `provider.decode_token()` (RS256 서명 검증) |
| `settings.auth.use_introspection = False`, `settings.auth.verify_jwt = False`, `settings.auth.allow_insecure_jwt_decode = True` | `provider.decode_token_insecure()` (서명 검증 생략) |
| 위 세 조건 모두 아니면 | `401 JWT verification is disabled but insecure decode is not allowed` |

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
    config: EnvConfig | DependsParam = Depends(get_config),
) -> Engine:
```

- `app.state.db_engine` 존재 시 반환 (싱글톤)
- `AttributeError` 시 `create_db_engine(config.db)` 호출 후 `app.state.db_engine`에 저장 (fallback lazy singleton)

### `get_db_session` — `fastapi_core.dependencies.database`

```python
def get_db_session(
    engine: Engine = Depends(get_db_engine),
) -> Iterator[Session]:
```

- SQLAlchemy `Session`을 생성해 요청 스코프에서 제공
- 정상/예외 종료와 관계없이 `session.close()` 보장

---

## 스토리지 (Storage / MinIO)

### `create_minio_client` — `fastapi_core.core.storage`

```python
def create_minio_client(config: MinIOConfig) -> Minio:
    """MinIOConfig로 minio.Minio 클라이언트 생성."""
```

### `check_minio_connection` — `fastapi_core.core.storage`

```python
def check_minio_connection(client: Minio, bucket: str) -> bool:
    """bucket_exists() 호출 성공 시 True, 예외 시 False."""
```

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
    config: EnvConfig | DependsParam = Depends(get_config),
) -> Minio:
```

- `app.state.minio_client` 존재 시 반환 (싱글톤)
- `AttributeError` 시 `create_minio_client(config.minio)` 호출 후 `app.state.minio_client`에 저장 (fallback lazy singleton)

---

## 벡터 데이터베이스 (Milvus)

### `create_milvus_client` — `fastapi_core.core.milvus`

```python
def create_milvus_client(config: MilvusConfig) -> MilvusClient:
```

- `config.uri`, `config.db_name`, `config.timeout`으로 `MilvusClient`를 생성한다.
- `config.token`이 있으면 함께 전달한다.

### `create_async_milvus_client` — `fastapi_core.core.milvus`

```python
def create_async_milvus_client(config: MilvusConfig) -> AsyncMilvusClient:
```

- `config.uri`, `config.db_name`, `config.timeout`으로 `AsyncMilvusClient`를 생성한다.
- `config.token`이 있으면 함께 전달한다.

### `set_milvus_client` — `fastapi_core.dependencies.milvus`

```python
def set_milvus_client(
    app: FastAPI,
    client: MilvusClient | None = None,
    *,
    config: EnvConfig | None = None,
) -> None:
```

- `client` 직접 전달 → `app.state.milvus_client`에 할당
- `config` 전달 → `create_milvus_client(config.milvus)` 내부 호출 후 할당
- 둘 다 `None` → `ValueError`

### `get_milvus_client` — `fastapi_core.dependencies.milvus`

```python
def get_milvus_client(
    request: Request,
    config: EnvConfig | DependsParam = Depends(get_config),
) -> MilvusClient:
```

- `app.state.milvus_client` 존재 시 반환 (싱글톤)
- `AttributeError` 시 `create_milvus_client(config.milvus)` 호출 후 `app.state.milvus_client`에 저장 (fallback lazy singleton)

### `set_async_milvus_client` — `fastapi_core.dependencies.async_milvus`

```python
async def set_async_milvus_client(
    app: FastAPI,
    client: AsyncMilvusClient | None = None,
    *,
    config: EnvConfig | None = None,
) -> None:
```

- `client` 직접 전달 → `app.state.async_milvus_client`에 할당
- `config` 전달 → `create_async_milvus_client(config.milvus)` 내부 호출 후 할당
- 둘 다 `None` → `ValueError`

### `get_async_milvus_client` — `fastapi_core.dependencies.async_milvus`

```python
async def get_async_milvus_client(
    request: Request,
    config: EnvConfig | DependsParam = Depends(get_config),
) -> AsyncMilvusClient:
```

- `app.state.async_milvus_client` 존재 시 반환 (싱글톤)
- `AttributeError` 시 `create_async_milvus_client(config.milvus)` 호출 후 `app.state.async_milvus_client`에 저장 (fallback lazy singleton)

---

## Ollama

### `create_ollama_client` — `fastapi_core.core.ollama`

```python
def create_ollama_client(config: OllamaConfig) -> ollama.Client:
```

- `config.host`와 `config.timeout`으로 Ollama HTTP 클라이언트를 생성한다.

### `check_ollama_connection` — `fastapi_core.core.ollama`

```python
def check_ollama_connection(client: ollama.Client) -> bool:
```

- `client.list()` 호출이 성공하면 `True`
- 예외가 발생하면 `False`

### `list_model_names` — `fastapi_core.core.ollama`

```python
def list_model_names(client: ollama.Client) -> list[str]:
```

- `client.list()` 응답의 `models[*].model` 값을 추출해 모델 이름 목록을 반환한다.

### `generate_text` — `fastapi_core.core.ollama`

```python
def generate_text(
    client: ollama.Client,
    config: OllamaConfig,
    prompt: str,
    *,
    model: str | None = None,
) -> str:
```

- 기본적으로 `config.model`을 사용해 `client.generate(model=..., prompt=...)` 를 호출한다.
- `model=` 인자를 주면 기본 모델 대신 override 한다.
- SDK 응답의 `response` 문자열을 반환한다.

### `set_ollama_client` — `fastapi_core.dependencies.ollama`

```python
def set_ollama_client(
    app: FastAPI,
    client: ollama.Client | None = None,
    *,
    config: EnvConfig | None = None,
) -> None:
```

- `client` 직접 전달 → `app.state.ollama_client`에 할당
- `config` 전달 → docmesh bridge의 `get_required_docmesh_service(..., "ollama_client", config=config)` 결과를 할당
- 둘 다 `None` → `ValueError`

### `get_ollama_client` — `fastapi_core.dependencies.ollama`

```python
def get_ollama_client(
    request: Request,
    config: EnvConfig | DependsParam = Depends(get_config),
) -> ollama.Client:
```

- `app.state.ollama_client` 존재 시 반환 (싱글톤)
- 없으면 docmesh bridge의 `get_required_docmesh_service(..., "ollama_client", config=resolved_config)` 를 통해 fallback lazy singleton을 만든다.

---

## Langfuse

### `get_langfuse_client` — `fastapi_core.core.langfuse`

```python
def get_langfuse_client(config: LangfuseConfig | None = None) -> Langfuse:
```

- `config`가 주어지면 먼저 내부 초기화 helper로 SDK 싱글톤을 준비한다.
- `config.public_key`가 있으면 `langfuse.get_client(public_key=...)`로 해당 프로젝트 싱글톤을 반환한다.
- `config`가 없으면 `langfuse.get_client()`를 그대로 반환한다.
- FastAPI state 기반 접근이 필요하면 `fastapi_core.dependencies.langfuse.get_langfuse_client()` 를 사용할 수 있다.

### `check_langfuse_connection` — `fastapi_core.core.langfuse`

```python
def check_langfuse_connection(config: LangfuseConfig) -> bool:
```

- `GET {config.host}/api/public/health` 호출
- HTTP 200이면서 JSON `status == "OK"`이면 `True`
- HTTP 오류, JSON 파싱 오류, 상태값 불일치 시 `False`

---

## 메시징 (NATS)

### `create_nats_client` — `fastapi_core.core.messaging`

```python
async def create_nats_client(config: NatsConfig) -> nats.aio.client.Client:
    """NATS 서버에 연결된 클라이언트를 생성한다."""
```

- `config.server_list`를 `servers=[...]`로 전달한다.
- `config.reconnect_time_wait_ms`는 초 단위 float로 변환해 `reconnect_time_wait`에 전달한다.

### `build_event_subject` — `fastapi_core.core.messaging`

```python
def build_event_subject(domain: str, entity: str, action: str) -> str:
```

- `<domain>.<entity>.<action>` 형식의 subject를 만든다.
- 각 segment는 소문자 영문/숫자와 하이픈만 허용한다.
- 형식이 맞지 않으면 `ValueError`를 발생시킨다.

### `validate_event_subject` — `fastapi_core.core.messaging`

```python
def validate_event_subject(subject: str) -> bool:
```

- 정확히 3개 segment를 가진 subject만 `True`
- 대문자, 빈 segment, 4단계 이상 subject는 `False`

### `publish_event` — `fastapi_core.core.messaging`

```python
async def publish_event(
    client: nats.aio.client.Client,
    subject: str,
    payload: Mapping[str, Any],
) -> None:
```

- 유효한 event subject인지 검증한다. 아니면 `ValueError`.
- payload를 compact JSON UTF-8 bytes로 인코딩해 `client.publish(...)` 한다.

### `subscribe_event` — `fastapi_core.core.messaging`

```python
async def subscribe_event(
    client: nats.aio.client.Client,
    subject: str,
    handler: Callable[[str, dict[str, Any]], Awaitable[None] | None],
) -> Any:
```

- `client.subscribe(subject, cb=...)`로 구독한다.
- 수신 메시지의 JSON payload를 decode한 뒤 `handler(subject, payload)` 형태로 전달한다.

### `subscribe_queue_event` — `fastapi_core.core.messaging`

```python
async def subscribe_queue_event(
    client: nats.aio.client.Client,
    subject: str,
    queue: str,
    handler: Callable[[str, dict[str, Any]], Awaitable[None] | None],
) -> Any:
```

- `subscribe_event`와 동일하되, `queue=`를 명시해 queue group 소비자를 등록한다.

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
- `config` 전달 → docmesh bridge의 `get_required_docmesh_service_async(..., "nats_client", config=config)` 결과를 할당
- 둘 다 `None` → `ValueError`

### `get_nats_client` — `fastapi_core.dependencies.messaging`

```python
async def get_nats_client(
    request: Request,
    config: EnvConfig | DependsParam = Depends(get_config),
) -> nats.aio.client.Client:
```

- `app.state.nats_client` 존재 시 반환 (싱글톤)
- 미등록 시 docmesh bridge의 `get_required_docmesh_service_async(..., "nats_client", config=resolved_config)` 를 통해 fallback lazy singleton을 만든다.

---

## 설정 (Config)

### `get_config` — `fastapi_core.dependencies.config`

```python
def get_config(request: Request) -> EnvConfig:
    """app.state.config 반환. 미등록 시 EnvConfig() 생성 후 app.state에 저장."""
```

### `get_settings` — `fastapi_core.dependencies.config`

```python
def get_settings(
    request: Request,
    config: EnvConfig | DependsParam = Depends(get_config),
) -> ServiceSettings:
    """app.state.settings 반환. 미등록 시 YAML에서 로드 후 app.state에 저장."""
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

Keycloak + PostgreSQL + MinIO 준비 상태를 종합 확인한다. `settings.health.check_langfuse`가 `true`이면 Langfuse public health endpoint도 함께 확인한다.

| 조건 | 응답 |
|---|---|
| Keycloak + DB + MinIO (+ 선택적 Langfuse) 모두 정상 | `200 { "status": "ok" }` |
| Keycloak 비정상 응답 | `503 { "detail": "Keycloak not ready" }` |
| Keycloak 연결 불가 (`RequestError`) | `503 { "detail": "Keycloak unreachable: ..." }` |
| DB 연결 실패 | `503 { "detail": "Database not ready" }` |
| MinIO 연결 실패 | `503 { "detail": "MinIO not ready" }` |
| Langfuse health check 실패 | `503 { "detail": "Langfuse not ready" }` |

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
| `app.state.milvus_client` | `MilvusClient` | `set_milvus_client` | `get_milvus_client` |
| `app.state.async_milvus_client` | `AsyncMilvusClient` | `set_async_milvus_client` | `get_async_milvus_client` |
| `app.state.ollama_client` | `ollama.Client` | `set_ollama_client` | `get_ollama_client` |
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
from fastapi_core.dependencies.milvus import set_milvus_client
from fastapi_core.dependencies.ollama import set_ollama_client
from fastapi_core.dependencies.messaging import set_nats_client

config = EnvConfig()

@asynccontextmanager
async def lifespan(app: FastAPI):
    set_auth_provider(app, config=config)
    set_db_engine(app, config=config)
    set_minio_client(app, config=config)
    set_milvus_client(app, config=config)
    set_ollama_client(app, config=config)
    await set_nats_client(app, config=config)
    yield
    app.state.db_engine.dispose()
    app.state.milvus_client.close()
    await app.state.nats_client.drain()

app = create_app(config=config, lifespan=lifespan)
```
