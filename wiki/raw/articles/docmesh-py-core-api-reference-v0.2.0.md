---
source_url: https://github.com/kyundae-kim/docmesh-py-core/blob/v0.2.0/docs/api.md
ingested: 2026-07-13
sha256: 0c82f08deda80af99da937df1ff7af331b58998f03afa0723daa9c61d91bd069
---
# docmesh-py-core API Reference

이 문서는 현재 소스코드(`docmesh_py_core/__init__.py`, 각 모듈 구현)를 기준으로 정리한 공개 API 레퍼런스입니다.

- 사용 흐름은 [README](../README.md)
- 환경변수/설정 규칙은 [config.md](./config.md)
- 실제 통합 예시는 [examples.md](./examples.md)

## 1. Public imports

패키지 루트에서 바로 import 가능한 공개 API는 다음과 같습니다.

```python
from docmesh_py_core import (
    AccessTokenResult,
    AuthenticatedUser,
    CommonConfig,
    ConfigError,
    ConfigIssue,
    HealthCheckError,
    HealthCheckResult,
    KeycloakAuthService,
    KeycloakConfig,
    KeycloakDiscoveryConfig,
    KeycloakProvisioner,
    KeycloakTokenAuthenticationError,
    KeycloakTokenConfigurationError,
    KeycloakTokenError,
    KeycloakTokenTemporaryError,
    LangfuseConfig,
    MinioConfig,
    MinioRuntimeDefaults,
    MilvusConfig,
    MilvusRuntimeDefaults,
    NatsConnectionBuilder,
    NatsConfig,
    OllamaConfig,
    OllamaRuntimeDefaults,
    PostgresConfig,
    ProvisioningResult,
    ServiceBundle,
    ServiceCloseError,
    ServiceCloseFailure,
    ServiceClientError,
    ServiceClientProtocol,
    ServiceClientWrapper,
    ServiceClientWrapperError,
    ServiceConfigs,
    ServiceRuntime,
    ServiceHealthStatus,
    SqliteConfig,
    TokenValidationError,
    assemble_services,
    assemble_service_runtime,
    async_check_all_services,
    async_close_service_clients,
    build_service_log_event,
    check_all_services,
    close_service_clients,
    configure_logging,
    create_keycloak_client,
    create_langfuse_client,
    create_milvus_client,
    create_minio_client,
    create_nats_client,
    create_ollama_client,
    create_postgres_client,
    create_sqlite_client,
    load_available_service_configs,
    load_service_configs,
    require_minio_bucket,
    mask_sensitive_value,
    retry_call,
    validate_service_requirements,
    validate_runtime_security,
)
```

> 위 목록은 `docmesh_py_core/__init__.py`의 `__all__` 기준입니다.

### 공개 결과 및 오류 데이터 구조

#### `AccessTokenResult`

- `access_token`: `str`; 토큰 원문이므로 로그에 기록하지 않습니다.
- `token_type`: `str`
- `expires_in`: `int`
- `refresh_token`: `str | None`; 토큰 원문이므로 로그에 기록하지 않습니다.
- `scope`: `str | None`

#### `AuthenticatedUser`

- 사용자 식별 필드: `sub`, `preferred_username`, `email`, `given_name`, `family_name`, `name`
- 권한 필드: `realm_roles: list[str]`, `client_roles: dict[str, list[str]]`
- 검증된 전체 JWT payload: `claims: dict[str, Any]`

#### `ProvisioningResult`

- `created`, `updated`, `unchanged`, `planned`: 리소스 식별자 목록
- `failed`: `(리소스 식별자, 마스킹된 오류)` tuple 목록
- `dry_run`: dry-run 실행 여부

#### `ConfigIssue`

- `service`, `env_key`, `reason`, `error_type`, `remediation`
- `ConfigError.issues`와 호환 별칭인 `ConfigError.errors`에서 확인할 수 있습니다.

#### `ServiceCloseFailure`

- `client`: 종료에 실패한 클라이언트 또는 wrapper
- `error`: 원래 종료 예외
- 여러 실패는 `ServiceCloseError.failures`에 tuple로 보존됩니다.

#### Runtime defaults

`ServiceClientWrapper.runtime_defaults`에는 SDK 생성자에 직접 전달되지 않은 typed 기본값이 저장될 수 있습니다.

