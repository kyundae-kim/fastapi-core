# fastapi-core 소프트웨어 요구사항 정의서 (SRS)

> 문서 목적: `fastapi-core` 제품 요구사항을 구현 가능한 소프트웨어 요구사항으로 구체화한다.
> 기준 문서: `docs/prd.md`
> 문서 상태: 초안(v0.1)

---

## 1. 문서 개요

- 문서명: `fastapi-core 소프트웨어 요구사항 정의서`
- 작성일: `2026-06-25`
- 작성자: `Hermes Agent 초안 / 사용자 검토 필요`
- 버전: `v0.1`
- 상태: `draft`

### 1.1 목적

본 문서는 `fastapi-core`가 제공해야 하는 설정 로딩, 인증, 외부 서비스 클라이언트 생성, 헬스체크, 운영 유틸리티, 메시징 연계 기능을 소프트웨어 관점에서 정의한다. 제품 요구사항(PRD)의 범위를 실제 패키지 인터페이스, 입력/출력, 오류 모델, 제약조건, 검증 기준 수준으로 구체화하는 것이 목적이다.

### 1.2 범위

`fastapi-core`는 DocMesh 프로젝트의 FastAPI 기반 서비스들이 공통으로 사용하는 Python SDK다. 이 SDK는 다음을 소프트웨어 범위로 포함한다.

- 환경변수 기반 설정 로딩 및 검증
- Keycloak 인증/토큰 검증 API
- 서비스 클라이언트 생성 registry
- PostgreSQL / SQLite / MinIO / Milvus / Ollama / Langfuse / NATS 통합 진입점
- 서비스별 및 집계형 헬스체크
- 민감정보 마스킹, 설정 스냅샷, 직렬화, 재시도 유틸리티
- 선택적 Keycloak provisioning 진입점

### 1.3 제외 범위

- 개별 FastAPI 서비스의 API 엔드포인트 구현
- 도메인별 비즈니스 규칙
- 프론트엔드/UI
- 배포 IaC 세부 구현
- 외부 시스템 자체의 전체 운영 자동화

---

## 2. 시스템 개요

### 2.1 시스템 목표

`fastapi-core`는 서비스별로 반복되던 인프라 연동 코드를 공통 라이브러리로 흡수하여 다음을 달성해야 한다.

- 공통 설정 계약 제공
- 일관된 인증/권한 검증 API 제공
- 표준화된 서비스 생성 및 연결 수명주기 제공
- 공통 헬스체크 및 운영 진단 모델 제공
- 운영 보안 기본 원칙(민감정보 마스킹, TLS 기본값) 내장

### 2.2 예상 사용 방식

- 서비스 기동 시 `load_settings(env)` 호출
- 설정 객체 기반으로 `ServiceFactoryRegistry(settings)` 생성
- 필요한 서비스 클라이언트 생성
- 인증, 헬스체크, 유틸리티 API를 서비스 코드에서 재사용

### 2.3 핵심 공개 API

현재 기준 공개 API는 다음 범주를 포함해야 한다.

- 설정: `load_settings`, `Settings`, `SqliteConfig`
- 서비스 생성: `ServiceFactoryRegistry`, `ServiceClientWrapper`, `NatsConnectionBuilder`
- 헬스체크: `check_all_services`, `HealthCheckError`
- 인증: `KeycloakAuthService`, `AccessTokenResult`, `AuthenticatedUser`
- 프로비저닝: `KeycloakProvisioner`
- 유틸리티: `mask_sensitive_value`, `build_service_log_event`, `build_settings_snapshot`, `retry_call`, `to_serializable`, `Page`

---

## 3. 용어 정의

- **설정 계약(Configuration Contract)**: 환경변수 이름, 필수 여부, 기본값, 타입, 범위, 상호 의존 규칙의 집합
- **서비스 registry**: 서비스명으로 외부 서비스 클라이언트를 생성하는 중앙 진입점
- **필수 서비스**: 실패 시 전체 헬스체크 또는 서비스 기동에 영향을 주는 의존성
- **선택 서비스**: 실패하더라도 핵심 서비스 흐름을 막지 않는 의존성
- **민감정보**: secret, token, password, 전체 DSN/URI 등 로그 원문 노출이 금지되는 값
- **프로비저닝**: Keycloak realm/client/role 생성·갱신을 위한 선언형 관리 기능

