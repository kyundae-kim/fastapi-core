# fastapi-core 설정 정의서

> 문서 목적: `fastapi-core`의 설정을 **현재 구현된 FastAPI 앱 조립 / dependency / readiness 관점**에서 설명한다.
> 기준 문서: `docs/prd.md`, `docs/srs.md`, `docs/api.md`
> 문서 상태: 구현 반영본(v0.4)

---

## 1. 문서 개요

이 문서는 계획 단계의 전체 플랫폼 설정 카탈로그가 아니라, **현재 저장소 구현이 실제로 읽고 사용하는 설정**을 우선 정리한다.
특히 `create_app(...)`, `AppConfig`, `load_docmesh_settings()`, `app.state` 연계 지점을 중심으로 본다.

- 작성일: `2026-06-29`
- 작성자: `Hermes Agent`
- 버전: `v0.4`
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
   - Keycloak / SQLite / MinIO / Milvus / Ollama / Langfuse / NATS 등 외부 시스템 설정을 포함한다.
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
| `token_url` | `set_oauth2_token_url(...)` | OpenAPI OAuth2 password flow token URL 반영 |
| `cors_origins` | `CORSMiddleware` | 허용 origin 목록 |
| `cors_credentials` | `CORSMiddleware` | credential 허용 여부 |
| `readiness_parallel` | `app.state.readiness_parallel` | readiness check 병렬 실행 여부 |
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
- `DOCMESH_LOG_LEVEL` (`log_level` alias)
- `APP_LOG_PATH` (`log_path` alias)
- `APP_LOG_JSON` (`log_json` alias)
- `APP_LOG_FORCE` (`log_force` alias)
- `DOCMESH_SERVICES` (`enabled_services` alias)
- `READINESS_REQUIRED_SERVICES` (`required_services` alias)

### 3.3 파싱 규칙

- `CORS_ORIGINS`, `DOCMESH_SERVICES`, `READINESS_REQUIRED_SERVICES`는 쉼표 구분 문자열을 list로 읽는다.
- 비어 있는 문자열은 기본값 처리로 넘긴다.
- bool 계열은 Pydantic settings 파싱을 따른다.
- `load_app_config()`는 `lru_cache(maxsize=1)`로 캐시된다.

예시:

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

---

## 4. `create_app(...)`와 설정 연결

현재 구현의 `create_app(config=None, settings=None, lifespan=None, include_auth_router=True)`는 다음 순서로 설정을 사용한다.

1. `config`가 없으면 `load_app_config()` 사용
2. `settings`가 없으면 `load_docmesh_settings(tuple(config.enabled_services))` 사용
3. `_configure_application_logging(config)`로 로깅 초기화
4. `_build_service_clients(settings, config.enabled_services)`로 서비스 클라이언트 맵 생성
5. `FastAPI(root_path=config.root_path, lifespan=_build_lifespan(...))` 생성
6. `app.state.config = config`
7. `app.state.root_logger = root_logger`
8. `app.state.settings = settings`
9. `app.state.service_clients = service_clients`
10. keycloak client가 있으면 `app.state.auth_provider = service_clients["keycloak"].client`
11. `app.state.readiness_parallel = config.readiness_parallel`
12. `app.state.readiness_checks = _build_readiness_checks(service_clients)`
13. `app.state.readiness_services = _build_readiness_metadata(config.enabled_services, config.required_services)`
14. `app.state.required_services = set(config.required_services)`
15. `set_oauth2_token_url(config.token_url)` 적용
16. CORS middleware 등록
17. health router 포함
18. 필요 시 auth router 포함

즉, 설정은 현재 코드에서 **앱 조립**, **로깅 초기화**, **service_clients/readiness 기본 구성**, **auth 문서 표면(OpenAPI) 조정**에 직접 사용된다.

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
- 내부 기본값 보강 컨텍스트를 적용한 뒤 `docmesh_py_core.load_service_configs(services=services)`를 호출한다.
- 서비스 선택이 없으면 전체 기본 서비스를 로딩한다.
- `lru_cache(maxsize=1)`로 캐시된다.

### 5.3 중요 해석

이 기본값들은 **운영 권장값이 아니라 개발/테스트용 fallback**이다.
운영 환경에서는 반드시 명시적 환경변수 또는 외부 secret 주입으로 대체해야 한다.