- `MinioRuntimeDefaults`: `bucket`, `request_timeout_seconds`, `max_retries`
- `MilvusRuntimeDefaults`: `collection`, `connect_timeout_seconds`, `max_retries`, `secure`
- `OllamaRuntimeDefaults`: `generation_model`, `embedding_model`, `max_retries`

## 2. 권장 사용 흐름

이 라이브러리는 **assembly-first, direct-api-when-needed** 정책을 따릅니다.

| 상황 | 우선 API | direct API가 필요한 경우 |
| --- | --- | --- |
| 동기 서비스 lifecycle 조립 | `assemble_services()` | 특정 SDK factory hook 또는 client lifecycle을 직접 제어할 때 |
| NATS 또는 async lifecycle 조립 | `assemble_service_runtime()` | NATS builder/SDK 연결을 직접 제어할 때 |
| Keycloak 토큰/JWT 기능만 사용 | `KeycloakAuthService(KeycloakConfig())` | 해당 direct API가 기본 경로 |
| CLI, 배치, 단일 서비스 테스트 | 서비스별 `*Config()` + `create_*_client()` | 해당 direct API가 기본 경로 |

일반 애플리케이션은 아래 순서로 assembly API를 사용합니다.

1. 환경변수 또는 명시적 mapping 준비
2. 동기 서비스는 `assemble_services()`, NATS/async 서비스는 `await assemble_service_runtime()` 호출
3. `required`, `one_of`, `check_on_startup`으로 구성·startup 정책 선언
4. `ServiceBundle` 또는 `ServiceRuntime`의 context manager로 lifecycle 관리

주의:

- `nats`만 예외적으로 `NatsConnectionBuilder`를 반환하며, 실제 네트워크 연결은 `await connect()` / `await ping()` / `await check()`에서 일어납니다.
- `langfuse`는 `LANGFUSE_ENABLED=false`면 `create_langfuse_client()`가 `None`을 반환할 수 있습니다.
- `CommonConfig.env`는 자유 문자열이며 enum 검증을 하지 않습니다. 운영 판정은 `DOCMESH_SECURITY_MODE`가 있으면 그 값을 우선하고, 없으면 `DOCMESH_PRODUCTION_ALIASES`(기본값 `prod,production`)와 환경 이름을 비교합니다.

## 3. Service config API

### Direct API용 config entrypoint

