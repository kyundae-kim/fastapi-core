---
source_url: https://github.com/kyundae-kim/docmesh-py-core/wiki/Configuration-v0.6.0
ingested: 2026-08-01
sha256: 86b2dd5e69d64b012c9e671eac36d3fa95115dcca84e61d4a65b3b6ce292b624
---
# docmesh-py-core 설정 가이드

이 문서는 docmesh-py-core v0.6.0이 사용하는 프로세스 환경변수 전체와 runtime wiring을 설명한다. 시작 template은 [`.env.example`](../.env.example), 사용 흐름은 [예제](./examples.md), client·lifecycle signature는 [공개 API](./api.md)를 참고한다.

## 1. 설정 로딩 계약

- canonical 설정 package는 `docmesh_config`다.
- 모든 `*Config()`는 현재 프로세스 환경변수만 읽는다. constructor kwargs, mapping, test 전용 env file로 값을 주입하면 `TypeError`다.
- 환경변수 이름은 대소문자를 구분하지 않고 읽지만 이 문서는 대문자를 canonical 표기로 사용한다.
- 공백 문자열은 미설정으로 처리한다.
- boolean은 Pydantic 기본 coercion을 사용한다.
- list는 쉼표로 구분한다. 예: `NATS_SERVERS=nats://n1:4222,nats://n2:4222`.
- secret과 endpoint를 포함한 설정 `model_dump()`는 마스킹된다.
- `RuntimePlan` assembly는 선택 서비스만 진단·로드한다. 설정의 일부만 있으면 partial error다.

```python
from docmesh_config import RuntimePlan, Service, diagnose_services

plan = RuntimePlan(services=(Service.POSTGRES.required(),))
diagnosis = diagnose_services(plan=plan)
if not diagnosis.ok:
    raise RuntimeError(diagnosis.to_dict())
```

### 선택과 자동 감지

- `load_service_configs(services={...})`: 명시한 서비스만 로드한다.
- `load_service_configs()` without `services`: 인식 가능한 환경변수가 하나라도 있는 서비스만 자동 감지한다.
- `load_available_service_configs(services={...})`: 후보 중 prefix가 존재하는 서비스만 로드한다.
- 일반 애플리케이션은 `RuntimePlan` assembly를 사용해 선택 정책과 lifecycle을 한곳에 둔다.

## 2. 공통 설정과 별도 환경 helper

| 환경변수 | 타입 | 필수 | 기본값 | 의미 |
| --- | --- | --- | --- | --- |
| `DOCMESH_ENV` | string | 아니요 | `development` | 실행 환경 이름. `prod`, `production`은 기본 production alias다. |
| `DOCMESH_SECURITY_MODE` | `development \| production` | 아니요 | 미설정 | 설정 시 `DOCMESH_ENV`보다 production 판정을 우선한다. |
| `DOCMESH_PRODUCTION_ALIASES` | CSV list | 아니요 | `prod,production` | `DOCMESH_ENV`를 production으로 판정할 별칭. |
| `DOCMESH_LOG_LEVEL` | logging level | 아니요 | `INFO` | `configure_logging()`이 읽는 별도 helper. 설정 모델 필드는 아니다. |

`DOCMESH_HEALTHCHECK_ENABLED`는 지원하지 않는다. startup 상태 확인은 `RuntimePlan.healthcheck`만 제어한다.

## 3. Production 보안 규칙

production 판정 시 다음 값은 반드시 `true`여야 한다.

- `KEYCLOAK_VERIFY_SSL`
- `MINIO_SECURE`
- `MINIO_CERT_CHECK`
- `MILVUS_SECURE`
- `OLLAMA_VERIFY_SSL`

또한 secret 값의 `replace-me`, `changeme`, `change-me`, `placeholder`와 endpoint의 `example.com`, `localhost`, `127.0.0.1`은 선택 서비스의 production preflight에서 거부된다.

## 4. Keycloak

