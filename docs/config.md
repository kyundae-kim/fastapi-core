# 설정 가이드

## 설정 체계

`fastapi-core`의 설정은 두 레이어로 나뉩니다.

| 레이어 | 클래스 | 소스 | 역할 |
| --- | --- | --- | --- |
| 환경 변수 | `EnvConfig` | OS 환경 변수 + `.env` | 외부 서비스 접속 정보, 실행 환경, 로깅, root path |
| 서비스 설정 | `ServiceSettings` | YAML 파일 (`config_path`) | CORS, 인증 정책, readiness/lifecycle 정책 |

핵심 동작:

- `EnvConfig`는 `pydantic-settings` 기반이며 `env_nested_delimiter="__"`를 사용합니다.
- 기본 `.env` 파일은 루트의 `.env`입니다.
- 알 수 없는 환경 변수는 `extra="ignore"`로 무시합니다.
- `ServiceSettings.from_yaml(path)`는 파일이 없으면 예외 없이 기본값을 사용합니다.
- 기본 YAML 경로는 `CONFIG_PATH=.devcontainer/config.yaml` 입니다.

---

## 환경 변수 (`EnvConfig`)

소스: `fastapi_core/core/config.py`

### 공통

| 변수명 | 타입 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `ENV` | `dev \| stage \| prod` | `dev` | 실행 환경 |
| `CONFIG_PATH` | `str` | `.devcontainer/config.yaml` | `ServiceSettings` YAML 경로 |
| `ROOT_PATH` | `str` | `/` | FastAPI `root_path` |
| `TOKEN_URL` | `str` | `/token` | `OAuth2PasswordBearer`가 사용하는 토큰 URL |

### 로깅

| 변수명 | 타입 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `LOGGING__LEVEL` | `WARNING \| INFO \| DEBUG` | `DEBUG` | `setup_logging()`에 전달되는 로그 레벨 |

### Keycloak

| 변수명 | 타입 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `KEYCLOAK__HTTP_URL` | `HttpUrl` | `http://keycloak:8080/` | Keycloak base URL |
| `KEYCLOAK__MANAGE_URL` | `HttpUrl` | `http://keycloak:9000/` | readiness용 관리 URL |
| `KEYCLOAK__REALM` | `str` | `restapi` | Realm 이름 |
| `KEYCLOAK__CLIENT_ID` | `str` | `fastapi` | OAuth client id / JWT audience |
| `KEYCLOAK__CLIENT_SECRET` | `str \| None` | `None` | Confidential client secret |
| `KEYCLOAK_USERNAME` | `str` | `test` | 통합 테스트용 사용자명 |
| `KEYCLOAK_PASSWORD` | `str` | `test` | 통합 테스트용 비밀번호 |

### PostgreSQL

| 변수명 | 타입 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `DB__HOST` | `str` | `postgres` | DB 호스트 |
| `DB__PORT` | `int` | `5432` | DB 포트 |
| `DB__NAME` | `str` | `postgres` | DB 이름 |
| `DB__USER` | `str` | `postgres` | DB 사용자 |
| `DB__PASSWORD` | `str` | `postgres` | DB 비밀번호 |
| `DB__AUTH_METHOD` | `password \| trust` | `password` | DSN 조합 방식 |
| `DB__SSLMODE` | `str` | `prefer` | PostgreSQL SSL 모드 |
| `DB__CONNECT_TIMEOUT` | `int` | `5` | 연결 타임아웃(초) |
| `DB__ECHO` | `bool` | `false` | SQLAlchemy SQL 로그 출력 |
| `DB__POOL_SIZE` | `int` | `5` | 기본 커넥션 풀 크기 |
| `DB__MAX_OVERFLOW` | `int` | `10` | 초과 허용 연결 수 |
| `DB__POOL_TIMEOUT` | `int` | `30` | 풀 획득 타임아웃(초) |
| `DB__POOL_RECYCLE` | `int` | `1800` | 커넥션 재생성 주기(초) |
| `DB__URL` | `str \| None` | `None` | 지정 시 나머지 DB 필드를 무시하고 DSN 직접 사용 |

### MinIO

| 변수명 | 타입 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `MINIO__ENDPOINT` | `str` | `minio:9000` | MinIO endpoint (`host:port`) |
| `MINIO__ACCESS_KEY` | `str` | `admin` | 액세스 키 |
| `MINIO__SECRET_KEY` | `str` | `password` | 시크릿 키 |
| `MINIO__SECURE` | `bool` | `false` | HTTPS 사용 여부 |
| `MINIO__BUCKET` | `str` | `default` | 기본 버킷 |
| `MINIO__PRESIGNED_EXPIRES_SEC` | `int` | `900` | presigned URL 만료 시간(초) |

