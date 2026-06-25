# fastapi-core 설정 정의서

> 문서 목적: `fastapi-core`가 사용하는 환경변수 기반 설정 계약을 정의한다.
> 기준 문서: `docs/prd.md`, `docs/srs.md`, `docs/api.md`
> 문서 상태: 초안(v0.1)

---

## 1. 문서 개요

- 문서명: `fastapi-core 설정 정의서`
- 작성일: `2026-06-25`
- 작성자: `Hermes Agent 초안 / 사용자 검토 필요`
- 버전: `v0.1`
- 상태: `draft`

### 1.1 목적

이 문서는 `fastapi-core`가 런타임에 사용하는 환경변수, 필수 여부, 타입, 기본 규칙, 보안 원칙을 정의한다. 서비스 개발자와 운영자는 이 문서를 기준으로 `.env`, 컨테이너 환경변수, secret manager, 배포 플랫폼 설정을 구성해야 한다.

### 1.2 범위

다음 설정 범주를 포함한다.

- 공통 설정
- Keycloak 인증/토큰 검증/프로비저닝 설정
- PostgreSQL 설정
- SQLite 설정
- MinIO 설정
- Milvus 설정
- Ollama 설정
- Langfuse 설정
- NATS 설정
- 보안 및 운영 규칙

### 1.3 비범위

- 각 외부 시스템 자체의 상세 운영 매뉴얼
- Kubernetes Secret / Vault / AWS Secrets Manager 구체 구현
- 서비스별 도메인 전용 환경변수

---

## 2. 공통 규칙

### 2.1 설정 로딩 원칙

- 모든 런타임 설정은 환경변수에서 읽는다.
- `load_settings(env)`는 OS 환경변수뿐 아니라 dict-like 입력도 받을 수 있어야 한다.
- 빈 문자열(`""`)은 미설정으로 처리한다.
- Boolean 값은 `true` / `false` 문자열로 표현한다.
- 숫자형 값은 정수/숫자 타입으로 변환하고 범위를 검증한다.
- 조건부 필수 항목은 관련 feature flag 또는 인증 방식에 따라 검증한다.

### 2.2 필수 여부 규칙

- **필수(Required)**: 기능 사용을 위해 반드시 있어야 하는 값
- **선택(Optional)**: 없어도 기본값 또는 비활성화 동작으로 처리 가능한 값
- **조건부 필수(Conditional)**: 특정 기능/모드가 활성화되었을 때만 필요한 값

### 2.3 보안 규칙

- `secret`, `token`, `password`, 전체 DSN/URI는 로그에 원문으로 남기지 않는다.
- `build_settings_snapshot(settings)` 결과는 반드시 마스킹된 값만 포함해야 한다.
- 운영 환경에서는 TLS 검증 비활성화를 기본값으로 두지 않는다.
- 민감정보는 가능하면 secret manager 또는 배포 플랫폼의 secret 기능으로 주입한다.

### 2.4 서비스별 timeout/retry 원칙

- timeout/retry는 전역 공통값이 아니라 서비스별로 관리한다.
- 외부 의존성마다 가용성/지연 특성이 다르므로 독립 설정이 필요하다.

---

## 3. 공통 설정

| 환경변수 | 필수 여부 | 타입 | 설명 |
| --- | --- | --- | --- |
| `DOCMESH_ENV` | 선택 | string | 실행 환경 식별자 (`local`, `dev`, `staging`, `prod` 등) |
| `DOCMESH_HEALTHCHECK_ENABLED` | 선택 | bool | 공통 헬스체크 기능 활성화 여부 |

### 예시

```env
DOCMESH_ENV=local
DOCMESH_HEALTHCHECK_ENABLED=true
```

---

## 4. Keycloak 설정

Keycloak 설정은 크게 세 영역으로 나뉜다.

1. 인증/JWT 검증
2. 토큰 획득
3. 프로비저닝

## 4.1 기본 인증/JWT 검증