최소 confidential client 구성:

```dotenv
KEYCLOAK_URL=https://keycloak.internal
KEYCLOAK_REALM=docmesh
KEYCLOAK_CLIENT_ID=backend
KEYCLOAK_CLIENT_SECRET=inject-from-secret-store
```

| 환경변수 | 타입/범위 | 필수·조건 | 기본값 | runtime wiring |
| --- | --- | --- | --- | --- |
| `KEYCLOAK_URL` | string | 필수 | - | issuer/token/JWKS endpoint base. 민감 endpoint로 마스킹 대상. |
| `KEYCLOAK_REALM` | string | 필수 | - | issuer realm과 provisioning 대상. |
| `KEYCLOAK_CLIENT_ID` | string | 필수 | - | token payload와 provisioning client. |
| `KEYCLOAK_CLIENT_SECRET` | secret string | `KEYCLOAK_CLIENT_PUBLIC=false`일 때 필수 | - | token payload. |
| `KEYCLOAK_VERIFY_SSL` | bool | 선택; production에서 `true` | `true` | token/JWKS HTTP TLS 검증. |
| `KEYCLOAK_AUDIENCE` | string | 선택 | - | 설정 시 JWT audience 검증 활성화. |
| `KEYCLOAK_TOKEN_GRANT_TYPE` | `password \| client_credentials` | 선택 | `password` | token endpoint grant. |
| `KEYCLOAK_TOKEN_SCOPE` | string | 선택 | - | call-time scope가 없을 때 사용. |
| `KEYCLOAK_TOKEN_USERNAME` | string | password grant 조건부 | - | call-time username이 없을 때 사용. |
| `KEYCLOAK_TOKEN_PASSWORD` | secret string | password grant 조건부 | - | call-time password가 없을 때 사용. |
| `KEYCLOAK_REQUEST_TIMEOUT_SECONDS` | int `>=1` | 선택 | `10` | token/JWKS HTTP timeout. |
| `KEYCLOAK_MAX_RETRIES` | int `>=0` | 선택 | `3` | token temporary error 재시도 횟수; 총 시도는 `+1`. |
| `KEYCLOAK_JWKS_CACHE_TTL_SECONDS` | int `>=0` | 선택 | `300` | JWKS cache TTL. `0`이면 로드된 cache를 만료시키지 않는다. |
| `KEYCLOAK_PROVISIONING_ENABLED` | bool | 선택 | `false` | admin auth mode 검증 활성화. `provision()` 호출을 자동 수행하거나 `KeycloakProvisioner` 내부에서 gate하지 않으므로 호출자가 확인한다. |
| `KEYCLOAK_PROVISIONING_DRY_RUN` | bool | 선택 | `false` | 원격 ensure 호출 대신 `planned` 결과 생성. |
| `KEYCLOAK_ADMIN_REALM` | string | 선택 | `master` | consumer admin adapter용 metadata. |
| `KEYCLOAK_ADMIN_CLIENT_ID` | string | 선택 | `admin-cli` | consumer admin adapter용 metadata. |
| `KEYCLOAK_ADMIN_CLIENT_SECRET` | secret string | provisioning auth mode A | - | service-account admin 인증 metadata. |
| `KEYCLOAK_ADMIN_USERNAME` | string | provisioning auth mode B | - | user admin 인증 metadata. |
| `KEYCLOAK_ADMIN_PASSWORD` | secret string | provisioning auth mode B | - | user admin 인증 metadata. |
| `KEYCLOAK_REALM_ENABLED` | bool | 선택 | `true` | `ensure_realm` adapter가 사용할 desired state. |
| `KEYCLOAK_REALM_DISPLAY_NAME` | string | 선택 | - | realm desired state. |
| `KEYCLOAK_CLIENT_PUBLIC` | bool | 선택 | `false` | public client이면 client secret 조건 해제. |
| `KEYCLOAK_CLIENT_REDIRECT_URIS` | CSV list | 선택 | 빈 목록 | client desired state. |
| `KEYCLOAK_CLIENT_WEB_ORIGINS` | CSV list | 선택 | 빈 목록 | client desired state. |
| `KEYCLOAK_REALM_ROLES` | CSV list | 선택 | 빈 목록 | provisioning realm roles. |
| `KEYCLOAK_CLIENT_ROLES` | CSV list | 선택 | 빈 목록 | provisioning client roles. |