---

## 4. 소프트웨어 아키텍처 요구사항

### 4.1 구성 원칙

- 시스템은 패키지 루트 import 기준의 안정적인 공개 API를 제공해야 한다.
- 설정, 인증, 서비스 생성, 헬스체크, 유틸리티는 관심사별로 분리되어야 한다.
- 서비스별 연결 로직은 registry 패턴으로 캡슐화되어야 한다.
- 공통 `check()` / `close()` 또는 동등한 인터페이스를 통해 수명주기 관리가 가능해야 한다.
- 선택 기능과 필수 기능은 설정과 헬스체크에서 구분 가능해야 한다.

### 4.2 기술 제약

- Python 패키지로 제공되어야 한다.
- FastAPI 서비스에서 직접 import 가능해야 한다.
- 환경변수 기반 설정 방식을 기본 전제로 해야 한다.
- 동기 서비스와 비동기 서비스(NATS 등)를 함께 수용해야 한다.

### 4.3 보안 기본 원칙

- 운영 기본값은 안전해야 한다.
- TLS 검증 비활성화는 기본값이 아니어야 한다.
- 민감정보는 로그, 설정 스냅샷, 구조화 이벤트에 원문으로 남기면 안 된다.

---

## 5. 기능 요구사항 상세

## 5.1 설정 로딩 및 검증

### SR-001 환경변수 입력
- 시스템은 입력으로 환경변수 매핑(`env`)을 받아야 한다.
- 시스템은 OS 환경변수뿐 아니라 테스트용 dict-like 입력도 수용할 수 있어야 한다.

### SR-002 공통 규칙
- 빈 문자열은 미설정으로 처리해야 한다.
- Boolean 문자열은 `true` / `false`를 해석해야 한다.
- 숫자형 값은 정수 또는 정의된 숫자 타입으로 변환되어야 한다.
- 숫자형 범위 위반 시 설정 오류가 발생해야 한다.

### SR-003 설정 객체
- `load_settings(env)`는 최상위 `Settings` 객체를 반환해야 한다.
- `Settings`는 최소한 다음 하위 설정을 포함할 수 있어야 한다:
  - common
  - keycloak
  - postgres
  - sqlite
  - minio
  - milvus
  - ollama
  - langfuse
  - nats

### SR-004 오류 처리
- 필수값 누락 시 `ConfigError` 또는 동등한 설정 오류를 발생시켜야 한다.
- 타입 변환 실패 시 어느 환경변수가 잘못되었는지 드러나야 한다.
- 조건부 필수값 누락 시 어떤 조건 때문에 필요한 값인지 설명 가능해야 한다.

### SR-005 PostgreSQL 규칙
- `POSTGRES_DSN`이 존재하면 개별 필드보다 우선 적용되어야 한다.
- DSN이 없으면 host/db/user/password 조합이 요구되어야 한다.
- 기본 포트와 timeout/pool 관련 기본값을 제공할 수 있어야 한다.

### SR-006 SQLite 규칙
- `SQLITE_PATH`는 파일 경로 또는 `:memory:`를 허용해야 한다.
- readonly, WAL, busy timeout 옵션을 해석해야 한다.
- 상대경로는 애플리케이션 작업 디렉터리 기준으로 해석되어야 한다.

### SR-007 선택 기능 규칙
- `LANGFUSE_ENABLED=false`와 같은 비활성화 플래그를 해석해야 한다.
- 선택 기능 비활성화 시 전체 설정 로딩은 성공해야 한다.

---

## 5.2 Keycloak 인증

### SR-020 인증 서비스 생성
- 시스템은 `KeycloakAuthService(settings, allowed_algorithms=None)`를 제공해야 한다.
- 설정 객체 기반으로 Keycloak 인증 동작을 구성해야 한다.

