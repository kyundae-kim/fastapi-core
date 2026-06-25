# fastapi-core API Reference

> 문서 목적: `fastapi-core`가 외부 FastAPI 서비스에 제공해야 하는 공개 Python API를 정의한다.
> 기준 문서: `docs/prd.md`, `docs/srs.md`
> 문서 상태: 초안(v0.1)

---

## 1. 문서 개요

- 문서명: `fastapi-core API Reference`
- 작성일: `2026-06-25`
- 작성자: `Hermes Agent 초안 / 사용자 검토 필요`
- 버전: `v0.1`
- 상태: `draft`

### 1.1 범위

이 문서는 `fastapi-core` 패키지 루트에서 소비 가능한 공개 API를 중심으로 설명한다. 여기에는 설정 로딩, 서비스 클라이언트 생성, 인증, 헬스체크, 유틸리티, 메시징 builder, 프로비저닝 진입점이 포함된다.

### 1.2 비범위

- 내부 구현 세부 클래스의 private 메서드
- 각 외부 서비스 SDK의 원본 API 전체
- 개별 FastAPI 애플리케이션의 엔드포인트 정의

---

## 2. Public imports

패키지 루트에서 다음 공개 API를 import할 수 있어야 한다.

```python
from fastapi_core import (
    AccessTokenResult,
    AuthenticatedUser,
    ConfigError,
    HealthCheckError,
    KeycloakAuthService,
    KeycloakProvisioner,
    NatsConnectionBuilder,
    Page,
    ServiceClientError,
    ServiceClientWrapper,
    ServiceClientWrapperError,
    ServiceFactoryRegistry,
    Settings,
    SqliteConfig,
    TokenValidationError,
    UnsupportedServiceError,
    build_service_log_event,
    build_settings_snapshot,
    check_all_services,
    load_settings,
    mask_sensitive_value,
    retry_call,
    to_serializable,
)
```

> 참고: 위 목록은 현재 PRD/SRS와 ingest된 `docmesh-py-core` API 패턴을 기준으로 한 초안이다. 실제 구현 시 공개 범위는 코드와 함께 확정되어야 한다.

---

## 3. Settings API

## 3.1 `load_settings(env) -> Settings`

환경변수 매핑에서 전체 설정을 읽고 검증한다.

### 입력
- `env`: dict-like 환경변수 매핑

### 출력
- `Settings`: 최상위 설정 객체

### 동작
- 공통 및 서비스별 환경변수를 읽는다.
- 빈 문자열을 미설정으로 처리한다.
- Boolean/숫자형 값을 검증 및 변환한다.
- 필수/선택/조건부 필수 규칙을 검증한다.

### 예외
- `ConfigError`: 필수값 누락, 타입 오류, 범위 오류, 조건부 필수 규칙 위반

### 예시

```python
from os import environ
from fastapi_core import load_settings

settings = load_settings(environ)
print(settings.common.env)
```

---

## 3.2 `Settings`

패키지의 최상위 설정 객체다.

### 주요 하위 설정
- `settings.common`
- `settings.keycloak`
- `settings.postgres`
- `settings.sqlite`
- `settings.minio`
- `settings.milvus`
- `settings.ollama`
- `settings.langfuse`
- `settings.nats`

### 요구 특성
- 서비스별 설정을 타입 안전한 구조로 제공해야 한다.
- 민감정보 포함 여부를 고려해 스냅샷 생성 시 마스킹 가능해야 한다.

---

## 3.3 `SqliteConfig`

SQLite 전용 설정 객체다.

### 대표 속성
- `path`
- `readonly`
- `enable_wal`
- `busy_timeout_ms`

### 사용 목적
- 로컬 개발
- 단위 테스트
- 경량 통합 테스트

---

## 4. Client factory API

## 4.1 `ServiceFactoryRegistry(settings)`

외부 서비스 클라이언트를 생성하는 중앙 진입점이다.

### 생성자 입력
- `settings`: `Settings`

### 주요 메서드
- `create_client(service_name)`
- `create_clients(services)`
- `close_all()`

### 지원 서비스명
- `keycloak`
- `postgres`
- `sqlite`
- `minio`
- `milvus`
- `ollama`
- `langfuse`
- `nats`

### 반환 타입

| 서비스 | 반환값 |
| --- | --- |
| `keycloak` | `ServiceClientWrapper` |
| `postgres` | `ServiceClientWrapper` |
| `sqlite` | `ServiceClientWrapper` |
| `minio` | `ServiceClientWrapper` |
| `milvus` | `ServiceClientWrapper` |
| `ollama` | `ServiceClientWrapper` |
| `langfuse` | `ServiceClientWrapper | None` |
| `nats` | `NatsConnectionBuilder` |