### Milvus

| 변수명 | 타입 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `MILVUS__URI` | `str` | `http://milvus:19530` | Milvus 엔드포인트 |
| `MILVUS__DB_NAME` | `str` | `""` | 기본 DB 이름 |
| `MILVUS__TOKEN` | `str` | `""` | 인증 토큰 |
| `MILVUS__TIMEOUT` | `float \| None` | `None` | 클라이언트 timeout |

### Ollama

| 변수명 | 타입 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `OLLAMA__HOST` | `str` | `http://ollama:11434` | Ollama HTTP API |
| `OLLAMA__MODEL` | `str` | `llama3.2` | 기본 생성 모델 |
| `OLLAMA__TIMEOUT` | `float` | `60.0` | HTTP timeout(초) |

### Langfuse

| 변수명 | 타입 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `LANGFUSE__HOST` | `str` | `http://langfuse-web:3000` | Langfuse host |
| `LANGFUSE__PUBLIC_KEY` | `str \| None` | `None` | public key |
| `LANGFUSE__SECRET_KEY` | `str \| None` | `None` | secret key |
| `LANGFUSE__TIMEOUT` | `int` | `5` | health/API timeout(초) |
| `LANGFUSE__TRACING_ENABLED` | `bool` | `true` | tracing 활성화 여부 |
| `LANGFUSE__ENVIRONMENT` | `str \| None` | `None` | tracing environment |
| `LANGFUSE__RELEASE` | `str \| None` | `None` | release 태그 |

### NATS

| 변수명 | 타입 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `NATS__SERVERS` | `str` (콤마 구분) | `nats://nats:4222` | 서버 목록 원본 문자열 |
| `NATS__NAME` | `str` | `fastapi-core` | 연결 이름 |
| `NATS__CONNECT_TIMEOUT` | `int` | `2` | 연결 timeout(초) |
| `NATS__MAX_RECONNECT_ATTEMPTS` | `int` | `60` | 최대 재연결 횟수 |
| `NATS__RECONNECT_TIME_WAIT_MS` | `int` | `2000` | 재연결 간격(ms) |
| `NATS__QUEUE_GROUP` | `str` | `default-workers` | 기본 queue group |

`NatsConfig.server_list`는 `NATS__SERVERS`를 콤마로 분리하고 공백을 제거한 계산 프로퍼티입니다.

---

## 서비스 설정 (`ServiceSettings`, YAML)

기본 경로: `.devcontainer/config.yaml`

### `cors`

| 키 | 타입 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `cors.origins` | `list[str]` | `["*"]` | 허용 Origin |
| `cors.credentials` | `bool` | `false` | `allow_credentials` 값 |

### `auth`

| 키 | 타입 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `auth.verify_jwt` | `bool` | `true` | `true`면 RS256 검증 후 decode |
| `auth.allow_insecure_jwt_decode` | `bool` | `false` | 검증 없는 decode 허용 여부 |
| `auth.use_introspection` | `bool` | `false` | Keycloak introspection 사용 여부 |

> Keycloak 접속 정보는 YAML이 아니라 `KEYCLOAK__*` 환경 변수에서 읽습니다.

### `health`

| 키 | 타입 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `health.check_keycloak` | `bool` | `true` | `/health/readiness`에서 Keycloak 확인 |
| `health.check_database` | `bool` | `true` | `/health/readiness`에서 DB 확인 |
| `health.check_minio` | `bool` | `true` | `/health/readiness`에서 MinIO 확인 |
| `health.check_langfuse` | `bool` | `false` | `/health/readiness`에서 Langfuse 확인 |

### `lifecycle`

| 키 | 타입 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `lifecycle.eager_keycloak` | `bool \| null` | `null` | `null`이면 `health.check_keycloak` 값을 따름 |
| `lifecycle.eager_database` | `bool \| null` | `null` | `null`이면 `health.check_database` 값을 따름 |
| `lifecycle.eager_minio` | `bool \| null` | `null` | `null`이면 `health.check_minio` 값을 따름 |
| `lifecycle.eager_langfuse` | `bool \| null` | `null` | `null`이면 `health.check_langfuse` 값을 따름 |
| `lifecycle.eager_milvus` | `bool` | `true` | startup에서 Milvus 준비 여부 |
| `lifecycle.eager_async_milvus` | `bool` | `false` | startup에서 AsyncMilvus 준비 여부 |
| `lifecycle.eager_ollama` | `bool` | `true` | startup에서 Ollama 준비 여부 |
| `lifecycle.eager_nats` | `bool` | `false` | startup에서 NATS 준비 여부 |
| `lifecycle.use_docmesh_registry` | `bool` | `false` | registry를 명시적으로 먼저 부트스트랩하도록 강제 |
| `lifecycle.use_docmesh_healthchecks` | `bool` | `false` | readiness에서 `docmesh_py_core.check_all_services()` 사용 시도 |