### SR-021 Access Token 발급
- `fetch_access_token(scope=None)`는 기본적으로 `client_credentials` grant를 사용해야 한다.
- 명시적 설정이 있을 경우 `password` grant를 지원할 수 있어야 한다.
- `password` grant 사용 시 username/password 누락은 설정 오류로 처리되어야 한다.

### SR-022 토큰 검증
- `extract_user_info(token)`는 raw JWT와 `Bearer <token>` 형식을 모두 허용해야 한다.
- 다음 검증 항목을 지원해야 한다:
  - 서명
  - 만료 시간
  - issuer
  - 선택적 audience
  - 허용 알고리즘

### SR-023 인증 결과 구조
- 검증 성공 시 반환 구조는 최소한 다음 필드를 포함해야 한다:
  - sub
  - preferred_username
  - email
  - name
  - realm_roles
  - client_roles
  - claims

### SR-024 인증 오류
- 설정 오류, 인증 오류, 일시 오류, 일반 토큰 오류를 구분할 수 있어야 한다.
- 검증 실패는 `TokenValidationError` 또는 동등한 오류로 드러나야 한다.

### SR-025 운영 보안
- 운영 기본값으로 `password` grant를 강제하면 안 된다.
- Access Token 및 Refresh Token 원문은 로그에 기록되면 안 된다.

---

## 5.3 서비스 클라이언트 registry

### SR-030 registry 생성
- 시스템은 `ServiceFactoryRegistry(settings)`를 제공해야 한다.
- registry는 설정 객체를 기반으로 서비스 클라이언트를 생성해야 한다.

### SR-031 지원 서비스
- 최소 지원 대상:
  - keycloak
  - postgres
  - sqlite
  - minio
  - milvus
  - ollama
  - langfuse
  - nats

### SR-032 생성 인터페이스
- registry는 다음 메서드를 제공해야 한다:
  - `create_client(service_name)`
  - `create_clients(services)`
  - `close_all()`

### SR-033 반환 타입
- 일반 서비스는 `ServiceClientWrapper` 또는 동등한 래퍼를 반환해야 한다.
- NATS는 비동기 연결 builder(`NatsConnectionBuilder`)를 반환할 수 있어야 한다.
- Langfuse는 설정 상태에 따라 `None`을 반환할 수 있어야 한다.

### SR-034 오류 모델
- 지원하지 않는 서비스명은 `UnsupportedServiceError`로 처리해야 한다.
- 래퍼 생성 실패와 실제 클라이언트 오류를 구분해야 한다.

### SR-035 수명주기 관리
- 생성된 클라이언트는 `check()` / `close()` 또는 동등한 메서드를 제공해야 한다.
- registry는 생성한 클라이언트 일괄 종료를 지원해야 한다.

---

## 5.4 헬스체크

### SR-040 개별 헬스체크
- 각 서비스 통합은 기본 연결 가능 여부를 확인하는 `check()`를 제공해야 한다.

### SR-041 기본 헬스체크 기대 동작
- Keycloak: access token 획득 기반 확인
- PostgreSQL: `SELECT 1`
- SQLite: `SELECT 1`
- MinIO: `list_buckets()`
- Milvus: `list_collections()`
- Ollama: `ps()`
- Langfuse: `auth_check()`
- NATS: connect 후 `flush()` 또는 동등한 확인

### SR-042 집계 헬스체크
- 시스템은 `check_all_services(service_checks, required_services=None, parallel=False)`를 제공해야 한다.
- 입력은 서비스명 → check callable 매핑이어야 한다.

### SR-043 집계 결과
- 최소 다음 정보를 제공해야 한다:
  - 전체 성공 여부
  - 서비스별 성공 여부
  - 서비스별 지연 시간
  - 마스킹된 오류 메시지

### SR-044 필수 서비스 실패
- 필수 서비스 실패 시 `HealthCheckError` 또는 동등한 예외를 발생시킬 수 있어야 한다.
- 선택 서비스 실패는 결과에 남기되 전체 동작 정책은 호출자가 선택 가능해야 한다.