### 예외
- `UnsupportedServiceError`
- `ServiceClientWrapperError`
- `ServiceClientError`

### 예시

```python
from os import environ
from fastapi_core import load_settings, ServiceFactoryRegistry

settings = load_settings(environ)
registry = ServiceFactoryRegistry(settings)
postgres = registry.create_client("postgres")
postgres.check()
registry.close_all()
```

---

## 4.2 `ServiceClientWrapper`

공통 `check()` / `close()` 인터페이스를 제공하는 서비스 래퍼다.

### 목적
- 서비스별 클라이언트의 공통 수명주기 노출
- 호출부의 서비스 종속 로직 감소

### 공통 메서드
- `check()`
- `close()`

### 예시

```python
client = registry.create_client("sqlite")
client.check()
client.close()
```

### 기본 `check()` 기대 동작

| 서비스 | 기본 확인 |
| --- | --- |
| Keycloak | `fetch_access_token()` |
| PostgreSQL | `SELECT 1` |
| SQLite | `SELECT 1` |
| MinIO | `list_buckets()` |
| Milvus | `list_collections()` |
| Ollama | `ps()` |
| Langfuse | `auth_check()` |

---

## 4.3 `NatsConnectionBuilder`

NATS 연결용 비동기 builder다.

### 특징
- `create_client("nats")`의 반환값
- 실제 연결은 `await connect()` 또는 `await check()`로 수행
- user/password, token, creds file 인증 중 하나를 사용 가능해야 함

### 예시

```python
from os import environ
from fastapi_core import load_settings, ServiceFactoryRegistry

settings = load_settings(environ)
registry = ServiceFactoryRegistry(settings)
builder = registry.create_client("nats")

# async context에서 사용
# await builder.check()
```

---

## 5. Health API

## 5.1 `check_all_services(service_checks, required_services=None, parallel=False)`

여러 서비스의 헬스체크를 집계 실행한다.

### 입력
- `service_checks`: `{service_name: callable}` 형태의 매핑
- `required_services`: 필수 서비스명 집합 또는 None
- `parallel`: 병렬 실행 여부

### 출력
집계 결과는 최소 다음 정보를 포함해야 한다.

- 전체 성공 여부
- 서비스별 성공 여부
- 서비스별 지연 시간
- 마스킹된 오류 메시지

### 예외
- `HealthCheckError`: 필수 서비스 실패 시

### 예시

```python
result = check_all_services(
    {
        "postgres": postgres.check,
        "minio": minio.check,
    },
    required_services={"postgres"},
    parallel=True,
)
```

### 동작 정책
- 필수 서비스와 선택 서비스를 구분해야 한다.
- `parallel=True`일 때 병렬 실행을 지원해야 한다.
- 오류 메시지는 민감정보가 마스킹되어야 한다.

---

## 6. Keycloak API

## 6.1 `KeycloakAuthService(settings, allowed_algorithms=None)`

Keycloak 인증 관련 고수준 진입점이다.

### 제공 기능
- Access Token 획득
- JWT 검증
- 사용자 정보 및 역할 추출

### 생성자 입력
- `settings`: `Settings`
- `allowed_algorithms`: 허용 알고리즘 목록 또는 None

---

## 6.2 `fetch_access_token(scope=None) -> AccessTokenResult`

Keycloak token endpoint에서 access token을 요청한다.

### 입력
- `scope`: 선택적 scope 문자열

### 기본 특성
- 기본 grant: `client_credentials`
- 선택적 `scope` 전달 지원
- 명시적 설정 시 `password` grant 지원 가능

### 반환 필드
- `access_token`
- `token_type`
- `expires_in`
- `refresh_token`
- `scope`

### 대표 예외
- `KeycloakTokenConfigurationError` 또는 `ConfigError`
- `KeycloakTokenAuthenticationError`
- `KeycloakTokenTemporaryError`
- `ServiceClientError`

---

## 6.3 `extract_user_info(token) -> AuthenticatedUser`

JWT를 검증한 뒤 표준 사용자 정보를 반환한다.

### 입력
- raw JWT 문자열
- `Bearer <token>` 형식 문자열

### 검증 항목
- 서명
- 만료 시간
- issuer
- 선택적 audience
- 허용 알고리즘

### 반환 필드
- `sub`
- `preferred_username`
- `email`
- `given_name` (있을 수 있음)
- `family_name` (있을 수 있음)
- `name`
- `realm_roles`
- `client_roles`
- `claims`

### 예외
- `TokenValidationError`

---

## 6.4 `AccessTokenResult`

토큰 응답 객체다.

### 대표 필드
- `access_token`
- `token_type`
- `expires_in`
- `refresh_token`
- `scope`

---

## 6.5 `AuthenticatedUser`