Provisioning이 enabled이면 admin auth는 `ADMIN_CLIENT_SECRET` 또는 `ADMIN_USERNAME`+`ADMIN_PASSWORD` 중 **정확히 하나**여야 한다. token password grant는 설정 시점이 아니라 `fetch_access_token()` 호출 시 call-time 또는 환경 credential을 검증한다.

`create_keycloak_client()`는 RS256/JWKS 검증이 적용된 `KeycloakAuthService` wrapper를 만든다. HS256은 환경변수 옵션이 아니며 direct constructor에서 explicit verification key와 함께만 사용할 수 있다.

## 5. PostgreSQL

```dotenv
POSTGRES_HOST=postgres.internal
POSTGRES_DB=docmesh
POSTGRES_USER=docmesh
POSTGRES_PASSWORD=inject-from-secret-store
```

| 환경변수 | 타입/범위 | 필수 | 기본값 | runtime wiring |
| --- | --- | --- | --- | --- |
| `POSTGRES_HOST` | string | 예 | - | SQLAlchemy URL host. |
| `POSTGRES_PORT` | int `1..65535` | 아니요 | `5432` | SQLAlchemy URL port. |
| `POSTGRES_DB` | string | 예 | - | SQLAlchemy URL database. |
| `POSTGRES_USER` | string | 예 | - | SQLAlchemy URL username. |
| `POSTGRES_PASSWORD` | secret string | 예 | - | SQLAlchemy URL password. |
| `POSTGRES_SSLMODE` | string | 아니요 | `prefer` | psycopg `connect_args.sslmode`. |
| `POSTGRES_CONNECT_TIMEOUT_SECONDS` | int `>=1` | 아니요 | `10` | `connect_args.connect_timeout`. |
| `POSTGRES_POOL_SIZE` | int `>=1` | 아니요 | `5` | `create_engine(pool_size=...)`. |
| `POSTGRES_MAX_OVERFLOW` | int `>=0` | 아니요 | `10` | `create_engine(max_overflow=...)`. |
| `POSTGRES_POOL_PRE_PING` | bool | 아니요 | `false` | `create_engine(pool_pre_ping=...)`. |
| `POSTGRES_POOL_RECYCLE_SECONDS` | int `>=-1` | 아니요 | `-1` | `create_engine(pool_recycle=...)`. |
| `POSTGRES_ECHO` | bool | 아니요 | `false` | SQLAlchemy echo. SQL/parameter logging 위험을 검토한다. |
| `POSTGRES_APPLICATION_NAME` | string | 아니요 | - | 값이 있으면 psycopg connect args에 전달. |

## 6. SQLite

```dotenv
SQLITE_PATH=:memory:
```

| 환경변수 | 타입/범위 | 필수 | 기본값 | runtime wiring |
| --- | --- | --- | --- | --- |
| `SQLITE_PATH` | path 또는 `:memory:` | 예 | - | `~` 확장 후 절대 경로로 해석. 부모 디렉터리는 만들지 않는다. |
| `SQLITE_READONLY` | bool | 아니요 | `false` | `mode=ro&uri=true` URL. |
| `SQLITE_ENABLE_WAL` | bool | 아니요 | `false` | connect event에서 `PRAGMA journal_mode=WAL`. |
| `SQLITE_BUSY_TIMEOUT_MS` | int `>=0` | 아니요 | `5000` | DBAPI timeout과 `PRAGMA busy_timeout`. |
| `SQLITE_CHECK_SAME_THREAD` | bool | 아니요 | `false` | sqlite DBAPI connect arg. |
| `SQLITE_ECHO` | bool | 아니요 | `false` | SQLAlchemy echo. |

