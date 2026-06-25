# fastapi-core 설정 정의서

> 문서 목적: `fastapi-core`의 설정을 **FastAPI 앱 조립과 request/auth/lifecycle 관점**에서 정의한다.
> 기준 문서: `docs/prd.md`, `docs/srs.md`, `docs/api.md`, `docs/messaging.md`
> 문서 상태: 초안(v0.2)

---

## 1. 문서 개요

이 문서는 단순히 환경변수 목록을 나열하는 문서가 아니라, `fastapi-core`가 FastAPI 앱을 조립할 때 어떤 설정이 어떤 계층에 영향을 주는지 설명한다.

- 작성일: `2026-06-25`
- 작성자: `Hermes Agent 초안 / 사용자 검토 필요`
- 버전: `v0.2`
- 상태: `draft`

핵심 관점은 다음과 같다.

- `create_app(...)`가 어떤 설정을 소비하는가
- auth router / health router / dependency가 어떤 설정에 의존하는가
- startup / shutdown / lifespan에서 어떤 외부 설정이 필요한가
- 운영자가 어떤 설정을 필수로 관리해야 하는가

---

## 2. 설정 계층 모델

`fastapi-core`의 설정은 크게 네 층으로 나눈다.

1. **FastAPI 앱 설정**
   - `root_path`
   - CORS
   - health endpoint 동작
2. **인증 설정**
   - Keycloak URL / realm / client
   - JWT 검증 / token 발급 방식
3. **외부 의존성 설정**
   - PostgreSQL / SQLite / MinIO / Milvus / Ollama / Langfuse / NATS
4. **운영/보안 설정**
   - timeout / retry / TLS / secret 처리 원칙

즉, 설정은 단순한 SDK 연결값이 아니라 **FastAPI 애플리케이션의 조립 규칙**에 직접 연결된다.

---

## 3. FastAPI 앱 설정

## 3.1 App factory 연계

`create_app(config=None, settings=None, lifespan=None, include_auth_router=True)`는 설정을 기반으로 다음을 결정한다.

- `FastAPI(root_path=...)` 생성
- CORS middleware 등록
- auth router 포함 여부
- health router 포함
- auth provider / external dependency의 lifecycle 연결

## 3.2 핵심 앱 설정 항목

| 설정 항목 | 적용 위치 | 설명 |
| --- | --- | --- |
| `root_path` | `FastAPI(...)` | reverse proxy 하위 경로 배포 시 사용 |
| CORS origins | `CORSMiddleware` | 허용 origin 목록 |
| CORS credentials | `CORSMiddleware` | credential 허용 여부 |
| `include_auth_router` | app factory 옵션 | `/token`, `/user` 라우터 포함 여부 |
| custom lifespan | app factory 옵션 | startup/shutdown 자원 초기화 로직 주입 |

> 주의: 이 문서의 일부 설정은 현재 공개된 wheel 구조와 문서 기준으로 정리한 것이다. 실제 필드명은 구현 소스 기준으로 최종 고정해야 한다.

---

## 4. 공통 설정 원칙

### 4.1 입력 원칙

- 설정은 환경변수 또는 환경 기반 설정 객체에서 읽는다.
- 빈 문자열은 미설정으로 처리한다.
- Boolean은 `true` / `false` 문자열을 사용한다.
- 숫자형 값은 타입과 범위를 검증해야 한다.
- 설정 오류는 앱 기동 초기에 발견되어야 한다.

### 4.2 보안 원칙

- `token`, `password`, `secret`, 전체 DSN/URI는 로그에 원문 노출 금지
- 설정 스냅샷은 반드시 마스킹
- 운영 환경 기본값은 안전한 방향이어야 함
- TLS 검증 비활성화는 기본값이 아니어야 함

### 4.3 FastAPI 관점 원칙

- auth dependency가 기대하는 설정은 앱 기동 전에 유효해야 한다.
- readiness가 참조하는 외부 의존성 설정은 startup 정책과 일치해야 한다.
- `app.state`에 저장되는 provider/connection은 설정 검증이 끝난 뒤 주입되어야 한다.

---

## 5. 인증 설정 (Keycloak)