| 환경변수 | 필수 여부 | 타입 | 설명 |
| --- | --- | --- | --- |
| `KEYCLOAK_URL` | 필수 | string | Keycloak base URL |
| `KEYCLOAK_REALM` | 필수 | string | Realm 이름 |
| `KEYCLOAK_CLIENT_ID` | 필수 | string | 기본 client id |
| `KEYCLOAK_CLIENT_SECRET` | 조건부 | string | confidential client용 client secret |
| `KEYCLOAK_AUDIENCE` | 선택 | string | JWT audience 검증 값 |
| `KEYCLOAK_VERIFY_SSL` | 선택 | bool | TLS 인증서 검증 여부, 운영 기본값은 `true` |
| `KEYCLOAK_ALLOWED_ALGORITHMS` | 선택 | string | 허용 JWT 알고리즘 목록(쉼표 구분 등 구현 정책에 따름) |
| `KEYCLOAK_TIMEOUT_SECONDS` | 선택 | int | Keycloak HTTP timeout |
| `KEYCLOAK_RETRY_COUNT` | 선택 | int | 일시 오류 재시도 횟수 |
| `KEYCLOAK_JWKS_CACHE_TTL_SECONDS` | 선택 | int | JWKS cache TTL |

### 4.2 토큰 획득

| 환경변수 | 필수 여부 | 타입 | 설명 |
| --- | --- | --- | --- |
| `KEYCLOAK_TOKEN_GRANT_TYPE` | 선택 | string | 기본값은 `client_credentials`, 필요 시 `password` |
| `KEYCLOAK_USERNAME` | 조건부 | string | `password` grant 사용 시 필요 |
| `KEYCLOAK_PASSWORD` | 조건부 | string | `password` grant 사용 시 필요 |
| `KEYCLOAK_SCOPE` | 선택 | string | 기본 scope |

### 4.3 프로비저닝

| 환경변수 | 필수 여부 | 타입 | 설명 |
| --- | --- | --- | --- |
| `KEYCLOAK_PROVISIONING_ENABLED` | 선택 | bool | 프로비저닝 활성화 여부 |
| `KEYCLOAK_ADMIN_REALM` | 조건부 | string | Admin API 접속 realm |
| `KEYCLOAK_ADMIN_CLIENT_ID` | 조건부 | string | Admin client id |
| `KEYCLOAK_ADMIN_CLIENT_SECRET` | 조건부 | string | Admin client secret |
| `KEYCLOAK_ADMIN_USERNAME` | 조건부 | string | Admin username |
| `KEYCLOAK_ADMIN_PASSWORD` | 조건부 | string | Admin password |
| `KEYCLOAK_PROVISIONING_DRY_RUN` | 선택 | bool | dry-run 수행 여부 |

### Keycloak 규칙

- 기본 token grant는 `client_credentials`다.
- `password` grant는 명시적 설정이 있을 때만 사용한다.
- 운영 기본값으로 `password` grant를 강제하지 않는다.
- `KEYCLOAK_PROVISIONING_ENABLED=true`이면 관리자 인증 관련 값이 조건부 필수가 된다.
- 프로비저닝은 최소 권한 service account 사용을 권장한다.

### 예시

```env
KEYCLOAK_URL=https://keycloak.example.com
KEYCLOAK_REALM=docmesh
KEYCLOAK_CLIENT_ID=fastapi-core
KEYCLOAK_CLIENT_SECRET=[REDACTED]
KEYCLOAK_VERIFY_SSL=true
KEYCLOAK_AUDIENCE=docmesh-api
KEYCLOAK_TIMEOUT_SECONDS=5
KEYCLOAK_RETRY_COUNT=2
KEYCLOAK_TOKEN_GRANT_TYPE=client_credentials
```

---

## 5. PostgreSQL 설정

| 환경변수 | 필수 여부 | 타입 | 설명 |
| --- | --- | --- | --- |
| `POSTGRES_DSN` | 조건부 | string | PostgreSQL 연결 DSN |
| `POSTGRES_HOST` | 조건부 | string | DB host |
| `POSTGRES_PORT` | 선택 | int | DB port |
| `POSTGRES_DB` | 조건부 | string | DB name |
| `POSTGRES_USER` | 조건부 | string | DB user |
| `POSTGRES_PASSWORD` | 조건부 | string | DB password |
| `POSTGRES_SSL_MODE` | 선택 | string | SSL mode |
| `POSTGRES_CONNECT_TIMEOUT_SECONDS` | 선택 | int | 연결 timeout |
| `POSTGRES_POOL_MIN_SIZE` | 선택 | int | 최소 pool 크기 |
| `POSTGRES_POOL_MAX_SIZE` | 선택 | int | 최대 pool 크기 |