healthcheck는 `SELECT 1`이다.

## 7. MinIO

```dotenv
MINIO_ENDPOINT=minio.internal:9000
MINIO_ACCESS_KEY=inject-from-secret-store
MINIO_SECRET_KEY=inject-from-secret-store
```

| 환경변수 | 타입/범위 | 필수 | 기본값 | runtime wiring |
| --- | --- | --- | --- | --- |
| `MINIO_ENDPOINT` | string | 예 | - | Minio SDK endpoint. |
| `MINIO_ACCESS_KEY` | secret string | 예 | - | SDK credential. |
| `MINIO_SECRET_KEY` | secret string | 예 | - | SDK credential. |
| `MINIO_SECURE` | bool | 아니요 | `true` | SDK TLS; production에서 true. |
| `MINIO_CERT_CHECK` | bool | 아니요 | `true` | SDK certificate check; production에서 true. |
| `MINIO_REGION` | string | 아니요 | - | SDK region. |
| `MINIO_BUCKET` | string | plan에 `minio_bucket_required=True`일 때 필수 | - | wrapper `runtime_defaults`; bucket 생성은 하지 않는다. |
| `MINIO_REQUEST_TIMEOUT_SECONDS` | int `>=1` | 아니요 | `30` | wrapper `runtime_defaults`; 현재 Minio constructor에 자동 전달되지 않는다. |
| `MINIO_MAX_RETRIES` | int `>=0` | 아니요 | `3` | wrapper `runtime_defaults`; 현재 SDK retry에 자동 연결되지 않는다. |

healthcheck는 `list_buckets()`다.

## 8. Milvus

```dotenv
MILVUS_ENDPOINT=https://milvus.internal:19530
MILVUS_SECURE=true
```

| 환경변수 | 타입/범위 | 필수 | 기본값 | runtime wiring |
| --- | --- | --- | --- | --- |
| `MILVUS_ENDPOINT` | string | 예 | - | `MilvusClient(uri=...)`. |
| `MILVUS_TOKEN` | secret string | 아니요 | - | `MilvusClient(token=...)`; 미설정이면 빈 문자열. |
| `MILVUS_DB_NAME` | string | 아니요 | `default` | SDK database. |
| `MILVUS_COLLECTION` | string | 아니요 | - | wrapper `runtime_defaults`; collection 생성/선택은 caller 책임. |
| `MILVUS_SECURE` | bool | 아니요 | `false` | SDK secure와 runtime defaults; production에서 true. |
| `MILVUS_CONNECT_TIMEOUT_SECONDS` | int `>=1` | 아니요 | `10` | wrapper `runtime_defaults`; SDK constructor timeout은 아니다. |
| `MILVUS_REQUEST_TIMEOUT_SECONDS` | int `>=1` | 아니요 | `30` | `MilvusClient(timeout=...)`. |
| `MILVUS_MAX_RETRIES` | int `>=0` | 아니요 | `3` | wrapper `runtime_defaults`; SDK retry에 자동 연결되지 않는다. |

healthcheck는 `list_collections()`다.

## 9. Ollama

```dotenv
OLLAMA_HOST=https://ollama.internal
OLLAMA_VERIFY_SSL=true
```

