---
source_url: https://github.com/kyundae-kim/docmesh-config/wiki/API-Reference-v0.1.0
ingested: 2026-08-01
sha256: 8c59c7d5e2f05f84416a6100292f577a908e3e076bbacf943ceabf0338fd8fdd
---
# docmesh-config 공개 API 레퍼런스

| 항목 | 내용 |
| --- | --- |
| 기준 버전 | 0.1.0 |
| 최종 갱신일 | 2026-07-31 |
| 안정 API 기준 | `docmesh_config.__all__` |
| 추적 요구사항 | [SRS NFR-8](./srs.md#5-비기능-요구사항) |
| 설정 레퍼런스 | [config.md](./config.md) |
| 실행 예제 | [example.md](./example.md) |

## 1. 사용 원칙

공개 API는 package root에서 가져오는 것을 권장한다.

```python
from docmesh_config import RuntimePlan, Service, diagnose_services
```

`docmesh_config.config`는 설정 모델·로딩·진단에 한정된 호환 facade다. package root에만 있는 runtime plan, metadata, 보안 helper와 일부 기반 오류 타입이 필요하면 package root를 사용한다.

설정 모델은 생성자 값이 아니라 프로세스 환경변수에서만 값을 읽는다. 환경변수 목록과 제약은 [설정 레퍼런스](./config.md)를 따른다.

## 2. 공개 심볼 추적표

다음 표는 `docmesh_config.__all__`의 모든 심볼을 추적한다.

| 공개 심볼 | 종류 | 정의 모듈 | 주요 요구사항 | 설명 |
| --- | --- | --- | --- | --- |
| `CommonConfig` | 설정 모델 | `settings` | FR-1.1, FR-1.10, SR-2 | 실행 환경과 production 판정 설정 |
| `ConfigError` | 오류 | `config_errors` | FR-2.2, FR-4.1 | 구조화된 `ConfigIssue` 목록을 포함하는 통합 설정 오류 |
| `ConfigIssue` | 데이터 타입 | `config_errors` | FR-2.2, FR-4.3 | 서비스·환경 키·원인·조치가 포함된 secret-safe 문제 |
| `ConfigurationError` | 오류 | `errors` | FR-4.1 | 설정과 runtime plan 오류의 기반 타입 |
| `DocmeshBaseSettings` | 설정 기반 클래스 | `settings` | FR-1.1~FR-1.3, FR-4.5 | 환경 전용 로딩과 secret-safe 직렬화의 기반 클래스 |
| `DocmeshConfigError` | 오류 | `errors` | FR-4.1 | 모든 안정적인 라이브러리 오류의 최상위 타입 |
| `EnvironmentDiagnosis` | 데이터 타입 | `config_errors` | FR-2.1~FR-2.11 | 전체 환경 진단 결과 |
| `HealthcheckPolicy` | 데이터 타입 | `runtime_plan` | FR-3.2, FR-3.5 | runtime 계층이 소비할 startup 상태 확인 정책 메타데이터 |
| `InvalidRuntimePlanError` | 오류 | `errors` | FR-3.1 | 비어 있거나 모순된 plan 입력 오류 |
| `KeycloakConfig` | 설정 모델 | `settings` | FR-1.7, SR-3 | 전체 Keycloak 설정 |
| `KeycloakDiscoveryConfig` | 설정 모델 | `settings` | FR-1.7 | Keycloak URL·realm discovery용 최소 설정 |
| `LangfuseConfig` | 설정 모델 | `settings` | FR-1.7 | Langfuse tracing 설정 |
| `MilvusConfig` | 설정 모델 | `settings` | FR-1.11, FR-4.5 | `MILVUS_ENDPOINT` 기반 Milvus 설정 |
| `MinioConfig` | 설정 모델 | `settings` | FR-1.7, FR-2.10 | MinIO 연결 및 선택적 bucket 설정 |
| `NatsConfig` | 설정 모델 | `settings` | FR-1.7 | NATS 서버·인증·재연결 설정 |
| `OllamaConfig` | 설정 모델 | `settings` | FR-1.7, SR-3 | Ollama host·모델·timeout 설정 |
| `PostgresConfig` | 설정 모델 | `settings` | FR-1.3, FR-1.7 | PostgreSQL 연결·pool 설정 |
| `RuntimePlan` | 데이터 타입 | `runtime_plan` | FR-2.3~FR-2.5, FR-3.1 | 선택·필수·대안 서비스와 startup 정책을 묶는 immutable plan |
| `RuntimePlanMetadata` | 데이터 타입 | `plan_metadata` | FR-3.1~FR-3.7 | 진단과 plan을 결합한 secret-safe 메타데이터 |
| `SERVICE_CONFIG_TYPES` | 상수 mapping | `settings` | FR-1.12 | `Service`에서 설정 타입으로의 read-only registry |
| `SUPPORTED_SERVICES` | 상수 set | `settings` | FR-1.4, FR-1.12 | 지원 서비스 이름의 `frozenset[str]` |
| `Service` | enum | `runtime_plan` | FR-1.12, FR-3.1 | 지원 서비스의 canonical key |
| `ServiceConfigs` | 데이터 타입 | `config_loading` | FR-1.4, FR-1.12 | common 설정과 선택적으로 로드된 8개 서비스 설정 bundle |
| `ServiceConfigurationDiagnosis` | 데이터 타입 | `config_errors` | FR-2.1, FR-2.7, FR-2.11 | 단일 서비스의 상태·문제·적용 기본값 |
| `ServiceSelection` | 데이터 타입 | `runtime_plan` | FR-2.3, FR-3.1 | 서비스와 required 여부의 immutable 쌍 |
| `StartupFailureMode` | enum | `runtime_plan` | FR-3.2, FR-3.5 | startup 상태 확인 실패 처리 메타데이터 (`fail`, `report`) |
| `SqliteConfig` | 설정 모델 | `settings` | FR-1.8~FR-1.9 | SQLite path·WAL·timeout 설정 |
| `UnknownServiceError` | 오류 | `errors` | FR-1.4 | 지원하지 않는 서비스 key 오류 |
| `build_runtime_plan_metadata` | 함수 | `plan_metadata` | FR-3.1~FR-3.7 | plan과 환경 진단을 결합해 metadata 생성 |
| `diagnose_services` | 함수 | `config_diagnostics` | FR-2.1~FR-2.11 | 외부 연결 없이 선택 서비스 진단 |
| `load_available_service_configs` | 함수 | `config_loading` | FR-1.4~FR-1.5 | 관련 환경변수가 존재하는 선택 후보만 로드 |
| `load_service_configs` | 함수 | `config_loading` | FR-1.1~FR-1.7 | 선택 서비스 설정을 환경에서 로드 |
| `mask_sensitive_value` | 함수 | `security` | FR-4.3~FR-4.6, SR-4~SR-7 | URL·token·assignment 형태의 민감값 마스킹 |
| `require_minio_bucket` | 함수 | `config_diagnostics` | FR-2.5, FR-2.10 | MinIO bucket 반환 또는 구조화 오류 발생 |
| `validate_runtime_security` | 함수 | `config_loading` | FR-2.6, SR-2~SR-3 | production transport 설정을 검증하고 실패 시 오류 발생 |
| `validate_service_requirements` | 함수 | `config_diagnostics` | FR-2.3~FR-2.4 | 로드된 bundle의 필수·대안 서비스 요구 검증 |

## 3. 설정 로딩 API

### `load_service_configs`

```python
def load_service_configs(
    *, services: set[str | Service] | None = None
) -> ServiceConfigs: ...
```

- `services` 지정 시 해당 서비스는 반드시 완전하고 유효해야 한다.
- 생략 시 환경변수가 존재하는 서비스를 optional 후보로 감지해 로드한다.
- production transport 정책을 위반하면 `ConfigError`가 발생한다.
- 외부 서비스 연결이나 client 생성을 수행하지 않는다.

### `load_available_service_configs`

```python
def load_available_service_configs(
    *, services: set[str | Service] | None = None
) -> ServiceConfigs: ...
```

선택한 후보 중 인식 가능한 환경변수가 존재하는 서비스만 로드한다. 환경변수 일부만 존재하면 해당 서비스를 건너뛰지 않고 `ConfigError`를 발생시킨다.

### `ServiceConfigs`

필드: `common`, `keycloak`, `postgres`, `sqlite`, `minio`, `milvus`, `ollama`, `langfuse`, `nats`.

- `docmesh_env`: `common.env` 편의 property
- `require_keycloak()` → `KeycloakConfig`
- `require_postgres()` → `PostgresConfig`
- `require_sqlite()` → `SqliteConfig`
- `require_minio()` → `MinioConfig`
- `require_milvus()` → `MilvusConfig`
- `require_ollama()` → `OllamaConfig`
- `require_langfuse()` → `LangfuseConfig`
- `require_nats()` → `NatsConfig`

`require_*()`는 설정이 로드되지 않았으면 `error_type="service_not_loaded"`인 `ConfigError`를 발생시킨다.

### 설정 모델 공통 계약

`CommonConfig`, `KeycloakDiscoveryConfig`, `KeycloakConfig`, `PostgresConfig`, `SqliteConfig`, `MinioConfig`, `MilvusConfig`, `OllamaConfig`, `LangfuseConfig`, `NatsConfig`는 모두 `DocmeshBaseSettings`를 상속한다.

- 인자 없이 생성하며 프로세스 환경변수만 읽는다.
- 생성자 keyword 값은 `TypeError`로 거부한다.
- 환경변수 key는 대소문자를 구분하지 않는다.
- 공백 문자열은 미설정으로 취급한다.
- `model_dump()`와 `model_dump_json()`은 민감값을 마스킹한다.
- `env_key(field_name)`은 필드의 canonical 환경변수 이름을 반환한다.
- `has_environment_values()`는 해당 모델이 인식하는 환경변수 존재 여부를 반환한다.

## 4. 진단 API

### `diagnose_services`

```python
def diagnose_services(
    *,
    plan: RuntimePlan,
    selection_mode: Literal["auto", "explicit", "strict"] = "auto",
) -> EnvironmentDiagnosis: ...
```

상태는 서비스별로 `absent`, `complete`, `partial`, `invalid` 중 하나다. `strict` 모드는 대안 그룹에서 둘 이상이 구성되면 `ambiguous_service_alternative` 문제를 추가한다.

### `validate_service_requirements`

```python
def validate_service_requirements(
    configs: ServiceConfigs,
    *,
    required: set[str | Service] | None = None,
    one_of: tuple[set[str | Service], ...] = (),
) -> frozenset[str]: ...
```

요구사항이 충족되면 구성된 서비스 이름을 반환하고, 아니면 `ConfigError`를 발생시킨다.

### `require_minio_bucket`

```python
def require_minio_bucket(config: MinioConfig | None) -> str: ...
```

bucket이 있으면 이름을 반환한다. 없으면 `MINIO_BUCKET`을 식별하는 `ConfigError`를 발생시킨다.

### 진단 데이터 타입

- `ConfigIssue`: `service`, `env_key`, `reason`, `error_type`, `remediation`, `severity`; `to_dict()` 제공
- `ServiceConfigurationDiagnosis`: `service`, `state`, `issues`, `applied_defaults`; `to_dict()` 제공
- `EnvironmentDiagnosis`: `services`, `selected_services`, `configured_services`, `issues`, `warnings`; `ok` property와 `to_dict()` 제공

`applied_defaults`와 `services`는 생성 후 변경할 수 없다. 직렬화 결과는 호출마다 새로운 컨테이너다.

## 5. Runtime plan API

### `Service`와 `ServiceSelection`

`Service` 값은 `keycloak`, `postgres`, `sqlite`, `minio`, `milvus`, `ollama`, `langfuse`, `nats`다.

- `Service.parse(value)`는 enum 또는 대소문자 무관 문자열을 정규화한다.
- `Service.required()`는 required selection을 반환한다.
- `Service.optional()`은 optional selection을 반환한다.

`ServiceSelection(service, required=False)`는 immutable이며 service를 `Service`로 정규화한다.

### `HealthcheckPolicy`

```python
HealthcheckPolicy(
    on_startup=False,
    parallel=False,
    timeout_seconds=None,
    overall_timeout_seconds=None,
    failure_mode=StartupFailureMode.FAIL,
    attempts=1,
    retry_delay_seconds=0,
)
```

이 타입은 상태 확인을 실행하지 않고 runtime 계층을 위한 정책만 표현한다. `to_dict()`를 제공한다.

### `RuntimePlan`

```python
RuntimePlan(
    services: tuple[ServiceSelection | Service, ...],
    one_of: tuple[tuple[Service, ...], ...] = (),
    healthcheck: HealthcheckPolicy = HealthcheckPolicy(),
    minio_bucket_required: bool = False,
)
```

- 최소 한 서비스를 선택해야 한다.
- 중복 서비스와 비어 있는 대안 그룹을 거부한다.
- 대안 그룹의 서비스는 모두 `services`에 포함되어야 한다.
- `minio_bucket_required=True`이면 MinIO를 선택해야 한다.
- `selected_services`, `required_services`, `alternative_groups` property와 `to_dict()`를 제공한다.

### `build_runtime_plan_metadata`와 `RuntimePlanMetadata`

```python
def build_runtime_plan_metadata(
    *,
    plan: RuntimePlan,
    selection_mode: Literal["auto", "explicit", "strict"] = "auto",
) -> RuntimePlanMetadata: ...
```

`RuntimePlanMetadata` 필드:

- `selected_services`, `configured_services`, `required_services`
- `alternative_groups`, `healthcheck`, `minio_bucket_required`
- `service_states`, `requirements_satisfied`, `diagnosis_ok`, `issues`

`to_dict()`는 정렬된 서비스 이름과 secret-safe 문제만 포함하며 executable object나 설정 원문은 포함하지 않는다.

## 6. 보안 API

### `mask_sensitive_value`

```python
def mask_sensitive_value(raw: str | None) -> str | None: ...
```

다음을 마스킹한다.

- 정상 URL과 malformed URL의 `username:password@` userinfo
- 민감한 query·fragment parameter
- bearer token과 JWT 형태
- `password=...`, `token:...`, `secret ...` 형태의 assignment

일반 이메일과 비민감 URL parameter는 보존한다. 이 함수는 라이브러리가 반환하는 설정·진단 경로를 보호하기 위한 helper이며 호출자가 별도로 남기는 로그나 외부 SDK 메시지를 전역 정제하지 않는다.

### `validate_runtime_security`

production 환경에서 Keycloak·MinIO·Milvus·Ollama의 transport 보안 비활성화를 `ConfigError`로 거부한다. development 환경에서는 metadata 검증만 수행하며 네트워크에 접속하지 않는다.

## 7. 오류 계층

```text
Exception
└── DocmeshConfigError
    └── ConfigurationError (ValueError)
        ├── ConfigError
        ├── InvalidRuntimePlanError
        └── UnknownServiceError
```

- `DocmeshConfigError`: `service`, `reason_code`, `remediation`
- `ConfigError`: 위 속성에 더해 `issues`, `errors`, `env_keys`
- `InvalidRuntimePlanError`: plan 구조나 policy 값이 유효하지 않을 때 발생
- `UnknownServiceError`: 지원하지 않는 서비스 이름을 요청했을 때 발생

validation 오류는 설정 모델 직접 생성 시 Pydantic `ValidationError`, 통합 로딩·진단 경로에서는 secret-safe `ConfigError` 또는 `ConfigIssue`로 제공된다.

## 8. 상수와 facade

### `SUPPORTED_SERVICES`

지원 서비스 이름 8개의 immutable `frozenset[str]`다.

### `SERVICE_CONFIG_TYPES`

각 `Service`를 해당 설정 모델에 연결하는 read-only mapping이다. 서비스 로더의 단일 정보원이며 직접 변경하면 안 된다.

### `docmesh_config.config`

호환 facade가 공개하는 24개 심볼:

- 설정: `CommonConfig`, `DocmeshBaseSettings`, `KeycloakDiscoveryConfig`, `KeycloakConfig`, `PostgresConfig`, `SqliteConfig`, `MinioConfig`, `MilvusConfig`, `OllamaConfig`, `LangfuseConfig`, `NatsConfig`
- 로딩·진단: `ServiceConfigs`, `load_service_configs`, `load_available_service_configs`, `diagnose_services`, `validate_runtime_security`, `validate_service_requirements`, `require_minio_bucket`
- 결과·오류: `ConfigError`, `ConfigIssue`, `EnvironmentDiagnosis`, `ServiceConfigurationDiagnosis`
- registry: `SERVICE_CONFIG_TYPES`, `SUPPORTED_SERVICES`

새 코드에서는 일관성을 위해 package-root import를 권장한다.
