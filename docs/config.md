# 설정 가이드

## 설정 체계

설정은 두 레이어로 분리됩니다.

| 레이어 | 클래스 | 소스 | 역할 |
| --- | --- | --- | --- |
| 환경 변수 | `EnvConfig` | 환경 변수 / `.env` 파일 | 실행 환경, 외부 서비스 접속 정보, 로깅 레벨 |
| 서비스 설정 | `ServiceSettings` | YAML 파일 | CORS, JWT 검증 정책 등 애플리케이션 동작 값 |

`EnvConfig`는 `__` 구분자를 사용하여 중첩 모델을 환경 변수로 주입합니다 (예: `KEYCLOAK__REALM`).  
`ServiceSettings`는 `CONFIG_PATH` 환경 변수가 가리키는 YAML 파일에서 로드되며, 기본 경로는 `.devcontainer/config.yaml`입니다.

---

## 환경 변수 (`EnvConfig`)

`fastapi_core/core/config.py`의 `EnvConfig` 기준입니다.

### 공통

| 변수명 | 타입 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `ENV` | `dev` \| `stage` \| `prod` | `dev` | 실행 환경 구분 |
| `CONFIG_PATH` | `str` | `.devcontainer/config.yaml` | 서비스 설정 YAML 파일 경로 |
| `ROOT_PATH` | `str` | `/` | FastAPI root path |
| `TOKEN_URL` | `str` | `/token` | OAuth2 토큰 엔드포인트 경로 (OpenAPI Swagger UI Authorize 버튼에 사용) |

### 로깅

| 변수명 | 타입 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `LOGGING__LEVEL` | `WARNING` \| `INFO` \| `DEBUG` | `DEBUG` | 애플리케이션 로그 레벨 |

### Keycloak

| 변수명 | 타입 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `KEYCLOAK__HTTP_URL` | `HttpUrl` | `http://keycloak:8080/` | 토큰 발급·JWKS·issuer URL (반드시 `/` 로 끝나야 함) |
| `KEYCLOAK__MANAGE_URL` | `HttpUrl` | `http://keycloak:9000/` | readiness check URL |
| `KEYCLOAK__REALM` | `str` | `restapi` | Keycloak Realm 이름 |
| `KEYCLOAK__CLIENT_ID` | `str` | `fastapi` | JWT audience 및 토큰 요청 client_id |
| `KEYCLOAK__CLIENT_SECRET` | `str \| None` | `None` | Confidential 클라이언트의 client secret |
| `KEYCLOAK_USERNAME` | `str` | `test` | 통합 테스트용 사용자명 |
| `KEYCLOAK_PASSWORD` | `str` | `test` | 통합 테스트용 비밀번호 |

### PostgreSQL

| 변수명 | 타입 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `DB__HOST` | `str` | `postgres` | PostgreSQL 호스트 |
| `DB__PORT` | `int` | `5432` | PostgreSQL 포트 |
| `DB__NAME` | `str` | `postgres` | 데이터베이스 이름 |
| `DB__USER` | `str` | `postgres` | DB 사용자 |
| `DB__PASSWORD` | `str` | `postgres` | DB 비밀번호 |
| `DB__AUTH_METHOD` | `password` \| `trust` | `password` | 연결 인증 방식 |
| `DB__SSLMODE` | `str` | `prefer` | PostgreSQL SSL 모드 |
| `DB__CONNECT_TIMEOUT` | `int` | `5` | 연결 타임아웃 (초) |
| `DB__ECHO` | `bool` | `false` | SQLAlchemy SQL 로그 출력 여부 |
| `DB__POOL_SIZE` | `int` | `5` | SQLAlchemy 커넥션 풀 기본 크기 |
| `DB__MAX_OVERFLOW` | `int` | `10` | 풀 초과 연결 허용 수 |
| `DB__POOL_TIMEOUT` | `int` | `30` | 풀 연결 획득 타임아웃 (초) |
| `DB__POOL_RECYCLE` | `int` | `1800` | 커넥션 재생성 주기 (초) |
| `DB__URL` | `str \| None` | `None` | 지정 시 위 DB 변수를 무시하고 DSN 직접 사용 |

### MinIO

| 변수명 | 타입 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `MINIO__ENDPOINT` | `str` | `minio:9000` | MinIO 서버 엔드포인트 (host:port, 스킴 제외) |
| `MINIO__ACCESS_KEY` | `str` | `admin` | MinIO 액세스 키 |
| `MINIO__SECRET_KEY` | `str` | `password` | MinIO 시크릿 키 |
| `MINIO__SECURE` | `bool` | `false` | TLS 사용 여부 (`true`이면 HTTPS) |
| `MINIO__BUCKET` | `str` | `default` | 기본 버킷 이름 |
| `MINIO__PRESIGNED_EXPIRES_SEC` | `int` | `900` | Presigned URL 기본 만료 (초) |