| 환경변수 | 타입/범위 | 필수 | 기본값 | runtime wiring |
| --- | --- | --- | --- | --- |
| `OLLAMA_HOST` | string | 예 | - | `ollama.Client(host=...)`. |
| `OLLAMA_VERIFY_SSL` | bool | 아니요 | `true` | SDK `verify`; production에서 true. |
| `OLLAMA_FOLLOW_REDIRECTS` | bool | 아니요 | `true` | SDK `follow_redirects`. |
| `OLLAMA_GENERATION_MODEL` | string | 아니요 | - | wrapper `runtime_defaults`; 모델 lifecycle은 caller 책임. |
| `OLLAMA_EMBEDDING_MODEL` | string | 아니요 | - | wrapper `runtime_defaults`. |
| `OLLAMA_REQUEST_TIMEOUT_SECONDS` | int `>=1` | 아니요 | `120` | SDK timeout. |
| `OLLAMA_MAX_RETRIES` | int `>=0` | 아니요 | `2` | wrapper `runtime_defaults`; SDK retry에 자동 연결되지 않는다. |

healthcheck는 `ps()`다.

## 10. Langfuse

비활성화:

```dotenv
LANGFUSE_ENABLED=false
```

활성화:

```dotenv
LANGFUSE_ENABLED=true
LANGFUSE_HOST=https://langfuse.internal
LANGFUSE_PUBLIC_KEY=inject-from-secret-store
LANGFUSE_SECRET_KEY=inject-from-secret-store
```

| 환경변수 | 타입/범위 | 필수·조건 | 기본값 | runtime wiring |
| --- | --- | --- | --- | --- |
| `LANGFUSE_ENABLED` | bool | 선택 | `true` | false이면 factory가 `None`; required runtime service로 선택하면 초기화 오류가 난다. |
| `LANGFUSE_HOST` | string | enabled=true | - | SDK host. |
| `LANGFUSE_PUBLIC_KEY` | string | enabled=true | - | SDK public key. |
| `LANGFUSE_SECRET_KEY` | secret string | enabled=true | - | SDK secret key. |
| `LANGFUSE_RELEASE` | string | 선택 | - | SDK release. |
| `LANGFUSE_ENVIRONMENT` | string | 선택 | `DOCMESH_ENV` | 미설정 시 설정 생성 시점의 common env. |
| `LANGFUSE_REQUEST_TIMEOUT_SECONDS` | int `>=1` | 선택 | `10` | SDK timeout. |
| `LANGFUSE_MAX_RETRIES` | int `>=0` | 선택 | `3` | 현재 파싱·검증만 하며 factory에 자동 연결되지 않는다. |
| `LANGFUSE_DEBUG` | bool | 선택 | `false` | SDK debug. |
| `LANGFUSE_TRACING_ENABLED` | bool | 선택 | `true` | SDK tracing flag. |
| `LANGFUSE_FLUSH_AT` | int `>=1` 또는 미설정 | 선택 | - | SDK batching option. |
| `LANGFUSE_FLUSH_INTERVAL_SECONDS` | float `>0` 또는 미설정 | 선택 | - | SDK flush interval. |
| `LANGFUSE_SAMPLE_RATE` | float `0..1` 또는 미설정 | 선택 | - | SDK sample rate. |

healthcheck는 `auth_check()`, 종료는 `flush()`다.

## 11. NATS

```dotenv
NATS_SERVERS=nats://nats-1.internal:4222,nats://nats-2.internal:4222
```

| 환경변수 | 타입/범위 | 필수·조건 | 기본값 | runtime wiring |
| --- | --- | --- | --- | --- |
| `NATS_SERVERS` | CSV list | 필수, 한 개 이상 | 빈 목록 | builder `servers`. |
| `NATS_USER` | string | password mode에서 pair | - | builder user. |
| `NATS_PASSWORD` | secret string | user와 함께 | - | builder password. |
| `NATS_TOKEN` | secret string | 선택 auth mode | - | builder token. |
| `NATS_CREDS_FILE` | path | 선택 auth mode | - | SDK `user_credentials`. |
| `NATS_NAME` | string | 선택 | 모델 `docmesh-config`; 미설정 factory `docmesh-py-core` | SDK connection name. 명시 설정하면 그 값을 사용한다. |
| `NATS_CONNECT_TIMEOUT_SECONDS` | int `>=1` | 선택 | `10` | SDK `connect_timeout`. |
| `NATS_MAX_RECONNECT_ATTEMPTS` | int `>=0` | 선택 | `10` | SDK reconnect. |
| `NATS_RECONNECT_TIME_WAIT_SECONDS` | float `>0` | 선택 | `2.0` | SDK reconnect delay. |
| `NATS_PING_INTERVAL_SECONDS` | int `>=1` | 선택 | `120` | SDK ping interval. |
| `NATS_MAX_OUTSTANDING_PINGS` | int `>=1` | 선택 | `2` | SDK outstanding ping limit. |
| `NATS_NO_ECHO` | bool | 선택 | `false` | SDK no_echo. |