### PostgreSQL 규칙

- `POSTGRES_DSN`이 있으면 host/db/user/password 조합보다 우선한다.
- `POSTGRES_DSN`이 없으면 host, db, user, password가 함께 필요하다.
- DSN/URI 전체 문자열은 로그에 원문 노출하면 안 된다.

### 예시

```env
POSTGRES_DSN=postgresql://docmesh:[REDACTED]@postgres:5432/docmesh
POSTGRES_CONNECT_TIMEOUT_SECONDS=5
POSTGRES_POOL_MIN_SIZE=1
POSTGRES_POOL_MAX_SIZE=10
```

---

## 6. SQLite 설정

| 환경변수 | 필수 여부 | 타입 | 설명 |
| --- | --- | --- | --- |
| `SQLITE_PATH` | 필수 | string | SQLite 파일 경로 또는 `:memory:` |
| `SQLITE_READONLY` | 선택 | bool | 읽기 전용 연결 여부 |
| `SQLITE_ENABLE_WAL` | 선택 | bool | WAL 모드 활성화 여부 |
| `SQLITE_BUSY_TIMEOUT_MS` | 선택 | int | busy timeout(ms) |

### SQLite 규칙

- `SQLITE_PATH`는 파일 경로 또는 `:memory:`를 허용한다.
- 상대경로는 애플리케이션 작업 디렉터리 기준으로 해석한다.
- 로컬 개발/단위 테스트/경량 통합 테스트에 적합하다.

### 예시

```env
SQLITE_PATH=./data/app.db
SQLITE_READONLY=false
SQLITE_ENABLE_WAL=true
SQLITE_BUSY_TIMEOUT_MS=5000
```

---

## 7. MinIO 설정

| 환경변수 | 필수 여부 | 타입 | 설명 |
| --- | --- | --- | --- |
| `MINIO_ENDPOINT` | 필수 | string | MinIO endpoint |
| `MINIO_ACCESS_KEY` | 필수 | string | access key |
| `MINIO_SECRET_KEY` | 필수 | string | secret key |
| `MINIO_SECURE` | 선택 | bool | HTTPS 사용 여부 |
| `MINIO_REGION` | 선택 | string | region |
| `MINIO_BUCKET` | 선택 | string | 기본 bucket |
| `MINIO_TIMEOUT_SECONDS` | 선택 | int | 연결/요청 timeout |
| `MINIO_RETRY_COUNT` | 선택 | int | 재시도 횟수 |

### 예시

```env
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=[REDACTED]
MINIO_SECRET_KEY=[REDACTED]
MINIO_SECURE=false
MINIO_TIMEOUT_SECONDS=5
MINIO_RETRY_COUNT=2
```

---

## 8. Milvus 설정

| 환경변수 | 필수 여부 | 타입 | 설명 |
| --- | --- | --- | --- |
| `MILVUS_URI` | 필수 | string | Milvus 접속 URI |
| `MILVUS_TOKEN` | 선택 | string | 인증 token |
| `MILVUS_DB_NAME` | 선택 | string | 대상 DB 이름 |
| `MILVUS_COLLECTION` | 선택 | string | 기본 collection |
| `MILVUS_SECURE` | 선택 | bool | TLS 사용 여부 |
| `MILVUS_TIMEOUT_SECONDS` | 선택 | int | 연결/요청 timeout |
| `MILVUS_RETRY_COUNT` | 선택 | int | 재시도 횟수 |

### 예시

```env
MILVUS_URI=http://milvus:19530
MILVUS_DB_NAME=default
MILVUS_COLLECTION=documents
MILVUS_SECURE=false
MILVUS_TIMEOUT_SECONDS=5
MILVUS_RETRY_COUNT=2
```

---

## 9. Ollama 설정