### NATS

| 변수명 | 타입 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `NATS__SERVERS` | `str` (콤마 구분) | `nats://nats:4222` | NATS 서버 주소 목록 |
| `NATS__NAME` | `str` | `fastapi-core` | NATS 연결 이름 |
| `NATS__CONNECT_TIMEOUT` | `int` | `2` | 연결 타임아웃 (초) |
| `NATS__MAX_RECONNECT_ATTEMPTS` | `int` | `60` | 재연결 최대 시도 횟수 |
| `NATS__RECONNECT_TIME_WAIT_MS` | `int` | `2000` | 재연결 간격 (ms) |
| `NATS__QUEUE_GROUP` | `str` | `default-workers` | 기본 queue group 이름 |

---

## 서비스 설정 (`ServiceSettings`, YAML)

기본 경로: `.devcontainer/config.yaml`

### `cors`

| 키 | 타입 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `cors.origins` | `list[str]` | `["*"]` | CORS 허용 Origin |
| `cors.credentials` | `bool` | `false` | `Access-Control-Allow-Credentials` 허용 여부 |

### `auth`

| 키 | 타입 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `auth.verify_jwt` | `bool` | `true` | `true`: RS256 서명 검증 후 디코드 / `false`: 서명 검증 없이 디코드 |
| `auth.allow_insecure_jwt_decode` | `bool` | `false` | 서명 검증 생략 허용 여부 (개발 환경용) |
| `auth.use_introspection` | `bool` | `false` | Keycloak 토큰 인트로스펙션 사용 여부 |

> Keycloak 접속 정보(`http_url`, `realm`, `client_id` 등)는 YAML이 아닌 환경 변수(`KEYCLOAK__*`)로 관리합니다.

### `health`

| 키 | 타입 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `health.check_keycloak` | `bool` | `true` | readiness에서 Keycloak 점검 여부 |
| `health.check_database` | `bool` | `true` | readiness에서 PostgreSQL 점검 여부 |
| `health.check_minio` | `bool` | `true` | readiness에서 MinIO 점검 여부 |

### YAML 예시

```yaml
cors:
  origins:
    - "https://example.com"
  credentials: false

auth:
  verify_jwt: true
  allow_insecure_jwt_decode: false
  use_introspection: false
```

---

## 환경 파일

| 환경 | 파일 경로 |
| --- | --- |
| 개발 | `.devcontainer/.env` |
| 배포 | `.release/.env` |

### `.env` 예시

```dotenv
# 공통
ENV=dev
ROOT_PATH=/
CONFIG_PATH=.devcontainer/config.yaml
LOGGING__LEVEL=DEBUG

# Keycloak
KEYCLOAK__HTTP_URL=http://keycloak:8080/
KEYCLOAK__MANAGE_URL=http://keycloak:9000/
KEYCLOAK__REALM=restapi
KEYCLOAK__CLIENT_ID=fastapi
KEYCLOAK__CLIENT_SECRET=

# 통합 테스트 계정 (개발/테스트 환경 전용)
KEYCLOAK_USERNAME=test
KEYCLOAK_PASSWORD=test

# PostgreSQL
DB__HOST=postgres
DB__PORT=5432
DB__NAME=postgres
DB__USER=postgres
DB__PASSWORD=postgres
DB__AUTH_METHOD=password
DB__SSLMODE=prefer
DB__CONNECT_TIMEOUT=5
DB__ECHO=false
DB__POOL_SIZE=5
DB__MAX_OVERFLOW=10
DB__POOL_TIMEOUT=30
DB__POOL_RECYCLE=1800
# DB__URL=postgresql+psycopg://user:pass@postgres:5432/dbname

# MinIO
MINIO__ENDPOINT=minio:9000
MINIO__ACCESS_KEY=admin
MINIO__SECRET_KEY=password
MINIO__SECURE=false
MINIO__BUCKET=default
MINIO__PRESIGNED_EXPIRES_SEC=900

# NATS
NATS__SERVERS=nats://nats:4222
NATS__NAME=fastapi-core
NATS__CONNECT_TIMEOUT=2
NATS__MAX_RECONNECT_ATTEMPTS=60
NATS__RECONNECT_TIME_WAIT_MS=2000
NATS__QUEUE_GROUP=default-workers
```

---

## `DatabaseConfig.sqlalchemy_database_url` 조합 규칙

`DB__URL`이 지정된 경우 해당 값을 그대로 사용합니다.  
지정되지 않은 경우 아래 규칙으로 DSN을 조합합니다.

| `DB__AUTH_METHOD` | 생성되는 DSN |
| --- | --- |
| `password` | `postgresql+psycopg://user:password@host:port/name?sslmode=...&connect_timeout=...` |
| `trust` | `postgresql+psycopg://user@host:port/name?sslmode=...&connect_timeout=...` |
