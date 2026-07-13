# fastapi-core 설정 정의서

> 문서 목적: `fastapi-core`의 설정을 **현재 구현된 FastAPI 앱 조립 / dependency / readiness 관점**에서 설명한다.
> 기준 문서: `docs/prd.md`, `docs/srs.md`, `docs/api.md`
> 문서 상태: 구현 반영본(v0.7)

---

## 1. 문서 개요

이 문서는 계획 단계의 전체 플랫폼 설정 카탈로그가 아니라, **현재 저장소 구현이 실제로 읽고 사용하는 설정**을 우선 정리한다.
특히 `create_app(...)`, `AppConfig`, `load_docmesh_settings()`, `app.state` 연계 지점을 중심으로 본다.

- 작성일: `2026-07-03`
- 작성자: `Hermes Agent`
- 버전: `v0.7`
- 상태: `implemented-surface`

핵심 관점:
- `create_app(...)`가 어떤 설정을 직접 소비하는가
- FastAPI dependency가 어떤 설정 객체를 참조하는가
- readiness가 어떤 방식으로 설정과 연결되는가
- 로깅/서비스 선택이 어떻게 반영되는가

---

## 2. 현재 구현의 설정 계층

현재 구현은 설정을 두 층으로 나눈다.

1. **앱 조립 설정 (`AppConfig`)**
   - 정의 위치: `fastapi_core.config.AppConfig`
   - FastAPI app 자체의 동작을 제어한다.
   - 예: `root_path`, `token_url`, CORS, readiness 병렬화, 로깅, 활성 서비스 집합

2. **서비스/외부 의존성 설정 (`docmesh_py_core.ServiceConfigs`)**
   - 로더: `fastapi_core.docmesh_settings.load_docmesh_settings(...)`
   - 실제 생성은 `docmesh_py_core.load_service_configs(...)`
   - Keycloak / PostgreSQL / SQLite / MinIO / Milvus / Ollama / Langfuse / NATS 등 외부 시스템 설정을 포함한다.
   - 현재 `fastapi_core`는 이 객체를 service client 구성과 auth provider/서비스 체크 기반값으로 사용한다.

즉, 현재 코드에서 FastAPI 앱은:
- `AppConfig`로 앱 조립 방식과 공개 표면 동작을 결정하고
- `ServiceConfigs`로 외부 시스템 구성을 보관하고 service client 구성에 전달한다.

---

## 3. AppConfig

정의 위치: `fastapi_core/config.py`

```python
class AppConfig(BaseSettings):
    root_path: str = ""
    token_url: str = "/token"
    cors_origins: list[str] = ["*"]
    cors_credentials: bool = False
    readiness_parallel: bool = False
    readiness_timeout_seconds: float | None = None
    readiness_overall_timeout_seconds: float | None = None
    service_alternatives: list[list[str]] = []
    startup_healthcheck: bool = False
    log_level: str | None = "WARNING"
    log_path: str | None = None
    log_json: bool = True
    log_force: bool = False
    enabled_services: list[str] = ["keycloak"]
    required_services: list[str] = ["keycloak"]
```

### 3.1 필드 의미

| 필드 | 적용 위치 | 현재 동작 |
| --- | --- | --- |
| `root_path` | `FastAPI(root_path=...)` | reverse proxy 하위 경로 배포 시 사용 |
| `token_url` | `set_oauth2_token_url(...)` | 모듈 전역 OAuth2 password flow의 token URL 반영 |
| `cors_origins` | `CORSMiddleware` | 허용 origin 목록 |
| `cors_credentials` | `CORSMiddleware` | credential 허용 여부 |
| `readiness_parallel` | `app.state.readiness_parallel` | readiness check 병렬 실행 여부 |
| `readiness_timeout_seconds` | runtime startup/readiness endpoint | 서비스별 healthcheck 제한 시간 |
| `readiness_overall_timeout_seconds` | runtime startup/readiness endpoint | 전체 healthcheck 실행 제한 시간 |
| `service_alternatives` | runtime `one_of` 검증 | 각 그룹에서 최소 한 서비스가 구성되어야 하는 대안 정책 |
| `startup_healthcheck` | `assemble_service_runtime(..., check_on_startup=...)` | startup에서 required service healthcheck를 수행할지 여부 |
| `log_level` | `_configure_application_logging(...)` | 루트 로거 레벨 |
| `log_path` | `_configure_application_logging(...)` | 파일 로그 경로 |
| `log_json` | `_configure_application_logging(...)` | JSON formatter 사용 여부 |
| `log_force` | `_configure_application_logging(...)` | 로거 재구성 강제 여부 |
| `enabled_services` | `load_docmesh_settings(...)`, readiness 기본 구성 | 로딩/체크할 서비스 집합 |
| `required_services` | `app.state.required_services`, readiness 상태 판정 | 실패 시 `503`을 유발하는 필수 서비스 집합 |