이 설정군은 다음 계층에 직접 영향을 준다.

- `POST /token`
- `GET /user`
- `get_auth_provider()`
- `get_current_user()`
- readiness의 인증 의존성 확인

## 5.1 필수 핵심 설정

| 환경변수 | 필수 여부 | 설명 |
| --- | --- | --- |
| `KEYCLOAK_URL` | 필수 | Keycloak base URL |
| `KEYCLOAK_REALM` | 필수 | realm 이름 |
| `KEYCLOAK_CLIENT_ID` | 필수 | auth client id |
| `KEYCLOAK_CLIENT_SECRET` | 조건부 | confidential client 사용 시 필요 |

## 5.2 JWT / token 검증 설정

| 환경변수 | 필수 여부 | 설명 |
| --- | --- | --- |
| `KEYCLOAK_AUDIENCE` | 선택 | audience 검증 값 |
| `KEYCLOAK_VERIFY_SSL` | 선택 | TLS 검증 여부 |
| `KEYCLOAK_ALLOWED_ALGORITHMS` | 선택 | 허용 JWT 알고리즘 |
| `KEYCLOAK_TIMEOUT_SECONDS` | 선택 | Keycloak HTTP timeout |
| `KEYCLOAK_RETRY_COUNT` | 선택 | 재시도 횟수 |

## 5.3 Token grant 설정

| 환경변수 | 필수 여부 | 설명 |
| --- | --- | --- |
| `KEYCLOAK_TOKEN_GRANT_TYPE` | 선택 | 기본 `client_credentials`, 필요 시 `password` |
| `KEYCLOAK_USERNAME` | 조건부 | `password` grant 사용 시 필요 |
| `KEYCLOAK_PASSWORD` | 조건부 | `password` grant 사용 시 필요 |
| `KEYCLOAK_SCOPE` | 선택 | 기본 scope |

## 5.4 FastAPI 계층 영향

- `/token`은 Keycloak 토큰 발급 설정에 직접 의존한다.
- `get_current_user()`는 JWT 검증 관련 설정에 의존한다.
- `require_permissions(...)`는 토큰에서 추출된 roles 구조에 의존한다.
- 잘못된 인증 설정은 라우터 동작 실패 또는 401 증가로 나타난다.

## 5.5 권장 정책

- 운영 기본 grant는 `client_credentials`
- `password` grant는 제한적으로만 사용
- `KEYCLOAK_VERIFY_SSL=true` 기본 유지
- client secret과 password는 반드시 secret 관리 체계로 주입

---

## 6. Health / readiness 관련 설정

현재 문서 기준 readiness는 외부 인증 또는 핵심 의존성 준비 상태와 연결된다.

기본 계약:
- readiness 응답은 최소 `status` 필드를 포함한다.
- 의존성별 세부 상태는 선택적으로 `details` 같은 확장 필드에 포함할 수 있다.
- 현재 기본 관찰 대상은 인증 계층(Keycloak)이다.
- NATS 같은 메시징 의존성은 서비스가 이를 필수 의존성으로 채택한 경우에만 readiness 실패 기준에 포함될 수 있다.

### 핵심 요구

- `/health/liveness`는 설정 의존성이 최소여야 한다.
- `/health/readiness`는 timeout과 의존성 URL 설정에 민감하다.
- readiness가 인증 시스템을 확인한다면 Keycloak 관련 URL/timeout이 올바르게 구성되어야 한다.

### 관련 설정 예시

| 환경변수 | 설명 |
| --- | --- |
| `DOCMESH_HEALTHCHECK_ENABLED` | health 기능 활성화 여부 |
| `KEYCLOAK_URL` | readiness가 인증 시스템을 보는 경우 필요 |
| `KEYCLOAK_TIMEOUT_SECONDS` | readiness HTTP timeout |

---

## 7. CORS 설정

`create_app()`는 CORS middleware를 등록하므로, 앱 설정에는 최소 다음 값이 필요하다.

| 설정 항목 | 설명 |
| --- | --- |
| `CORS_ORIGINS` 또는 동등 설정 | 허용 origin 목록 |
| `CORS_CREDENTIALS` 또는 동등 설정 | credential 허용 여부 |