### SR-045 병렬 실행
- `parallel=True`일 때 병렬 실행을 지원해야 한다.
- 병렬 실행 여부와 무관하게 결과 포맷은 일관되어야 한다.

---

## 5.5 운영 유틸리티

### SR-050 민감정보 마스킹
- `mask_sensitive_value(raw)`는 password, token, secret, DSN/URI 민감값을 마스킹해야 한다.

### SR-051 설정 스냅샷
- `build_settings_snapshot(settings)`는 민감정보가 마스킹된 스냅샷을 반환해야 한다.

### SR-052 구조화 이벤트
- `build_service_log_event(...)`는 서비스 연결/헬스체크/재시도 이벤트를 구조화된 dict로 생성할 수 있어야 한다.

### SR-053 재시도 유틸리티
- `retry_call(operation, ..., retry_on, max_attempts)`는 일시적 오류에 대한 동기 함수 재시도를 지원해야 한다.

### SR-054 직렬화 유틸리티
- `to_serializable(value)`는 dataclass, 모델 객체, datetime 등 복합 값을 JSON 친화 구조로 변환해야 한다.

### SR-055 페이지네이션 타입
- `Page`는 공통 페이지네이션 표현용 타입으로 제공되어야 한다.

---

## 5.6 NATS 메시징

### SR-060 연결 설정
- `NATS_SERVERS`는 쉼표 구분 URL 목록을 허용해야 한다.
- 인증 방식은 아래 중 하나를 지원해야 한다:
  - user/password
  - token
  - creds file

### SR-061 연결 builder
- NATS 통합은 즉시 연결된 클라이언트 대신 비동기 builder를 반환할 수 있어야 한다.
- 실제 연결은 `await connect()` 또는 `await check()`에서 수행될 수 있어야 한다.

### SR-062 운영 제약
- 연결 이름, 연결 timeout, 최대 재연결 횟수를 설정할 수 있어야 한다.
- NATS 연결 실패는 다른 설정 오류와 구분 가능해야 한다.

---

## 5.7 Keycloak provisioning

### SR-070 프로비저닝 활성화
- `KEYCLOAK_PROVISIONING_ENABLED=true`이면 프로비저닝 관련 설정 검증이 활성화되어야 한다.

### SR-071 필수 입력
- 프로비저닝이 활성화되면 관리자 인증용 realm/client/user/password/secret 등 조건부 입력값을 검증해야 한다.

### SR-072 동작 특성
- 프로비저닝은 멱등 실행을 지원해야 한다.
- dry-run을 지원해야 한다.
- 생성/갱신/변경 없음/실패 상태를 구분할 수 있어야 한다.
- 선언에서 제거된 리소스를 자동 삭제하면 안 된다.

---

## 6. 데이터 모델 및 인터페이스 요구사항

### 6.1 Settings
- 최상위 설정 객체로서 공통 및 서비스별 설정 하위 객체를 포함해야 한다.

### 6.2 SqliteConfig
- SQLite 전용 설정 구조를 제공해야 한다.
- path, readonly, WAL, busy timeout 같은 속성을 표현할 수 있어야 한다.

### 6.3 AccessTokenResult
- 최소 필드:
  - access_token
  - token_type
  - expires_in
  - refresh_token
  - scope

### 6.4 AuthenticatedUser
- 최소 필드:
  - sub
  - preferred_username
  - email
  - given_name (있을 수 있음)
  - family_name (있을 수 있음)
  - name
  - realm_roles
  - client_roles
  - claims

### 6.5 헬스체크 결과
- 서비스별 결과는 성공 여부, 지연 시간, 마스킹된 메시지를 담을 수 있어야 한다.
- 집계 결과는 전체 성공 여부와 서비스별 결과 컬렉션을 포함해야 한다.

---

## 7. 오류 처리 요구사항

### 7.1 오류 분류
시스템은 최소 다음 오류 범주를 구분해야 한다.

