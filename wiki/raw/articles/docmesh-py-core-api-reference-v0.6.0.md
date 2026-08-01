---
source_url: https://github.com/kyundae-kim/docmesh-py-core/wiki/API-Reference-v0.6.0
ingested: 2026-08-01
sha256: 30c67211392e75b9d3122a00ed9e7473d8ae91d52003a41219fdefceeee199fc
---
# docmesh-py-core 공개 API 레퍼런스

이 문서는 `docmesh_py_core` package root의 공개 API 전체를 추적한다. 소비자 사용 흐름은 [예제](./examples.md), 환경변수와 설정 규칙은 [설정 가이드](./config.md), 제품 요구사항은 [SRS](./srs.md)를 참고한다.

## 1. 공개 import 경계

신규 코드는 다음 경계를 사용한다.

```python
from docmesh_config import HealthcheckPolicy, RuntimePlan, Service
from docmesh_py_core import assemble_service_runtime, service_lifespan
```

- `docmesh_config`: 설정 모델, 진단, `RuntimePlan`, `Service`, `HealthcheckPolicy`의 canonical package다.
- `docmesh_py_core`: client factory, container, lifecycle, healthcheck, Keycloak domain API, 오류·관측성 helper의 canonical package다.
- `docmesh_py_core.config`, `docmesh_py_core.settings`, `docmesh_py_core.runtime_plan`, `docmesh_py_core.factories`는 기존 import 호환용 facade다.
- `docmesh_py_core` package root는 `docmesh_config` 심볼을 재노출하지 않는다.

## 2. 전체 공개 API inventory

아래 표의 각 행은 `docmesh_py_core.__all__`의 한 심볼과 정확히 대응한다. 정의 모듈은 구현 추적 위치이고, 상세 계약은 이 문서의 해당 절로 연결된다.