FastAPI 계층 영향:

- 브라우저 기반 클라이언트 접근 허용 범위 결정
- auth cookie / credential 전달 가능 여부 결정

권장 원칙:

- 운영에서는 wildcard 대신 명시 origin 사용
- credentials 사용 시 origin을 더 엄격히 제한

---

## 8. 데이터 저장소 설정

이 설정군은 FastAPI app factory가 직접 사용하기보다, startup/lifespan 또는 service layer에서 사용될 가능성이 높다.

## 8.1 PostgreSQL

| 환경변수 | 필수 여부 | 설명 |
| --- | --- | --- |
| `POSTGRES_DSN` | 조건부 | 전체 DSN |
| `POSTGRES_HOST` | 조건부 | host |
| `POSTGRES_PORT` | 선택 | port |
| `POSTGRES_DB` | 조건부 | database |
| `POSTGRES_USER` | 조건부 | user |
| `POSTGRES_PASSWORD` | 조건부 | password |
| `POSTGRES_CONNECT_TIMEOUT_SECONDS` | 선택 | connect timeout |

규칙:

- `POSTGRES_DSN` 우선
- DSN이 없으면 host/db/user/password 조합 필요
- DSN 원문 로깅 금지

## 8.2 SQLite

| 환경변수 | 필수 여부 | 설명 |
| --- | --- | --- |
| `SQLITE_PATH` | 필수 | 파일 경로 또는 `:memory:` |
| `SQLITE_READONLY` | 선택 | readonly 여부 |
| `SQLITE_ENABLE_WAL` | 선택 | WAL 사용 여부 |
| `SQLITE_BUSY_TIMEOUT_MS` | 선택 | busy timeout |

FastAPI 계층 활용 예:

- 로컬 개발용 앱 실행
- 테스트 환경의 lightweight persistence

---

## 9. 외부 플랫폼 설정

## 9.1 MinIO

| 환경변수 | 필수 여부 | 설명 |
| --- | --- | --- |
| `MINIO_ENDPOINT` | 필수 | endpoint |
| `MINIO_ACCESS_KEY` | 필수 | access key |
| `MINIO_SECRET_KEY` | 필수 | secret key |
| `MINIO_SECURE` | 선택 | HTTPS 여부 |
| `MINIO_TIMEOUT_SECONDS` | 선택 | timeout |

## 9.2 Milvus

| 환경변수 | 필수 여부 | 설명 |
| --- | --- | --- |
| `MILVUS_URI` | 필수 | 접속 URI |
| `MILVUS_TOKEN` | 선택 | 인증 token |
| `MILVUS_DB_NAME` | 선택 | DB 이름 |
| `MILVUS_COLLECTION` | 선택 | 기본 collection |
| `MILVUS_TIMEOUT_SECONDS` | 선택 | timeout |

## 9.3 Ollama

| 환경변수 | 필수 여부 | 설명 |
| --- | --- | --- |
| `OLLAMA_HOST` | 필수 | base URL |
| `OLLAMA_GENERATION_MODEL` | 선택 | 생성 모델 |
| `OLLAMA_EMBEDDING_MODEL` | 선택 | 임베딩 모델 |
| `OLLAMA_TIMEOUT_SECONDS` | 선택 | timeout |

## 9.4 Langfuse

| 환경변수 | 필수 여부 | 설명 |
| --- | --- | --- |
| `LANGFUSE_ENABLED` | 선택 | 기능 활성화 여부 |
| `LANGFUSE_HOST` | 조건부 | host |
| `LANGFUSE_PUBLIC_KEY` | 조건부 | public key |
| `LANGFUSE_SECRET_KEY` | 조건부 | secret key |

규칙:

- `LANGFUSE_ENABLED=false`면 앱 자체 기동은 가능해야 함
- 선택 기능 비활성화가 request/auth 흐름을 깨면 안 됨

---

## 10. 메시징 설정 (NATS)

이 설정군은 FastAPI request handler보다 **startup/shutdown / lifespan**과 더 강하게 연결된다.