- 설정 오류
- 인증 오류
- 토큰 검증 오류
- 일시적 외부 서비스 오류
- 서비스 클라이언트 생성 오류
- 헬스체크 실패 오류
- 지원하지 않는 서비스 오류

### 7.2 오류 메시지 원칙
- 오류 메시지는 문제 환경변수 또는 실패 서비스를 식별 가능해야 한다.
- 민감정보가 포함되면 안 된다.
- 운영 분석에 필요한 최소 맥락은 유지해야 한다.

---

## 8. 비기능 요구사항

### 8.1 신뢰성
- 설정 오류는 기동 초기에 발견되어야 한다.
- 공통 헬스체크는 필수 의존성 문제를 빠르게 드러내야 한다.

### 8.2 보안
- 민감정보 마스킹은 기본 동작이어야 한다.
- TLS 검증 비활성화는 명시적 opt-out이어야 한다.

### 8.3 유지보수성
- 공개 API는 서비스 코드에서 재사용하기 쉬워야 한다.
- 새로운 서비스 통합 추가 시 기존 호출부 수정이 최소화되어야 한다.

### 8.4 관측성
- 장애 원인은 구조화된 이벤트와 마스킹된 메시지로 추적 가능해야 한다.

### 8.5 개발 생산성
- 신규 서비스는 공통 SDK와 문서만으로 통합을 시작할 수 있어야 한다.

---

## 9. 검증 및 테스트 요구사항

### 9.1 설정 검증 테스트
- 필수값 누락
- 타입 오류
- 범위 오류
- 조건부 필수 규칙
- 비활성화 플래그 해석

### 9.2 인증 테스트
- 토큰 발급 성공/실패
- JWT 검증 성공/실패
- audience/issuer 검증
- `Bearer <token>` 입력 처리

### 9.3 서비스 통합 테스트
- registry를 통한 서비스별 클라이언트 생성
- `check()` / `close()` 동작
- NATS 비동기 builder 동작

### 9.4 헬스체크 테스트
- 개별 서비스 성공/실패
- 필수 서비스 실패 시 예외
- 병렬/직렬 집계 결과 일관성

### 9.5 보안 테스트
- 마스킹 함수가 민감정보를 숨기는지 확인
- 설정 스냅샷에 민감정보가 포함되지 않는지 확인

---

## 10. 추적 매트릭스 (PRD → SRS)

- PRD 설정 요구사항 → SRS 5.1
- PRD 인증/인가 요구사항 → SRS 5.2
- PRD 서비스 클라이언트 생성 요구사항 → SRS 5.3
- PRD 헬스체크 요구사항 → SRS 5.4
- PRD 운영/보안 유틸리티 요구사항 → SRS 5.5
- PRD 메시징 요구사항 → SRS 5.6
- PRD 프로비저닝 요구사항 → SRS 5.7

---

## 11. 오픈 이슈

- 실제 코드베이스 기준 공개 API와 문서상의 공개 API가 완전히 일치하는지 검증 필요
- Langfuse와 NATS의 기본 활성화 정책 확정 필요
- 헬스체크 결과를 FastAPI 엔드포인트에서 어떤 스키마로 노출할지 별도 정의 필요
- 예외 타입을 외부 소비자에게 어느 수준까지 노출할지 정책 결정 필요
- 프로비저닝 기능의 MVP 포함 여부 확정 필요

---

## 12. 참고 문서

- `docs/prd.md`
- `README.md`
- `wiki/entities/docmesh-py-core.md`
- `wiki/concepts/service-factory-registry.md`
- `wiki/concepts/service-health-check-aggregation.md`
- `wiki/concepts/keycloak-authentication-api.md`
- `wiki/concepts/service-configuration-contracts.md`

---

## 부록 A. 문서 상태 메모

이 초안은 현재 확인 가능한 README 및 wiki에 ingest된 `docmesh-py-core` API/config 문서를 기준으로 작성되었다. 실제 구현 코드와 테스트 스위트를 확인하면서 API 레벨, 예외 타입, 결과 스키마, 메시징 정책을 추가 구체화해야 한다.