### 3.2 로더

`load_app_config()`는 환경변수에서 `AppConfig`를 구성한다.

읽는 환경변수:
- `ROOT_PATH`
- `TOKEN_URL`
- `CORS_ORIGINS`
- `CORS_CREDENTIALS`
- `READINESS_PARALLEL`
- `READINESS_TIMEOUT_SECONDS`
- `READINESS_OVERALL_TIMEOUT_SECONDS`
- `DOCMESH_SERVICE_ALTERNATIVES`
- `DOCMESH_HEALTHCHECK_ENABLED` (`startup_healthcheck` alias)
- `DOCMESH_LOG_LEVEL` (`log_level` alias)
- `APP_LOG_PATH` (`log_path` alias)
- `APP_LOG_JSON` (`log_json` alias)
- `APP_LOG_FORCE` (`log_force` alias)
- `DOCMESH_SERVICES` (`enabled_services` alias)
- `READINESS_REQUIRED_SERVICES` (`required_services` alias)

`AliasChoices`로 인해 아래 lowercase field 이름도 직접 입력 alias로 허용된다.
- `readiness_timeout_seconds`, `readiness_overall_timeout_seconds`, `service_alternatives`, `startup_healthcheck`
- `log_level`, `log_path`, `log_json`, `log_force`
- `enabled_services`, `required_services`

### 3.3 파싱 규칙

- `CORS_ORIGINS`, `DOCMESH_SERVICES`, `READINESS_REQUIRED_SERVICES`는 쉼표 구분 문자열을 list로 읽는다.
- `DOCMESH_SERVICE_ALTERNATIVES`는 세미콜론으로 그룹을, 쉼표로 그룹 내 서비스를 구분한다. 예: `postgres,sqlite;minio,milvus`.
- readiness timeout 두 필드는 양수만 허용하며 미설정 시 제한을 적용하지 않는다.
- 위 CSV 환경변수에 빈 문자열을 지정하면 validator가 `None`으로 변환한다. 세 필드는 non-optional `list[str]`이므로 기본값으로 복원되지 않고 validation error가 발생한다. 기본값을 사용하려면 변수를 설정하지 않는다.
- bool 계열은 Pydantic settings 파싱을 따른다.
- `load_app_config()`는 `lru_cache(maxsize=1)`로 캐시된다.

예시:

```env
ROOT_PATH=/api
TOKEN_URL=/api/v1/auth/token
CORS_ORIGINS=https://app.example.com,https://admin.example.com
CORS_CREDENTIALS=true
READINESS_PARALLEL=true
READINESS_TIMEOUT_SECONDS=5
READINESS_OVERALL_TIMEOUT_SECONDS=15
DOCMESH_SERVICE_ALTERNATIVES=postgres,sqlite;minio,milvus
DOCMESH_HEALTHCHECK_ENABLED=true
DOCMESH_LOG_LEVEL=INFO
APP_LOG_PATH=/tmp/app.log
APP_LOG_JSON=true
APP_LOG_FORCE=true
DOCMESH_SERVICES=keycloak,nats
READINESS_REQUIRED_SERVICES=keycloak
```

---

## 4. `create_app(...)`와 설정 연결

현재 구현의 `create_app(config=None, settings=None, lifespan=None, include_auth_router=True)`는 다음 순서로 설정을 사용한다.