| 환경변수 | 필수 여부 | 설명 |
| --- | --- | --- |
| `NATS_SERVERS` | 필수 | 쉼표 구분 서버 목록 |
| `NATS_USER` | 조건부 | user/password 인증 |
| `NATS_PASSWORD` | 조건부 | user/password 인증 |
| `NATS_TOKEN` | 조건부 | token 인증 |
| `NATS_CREDS_FILE` | 조건부 | creds file 인증 |
| `NATS_NAME` | 선택 | 연결 이름 |
| `NATS_CONNECT_TIMEOUT_SECONDS` | 선택 | 연결 timeout |
| `NATS_MAX_RECONNECT_ATTEMPTS` | 선택 | 최대 재연결 횟수 |

### FastAPI 계층 영향

- lifespan startup에서 연결 가능 여부 결정
- readiness에 메시징 상태 반영 여부 결정
- `app.state` 저장 객체의 생명주기 결정

### 규칙

- 인증 방식은 user/password, token, creds file 중 최소 하나
- 서버 목록은 쉼표 구분
- 민감정보 로그 노출 금지

---

## 11. 권장 배포 패턴

### 11.1 로컬 개발

- SQLite 또는 로컬 PostgreSQL 사용
- self-signed 개발 환경에서만 제한적으로 SSL 완화 허용
- auth router 테스트 시 로컬 Keycloak 또는 mock provider 고려

### 11.2 테스트 환경

- `pytest-asyncio` 기반 async 테스트 사용
- dependency override로 auth/config/provider 대체 가능해야 함
- SQLite `:memory:` 또는 테스트 전용 인스턴스 사용

### 11.3 운영 환경

- root path / reverse proxy 설정 검토
- CORS origin 명시적 설정
- auth secret/token을 secret manager로 주입
- readiness가 보는 외부 의존성을 명시적으로 결정
- NATS/DB 연결을 startup 정책과 일치시킴

---

## 12. 설정 오류 처리 기준

설정 오류는 FastAPI 앱이 요청을 받기 전에 드러나는 것이 바람직하다.

대표 오류 예:

- `KEYCLOAK_URL` 누락
- `KEYCLOAK_TOKEN_GRANT_TYPE=password`인데 username/password 누락
- `POSTGRES_DSN`도 없고 host/db/user/password도 불완전
- `NATS_SERVERS` 누락
- timeout 값이 음수 또는 비정상

오류 메시지 원칙:

- 어떤 설정이 잘못됐는지 식별 가능
- 민감정보 원문 비노출
- 가능하면 수정 방향 포함

---

## 13. 샘플 FastAPI 서비스 관점 구성

### 13.1 최소 auth + health 앱

```env
KEYCLOAK_URL=http://keycloak:8080
KEYCLOAK_REALM=docmesh
KEYCLOAK_CLIENT_ID=fastapi-core
KEYCLOAK_CLIENT_SECRET=[REDACTED]
KEYCLOAK_VERIFY_SSL=false
DOCMESH_HEALTHCHECK_ENABLED=true
```

### 13.2 startup에서 NATS 연결을 가지는 앱

```env
KEYCLOAK_URL=https://keycloak.example.com
KEYCLOAK_REALM=docmesh
KEYCLOAK_CLIENT_ID=fastapi-core
KEYCLOAK_CLIENT_SECRET=[REDACTED]
KEYCLOAK_VERIFY_SSL=true

NATS_SERVERS=nats://nats-a:4222,nats://nats-b:4222
NATS_CREDS_FILE=/run/secrets/nats.creds
NATS_CONNECT_TIMEOUT_SECONDS=3
NATS_MAX_RECONNECT_ATTEMPTS=10
```

---

## 14. 참고 문서

- `docs/prd.md`
- `docs/srs.md`
- `docs/api.md`
- `docs/messaging.md`
- `pyproject.toml`

---

## 부록 A. 문서 상태 메모

이 문서는 기존의 인프라 설정 카탈로그 중심 서술에서 벗어나, `create_app`, auth/health router, dependency, lifespan, `app.state` 연계 관점으로 다시 작성했다. 정확한 필드명과 설정 모델은 실제 소스 트리 기준으로 한 번 더 맞춰야 한다.