<!-- PUBLIC_API_INVENTORY_START -->
| 공개 심볼 | 종류 | 정의 모듈 | 상세 계약 |
| --- | --- | --- | --- |
| `AccessTokenResult` | dataclass | `keycloak` | [Keycloak 결과](#83-keycloak-결과와-오류) |
| `AuthenticatedUser` | dataclass | `keycloak` | [Keycloak 결과](#83-keycloak-결과와-오류) |
| `DocMeshError` | exception | `errors` | [오류 계층](#10-공개-오류-계층) |
| `EnvironmentRequirement` | dataclass | `service_catalog` | [서비스 카탈로그](#9-서비스-카탈로그와-문서-생성) |
| `HealthCheckError` | exception | `health` | [상태 확인](#6-상태-확인) |
| `HealthCheckResult` | dataclass | `health` | [상태 확인 결과](#62-결과와-timeout-계약) |
| `KeycloakAuthService` | class | `keycloak` | [Keycloak 인증](#81-keycloakauthservice) |
| `KeycloakProvisioner` | class | `keycloak` | [Keycloak 프로비저닝](#82-keycloakprovisioner) |
| `KeycloakTokenAuthenticationError` | exception | `keycloak` | [Keycloak 결과](#83-keycloak-결과와-오류) |
| `KeycloakTokenConfigurationError` | exception | `keycloak` | [Keycloak 결과](#83-keycloak-결과와-오류) |
| `KeycloakTokenError` | exception | `keycloak` | [Keycloak 결과](#83-keycloak-결과와-오류) |
| `KeycloakTokenTemporaryError` | exception | `keycloak` | [Keycloak 결과](#83-keycloak-결과와-오류) |
| `LifecycleEvent` | dataclass | `lifecycle` | [관측성](#7-관측성로깅재시도마스킹) |
| `LifecycleObserver` | type alias | `lifecycle` | [관측성](#7-관측성로깅재시도마스킹) |
| `MilvusRuntimeDefaults` | dataclass | `service_clients` | [runtime defaults](#53-runtime-defaults) |
| `MinioRuntimeDefaults` | dataclass | `service_clients` | [runtime defaults](#53-runtime-defaults) |
| `NatsConnectionBuilder` | class | `service_clients` | [NATS 소유권](#52-natsconnectionbuilder) |
| `OllamaRuntimeDefaults` | dataclass | `service_clients` | [runtime defaults](#53-runtime-defaults) |
| `ProvisioningResult` | dataclass | `keycloak` | [Keycloak 결과](#83-keycloak-결과와-오류) |
| `RuntimeHealthDescriptor` | dataclass | `service_containers` | [runtime descriptor](#44-runtimehealthdescriptor) |
| `RuntimeHealthDescriptorError` | exception | `errors` | [오류 계층](#10-공개-오류-계층) |
| `SERVICE_CATALOG` | immutable mapping | `service_catalog` | [서비스 카탈로그](#9-서비스-카탈로그와-문서-생성) |
| `ServiceAssemblyError` | exception | `errors` | [오류 계층](#10-공개-오류-계층) |
| `ServiceBundle` | class | `service_containers` | [container](#4-container와-조회-계약) |
| `ServiceClientCreationError` | exception | `errors` | [오류 계층](#10-공개-오류-계층) |
| `ServiceClientError` | exception | `service_clients` | [wrapper 오류](#51-serviceclientwrapper) |
| `ServiceClientProtocol` | protocol | `service_clients` | [protocol](#54-public-protocol) |
| `ServiceClientTypeError` | exception | `errors` | [조회 계약](#43-concrete-client-타입-검증) |
| `ServiceClientWrapper` | class | `service_clients` | [wrapper](#51-serviceclientwrapper) |
| `ServiceClientWrapperError` | exception | `service_clients` | [wrapper 오류](#51-serviceclientwrapper) |
| `ServiceCloseError` | exception | `service_containers` | [종료](#45-종료-계약) |
| `ServiceCloseFailure` | dataclass | `service_containers` | [종료](#45-종료-계약) |
| `ServiceContainerProtocol` | protocol | `service_clients` | [protocol](#54-public-protocol) |
| `ServiceDescriptor` | dataclass | `service_catalog` | [서비스 카탈로그](#9-서비스-카탈로그와-문서-생성) |
| `ServiceHandle` | protocol | `service_clients` | [protocol](#54-public-protocol) |
| `ServiceHealthStatus` | dataclass | `health` | [상태 확인 결과](#62-결과와-timeout-계약) |
| `ServiceLookupError` | exception | `errors` | [오류 계층](#10-공개-오류-계층) |
| `ServiceNotInitializedError` | exception | `errors` | [조회 계약](#42-getrequireget_client) |
| `ServiceNotSelectedError` | exception | `errors` | [조회 계약](#42-getrequireget_client) |
| `ServiceRuntime` | class | `service_containers` | [container](#4-container와-조회-계약) |
| `ServiceUnavailableError` | exception | `errors` | [오류 계층](#10-공개-오류-계층) |
| `ShutdownError` | exception | `errors` | [오류 계층](#10-공개-오류-계층) |
| `StartupCheckError` | exception | `errors` | [오류 계층](#10-공개-오류-계층) |
| `TokenValidationError` | exception | `keycloak` | [Keycloak 결과](#83-keycloak-결과와-오류) |
| `assemble_service_runtime` | async function | `service_assembly` | [비동기 bootstrap](#31-assemble_service_runtime) |
| `assemble_services` | function | `service_assembly` | [동기 bootstrap](#32-assemble_services) |
| `async_check_all_services` | async function | `health` | [상태 확인](#61-집계-api) |
| `async_close_service_clients` | async function | `service_containers` | [종료](#45-종료-계약) |
| `authenticated_runtime_plan` | function | `runtime_presets` | [preset](#34-runtime-plan-preset) |
| `build_service_log_event` | function | `observability` | [관측성](#7-관측성로깅재시도마스킹) |
| `check_all_services` | function | `health` | [상태 확인](#61-집계-api) |
| `close_service_clients` | function | `service_containers` | [종료](#45-종료-계약) |
| `configure_logging` | function | `function_logging` | [로깅](#71-configure_logging) |
| `create_empty_service_runtime` | function | `service_assembly` | [empty runtime](#33-create_empty_service_runtime) |
| `create_keycloak_client` | function | `service_factories` | [factory matrix](#5-service-factory와-wrapper) |
| `create_langfuse_client` | function | `service_factories` | [factory matrix](#5-service-factory와-wrapper) |
| `create_milvus_client` | function | `service_factories` | [factory matrix](#5-service-factory와-wrapper) |
| `create_minio_client` | function | `service_factories` | [factory matrix](#5-service-factory와-wrapper) |
| `create_nats_client` | function | `service_factories` | [factory matrix](#5-service-factory와-wrapper) |
| `create_ollama_client` | function | `service_factories` | [factory matrix](#5-service-factory와-wrapper) |
| `create_postgres_client` | function | `service_factories` | [factory matrix](#5-service-factory와-wrapper) |
| `create_sqlite_client` | function | `service_factories` | [factory matrix](#5-service-factory와-wrapper) |
| `generate_configuration_reference` | function | `service_catalog` | [문서 생성](#92-생성-api) |
| `generate_environment_template` | function | `service_catalog` | [문서 생성](#92-생성-api) |
| `mask_sensitive_value` | function | `security` | [마스킹](#74-mask_sensitive_value) |
| `production_runtime_plan` | function | `runtime_presets` | [preset](#34-runtime-plan-preset) |
| `retry_call` | function | `retry` | [재시도](#73-retry_call) |
| `serialize_error` | function | `error_utils` | [오류 직렬화](#72-serialize_error) |
| `service_lifespan` | async context manager | `service_assembly` | [lifespan](#35-service_lifespan) |
<!-- PUBLIC_API_INVENTORY_END -->

### 2.1 API → example → config → `.env.example` 추적표

`설정 없음`은 API가 process configuration을 읽지 않는다는 뜻이다. 오류나 결과 타입처럼 독립 설정이 없는 심볼도 관련 소비자 예제와 원인이 되는 설정 계약으로 추적한다.

| API family와 포함 심볼 | 소비자 예제 | 설정 계약 | `.env.example` |
| --- | --- | --- | --- |
| Assembly: `assemble_service_runtime`, `assemble_services`, `create_empty_service_runtime`, `service_lifespan` | [async](./examples.md#1-최소-sqlite-비동기-runtime), [sync](./examples.md#3-동기-clibatch), [empty](./examples.md#13-empty-runtime) | [로딩·선택](./config.md#1-설정-로딩-계약) | [공통 및 선택 서비스](../.env.example) |
| Preset: `authenticated_runtime_plan`, `production_runtime_plan` | [runtime policy](./examples.md#7-runtime-상태-정책-재실행) | [production 규칙](./config.md#3-production-보안-규칙) | [`DOCMESH_*`와 선택 서비스](../.env.example) |
| Container: `RuntimeHealthDescriptor`, `ServiceBundle`, `ServiceRuntime`, `ServiceContainerProtocol`, `ServiceCloseFailure`, `ServiceCloseError`, `close_service_clients`, `async_close_service_clients` | [lifespan](./examples.md#2-fastapi-lifespan과-readiness), [typed client](./examples.md#4-concrete-client-타입-검증) | [선택·자동 감지](./config.md#선택과-자동-감지) | [선택 서비스](../.env.example) |
| Client handle: `ServiceClientProtocol`, `ServiceHandle`, `ServiceClientWrapper`, `ServiceClientError`, `ServiceClientWrapperError` | [direct factory](./examples.md#5-direct-factory-sqlite), [NATS](./examples.md#6-nats-lazy-connection과-소유권) | [서비스별 wiring](./config.md#13-설정-api-추적표) | [서비스별 section](../.env.example) |
| Runtime defaults: `MinioRuntimeDefaults`, `MilvusRuntimeDefaults`, `OllamaRuntimeDefaults` | [factory 계약](#5-service-factory와-wrapper) | [MinIO](./config.md#7-minio), [Milvus](./config.md#8-milvus), [Ollama](./config.md#9-ollama) | [서비스별 section](../.env.example) |
| NATS: `NatsConnectionBuilder` | [persistent connection](./examples.md#6-nats-lazy-connection과-소유권) | [NATS](./config.md#11-nats) | [`NATS_*`](../.env.example) |
| Factory: `create_keycloak_client`, `create_postgres_client`, `create_sqlite_client`, `create_minio_client`, `create_milvus_client`, `create_ollama_client`, `create_langfuse_client`, `create_nats_client` | [direct SQLite](./examples.md#5-direct-factory-sqlite), [NATS](./examples.md#6-nats-lazy-connection과-소유권), [Keycloak](./examples.md#8-keycloak-token-획득과-jwt-사용자-정보) | [8개 서비스](./config.md#13-설정-api-추적표) | [8개 서비스 section](../.env.example) |
| Health: `HealthCheckError`, `HealthCheckResult`, `ServiceHealthStatus`, `check_all_services`, `async_check_all_services` | [readiness](./examples.md#2-fastapi-lifespan과-readiness), [policy](./examples.md#7-runtime-상태-정책-재실행) | `HealthcheckPolicy`; [환경 toggle 없음](./config.md#2-공통-설정과-별도-환경-helper) | 설정 없음 |
| Keycloak auth/provisioning: `KeycloakAuthService`, `KeycloakProvisioner`, `AccessTokenResult`, `AuthenticatedUser`, `ProvisioningResult`, `KeycloakTokenError`, `KeycloakTokenConfigurationError`, `KeycloakTokenAuthenticationError`, `KeycloakTokenTemporaryError`, `TokenValidationError` | [token/JWT](./examples.md#8-keycloak-token-획득과-jwt-사용자-정보), [provisioning](./examples.md#9-keycloak-provisioning) | [Keycloak](./config.md#4-keycloak) | [`KEYCLOAK_*`](../.env.example) |
| Lookup·assembly error: `DocMeshError`, `ServiceLookupError`, `ServiceNotSelectedError`, `ServiceNotInitializedError`, `ServiceClientTypeError`, `ServiceAssemblyError`, `ServiceClientCreationError`, `ServiceUnavailableError`, `StartupCheckError`, `ShutdownError`, `RuntimeHealthDescriptorError` | [typed lookup](./examples.md#4-concrete-client-타입-검증), [error response](./examples.md#11-오류를-api-응답으로-변환) | [선택·설정 진단](./config.md#1-설정-로딩-계약) | 직접 설정 없음 |
| Error/security utility: `serialize_error`, `mask_sensitive_value`, `retry_call` | [error response](./examples.md#11-오류를-api-응답으로-변환), [Keycloak retry](./examples.md#8-keycloak-token-획득과-jwt-사용자-정보) | [Keycloak retry 설정](./config.md#4-keycloak) | `KEYCLOAK_MAX_RETRIES`; 나머지는 설정 없음 |
| Lifecycle/logging: `LifecycleEvent`, `LifecycleObserver`, `build_service_log_event`, `configure_logging` | [observer/logging](./examples.md#10-로깅과-lifecycle-observer) | [공통 helper](./config.md#2-공통-설정과-별도-환경-helper) | `DOCMESH_LOG_LEVEL` |
| Catalog: `SERVICE_CATALOG`, `ServiceDescriptor`, `EnvironmentRequirement`, `generate_environment_template`, `generate_configuration_reference` | [catalog generation](./examples.md#12-서비스-카탈로그와-설정-문서-생성) | [전체 설정](./config.md) | [전체 key](../.env.example) |

### 2.2 호환 facade 공개 inventory

다음 module들은 기존 import를 유지하지만 새 코드의 canonical import 위치는 각각 `docmesh_config` 또는 `docmesh_py_core` package root다. facade는 추가 동작이나 별도 상태를 만들지 않는다.

| 호환 module | `__all__` 공개 심볼 | Canonical 위치 |
| --- | --- | --- |
| `docmesh_py_core.config` | `CommonConfig`, `ConfigError`, `ConfigIssue`, `DocmeshBaseSettings`, `EnvironmentDiagnosis`, `KeycloakConfig`, `KeycloakDiscoveryConfig`, `LangfuseConfig`, `MilvusConfig`, `MinioConfig`, `NatsConfig`, `OllamaConfig`, `PostgresConfig`, `SERVICE_CONFIG_TYPES`, `SUPPORTED_SERVICES`, `ServiceConfigs`, `ServiceConfigurationDiagnosis`, `SqliteConfig`, `diagnose_services`, `load_available_service_configs`, `load_service_configs`, `require_minio_bucket`, `validate_runtime_security`, `validate_service_requirements` | `docmesh_config` |
| `docmesh_py_core.config_diagnostics` | `diagnose_services`, `require_minio_bucket`, `validate_service_requirements` | `docmesh_config` |
| `docmesh_py_core.config_errors` | `ConfigError`, `ConfigIssue`, `EnvironmentDiagnosis`, `ServiceConfigurationDiagnosis` | `docmesh_config` |
| `docmesh_py_core.config_loading` | `ServiceConfigs`, `load_available_service_configs`, `load_service_configs`, `runtime_security_issues`, `validate_runtime_security` | `docmesh_config` |
| `docmesh_py_core.settings` | `CommonConfig`, `DocmeshBaseSettings`, `KeycloakConfig`, `KeycloakDiscoveryConfig`, `LangfuseConfig`, `MilvusConfig`, `MinioConfig`, `NatsConfig`, `OllamaConfig`, `PostgresConfig`, `SERVICE_CONFIG_TYPES`, `SUPPORTED_SERVICES`, `SettingsT`, `SqliteConfig` | `docmesh_config` |
| `docmesh_py_core.runtime_plan` | `HealthcheckPolicy`, `RuntimePlan`, `RuntimePlanMetadata`, `Service`, `ServiceSelection`, `StartupFailureMode`, `build_runtime_plan_metadata` | `docmesh_config` |
| `docmesh_py_core.factories` | `EnvironmentRequirement`, `MilvusRuntimeDefaults`, `MinioRuntimeDefaults`, `NatsConnectionBuilder`, `OllamaRuntimeDefaults`, `RuntimeHealthDescriptor`, `SERVICE_CATALOG`, `ServiceBundle`, `ServiceClientError`, `ServiceClientProtocol`, `ServiceClientWrapper`, `ServiceClientWrapperError`, `ServiceCloseError`, `ServiceCloseFailure`, `ServiceContainerProtocol`, `ServiceDescriptor`, `ServiceHandle`, `ServiceRuntime`, `assemble_service_runtime`, `assemble_services`, `async_close_service_clients`, `close_service_clients`, `create_empty_service_runtime`, `create_keycloak_client`, `create_langfuse_client`, `create_milvus_client`, `create_minio_client`, `create_nats_client`, `create_ollama_client`, `create_postgres_client`, `create_sqlite_client`, `generate_configuration_reference`, `generate_environment_template`, `service_lifespan` | `docmesh_py_core` package root |

## 3. Bootstrap과 lifecycle

### 3.1 `assemble_service_runtime`

```text
async def assemble_service_runtime(
    *,
    plan: RuntimePlan,
    observer: LifecycleObserver | None = None,
) -> ServiceRuntime
```

선택 설정을 프로세스 환경에서 한 번 진단·로드하고 client를 생성한 뒤 비동기 runtime을 반환한다. 생성 또는 startup healthcheck 실패 시 이미 생성된 client를 best-effort로 닫는다. preflight diagnosis는 성공한 runtime과 구조화 오류에 보존된다.

- NATS를 포함할 수 있는 표준 bootstrap이다.
- `plan.healthcheck.on_startup=True`이면 `ServiceRuntime.check_with_policy()`를 실행한다.
- rollback 종료 실패는 원래 예외를 교체하지 않고 exception note에 추가된다.
- 설정/plan 타입은 `docmesh_config`가 소유한다.

### 3.2 `assemble_services`

```text
def assemble_services(
    *,
    plan: RuntimePlan,
    observer: LifecycleObserver | None = None,
) -> ServiceBundle
```

동기 서비스만 조립한다. NATS처럼 async lifecycle인 서비스 또는 timeout이 지정된 동기 startup healthcheck는 client 생성 전에 `ConfigError`로 거부한다. 반환된 bundle은 context manager로 닫거나 `close()`를 직접 호출한다.

### 3.3 `create_empty_service_runtime`

```text
def create_empty_service_runtime() -> ServiceRuntime
```

설정 loader, factory, 네트워크를 호출하지 않는 canonical empty runtime을 반환한다. 빈 상태 확인은 `{"ok": True, "services": []}`이며 `close()`는 멱등적이다. 빈 `RuntimePlan`을 허용하는 API가 아니라 별도 경로다.

### 3.4 Runtime plan preset

```text
def production_runtime_plan(services: Iterable[Service | str]) -> RuntimePlan
def authenticated_runtime_plan(
    services: Iterable[ServiceSelection | Service | str] = (),
    *,
    healthcheck: HealthcheckPolicy | None = None,
) -> RuntimePlan
```

- `production_runtime_plan`: 모든 입력 서비스를 required로 만들고 병렬 startup check, 서비스별 10초, 전체 30초, 3회 시도, 1초 간격, `FAIL`을 적용한다.
- `authenticated_runtime_plan`: Keycloak을 required로 추가한다. 다른 `ServiceSelection`의 required/optional 의미는 유지하고 Keycloak 중복은 제거한다.

### 3.5 `service_lifespan`

```text
async with service_lifespan(plan=plan, observer=observer) as runtime:
    ...
```

framework-neutral async context manager다. 현재 event loop를 사용하며 새 loop를 만들거나 종료하지 않는다. body의 정상 종료와 예외 종료 모두에서 `await runtime.close()`를 수행한다. 복사 가능한 FastAPI 예제는 [예제 문서](./examples.md#2-fastapi-lifespan과-readiness)를 참고한다.

## 4. Container와 조회 계약

### 4.1 `ServiceBundle`과 `ServiceRuntime`

| 기능 | `ServiceBundle` | `ServiceRuntime` |
| --- | --- | --- |
| key 타입 | `str` | `docmesh_config.Service` |
| context manager | `with` | `async with` |
| `check` | sync, 선택적 thread 병렬 | async, sync/async callback·timeout 지원 |
| `close` | sync | async |
| startup 결과 | `startup_healthcheck_result` | `startup_healthcheck_result` |
| diagnosis | `diagnosis` | `diagnosis` |

두 container 모두 `configs`, `clients`, `selected_services`, `required_services`, `checks`를 공개한다. 직접 생성도 가능하지만 일반 소비자는 assembly API를 사용해야 descriptor·rollback 불변조건이 보장된다.

### 4.2 `get`·`require`·`get_client`

| 메서드 | 미선택 | 선택됐지만 client 없음 | 성공 |
| --- | --- | --- | --- |
| `get(service)` | `None` | `None` | lifecycle handle |
| `require(service)` | `ServiceNotSelectedError` | `ServiceNotInitializedError` | lifecycle handle |
| `get_client(service)` | `ConfigError` | `ConfigError` | lifecycle handle |

`require()`가 선택/초기화 상태를 구분하는 canonical 조회 API다. `get_client()`는 호환 API이며 두 실패를 같은 `ConfigError`로 보고한다.

### 4.3 Concrete client 타입 검증

```python
concrete = runtime.require_client(Service.POSTGRES, Engine)
```

`require_client(service, expected_type)`은 `ServiceClientWrapper`를 `unwrap()`한 뒤 `isinstance`를 검사한다. wrapper가 아닌 handle은 handle 자체를 검사한다. 불일치 시 `ServiceClientTypeError`가 발생한다.

### 4.4 `RuntimeHealthDescriptor`

```text
RuntimeHealthDescriptor(
    service: Service,
    check: Callable[[], object],
    required: bool = False,
)
```

immutable descriptor다. runtime 생성 시 서비스 중복, callback 호출 가능 여부, 선택·초기화 여부, handle의 `service_name`, required flag, 모든 client/required 서비스의 descriptor 존재를 검증한다. 위반 시 `RuntimeHealthDescriptorError`가 발생한다.

### 4.5 종료 계약

```text
def close_service_clients(clients: Iterable[Any]) -> None
async def async_close_service_clients(clients: Iterable[Any]) -> None
```

- 모든 client의 종료를 시도한 뒤 실패를 `ServiceCloseFailure(client, error)`로 모은다.
- 하나 이상 실패하면 `ServiceCloseError.failures`에 전체 실패를 담아 발생시킨다.
- async 버전은 sync/async `close()`를 모두 처리한다. sync 버전에 awaitable client를 전달하지 않는다.
- `ServiceBundle.close()`와 `ServiceRuntime.close()`는 한 번 종료된 뒤 멱등적이다.

## 5. Service factory와 wrapper

모든 factory는 이미 검증된 `docmesh_config` 설정 객체를 받는다. test 전용 factory override나 임의 kwargs는 공개하지 않는다.

| Factory | 반환 | 상태 확인 | 종료/소유권 |
| --- | --- | --- | --- |
| `create_keycloak_client(KeycloakConfig)` | `ServiceClientWrapper[KeycloakAuthService]` | token 획득; 기본 password grant는 자격증명 필요 | auth client에 `close`가 없어 no-op |
| `create_postgres_client(PostgresConfig)` | `ServiceClientWrapper[Engine]` | `SELECT 1` | `Engine.dispose()` |
| `create_sqlite_client(SqliteConfig)` | `ServiceClientWrapper[Engine]` | `SELECT 1` | `Engine.dispose()` |
| `create_minio_client(MinioConfig)` | `ServiceClientWrapper[Minio]` | `list_buckets()` | SDK `close()`가 있으면 호출 |
| `create_milvus_client(MilvusConfig)` | `ServiceClientWrapper[MilvusClient]` | `list_collections()` | SDK `close()` |
| `create_ollama_client(OllamaConfig)` | `ServiceClientWrapper[ollama.Client]` | `ps()` | SDK `close()`가 있으면 호출 |
| `create_langfuse_client(LangfuseConfig)` | `ServiceClientWrapper[Langfuse] \| None` | `auth_check()` | `flush()`; `enabled=false`이면 `None` |
| `create_nats_client(NatsConfig)` | `NatsConnectionBuilder` | async 임시 연결·flush·종료 | builder 자체 close는 no-op |

설정별 실제 wiring은 [설정 가이드](./config.md)에 기록한다.

### 5.1 `ServiceClientWrapper`

```text
ServiceClientWrapper(
    client,
    healthcheck,
    service_name="unknown",
    close_fn=None,
    runtime_defaults=None,
)
```

- `unwrap()`은 concrete client를 반환한다.
- `ping()`과 `check()`는 같은 동기 health callback을 호출한다.
- callback 실패는 secret-safe `ServiceClientWrapperError`로 변환한다.
- `close_fn`이 있으면 우선 호출하고, 없으면 concrete client의 `close()`를 호출한다.
- 알 수 없는 속성은 concrete client로 전달한다.

`ServiceClientError`는 service, operation, error_type, masked error를 보존하는 일반 client operation 오류다. `ServiceClientWrapperError`는 wrapper healthcheck 전용 하위 타입이다.

### 5.2 `NatsConnectionBuilder`

```text
async def connect(self) -> Any
async def ping(self) -> Any
async def check(self) -> Any
async def close(self) -> None
```

- 생성 시 연결하지 않는다.
- `connect()`는 persistent NATS connection을 반환하며 **호출자가 drain/close를 소유**한다.
- `ping()`/`check()`는 임시 연결을 열어 가능한 경우 `flush()`하고 `drain()` 또는 `close()`한 뒤 반환한다. 반환값을 live connection으로 사용하면 안 된다.
- `connect_kwargs`는 SDK에 전달할 정규화된 옵션을 반환한다. credential 값이 포함될 수 있으므로 로그에 기록하지 않는다.
- builder `close()`는 아무 자원도 소유하지 않아 no-op이다.

### 5.3 Runtime defaults

일부 설정은 SDK constructor가 아니라 wrapper의 `runtime_defaults`에 보존된다.

- `MinioRuntimeDefaults(bucket, request_timeout_seconds, max_retries)`
- `MilvusRuntimeDefaults(collection, connect_timeout_seconds, max_retries, secure)`
- `OllamaRuntimeDefaults(generation_model, embedding_model, max_retries)`

### 5.4 Public protocol

- `ServiceClientProtocol`: runtime-checkable `check()`/`close()` 계약.
- `ServiceHandle`: `ServiceClientProtocol` + `service_name`.
- `ServiceContainerProtocol`: `configs`, `selected_services`, 조회, 상태 확인, 종료의 최소 소비자 계약.

## 6. 상태 확인

### 6.1 집계 API

```text
def check_all_services(
    service_checks: Mapping[str, Callable[[], object]],
    *,
    required_services: Set[str] | None = None,
    timer=time.perf_counter,
    parallel: bool = False,
) -> HealthCheckResult

async def async_check_all_services(
    service_checks: Mapping[str, Callable[[], object | Awaitable[object]]],
    *,
    required_services: Set[str] | None = None,
    timer=time.perf_counter,
    parallel: bool = False,
    timeout_seconds: float | None = None,
    overall_timeout_seconds: float | None = None,
) -> HealthCheckResult
```

입력 mapping 순서가 결과 순서다. sync 병렬 모드는 thread pool을 사용한다. async API는 coroutine callback과 thread에서 실행할 sync callback을 함께 처리한다.

### 6.2 결과와 timeout 계약

- `ServiceHealthStatus(service, ok, latency_ms, required=False, error=None, error_type=None)`
- `HealthCheckResult(ok, services)`
- 두 타입 모두 `to_dict()`를 제공한다.
- 하나라도 실패하면 `HealthCheckResult.ok=False`다.
- optional 실패는 결과로 반환되지만 required 실패는 전체 결과를 가진 `HealthCheckError`를 발생시킨다.
- 서비스별 `timeout_seconds`는 해당 서비스의 실패 status로 변환된다.
- `overall_timeout_seconds` 초과는 partial result 없이 `asyncio.TimeoutError`가 전파될 수 있다.

`ServiceRuntime.check_with_policy(policy)`는 `on_startup` 값과 관계없이 즉시 실행하고 runtime을 닫지 않는다. `REPORT`는 최종 required 실패 결과를 반환하며 `FAIL`은 `HealthCheckError`를 유지한다.

## 7. 관측성·로깅·재시도·마스킹

### 7.1 `configure_logging`

```text
def configure_logging(
    *,
    level: int | str | None = None,
    log_path: str | Path | None = None,
    force: bool = False,
    env: Mapping[str, str] | None = None,
    env_key: str = "DOCMESH_LOG_LEVEL",
) -> logging.Logger
```

우선순위는 명시적 `level` > `env[env_key]` 또는 `os.environ` > `INFO`다. stderr handler를 항상 만들고 `log_path`가 있으면 부모 디렉터리와 UTF-8 file handler를 추가한다. 잘못된 환경 로그 레벨은 `ValueError`다.

### 7.2 `serialize_error`

```text
def serialize_error(error: BaseException) -> dict[str, object]
```

최소 `error_type`, masked `message`, `service`, `reason_code`, `remediation`을 반환한다. `issues`, `result`, `failures`, `status`, `diagnosis`가 있으면 JSON-safe `details`로 보존한다. shutdown failure의 raw client 객체는 제외한다.

### 7.3 `retry_call`

```text
def retry_call(
    operation,
    *args,
    retry_on: tuple[type[BaseException], ...],
    max_attempts: int,
    base_delay_seconds: float = 0.5,
    sleep=time.sleep,
    **kwargs,
)
```

지정한 예외만 지수 backoff로 재시도한다. 지연은 `base_delay_seconds * 2 ** (attempt - 1)`이다. 최종 예외를 그대로 다시 발생시키며 `max_attempts < 1`이면 `ValueError`다.

### 7.4 `mask_sensitive_value`

```text
def mask_sensitive_value(raw: str | None) -> str | None
```

URL userinfo와 민감 query parameter, Bearer/JWT 형태, password/secret/token/key marker 뒤 값을 마스킹한다. 임의 문자열의 모든 secret을 탐지하는 DLP 기능은 아니다.

### 7.5 구조화 event

```text
def build_service_log_event(
    *, service, operation, outcome, host=None,
    latency_ms=None, retry_count=None, error=None, extra=None,
) -> dict[str, Any]
```

`error`와 민감 key 이름을 가진 `extra` 값은 마스킹한다. `host`는 자동 정제하지 않으므로 secret-safe 값만 전달한다.

`LifecycleEvent(operation, outcome, service=None, latency_ms=None, retry_count=None, error=None)`는 `to_dict()`를 제공한다. `LifecycleObserver = Callable[[LifecycleEvent], None]`이며 observer 예외는 primary lifecycle 결과를 바꾸지 않는다.

## 8. Keycloak domain API

### 8.1 `KeycloakAuthService`

```text
KeycloakAuthService(
    config: KeycloakConfig,
    *,
    http_client=None,
    verification_key=None,
    allowed_algorithms=None,
    logger=None,
    event_logger=None,
    timer=time.perf_counter,
    sleep=time.sleep,
    current_time=time.time,
)
```

주요 API:

- `fetch_access_token(*, scope=None, username=None, password=None) -> AccessTokenResult`
- `extract_user_info(token: str) -> AuthenticatedUser`
- `issuer`, `token_endpoint`, `jwks_endpoint` property

기본 JWT 허용 목록은 `RS256`이다. `HS256`은 명시적 `verification_key`와 함께 direct API에서만 선택할 수 있다. token header 알고리즘은 고정 허용 목록에 포함돼야 하며 issuer·expiration·서명, 설정된 경우 audience를 검증한다. RS256은 JWKS cache와 signature 실패 시 refresh를 지원한다.

password grant의 call-time username/password가 설정값보다 우선한다. `client_credentials`는 username/password를 사용하지 않는다. 일시 오류만 `max_retries + 1`회까지 재시도한다.

### 8.2 `KeycloakProvisioner`

```text
KeycloakProvisioner(config: KeycloakConfig, *, admin_client).provision() -> ProvisioningResult
```

`admin_client`는 `ensure_realm`, `ensure_client`, `ensure_realm_role`, `ensure_client_role`을 구현해야 한다. `KeycloakProvisioner`는 `config.provisioning_enabled`를 실행 gate로 검사하지 않으므로 호출자가 확인해야 한다. dry-run은 원격 호출 없이 `planned`만 채운다. 각 작업 실패는 masked 문자열로 `failed`에 누적하고 나머지 작업을 계속하며, 호출자는 비어 있지 않은 `result.failed`를 처리해야 한다. 선언에서 빠진 원격 리소스를 삭제하지 않는다.

### 8.3 Keycloak 결과와 오류

- `AccessTokenResult`: `access_token`, `token_type`, `expires_in`, optional `refresh_token`, `scope`. token 원문을 출력·로그하지 않는다.
- `AuthenticatedUser`: `sub`, username/email/name fields, `realm_roles`, `client_roles`, raw `claims`.
- `ProvisioningResult`: `created`, `updated`, `unchanged`, `failed`, `planned`, `dry_run`.
- `KeycloakTokenConfigurationError`: grant credential, algorithm/key 등 로컬 구성 오류.
- `KeycloakTokenAuthenticationError`: HTTP 400/401/403 인증 실패.
- `KeycloakTokenTemporaryError`: network, 408, 429, 5xx 등 재시도 가능한 실패.
- `KeycloakTokenError`: 그 밖의 token endpoint/response 오류의 기반 타입.
- `TokenValidationError`: JWT 형식·서명·claim·JWKS·algorithm 검증 실패.

## 9. 서비스 카탈로그와 문서 생성

### 9.1 Metadata

`SERVICE_CATALOG`은 `Service -> ServiceDescriptor`의 immutable mapping이다.

- `ServiceDescriptor`: `service`, `config_type`, `factory`, `supports_sync_runtime`, `order`, `environment`.
- `environment_variables()`: 전체 `EnvironmentRequirement` tuple.
- `required_environment()`: required 또는 conditional required 항목.
- `EnvironmentRequirement`: `key`, `secret`, `required_when`, `required`, `default`, `production_constraint`.

metadata는 환경변수 값을 읽지 않고 secret 원문을 담지 않는다.

### 9.2 생성 API

- `generate_environment_template() -> str`: catalog 순서로 deterministic `KEY=value` template 생성.
- `generate_configuration_reference() -> str`: required/secret/default/production constraint Markdown 표 생성.

저장소의 [`.env.example`](../.env.example)은 common/logging 변수와 사용 안내를 추가한 소비자용 template이고, catalog 생성 결과는 service 설정 metadata의 기계적 source다.

## 10. 공개 오류 계층

```text
DocmeshConfigError (docmesh_config)
├── DocMeshError
│   ├── ServiceLookupError
│   │   ├── ServiceNotSelectedError
│   │   ├── ServiceNotInitializedError
│   │   └── ServiceClientTypeError
│   ├── ServiceAssemblyError
│   │   └── ServiceClientCreationError
│   ├── ServiceUnavailableError
│   │   ├── ServiceClientError
│   │   │   └── ServiceClientWrapperError
│   │   └── StartupCheckError
│   │       └── HealthCheckError
│   └── ShutdownError
│       └── ServiceCloseError
└── ConfigurationError
    └── RuntimeHealthDescriptorError
```

Keycloak의 `KeycloakToken*Error`와 `TokenValidationError`는 별도 `RuntimeError` 계층이다. 모든 공개 SDK 오류는 응답 경계에서 `serialize_error()`로 정규화할 수 있다.