검증된 토큰에서 추출한 사용자 정보 객체다.

### 대표 필드
- `sub`
- `preferred_username`
- `email`
- `name`
- `realm_roles`
- `client_roles`
- `claims`

---

## 6.6 `KeycloakProvisioner`

Keycloak Realm/Client/Role을 선언형으로 생성/갱신하는 프로비저너다.

### 주요 특징
- 멱등 실행
- Dry-run 지원
- 생성/갱신/변경 없음/실패 구분
- 선언에서 제거된 리소스 자동 삭제 없음

### 운영 조건
- `KEYCLOAK_PROVISIONING_ENABLED=true`일 때 관련 설정 검증이 필요함
- 관리자 인증정보가 조건부 필수일 수 있음

---

## 7. Utility API

## 7.1 `mask_sensitive_value(raw)`

민감값을 마스킹한다.

### 마스킹 대상 예시
- password
- token
- secret
- 전체 DSN/URI

### 기대 동작
- 원문 노출 없이 운영 분석 가능한 수준의 형태 유지

---

## 7.2 `build_service_log_event(...)`

서비스 연결/헬스체크/재시도 이벤트를 구조화된 dict로 생성한다.

### 사용 목적
- 구조화 로그
- 운영 이벤트 추적
- 장애 분석 보조

---

## 7.3 `retry_call(operation, ..., retry_on, max_attempts)`

일시적 오류에 대해 동기 함수를 재시도한다.

### 입력 개념
- `operation`: 실행할 호출 가능 객체
- `retry_on`: 재시도 대상 오류 타입 또는 조건
- `max_attempts`: 최대 시도 횟수

### 사용 목적
- 외부 서비스 일시 오류 완화
- 공통 retry 정책 재사용

---

## 7.4 `to_serializable(value)`

복합 값을 JSON 친화 구조로 변환한다.

### 지원 대상 예시
- dataclass
- 모델 객체
- datetime
- nested container

---

## 7.5 `build_settings_snapshot(settings)`

민감정보가 마스킹된 설정 스냅샷을 생성한다.

### 목적
- 진단용 출력
- 운영 상태 점검
- 설정 비교

### 주의사항
- secret/token/password/전체 DSN·URI는 마스킹되어야 한다.

---

## 7.6 `Page`

공통 페이지네이션 표현용 타입이다.

### 사용 목적
- 목록 API/쿼리 결과의 페이지 표현 통일

---

## 8. Error model

시스템은 최소 다음 오류 범주를 제공하거나 구분 가능해야 한다.

- `ConfigError`
- `TokenValidationError`
- `HealthCheckError`
- `UnsupportedServiceError`
- `ServiceClientError`
- `ServiceClientWrapperError`
- `KeycloakTokenAuthenticationError`
- `KeycloakTokenConfigurationError`
- `KeycloakTokenTemporaryError`

### 오류 메시지 원칙
- 어떤 서비스 또는 환경변수가 문제인지 식별 가능해야 한다.
- 민감정보를 포함하면 안 된다.
- 호출자가 대응할 수 있는 수준의 오류 의미를 제공해야 한다.

---

## 9. Minimal usage examples

## 9.1 설정 로딩과 registry 생성

```python
from os import environ
from fastapi_core import load_settings, ServiceFactoryRegistry

settings = load_settings(environ)
registry = ServiceFactoryRegistry(settings)
```

## 9.2 헬스체크 집계

```python
postgres = registry.create_client("postgres")
minio = registry.create_client("minio")

result = check_all_services(
    {
        "postgres": postgres.check,
        "minio": minio.check,
    },
    required_services={"postgres"},
    parallel=True,
)
```

## 9.3 Keycloak 토큰 검증

```python
auth = KeycloakAuthService(settings)
user = auth.extract_user_info("Bearer <token>")
print(user.preferred_username)
```

## 9.4 설정 스냅샷

```python
snapshot = build_settings_snapshot(settings)
print(snapshot)
```

---

## 10. 참고 문서

- `docs/prd.md`
- `docs/srs.md`
- `README.md`
- `wiki/entities/docmesh-py-core.md`
- `wiki/concepts/service-factory-registry.md`
- `wiki/concepts/service-health-check-aggregation.md`
- `wiki/concepts/keycloak-authentication-api.md`
- `wiki/concepts/service-configuration-contracts.md`

---

## 부록 A. 문서 상태 메모

이 초안은 현재 확인 가능한 PRD/SRS 및 wiki에 ingest된 `docmesh-py-core` API/config 내용을 바탕으로 작성되었다. 실제 구현 코드가 준비되면 import 경로, 예외 클래스명, 반환 타입 상세 스키마를 코드 기준으로 다시 맞춰야 한다.