---

## 6. 인증 설정 (현재 구현 관점)

현재 auth 경로에 직접 연결되는 설정은 `docmesh_py_core.ServiceConfigs` 내부의 Keycloak 관련 값들이다.

핵심 필수값:
- `KEYCLOAK_URL`
- `KEYCLOAK_REALM`
- `KEYCLOAK_CLIENT_ID`
- `KEYCLOAK_CLIENT_SECRET`

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

### 7.1 현재 설정 연결 방식

| 항목 | 공급 방식 | 설명 |
| --- | --- | --- |
| `readiness_checks` | 기본 create_app 자동 구성 또는 사용자/lifespan override | 서비스명 → callable 매핑 |
| `readiness_services` | 기본 create_app 자동 구성 또는 사용자 override | 서비스별 `{required, enabled}` 메타데이터 |
| `required_services` | `AppConfig` 또는 직접 state 설정 | 실패 시 503을 유발하는 필수 서비스 집합 |
| `readiness_parallel` | `AppConfig` 또는 직접 state 설정 | 병렬 실행 여부 |

### 7.2 구현상 의미

- `READINESS_PARALLEL`은 실제로 사용된다.
- `DOCMESH_SERVICES`는 기본 readiness 대상 집합을 결정한다.
- `READINESS_REQUIRED_SERVICES`는 필수 실패 기준을 결정한다.
- health endpoint 자체가 `KEYCLOAK_URL`, `NATS_SERVERS`를 직접 읽는 것은 아니다.
- 대신 create_app이 service client 기반 check를 미리 구성해 둔다.

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
- SQLite
- MinIO
- Milvus
- Ollama
- Langfuse
- NATS

하지만 현재 `fastapi_core` 자체는 이들을 다음 정도로만 직접 다룬다.

| 시스템 | 현재 fastapi_core 직접 사용 여부 | 비고 |
| --- | --- | --- |
| Keycloak | 직접/간접 | auth provider, 기본 readiness 대상 |
| SQLite | 간접 | 선택 서비스 로딩 및 service_clients/readiness 대상 |
| MinIO | 간접 | settings/service_clients 기반 확장 지점 |
| Milvus | 간접 | settings/service_clients 기반 확장 지점 |
| Ollama | 간접 | settings/service_clients 기반 확장 지점 |
| Langfuse | 간접 | settings/service_clients 기반 확장 지점 |
| NATS | 간접 | settings/service_clients 기반 readiness 또는 custom lifespan 확장 지점 |

즉, 현재 구현에서 이 값들은 각 서비스를 개별 이름의 전용 dependency로 모두 노출하는 API라기보다, `ServiceConfigs`와 `app.state.service_clients`를 통한 통합 기반이며 공통 접근용 `get_service_client(service_name)` dependency가 그 위에 얹힌 형태다.

---

## 10. 테스트 환경에서 확인된 최소 설정

`test_fastapi_core/conftest.py`의 `build_test_settings()` 기준, 테스트용 `ServiceConfigs`를 만들기 위해 다음 값들이 제공된다.

- `KEYCLOAK_URL`
- `KEYCLOAK_REALM`
- `KEYCLOAK_CLIENT_ID`
- `KEYCLOAK_CLIENT_SECRET`
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
- 현재 `docmesh_py_core.load_service_configs(...)`를 통과하려면 위 수준의 필수 세트가 필요했다.
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
- 실제 외부 연동을 포함한 기본 회귀 테스트

---

## 13. 최소 예시

### 13.1 AppConfig 환경변수

```env
ROOT_PATH=/api
TOKEN_URL=/api/v1/auth/token
CORS_ORIGINS=https://app.example.com
CORS_CREDENTIALS=true
READINESS_PARALLEL=false
DOCMESH_SERVICES=keycloak,nats
READINESS_REQUIRED_SERVICES=keycloak
```

### 13.2 테스트/개발용 개념 예시

```env
KEYCLOAK_URL=http://keycloak.local
KEYCLOAK_REALM=docmesh
KEYCLOAK_CLIENT_ID=fastapi-core
KEYCLOAK_CLIENT_SECRET=[REDACTED]
SQLITE_PATH=:memory:
NATS_SERVERS=nats://nats.local:4222
NATS_TOKEN=[REDACTED]
```

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