1. `config`가 없으면 `load_app_config()` 사용
2. `_configure_application_logging(config)`로 로깅 초기화
3. 명시적 `settings`가 있으면 direct factory client를 `ServiceRuntime`으로 감싸 주입 경로 구성
4. `FastAPI(root_path=config.root_path, lifespan=_build_lifespan(...))` 생성
5. lifespan startup에서 `settings`가 없으면 `assemble_service_runtime(build_docmesh_env_overlay(), services=..., required=..., one_of=..., check_on_startup=..., healthcheck_timeout_seconds=..., overall_healthcheck_timeout_seconds=...)` 실행
6. runtime의 `configs`, `clients`, readiness check를 `app.state`에 설치
7. `app.state.config = config`, `app.state.root_logger = root_logger`
8. `app.state.service_runtime = runtime`
9. `app.state.settings = runtime.configs`
10. `app.state.service_clients = runtime.clients`
11. keycloak client가 있으면 `app.state.auth_provider = service_clients["keycloak"].client`
12. `app.state.readiness_parallel = config.readiness_parallel`
13. per-service/overall timeout을 `app.state`에 저장
14. `app.state.readiness_checks = _build_readiness_checks(service_clients)`
15. `app.state.readiness_services = _build_readiness_metadata(config.enabled_services, config.required_services)`
16. `app.state.required_services = set(config.required_services)`
17. `set_oauth2_token_url(config.token_url)` 적용
18. CORS middleware 등록 및 router 포함
19. lifespan 종료 시 `await service_runtime.close()` 실행; 실패 시 구조화 로그 후 `ServiceCloseError` 전파

즉, 설정은 현재 코드에서 **앱 조립**, **로깅 초기화**, **service_clients/readiness 기본 구성**, **auth 문서 표면(OpenAPI) 조정**에 직접 사용된다. `token_url`은 앱 인스턴스별 값이 아니라 module-global `oauth2_scheme`을 변경하므로, 한 프로세스에서 서로 다른 `token_url`로 여러 앱을 만들면 마지막 `create_app()` 호출 값이 OpenAPI password flow에 반영된다.

---

## 5. DocMesh settings 로더

정의 위치: `fastapi_core/docmesh_settings.py`

### 5.1 `build_docmesh_env_overlay()`

현재 환경변수를 복사한 뒤, `docmesh_py_core.load_service_configs(...)`가 실패하지 않도록 개발/테스트용 fallback 값을 채운다.

대표 기본값:
- `KEYCLOAK_URL=http://keycloak.local`
- `KEYCLOAK_REALM=docmesh`
- `KEYCLOAK_CLIENT_ID=fastapi-core`
- `KEYCLOAK_CLIENT_SECRET=dev-secret`
- `POSTGRES_DSN=postgresql+psycopg://docmesh:dev-secret@postgres.local:5432/docmesh`
- `SQLITE_PATH=:memory:`
- `MINIO_ENDPOINT=minio.local:9000`
- `MINIO_ACCESS_KEY=minio`
- `MINIO_SECRET_KEY=miniosecret`
- `MILVUS_URI=http://milvus.local:19530`
- `OLLAMA_HOST=http://ollama.local:11434`
- `LANGFUSE_HOST=http://langfuse.local:3000`
- `LANGFUSE_PUBLIC_KEY=dev-public`
- `LANGFUSE_SECRET_KEY=dev-secret`
- `NATS_SERVERS=nats://nats.local:4222`
- `NATS_TOKEN=dev-token`

### 5.2 `load_docmesh_settings(enabled_services: tuple[str, ...] | None = None)`

동작:
- `enabled_services`가 있으면 집합으로 변환한다.
- `build_docmesh_env_overlay()`로 현재 환경의 복사본과 fallback을 결합한다.
- `docmesh_py_core.load_service_configs(env, services=services)`에 mapping을 직접 전달한다.
- 로딩 과정에서 프로세스 `os.environ`을 추가·삭제·수정하지 않는다.
- 서비스 선택이 없으면 전체 기본 서비스를 로딩한다.
- `lru_cache(maxsize=1)`로 캐시된다.

### 5.3 중요 해석

이 기본값들은 **운영 권장값이 아니라 개발/테스트용 fallback**이다.
운영 환경에서는 반드시 명시적 환경변수 또는 외부 secret 주입으로 대체해야 한다.

### 5.4 공통 보안 모드

mapping loader를 통해 다음 `docmesh-py-core` 공통 설정도 실제 검증에 사용된다.