### lifecycle 해석 규칙

`resolve_lifecycle_policy(settings)`는 다음 규칙으로 startup 정책을 계산합니다.

- `eager_keycloak`, `eager_database`, `eager_minio`, `eager_langfuse`가 `null`이면 각각의 `health.check_*` 값을 상속합니다.
- `eager_milvus`, `eager_async_milvus`, `eager_ollama`, `eager_nats`는 명시값 그대로 사용합니다.
- 관리 대상 서비스(`auth_provider`, `db_engine`, `minio_client`, `milvus_client`, `ollama_client`, `langfuse_client`, `nats_client`) 중 하나라도 eager-init 대상이면 startup에서 docmesh registry를 초기화합니다.
- `async_milvus_client`만 예외적으로 registry가 아니라 `create_async_milvus_client(config.milvus)`로 직접 생성됩니다.

> 현재 FastAPI dependency 계층의 auth/db/minio/milvus/ollama/langfuse/nats 조회는 docmesh registry 기반 helper를 사용합니다. `use_docmesh_registry`는 이 동작을 끄는 스위치가 아니라, startup 시 registry를 선행 초기화할지까지 포함한 lifecycle 정책 플래그입니다.

### YAML 예시

```yaml
cors:
  origins:
    - https://example.com
  credentials: false

auth:
  verify_jwt: true
  allow_insecure_jwt_decode: false
  use_introspection: false

health:
  check_keycloak: true
  check_database: true
  check_minio: true
  check_langfuse: false

lifecycle:
  eager_milvus: true
  eager_async_milvus: false
  eager_ollama: true
  eager_nats: false
  use_docmesh_registry: false
  use_docmesh_healthchecks: false
```

---

## 환경 파일

| 환경 | 파일 경로 |
| --- | --- |
| 예제 | `.env.example` |
| 개발 | `.devcontainer/.env` |
| 배포 | `.release/.env` |

### `.env` 예시

```dotenv
ENV=dev
CONFIG_PATH=.devcontainer/config.yaml
ROOT_PATH=/
TOKEN_URL=/token
LOGGING__LEVEL=DEBUG

KEYCLOAK__HTTP_URL=http://keycloak:8080/
KEYCLOAK__MANAGE_URL=http://keycloak:9000/
KEYCLOAK__REALM=restapi
KEYCLOAK__CLIENT_ID=fastapi
KEYCLOAK__CLIENT_SECRET=
KEYCLOAK_USERNAME=test
KEYCLOAK_PASSWORD=test

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

MINIO__ENDPOINT=minio:9000
MINIO__ACCESS_KEY=admin
MINIO__SECRET_KEY=password
MINIO__SECURE=false
MINIO__BUCKET=default
MINIO__PRESIGNED_EXPIRES_SEC=900

MILVUS__URI=http://milvus:19530
MILVUS__DB_NAME=
MILVUS__TOKEN=
MILVUS__TIMEOUT=10.0

OLLAMA__HOST=http://ollama:11434
OLLAMA__MODEL=llama3.2
OLLAMA__TIMEOUT=60.0

LANGFUSE__HOST=http://langfuse-web:3000
LANGFUSE__PUBLIC_KEY=
LANGFUSE__SECRET_KEY=
LANGFUSE__TIMEOUT=5
LANGFUSE__TRACING_ENABLED=true
LANGFUSE__ENVIRONMENT=
LANGFUSE__RELEASE=

NATS__SERVERS=nats://nats:4222,nats://nats-2:4222
NATS__NAME=fastapi-core
NATS__CONNECT_TIMEOUT=2
NATS__MAX_RECONNECT_ATTEMPTS=60
NATS__RECONNECT_TIME_WAIT_MS=2000
NATS__QUEUE_GROUP=default-workers
```

---

## `DatabaseConfig.sqlalchemy_database_url` 조합 규칙

`DB__URL`이 설정되면 그 값을 그대로 사용합니다.
그 외에는 아래 규칙으로 DSN을 조합합니다.

| `DB__AUTH_METHOD` | 생성 DSN |
| --- | --- |
| `password` | `postgresql+psycopg://user:password@host:port/name?sslmode=...&connect_timeout=...` |
| `trust` | `postgresql+psycopg://user@host:port/name?sslmode=...&connect_timeout=...` |