| 환경변수 | 필수 여부 | 타입 | 설명 |
| --- | --- | --- | --- |
| `OLLAMA_HOST` | 필수 | string | Ollama base URL |
| `OLLAMA_GENERATION_MODEL` | 선택 | string | 기본 생성 모델 |
| `OLLAMA_EMBEDDING_MODEL` | 선택 | string | 기본 임베딩 모델 |
| `OLLAMA_TIMEOUT_SECONDS` | 선택 | int | 요청 timeout |
| `OLLAMA_RETRY_COUNT` | 선택 | int | 재시도 횟수 |

### 예시

```env
OLLAMA_HOST=http://ollama:11434
OLLAMA_GENERATION_MODEL=qwen3:8b
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
OLLAMA_TIMEOUT_SECONDS=30
OLLAMA_RETRY_COUNT=1
```

---

## 10. Langfuse 설정

| 환경변수 | 필수 여부 | 타입 | 설명 |
| --- | --- | --- | --- |
| `LANGFUSE_ENABLED` | 선택 | bool | Langfuse 활성화 여부 |
| `LANGFUSE_HOST` | 조건부 | string | Langfuse host |
| `LANGFUSE_PUBLIC_KEY` | 조건부 | string | public key |
| `LANGFUSE_SECRET_KEY` | 조건부 | string | secret key |
| `LANGFUSE_RELEASE` | 선택 | string | 애플리케이션 release 식별자 |
| `LANGFUSE_ENVIRONMENT` | 선택 | string | Langfuse 환경 식별자 |
| `LANGFUSE_TIMEOUT_SECONDS` | 선택 | int | 요청 timeout |
| `LANGFUSE_RETRY_COUNT` | 선택 | int | 재시도 횟수 |

### Langfuse 규칙

- `LANGFUSE_ENABLED=false`이면 Langfuse 통합은 비활성화될 수 있어야 한다.
- 비활성화 상태에서는 설정 로딩 자체가 실패하면 안 된다.
- 활성화된 경우 host/public key/secret key가 조건부 필수다.

### 예시

```env
LANGFUSE_ENABLED=true
LANGFUSE_HOST=http://langfuse-web:3000
LANGFUSE_PUBLIC_KEY=[REDACTED]
LANGFUSE_SECRET_KEY=[REDACTED]
LANGFUSE_ENVIRONMENT=local
LANGFUSE_TIMEOUT_SECONDS=5
LANGFUSE_RETRY_COUNT=2
```

---

## 11. NATS 설정

| 환경변수 | 필수 여부 | 타입 | 설명 |
| --- | --- | --- | --- |
| `NATS_SERVERS` | 필수 | string | 쉼표 구분 서버 목록 |
| `NATS_USER` | 조건부 | string | user/password 인증용 사용자 |
| `NATS_PASSWORD` | 조건부 | string | user/password 인증용 비밀번호 |
| `NATS_TOKEN` | 조건부 | string | token 인증값 |
| `NATS_CREDS_FILE` | 조건부 | string | creds file 경로 |
| `NATS_NAME` | 선택 | string | 연결 이름 |
| `NATS_CONNECT_TIMEOUT_SECONDS` | 선택 | int | 연결 timeout |
| `NATS_MAX_RECONNECT_ATTEMPTS` | 선택 | int | 최대 재연결 횟수 |

### NATS 인증 규칙

다음 중 하나를 선택한다.

1. `NATS_USER` + `NATS_PASSWORD`
2. `NATS_TOKEN`
3. `NATS_CREDS_FILE`

### NATS 규칙

- `NATS_SERVERS`는 쉼표 구분 URL 목록을 허용한다.
- 인증 방식은 하나 이상 지정되어야 한다.
- 연결 실패는 일반 설정 오류와 구분 가능한 오류로 다뤄야 한다.

### 예시

```env
NATS_SERVERS=nats://nats:4222
NATS_TOKEN=[REDACTED]
NATS_NAME=fastapi-core
NATS_CONNECT_TIMEOUT_SECONDS=3
NATS_MAX_RECONNECT_ATTEMPTS=10
```

---

## 12. 권장 배포 패턴

### 12.1 로컬 개발

- `DOCMESH_ENV=local`
- `SQLITE_PATH` 또는 로컬 PostgreSQL 사용
- `LANGFUSE_ENABLED=false` 또는 로컬 Langfuse 연결
- `KEYCLOAK_VERIFY_SSL=false`는 로컬 self-signed 환경에서만 제한적으로 허용