| 환경변수 | 기본값 | 의미 |
| --- | --- | --- |
| `DOCMESH_SECURITY_MODE` | 없음 | `development` 또는 `production`; 설정 시 환경 이름보다 우선 |
| `DOCMESH_PRODUCTION_ALIASES` | `prod,production` | `DOCMESH_ENV`를 운영으로 판정할 alias 목록 |
| `DOCMESH_HEALTHCHECK_ENABLED` | `true` (Py Core config) | Py Core 공통 값; FastAPI startup 정책은 `AppConfig.startup_healthcheck` 기본값 `False`로 별도 연결 |

production 판정 시 `validate_runtime_security()`가 TLS 등 추가 보안 제약을 검사한다. FastAPI Core가 이 검증을 재구현하지 않고 v0.2.0 loader/assembly 결과를 그대로 사용한다.

---

## 6. 인증 설정 (현재 구현 관점)

현재 auth 경로에 직접 연결되는 설정은 `docmesh_py_core.ServiceConfigs` 내부의 Keycloak 관련 값들이다.

핵심 필수값:
- `KEYCLOAK_URL`
- `KEYCLOAK_REALM`
- `KEYCLOAK_CLIENT_ID`
- `KEYCLOAK_CLIENT_SECRET`

password grant에서는 함수 인자의 `username` / `password`가 우선하고, 생략한 값은 `KEYCLOAK_TOKEN_USERNAME` / `KEYCLOAK_TOKEN_PASSWORD`에서 fallback한다. 두 경로 모두 필요한 자격증명을 제공하지 않으면 Keycloak configuration error가 발생한다. 실제 값은 문서나 로그에 기록하지 않는다.

현재 구현 기준 영향 범위:
- `create_app()`의 `service_clients` 구성 중 keycloak client/provider 준비
- `get_auth_provider()`의 `app.state.service_clients` 기반 provider 재사용
- `/token` endpoint의 provider 호출 기반값
- `/user` / `get_current_user()`의 token 해석 기반값

### 현재 문서화 시 주의할 점

다음 항목들은 `fastapi_core`가 직접 노출하는 분기 API가 아니다.
- secure/insecure decode 분기
- introspection 모드 분기
- timeout/retry 정책의 FastAPI 계층 직접 반영

이 값들은 `docmesh_py_core` 내부에서 의미가 있을 수 있지만, 현재 `fastapi_core` 공개 표면 문서에서는 **직접 구현된 FastAPI API처럼 과장하면 안 된다**.

---

## 7. readiness / health 관련 설정

현재 readiness는 `AppConfig`와 `app.state`가 함께 결정한다.

실제 동작:
- `/health/liveness`는 설정 의존성이 거의 없다.
- `/health/readiness`는 아래 값을 읽는다.
  - `app.state.readiness_checks`
  - `app.state.readiness_services`
  - `app.state.required_services`
  - `app.state.readiness_parallel`
  - `app.state.readiness_timeout_seconds`
  - `app.state.readiness_overall_timeout_seconds`

### 7.1 현재 설정 연결 방식

| 항목 | 공급 방식 | 설명 |
| --- | --- | --- |
| `readiness_checks` | 기본 create_app 자동 구성 또는 사용자/lifespan override | 서비스명 → callable 매핑 |
| `readiness_services` | 기본 create_app 자동 구성 또는 사용자 override | 서비스별 `{required, enabled}` 메타데이터 |
| `required_services` | `AppConfig` 또는 직접 state 설정 | 실패 시 503을 유발하는 필수 서비스 집합 |
| `readiness_parallel` | `AppConfig` 또는 직접 state 설정 | 병렬 실행 여부 |
| `readiness_timeout_seconds` | `AppConfig` 또는 직접 state 설정 | 서비스별 제한 시간 |
| `readiness_overall_timeout_seconds` | `AppConfig` 또는 직접 state 설정 | 전체 제한 시간 |
| `service_alternatives` | `AppConfig` | assembly `one_of` 구성 검증 |
| `startup_healthcheck` | `AppConfig` | runtime 조립 직후 required service check 실행 여부 |

### 7.2 구현상 의미