인증은 user/password, token, creds file 중 **최대 하나**다. user/password는 함께 제공해야 한다. 인증 없는 연결도 허용한다. `create_nats_client()`는 연결을 열지 않는 builder를 만들며 persistent connection 소유권은 caller에게 있다.

## 12. `.env.example` 사용법

[`.env.example`](../.env.example)은 모든 인식 key를 한 번씩 제공한다.

1. 파일을 복사한다.
2. 사용할 서비스 section만 uncomment한다.
3. `replace-me` placeholder를 실제 Secret 주입으로 교체한다.
4. 애플리케이션의 `RuntimePlan`에 같은 서비스를 선택한다.
5. startup 전에 `diagnose_services(plan=...)`를 실행한다.

```bash
cp .env.example .env
```

라이브러리는 `.env` 파일을 자동 로드하지 않는다. shell, container orchestrator 또는 애플리케이션 bootstrap이 파일 값을 **프로세스 환경변수로 주입**해야 한다.

## 13. 설정 → API 추적표

| 설정 영역 | 설정 타입 (`docmesh_config`) | client API (`docmesh_py_core`) | 예제 |
| --- | --- | --- | --- |
| Keycloak | `KeycloakConfig` | `create_keycloak_client`, `KeycloakAuthService`, `KeycloakProvisioner` | [token/JWT](./examples.md#8-keycloak-token-획득과-jwt-사용자-정보), [provisioning](./examples.md#9-keycloak-provisioning) |
| PostgreSQL | `PostgresConfig` | `create_postgres_client` | [동기 batch](./examples.md#3-동기-clibatch) |
| SQLite | `SqliteConfig` | `create_sqlite_client` | [최소 runtime](./examples.md#1-최소-sqlite-비동기-runtime), [direct](./examples.md#5-direct-factory-sqlite) |
| MinIO | `MinioConfig` | `create_minio_client`, `MinioRuntimeDefaults` | [FastAPI](./examples.md#2-fastapi-lifespan과-readiness) |
| Milvus | `MilvusConfig` | `create_milvus_client`, `MilvusRuntimeDefaults` | [API factory matrix](./api.md#5-service-factory와-wrapper) |
| Ollama | `OllamaConfig` | `create_ollama_client`, `OllamaRuntimeDefaults` | [API factory matrix](./api.md#5-service-factory와-wrapper) |
| Langfuse | `LangfuseConfig` | `create_langfuse_client` | [API factory matrix](./api.md#5-service-factory와-wrapper) |
| NATS | `NatsConfig` | `create_nats_client`, `NatsConnectionBuilder` | [NATS 소유권](./examples.md#6-nats-lazy-connection과-소유권) |
| 공통 lifecycle | `RuntimePlan`, `HealthcheckPolicy`, `Service` | `service_lifespan`, `assemble_service_runtime`, `assemble_services` | [SQLite](./examples.md#1-최소-sqlite-비동기-runtime), [policy](./examples.md#7-runtime-상태-정책-재실행) |
| 로깅 | 별도 `DOCMESH_LOG_LEVEL` helper | `configure_logging`, `LifecycleEvent` | [관측성](./examples.md#10-로깅과-lifecycle-observer) |