서비스별 config class 직접 생성은 direct-api-when-needed 경로입니다. 일반 애플리케이션 lifecycle 조립에는 먼저 [assembly API](#5-공통-wrapper--helper-api)의 `assemble_services()` 또는 `assemble_service_runtime()`을 고려하세요.

- 공통: `CommonConfig()`
- Keycloak discovery 전용: `KeycloakDiscoveryConfig()`
- Keycloak 전체: `KeycloakConfig()`
- PostgreSQL: `PostgresConfig()`
- SQLite: `SqliteConfig()`
- MinIO: `MinioConfig()`
- Milvus: `MilvusConfig()`
- Ollama: `OllamaConfig()`
- Langfuse: `LangfuseConfig()`
- NATS: `NatsConfig()`

규칙:

- 서비스별 `*Config()` 직접 생성은 pydantic `ValidationError`를 그대로 발생시킵니다.
- `load_service_configs()`는 선택된 서비스만 읽고, 검증 실패를 `ConfigError`로 다시 감싸서 반환합니다.
- `LANGFUSE_ENVIRONMENT`가 비어 있으면 `CommonConfig().env` 값을 상속합니다.

예시:

```python
from docmesh_py_core import CommonConfig, KeycloakAuthService, KeycloakConfig

common = CommonConfig()
keycloak = KeycloakConfig()

auth = KeycloakAuthService(keycloak)

assert isinstance(common.env, str)
assert keycloak.client_id
```

### 3.2 `load_service_configs(env=None, *, services=None) -> ServiceConfigs`

설정을 읽고 검증합니다. `env`를 생략하면 현재 프로세스 환경변수를 읽고,
`Mapping[str, str]`을 전달하면 해당 mapping만 사용하며 `os.environ`과 병합하거나
수정하지 않습니다.

주요 동작:

- `services=None`이면 지원 서비스 전체(`keycloak`, `postgres`, `sqlite`, `minio`, `milvus`, `ollama`, `langfuse`, `nats`)를 검증합니다.
- `services={...}`를 주면 지정한 서비스만 검증하고, 나머지 필드는 `None`으로 둡니다.
- 지원하지 않는 서비스 이름이 들어오면 `ConfigError`가 발생합니다.
- 선택된 서비스에서 필수 env가 없거나 타입/범위 검증에 실패하면 `ConfigError`가 발생합니다.
- 마지막에 `validate_runtime_security()`를 호출해 production 계열 보안 제약을 확인합니다.

### 3.3 `load_available_service_configs(env, *, services=None) -> ServiceConfigs`

명시한 후보 서비스 중 관련 prefix가 존재하는 서비스만 로딩합니다.

- 관련 키가 전혀 없는 서비스는 결과에서 `None`입니다.
- 관련 키가 하나라도 있지만 설정이 불완전하면 `ConfigError`가 발생합니다.
- 단순 prefix 존재를 유효한 설정으로 간주하지 않고 실제 config validation을 수행합니다.

PostgreSQL과 SQLite 같은 대안 서비스 후보를 전역 backend selector 없이 탐색할 때 사용할 수 있습니다.

예시:

```python
from docmesh_py_core import load_available_service_configs

settings = load_available_service_configs(
    {"SQLITE_PATH": ":memory:"},
    services={"postgres", "sqlite"},
)

assert settings.postgres is None
assert settings.sqlite is not None
```

### 3.4 서비스 조합 및 MinIO bucket 검증

- `validate_service_requirements(configs, required=..., one_of=...)`는 필수 서비스와 대안 서비스 그룹을 검증하고 현재 구성된 서비스 이름을 반환합니다.
- `require_minio_bucket(config)`은 제품이 bucket을 필수로 사용할 때 opt-in으로 검증하고 bucket 이름을 반환합니다.
- 두 helper의 실패는 구조화된 `ConfigError.issues`로 제공됩니다.

### 3.5 `ServiceConfigs`

서비스 설정 묶음 dataclass입니다.

필드:

- `common: CommonConfig`
- `keycloak: KeycloakConfig | None`
- `postgres: PostgresConfig | None`
- `sqlite: SqliteConfig | None`
- `minio: MinioConfig | None`
- `milvus: MilvusConfig | None`
- `ollama: OllamaConfig | None`
- `langfuse: LangfuseConfig | None`
- `nats: NatsConfig | None`

추가 속성:

- `docmesh_env -> str`: `common.env`를 그대로 반환하는 convenience property

각 optional 필드에는 `require_keycloak()`, `require_postgres()`, `require_sqlite()`, `require_minio()`, `require_milvus()`, `require_ollama()`, `require_langfuse()`, `require_nats()`가 대응합니다. 로딩된 config는 non-optional 타입으로 반환하고, 로딩되지 않은 서비스는 구조화된 `ConfigError`를 발생시킵니다.

## 4. Client creation API

서비스별 `create_*_client()` 함수는 direct-api-when-needed 경로입니다. 일반 애플리케이션 lifecycle 조립에는 `assemble_services()` 또는 `assemble_service_runtime()`을 우선 사용합니다.

모든 factory는 테스트와 특수 실행 환경을 위해 keyword-only `client_factory` hook을 제공합니다. NATS는 `connect_factory`, SQLite는 추가로 `configure_engine`을 지원합니다.

### Factory 확장 hook

- `client_factory`: 기본 SDK 생성자를 대체합니다. 기본 생성자와 같은 인자를 받고 호환 client를 반환해야 합니다.
- `connect_factory`: NATS 연결 함수를 대체합니다. `NatsConnectionBuilder.connect_kwargs`를 받아 client 또는 awaitable client를 반환해야 합니다.
- `configure_engine`: `(engine, SqliteConfig)`를 받아 SQLite pragma/listener 구성을 대체합니다.
- `engine_options`: PostgreSQL/SQLite의 SQLAlchemy 옵션을 확장합니다. `connect_args`는 기본값과 중첩 병합됩니다.
- `factory_overrides`: `assemble_service_runtime()`에서 서비스 이름별 `(config) -> client` factory를 대체합니다.

이 hook들은 mock 기반 단위 테스트나 명시적인 실행 환경 대체에 적합합니다. 반환 객체는 해당 서비스의 healthcheck와 lifecycle 계약을 충족해야 합니다.

### `create_keycloak_client(config: KeycloakConfig, *, client_factory=None) -> ServiceClientWrapper`

- 내부적으로 `KeycloakAuthService(config)`를 생성합니다.
- `check()` / `ping()`는 `fetch_access_token()`을 호출합니다.

### `create_postgres_client(config: PostgresConfig, *, engine_options=None, client_factory=None) -> ServiceClientWrapper[Engine]`

- SQLAlchemy engine을 생성합니다.
- `config.dsn`이 있으면 그 값을 사용하고, 없으면 host/db/user/password 조합으로 URL을 만듭니다.
- `check()` / `ping()`는 `SELECT 1`을 실행합니다.
- `close()`는 내부 `dispose()`를 호출합니다.
- `engine_options`는 SQLAlchemy `create_engine()` 옵션을 확장하며, 중첩된 `connect_args`는 기본 연결 옵션과 병합됩니다.

### `create_sqlite_client(config: SqliteConfig, *, engine_options=None, client_factory=None, configure_engine=None) -> ServiceClientWrapper[Engine]`

- SQLAlchemy engine을 생성합니다.
- `config.path == ":memory:"`를 지원합니다.
- `readonly`, `enable_wal`, `busy_timeout_ms`를 반영합니다.
- `check()` / `ping()`는 `SELECT 1`을 실행합니다.
- `close()`는 내부 `dispose()`를 호출합니다.
- `engine_options`와 `connect_args`를 추가하거나 기본값 위에 덮어쓸 수 있습니다.

### `create_minio_client(config: MinioConfig, *, client_factory=None) -> ServiceClientWrapper`

- `Minio(...)` 클라이언트를 즉시 생성합니다.
- `secure` 값은 `cert_check`에도 그대로 반영됩니다.
- `check()` / `ping()`는 `list_buckets()`를 호출합니다.

### `create_milvus_client(config: MilvusConfig, *, client_factory=None) -> ServiceClientWrapper`

- `MilvusClient(...)`를 생성합니다.
- `check()` / `ping()`는 `list_collections()`를 호출합니다.

### `create_ollama_client(config: OllamaConfig, *, client_factory=None) -> ServiceClientWrapper`

- `ollama.Client(...)`를 생성합니다.
- `check()` / `ping()`는 `ps()`를 호출합니다.

### `create_langfuse_client(config: LangfuseConfig, *, client_factory=None) -> ServiceClientWrapper | None`

- `config.enabled`가 `False`면 `None`을 반환합니다.
- 활성화 시 `Langfuse(...)`를 생성합니다.
- `check()` / `ping()`는 `auth_check()`를 호출합니다.
- `close()`는 `flush()`를 호출합니다.

### `create_nats_client(config: NatsConfig, *, connect_factory=None) -> NatsConnectionBuilder`

- 즉시 연결하지 않습니다.
- 실제 네트워크 연결은 `await builder.connect()` / `await builder.ping()` / `await builder.check()`에서 일어납니다.
- `ping()` / `check()`는 임시 연결 후 `flush()`를 수행하고, 끝나면 연결을 정리합니다.

예시:

```python
from docmesh_py_core import create_postgres_client, load_service_configs

settings = load_service_configs(services={"postgres"})
postgres = create_postgres_client(settings.require_postgres())

postgres.check()
postgres.close()
```

## 5. 공통 wrapper / helper API

### `ServiceClientWrapper`

서비스 클라이언트를 표준 인터페이스로 감싸는 `ServiceClientWrapper[T]` 제네릭 wrapper입니다.
underlying `client`의 타입을 보존합니다.

주요 메서드:

- `check()` / `ping()`
- `close()`
- `unwrap() -> T`
- `__getattr__()` 위임

동작 규칙:

- healthcheck 호출 중 예외가 발생하면 `ServiceClientWrapperError`로 변환합니다.
- 오류 메시지는 `mask_sensitive_value()`를 거쳐 민감정보를 숨깁니다.
- `close_fn`이 있으면 그 함수를 우선 호출하고, 없으면 내부 client의 `close()`를 찾습니다.
- SDK 생성자에 직접 전달할 수 없는 기본 resource/retry 값은 서비스별 typed `runtime_defaults`로 보존됩니다.

### `close_service_clients(clients: Iterable[Any]) -> None`

여러 wrapper/client에 대해 `close()`를 순회 호출합니다. `None` 값은 무시합니다.

### `async_close_service_clients(clients) -> None`

동기·비동기 `close()` 반환을 모두 수용합니다. 한 client의 종료 실패와 관계없이 나머지 client를 계속 정리하며, 실패가 있으면 전체 `ServiceCloseFailure`를 담은 `ServiceCloseError`를 발생시킵니다.

### `assemble_services(...) -> ServiceBundle`

mapping 기반 설정 로딩, available 서비스 탐지, required/one-of 검증, 클라이언트 생성과 선택적 startup healthcheck를 한 번에 수행합니다.

- `services`: 탐색할 서비스 후보
- `required`: 반드시 구성되어야 하는 서비스
- `one_of`: 각 그룹에서 하나 이상 필요한 대안 서비스 조합
- `engine_options`: `postgres`/`sqlite`별 SQLAlchemy 옵션
- `check_on_startup`: 생성 직후 healthcheck 실행 여부
- `parallel_healthchecks`: startup healthcheck 병렬 실행 여부

`ServiceBundle`은 `configs`, `clients`, `checks`, `selected_services`를 제공하며 `check()`, `close()`와 context manager를 지원합니다. startup healthcheck가 실패하면 이미 생성된 클라이언트를 닫은 뒤 예외를 다시 발생시킵니다.

NATS는 비동기 lifecycle이므로 동기 `ServiceBundle` 조립 대상에서 제외되며 `create_nats_client()`로 별도 생성해야 합니다.

### `assemble_service_runtime(...) -> ServiceRuntime`

NATS를 포함해 동기·비동기 서비스를 함께 조립하는 비동기 runtime API입니다. `await assemble_service_runtime(...)`으로 생성하며 `async with`를 지원합니다.

- sync/async health check를 한 API에서 실행
- 개별 health check timeout과 전체 timeout 지원
- 생성 또는 startup health check 실패 시 생성 완료 client rollback
- 종료 실패와 관계없이 모든 client에 best-effort cleanup 수행
- `factory_overrides`로 명시적인 서비스별 factory 대체 지원
- `runtime.require(name)`으로 생성된 client 조회

### `async_check_all_services(...)`

동기 함수와 awaitable health check를 모두 실행합니다. `parallel`, `timeout_seconds`, `overall_timeout_seconds`를 지원하며 required 실패 시 예외의 `result`와 `failures`에서 전체 상태를 확인할 수 있습니다.

### 주요 예외 및 cleanup 계약

| API | 주요 실패 | cleanup 계약 |
| --- | --- | --- |
| `load_service_configs()` | `ConfigError` | 클라이언트를 생성하지 않음 |
| `ServiceClientWrapper.check()` | `ServiceClientWrapperError` | 자동 종료하지 않음 |
| `check_all_services()` / `async_check_all_services()` | required 실패 시 `HealthCheckError` | 호출자가 lifecycle을 관리 |
| `assemble_services()` | 설정/생성/startup healthcheck 예외 | startup healthcheck 실패 시 생성한 client를 닫고 원래 예외를 다시 발생 |
| `assemble_service_runtime()` | 설정/생성/startup healthcheck 예외 | 이미 생성한 client를 best-effort로 닫고 원래 예외를 다시 발생 |
| `async_close_service_clients()` | 종료 실패 시 `ServiceCloseError` | 나머지 client 종료를 계속 시도하고 전체 실패를 보존 |

동기 `close_service_clients()`는 첫 종료 예외를 그대로 전파하므로 이후 항목까지 정리해야 한다면 `async_close_service_clients()`를 사용합니다.

### `check_all_services(service_checks, *, required_services=None, timer=time.perf_counter, parallel=False)`

서비스 헬스체크 함수를 모아 실행합니다.

반환값:

- `HealthCheckResult(ok: bool, services: list[ServiceHealthStatus])`

각 항목:

- `ServiceHealthStatus(service, ok, latency_ms, required=False, error=None, error_type=None)`
- `HealthCheckResult.to_dict()`와 `ServiceHealthStatus.to_dict()`는 JSON-friendly dict를 반환합니다.

규칙:

- `parallel=False`면 입력 순서대로 순차 실행합니다.
- `parallel=True`면 `ThreadPoolExecutor`로 병렬 실행하지만 반환 순서는 입력 순서를 유지합니다.
- required 서비스가 실패하면 `HealthCheckError`를 발생시킵니다.
- `HealthCheckError.status`는 첫 번째 required 서비스 실패 상태를 제공합니다.
- `HealthCheckError.failures`는 실패한 required 서비스 전체를 제공합니다.
- `HealthCheckError.result`는 optional 서비스를 포함한 전체 healthcheck 결과를 제공합니다.
- 오류 문자열은 마스킹됩니다.

### `mask_sensitive_value(value: str | None) -> str | None`

민감정보를 로그 친화적으로 마스킹합니다.

주요 동작:

- URL/DSN이면 사용자정보와 민감 query parameter를 마스킹합니다.
- raw token/secret/password 계열 문자열도 `***` 또는 `key=***` 형태로 변환합니다.
- 민감 키워드가 없는 일반 진단 문자열은 보존합니다.

### `retry_call(operation, *args, retry_on=..., max_attempts=..., base_delay_seconds=0.5, sleep=time.sleep, **kwargs)`

동기 함수 재시도 helper입니다.

- `max_attempts`는 1 이상이어야 합니다.
- 실패 간격은 지수 백오프(`0.5`, `1.0`, `2.0`, ...)입니다.
- 재시도 대상 예외만 다시 시도하고, 마지막 시도에서도 실패하면 원래 예외를 그대로 올립니다.

### `build_service_log_event(...) -> dict[str, Any]`

서비스 이벤트를 구조화된 dict로 생성합니다.

기본 키:

- `service`
- `operation`
- `outcome`
- optional: `host`, `latency_ms`, `retry_count`, `error`

`error`와 민감한 `extra` 필드는 마스킹됩니다.

### `configure_logging(*, level=None, log_path=None, force=False, env=None, env_key="DOCMESH_LOG_LEVEL") -> logging.Logger`

루트 로거를 설정합니다.

동작:

- `level`이 주어지면 그 값을 우선 사용합니다.
- 아니면 `DOCMESH_LOG_LEVEL` 환경변수를 읽습니다.
- 값이 없거나 빈 문자열이면 `INFO`를 사용합니다.
- 잘못된 로그 레벨이면 `ValueError`를 발생시킵니다.
- `log_path`가 있으면 부모 디렉터리를 생성한 뒤 파일 핸들러를 추가합니다.

## 6. Keycloak API

### `KeycloakAuthService(config: KeycloakConfig, ...)`

Keycloak 토큰 획득과 JWT 검증을 담당합니다.

주요 속성/메서드:

- `issuer`
- `token_endpoint`
- `jwks_endpoint`
- `fetch_access_token(...) -> AccessTokenResult`
- `extract_user_info(token: str) -> AuthenticatedUser`

### `fetch_access_token(*, scope=None, username=None, password=None) -> AccessTokenResult`

- 기본 grant type은 `client_credentials`입니다.
- password grant는 함수 인자를 우선 사용하고, 생략된 값은 `config.token_username`, `config.token_password`에서 가져옵니다.
- 두 입력 경로에도 username/password가 모두 갖춰지지 않으면 `KeycloakTokenConfigurationError`가 발생합니다.
- 일시적 장애(`KeycloakTokenTemporaryError`)는 `config.max_retries + 1`번까지 재시도합니다.
- 재시도 이벤트는 `build_service_log_event()` 형식으로 로깅됩니다.

### `extract_user_info(token: str) -> AuthenticatedUser`

- `Bearer <jwt>` 형식과 raw JWT 문자열을 모두 받습니다.
- `HS256`과 `RS256` 검증 경로를 지원합니다.
- `audience`가 설정되면 audience 검증을 수행하고, 없으면 audience 검증을 끕니다.
- RS256에서는 JWKS 캐시(`jwks_cache_ttl_seconds`)를 사용하고, 필요 시 refresh합니다.
- 반환 객체에는 `sub`, `preferred_username`, `email`, `given_name`, `family_name`, `name`, `realm_roles`, `client_roles`, `claims`가 포함됩니다.

### `KeycloakProvisioner(config: KeycloakConfig, *, admin_client)`

Realm / Client / Role 프로비저닝 orchestration을 담당합니다.

- `config.provisioning_dry_run=True`면 실제 변경 없이 `planned`만 채웁니다.
- 실제 실행 시 결과를 `created`, `updated`, `unchanged`, `failed`로 나눕니다.
- 선언에서 빠진 리소스를 자동 삭제하지 않습니다.

## 7. Runtime security API

### `validate_runtime_security(common, *, keycloak=None, minio=None, milvus=None) -> None`

현재 구현은 `CommonConfig.is_production`이 참인 환경에서 아래 제약만 검사합니다.

- `KEYCLOAK_VERIFY_SSL=false` 금지
- `MINIO_SECURE=false` 금지
- `MILVUS_SECURE=false` 금지

`is_production`은 `security_mode`가 명시되면 그 값을 사용하고, 아니면 소문자 환경 이름이 `production_aliases`에 포함되는지 확인합니다.