- `READINESS_PARALLEL`은 실제로 사용된다.
- 두 timeout은 startup healthcheck와 `/health/readiness`에 동일하게 전달된다.
- 서비스별 timeout은 해당 서비스 실패로, overall timeout은 details 없는 `503 error`로 반환된다.
- `DOCMESH_SERVICE_ALTERNATIVES` 각 그룹은 assembly 시 적어도 하나의 설정된 서비스를 요구한다.
- `DOCMESH_HEALTHCHECK_ENABLED`는 `AppConfig.startup_healthcheck`로 연결된다.
- 앱 정책 기본값은 `False`이며, 환경변수를 설정하지 않으면 startup network check 없이 readiness endpoint에서 상태를 확인한다.
- `startup_healthcheck=True`이면 custom lifespan 진입 전에 runtime healthcheck가 실행되고 required 실패 시 앱 startup이 실패한다.
- `DOCMESH_SERVICES`는 기본 readiness 대상 집합을 결정한다.
- `READINESS_REQUIRED_SERVICES`는 필수 실패 기준을 결정한다.
- health endpoint 자체가 `KEYCLOAK_URL`, `NATS_SERVERS`를 직접 읽는 것은 아니다.
- 대신 기본 create_app lifespan startup이 runtime client 기반 check를 구성해 둔다.

기본 예시:

```python
app.state.readiness_services == {
    "keycloak": {"enabled": True, "required": True}
}
app.state.required_services == {"keycloak"}
```

수동 override 예시:

```python
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

### 7.3 상태 판정 규칙

- 모든 서비스 성공 → `200`, `status="ok"`
- 선택 서비스만 실패 → `200`, `status="degraded"`
- 필수 서비스 실패 → `503`, `status="error"`

---

## 8. CORS 설정

현재 CORS는 `create_app()`에서 항상 등록된다.

직접 연결되는 설정:
- `CORS_ORIGINS`
- `CORS_CREDENTIALS`

적용 코드:
- `allow_origins=app_config.cors_origins`
- `allow_credentials=app_config.cors_credentials`
- `allow_methods=["*"]`
- `allow_headers=["*"]`

운영 권장:
- wildcard 대신 명시 origin 사용
- credential 허용 시 origin 범위를 엄격하게 제한

---

## 9. 외부 의존성 설정 범위

`load_docmesh_settings()`는 다음 외부 시스템 설정을 다룰 수 있다.

- Keycloak
- PostgreSQL
- SQLite
- MinIO
- Milvus
- Ollama
- Langfuse
- NATS

하지만 현재 `fastapi_core` 자체는 이들을 다음 정도로만 직접 다룬다.

| 시스템 | 현재 fastapi_core 직접 사용 여부 | 비고 |
| --- | --- | --- |
| Keycloak | 직접/간접 | auth provider, service client가 생성되면 readiness 대상 |
| PostgreSQL | 간접 | 선택 서비스 로딩 및 service client/readiness 대상 |
| SQLite | 간접 | 선택 서비스 로딩 및 service client/readiness 대상 |
| MinIO | 간접 | 선택 서비스 로딩 및 service client/readiness 대상 |
| Milvus | 간접 | 선택 서비스 로딩 및 service client/readiness 대상 |
| Ollama | 간접 | 선택 서비스 로딩 및 service client/readiness 대상 |
| Langfuse | 간접 | 선택 서비스 로딩 및 service client/readiness 대상 |
| NATS | 간접 | 선택 서비스 로딩 및 service client/readiness 또는 custom lifespan 확장 지점 |

즉, 현재 구현에서 이 값들은 `ServiceConfigs`와 `app.state.service_clients`를 통한 통합 기반이며, 그 위에 공통 접근용 `get_service_client(service_name)`와 구체 타입 반환용 전용 dependency(`get_keycloak_auth_service`, `get_postgres_engine`, `get_sqlite_engine`, `get_minio_client`, `get_milvus_client`, `get_ollama_client`, `get_langfuse_client`, `get_nats_connection_builder`)가 얹힌 형태다.

---

## 10. 테스트 환경에서 확인된 최소 설정

`test_fastapi_core/conftest.py`의 `build_test_settings()`는 fixture 편의를 위해 다음 값을 제공한다.

- `KEYCLOAK_URL`
- `KEYCLOAK_REALM`
- `KEYCLOAK_CLIENT_ID`
- `KEYCLOAK_CLIENT_SECRET`
- `POSTGRES_DSN`
- `SQLITE_PATH`
- `MINIO_ENDPOINT`
- `MINIO_ACCESS_KEY`
- `MINIO_SECRET_KEY`
- `MILVUS_URI`
- `OLLAMA_HOST`
- `LANGFUSE_HOST`
- `LANGFUSE_PUBLIC_KEY`
- `LANGFUSE_SECRET_KEY`
- `NATS_SERVERS`
- `NATS_TOKEN`

문서상 의미:
- 실제 필요한 환경변수는 `load_docmesh_settings(...)`에 전달한 서비스 선택에 따라 달라진다. 예를 들어 `load_docmesh_settings(("sqlite",))`는 SQLite 설정만 로드한다.
- 테스트는 단순 mock dict가 아니라 실제 `ServiceConfigs` 생성 경로를 통과한다.

---

## 11. 운영/보안 원칙

- secret / token / password / 전체 URI는 문서 예시와 로그에서 원문 노출 금지
- 개발 fallback를 운영 기본값처럼 안내하지 말 것
- readiness 필수/선택 서비스 집합을 운영 정책으로 명시할 것
- `app.state` override 객체는 startup/lifespan과 정합성을 맞출 것

---

## 12. 현재 구현 기준 제한 사항

현재 구현 기준으로 아직 직접 제공되지 않는 것:
- auth 전용 exception handler 설정 API
- secure/insecure JWT decode 분기 설정 API
- introspection 모드 선택 API
- 메시징 전용 FastAPI dependency (`get_nats_connection` 등)
- NATS 연결 상태 객체를 기본 `app.state` 키로 노출하는 표준 API

참고로 실제 외부 연동은 `test_fastapi_core/integration/`의 live integration 테스트에서 별도로 검증된다.

---

## 13. 최소 예시

### 13.1 AppConfig 환경변수

```env
ROOT_PATH=/api
TOKEN_URL=/api/v1/auth/token
CORS_ORIGINS=https://app.example.com
CORS_CREDENTIALS=true
READINESS_PARALLEL=false
READINESS_TIMEOUT_SECONDS=5
READINESS_OVERALL_TIMEOUT_SECONDS=15
DOCMESH_SERVICE_ALTERNATIVES=postgres,sqlite
DOCMESH_HEALTHCHECK_ENABLED=true
DOCMESH_SERVICES=keycloak,nats
READINESS_REQUIRED_SERVICES=keycloak
```

### 13.2 테스트/개발용 개념 예시

```env
KEYCLOAK_URL=http://keycloak.local
KEYCLOAK_REALM=docmesh
KEYCLOAK_CLIENT_ID=fastapi-core
KEYCLOAK_CLIENT_SECRET=[REDACTED]
POSTGRES_DSN=postgresql+psycopg://docmesh:[REDACTED]@postgres.local:5432/docmesh
SQLITE_PATH=:memory:
NATS_SERVERS=nats://nats.local:4222
NATS_TOKEN=[REDACTED]
```

`POSTGRES_DSN` 대신 `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`를 설정할 수 있다. 선택 항목은 `POSTGRES_SSLMODE`, `POSTGRES_CONNECT_TIMEOUT_SECONDS`, `POSTGRES_POOL_SIZE`, `POSTGRES_MAX_OVERFLOW`이다.

---

## 14. 참고 문서

- `docs/prd.md`
- `docs/srs.md`
- `docs/api.md`
- `docs/examples.md`
- `README.md`
- `fastapi_core/config.py`
- `fastapi_core/docmesh_settings.py`
- `fastapi_core/factory.py`
- `test_fastapi_core/conftest.py`
- `test_fastapi_core/test_config.py`

---

## 15. 문서 상태 메모

이 문서는 기존의 광범위한 플랫폼 설정 계획 문서를, **현재 저장소에서 실제 확인된 설정 소비 경로** 중심으로 재정렬한 것이다.
특히 `load_default_settings()` 중심 설명을 제거하고, 현재 코드가 실제 사용하는 `load_docmesh_settings()`, 로깅 설정, 서비스 선택/필수 readiness 구조를 기준으로 맞췄다.