### 12.2 테스트 환경

- SQLite `:memory:` 또는 전용 테스트 DB 사용
- 외부 서비스는 mock/stub 또는 독립 테스트 인스턴스 사용
- 헬스체크는 선택 서비스 비활성화 정책을 명확히 분리

### 12.3 운영 환경

- secret/token/password는 secret manager 또는 배포 secret에 저장
- TLS 검증 기본 활성화
- `password` grant 기본 사용 금지
- 프로비저닝 활성화 시 최소 권한 계정 사용
- DSN/URI, token, secret은 로그와 진단 출력에서 마스킹

---

## 13. 설정 오류 처리 기준

설정 로더는 다음 상황에서 오류를 반환해야 한다.

- 필수 환경변수 누락
- 숫자형 값 파싱 실패
- 허용 범위를 벗어난 timeout/retry 값
- 조건부 필수 항목 누락
- 상호 배타적이거나 모순된 인증 설정

오류 메시지는 다음 원칙을 따라야 한다.

- 어떤 환경변수가 문제인지 식별 가능해야 한다.
- 민감정보 원문을 포함하면 안 된다.
- 가능하면 수정 방향을 제시해야 한다.

예시:

- `ConfigError: KEYCLOAK_URL is required`
- `ConfigError: NATS authentication requires one of user/password, token, or creds file`
- `ConfigError: POSTGRES_PORT must be a positive integer`

---

## 14. 샘플 환경변수 묶음

### 14.1 최소 개발 예시

```env
DOCMESH_ENV=local
DOCMESH_HEALTHCHECK_ENABLED=true

KEYCLOAK_URL=http://keycloak:8080
KEYCLOAK_REALM=docmesh
KEYCLOAK_CLIENT_ID=fastapi-core
KEYCLOAK_CLIENT_SECRET=[REDACTED]
KEYCLOAK_VERIFY_SSL=false

SQLITE_PATH=./data/app.db
SQLITE_ENABLE_WAL=true

OLLAMA_HOST=http://ollama:11434
LANGFUSE_ENABLED=false

NATS_SERVERS=nats://nats:4222
NATS_TOKEN=[REDACTED]
```

### 14.2 운영 예시

```env
DOCMESH_ENV=prod
DOCMESH_HEALTHCHECK_ENABLED=true

KEYCLOAK_URL=https://keycloak.example.com
KEYCLOAK_REALM=docmesh
KEYCLOAK_CLIENT_ID=fastapi-core
KEYCLOAK_CLIENT_SECRET=[REDACTED]
KEYCLOAK_VERIFY_SSL=true
KEYCLOAK_AUDIENCE=docmesh-api

POSTGRES_DSN=[REDACTED]
MINIO_ENDPOINT=minio.internal:9000
MINIO_ACCESS_KEY=[REDACTED]
MINIO_SECRET_KEY=[REDACTED]
MINIO_SECURE=true

MILVUS_URI=https://milvus.internal:19530
MILVUS_TOKEN=[REDACTED]
MILVUS_SECURE=true

OLLAMA_HOST=http://ollama.internal:11434

LANGFUSE_ENABLED=true
LANGFUSE_HOST=https://langfuse.example.com
LANGFUSE_PUBLIC_KEY=[REDACTED]
LANGFUSE_SECRET_KEY=[REDACTED]

NATS_SERVERS=nats://nats-a:4222,nats://nats-b:4222
NATS_CREDS_FILE=/run/secrets/nats.creds
```

---

## 15. 참고 문서

- `docs/prd.md`
- `docs/srs.md`
- `docs/api.md`
- `README.md`
- `wiki/concepts/service-configuration-contracts.md`
- `wiki/concepts/keycloak-authentication-api.md`

---

## 부록 A. 문서 상태 메모

이 초안은 현재 확인 가능한 PRD/SRS/API 문서와 wiki에 ingest된 `docmesh-py-core` 설정 가이드를 기준으로 작성되었다. 실제 구현 코드가 준비되면 정확한 환경변수 이름, 기본값, 허용 범위, 설정 객체 필드와 1:1로 재검증해야 한다.
