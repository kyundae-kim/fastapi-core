---
source_url: https://github.com/kyundae-kim/docmesh-config/wiki/Configuration-v0.1.0
ingested: 2026-08-01
sha256: a1b0c9d61fda4653b52fbbefc8d6a6b92922c83f7166808a00194c684455d830
---
# docmesh-config 설정 레퍼런스

| 항목 | 내용 |
| --- | --- |
| 기준 버전 | 0.1.0 |
| 최종 갱신일 | 2026-07-31 |
| 설정 입력 | 프로세스 환경변수 전용 |
| 추적 요구사항 | [SRS NFR-8](./srs.md#5-비기능-요구사항) |
| 환경 템플릿 | [../.env.example](../.env.example) |
| API 레퍼런스 | [api.md](./api.md) |
| 실행 예제 | [example.md](./example.md) |

이 문서는 `CommonConfig`와 `SERVICE_CONFIG_TYPES`에 등록된 8개 서비스의 **98개 환경변수**를 모두 추적한다.

## 1. 공통 규칙

- 설정 모델은 생성자 인자 없이 생성하며 프로세스 환경변수만 읽는다.
- 환경변수 이름은 대소문자를 구분하지 않지만 문서와 배포 설정에는 canonical 대문자 이름을 사용한다.
- 앞뒤 공백은 제거하고, 공백만 있는 값은 미설정으로 처리한다.
- `bool`은 Pydantic이 지원하는 boolean 문자열(`true`/`false`, `1`/`0` 등)로 파싱한다.
- `CSV`는 쉼표로 구분하며 각 항목의 공백과 빈 항목을 제거한다.
- 필수값은 해당 서비스를 선택하거나 관련 환경변수로 활성화했을 때 필수다.
- `repr`, `str`, `model_dump()`, `model_dump_json()`, validation 오류와 진단 결과에서 secret 및 endpoint credential을 마스킹한다.
- `.env` 파일은 자동 로드하지 않는다. 애플리케이션·container·orchestrator가 프로세스 환경으로 주입해야 한다.

표기:

- **필수**: 서비스가 선택되면 반드시 제공
- **조건부**: 다른 설정값에 따라 필수
- **선택**: 생략 가능하며 기본값 적용
- **민감**: 로그·직렬화 출력에서 원문 사용 금지

## 2. 공통 환경

### `CommonConfig` (`DOCMESH_`)

| 환경변수 | 필드 | 타입 | 필수 여부 | 기본값 | 설명·제약 |
| --- | --- | --- | --- | --- | --- |
| `DOCMESH_ENV` | `env` | string | 선택 | `development` | 실행 환경 이름. production alias와 비교한다. |
| `DOCMESH_SECURITY_MODE` | `security_mode` | `development` 또는 `production` | 선택 | 미설정 | 설정하면 `DOCMESH_ENV`보다 production 판정에 우선한다. |
| `DOCMESH_PRODUCTION_ALIASES` | `production_aliases` | CSV | 선택 | `prod,production` | `DOCMESH_ENV`를 production으로 간주할 소문자 비교 alias. |

## 3. Keycloak

### 최소 discovery: `KeycloakDiscoveryConfig`

`KEYCLOAK_URL`, `KEYCLOAK_REALM`만 읽는 최소 모델이다. 전체 설정은 아래 `KeycloakConfig`를 사용한다.

### `KeycloakConfig` (`KEYCLOAK_`)

| 환경변수 | 필드 | 타입 | 필수 여부 | 기본값 | 설명·제약 |
| --- | --- | --- | --- | --- | --- |
| `KEYCLOAK_URL` | `url` | string | 필수·민감 출력 | 없음 | Keycloak base URL. URL credential은 마스킹한다. |
| `KEYCLOAK_REALM` | `realm` | string | 필수 | 없음 | 사용자 realm 이름. |
| `KEYCLOAK_CLIENT_ID` | `client_id` | string | 필수 | 없음 | 애플리케이션 client ID. |
| `KEYCLOAK_CLIENT_SECRET` | `client_secret` | string | 조건부·민감 | 미설정 | `KEYCLOAK_CLIENT_PUBLIC=false`이면 필수. |
| `KEYCLOAK_VERIFY_SSL` | `verify_ssl` | bool | 선택 | `true` | production에서 `false` 금지. |
| `KEYCLOAK_AUDIENCE` | `audience` | string | 선택 | 미설정 | 기대 token audience. |
| `KEYCLOAK_TOKEN_GRANT_TYPE` | `token_grant_type` | string | 선택 | `password` | `password` 또는 `client_credentials`. |
| `KEYCLOAK_TOKEN_SCOPE` | `token_scope` | string | 선택 | 미설정 | token 요청 scope. |
| `KEYCLOAK_TOKEN_USERNAME` | `token_username` | string | 선택 | 미설정 | password grant 사용자명. |
| `KEYCLOAK_TOKEN_PASSWORD` | `token_password` | string | 선택·민감 | 미설정 | password grant 비밀번호. |
| `KEYCLOAK_REQUEST_TIMEOUT_SECONDS` | `request_timeout_seconds` | int | 선택 | `10` | 1 이상. |
| `KEYCLOAK_MAX_RETRIES` | `max_retries` | int | 선택 | `3` | 0 이상. |
| `KEYCLOAK_JWKS_CACHE_TTL_SECONDS` | `jwks_cache_ttl_seconds` | int | 선택 | `300` | 0 이상. |
| `KEYCLOAK_PROVISIONING_ENABLED` | `provisioning_enabled` | bool | 선택 | `false` | provisioning metadata 활성화. |
| `KEYCLOAK_PROVISIONING_DRY_RUN` | `provisioning_dry_run` | bool | 선택 | `false` | provisioning dry-run metadata. |
| `KEYCLOAK_ADMIN_REALM` | `admin_realm` | string | 선택 | `master` | admin 인증 realm. |
| `KEYCLOAK_ADMIN_CLIENT_ID` | `admin_client_id` | string | 선택 | `admin-cli` | admin client ID. |
| `KEYCLOAK_ADMIN_CLIENT_SECRET` | `admin_client_secret` | string | 조건부·민감 | 미설정 | provisioning 시 admin service-account 방식. |
| `KEYCLOAK_ADMIN_USERNAME` | `admin_username` | string | 조건부 | 미설정 | provisioning 시 사용자 인증 방식의 username. |
| `KEYCLOAK_ADMIN_PASSWORD` | `admin_password` | string | 조건부·민감 | 미설정 | provisioning 시 사용자 인증 방식의 password. |
| `KEYCLOAK_REALM_ENABLED` | `realm_enabled` | bool | 선택 | `true` | 선언적 realm 활성화 상태. |
| `KEYCLOAK_REALM_DISPLAY_NAME` | `realm_display_name` | string | 선택 | 미설정 | 선언적 realm 표시 이름. |
| `KEYCLOAK_CLIENT_PUBLIC` | `client_public` | bool | 선택 | `false` | `true`이면 client secret이 없어도 된다. |
| `KEYCLOAK_CLIENT_REDIRECT_URIS` | `client_redirect_uris` | CSV | 선택·민감 출력 | 빈 목록 | redirect URI 목록. URL credential을 마스킹한다. |
| `KEYCLOAK_CLIENT_WEB_ORIGINS` | `client_web_origins` | CSV | 선택·민감 출력 | 빈 목록 | web origin 목록. URL credential을 마스킹한다. |
| `KEYCLOAK_REALM_ROLES` | `realm_roles` | CSV | 선택 | 빈 목록 | 선언적 realm role 목록. |
| `KEYCLOAK_CLIENT_ROLES` | `client_roles` | CSV | 선택 | 빈 목록 | 선언적 client role 목록. |

`KEYCLOAK_PROVISIONING_ENABLED=true`이면 admin 인증 방식은 정확히 하나여야 한다.

1. `KEYCLOAK_ADMIN_CLIENT_SECRET`, 또는
2. `KEYCLOAK_ADMIN_USERNAME`과 `KEYCLOAK_ADMIN_PASSWORD`의 쌍

## 4. PostgreSQL

### `PostgresConfig` (`POSTGRES_`)

| 환경변수 | 필드 | 타입 | 필수 여부 | 기본값 | 설명·제약 |
| --- | --- | --- | --- | --- | --- |
| `POSTGRES_HOST` | `host` | string | 필수 | 없음 | database host. |
| `POSTGRES_PORT` | `port` | int | 선택 | `5432` | 1~65535. |
| `POSTGRES_DB` | `db` | string | 필수 | 없음 | database 이름. |
| `POSTGRES_USER` | `user` | string | 필수 | 없음 | database 사용자명. |
| `POSTGRES_PASSWORD` | `password` | string | 필수·민감 | 없음 | database 비밀번호. |
| `POSTGRES_SSLMODE` | `sslmode` | string | 선택 | `prefer` | PostgreSQL client에 전달할 SSL mode metadata. |
| `POSTGRES_CONNECT_TIMEOUT_SECONDS` | `connect_timeout_seconds` | int | 선택 | `10` | 1 이상. |
| `POSTGRES_POOL_SIZE` | `pool_size` | int | 선택 | `5` | 1 이상. |
| `POSTGRES_MAX_OVERFLOW` | `max_overflow` | int | 선택 | `10` | 0 이상. |
| `POSTGRES_POOL_PRE_PING` | `pool_pre_ping` | bool | 선택 | `false` | pool pre-ping metadata. |
| `POSTGRES_POOL_RECYCLE_SECONDS` | `pool_recycle_seconds` | int | 선택 | `-1` | -1 이상. -1은 비활성 의미. |
| `POSTGRES_ECHO` | `echo` | bool | 선택 | `false` | SQL echo metadata. 민감정보 로그 위험을 호출자가 관리한다. |
| `POSTGRES_APPLICATION_NAME` | `application_name` | string | 선택 | 미설정 | database application name. |

## 5. SQLite

### `SqliteConfig` (`SQLITE_`)

| 환경변수 | 필드 | 타입 | 필수 여부 | 기본값 | 설명·제약 |
| --- | --- | --- | --- | --- | --- |
| `SQLITE_PATH` | `path` | string | 필수 | 없음 | `:memory:` 또는 파일 경로. 상대 경로는 현재 작업 디렉터리 기준 절대 경로로 변환. |
| `SQLITE_READONLY` | `readonly` | bool | 선택 | `false` | 읽기 전용 metadata. |
| `SQLITE_ENABLE_WAL` | `enable_wal` | bool | 선택 | `false` | WAL 활성화 metadata. |
| `SQLITE_BUSY_TIMEOUT_MS` | `busy_timeout_ms` | int | 선택 | `5000` | 0 이상. |
| `SQLITE_CHECK_SAME_THREAD` | `check_same_thread` | bool | 선택 | `false` | SQLite thread check metadata. |
| `SQLITE_ECHO` | `echo` | bool | 선택 | `false` | SQL echo metadata. |

## 6. MinIO

### `MinioConfig` (`MINIO_`)

| 환경변수 | 필드 | 타입 | 필수 여부 | 기본값 | 설명·제약 |
| --- | --- | --- | --- | --- | --- |
| `MINIO_ENDPOINT` | `endpoint` | string | 필수·민감 출력 | 없음 | MinIO endpoint. URL credential은 마스킹한다. |
| `MINIO_ACCESS_KEY` | `access_key` | string | 필수·민감 | 없음 | access key. |
| `MINIO_SECRET_KEY` | `secret_key` | string | 필수·민감 | 없음 | secret key. |
| `MINIO_SECURE` | `secure` | bool | 선택 | `true` | production에서 `false` 금지. |
| `MINIO_CERT_CHECK` | `cert_check` | bool | 선택 | `true` | production에서 `false` 금지. |
| `MINIO_REGION` | `region` | string | 선택 | 미설정 | object storage region. |
| `MINIO_BUCKET` | `bucket` | string | 조건부 | 미설정 | `RuntimePlan.minio_bucket_required=true`인 소비자에게 필수. |
| `MINIO_REQUEST_TIMEOUT_SECONDS` | `request_timeout_seconds` | int | 선택 | `30` | 1 이상. |
| `MINIO_MAX_RETRIES` | `max_retries` | int | 선택 | `3` | 0 이상. |

## 7. Milvus

### `MilvusConfig` (`MILVUS_`)

| 환경변수 | 필드 | 타입 | 필수 여부 | 기본값 | 설명·제약 |
| --- | --- | --- | --- | --- | --- |
| `MILVUS_ENDPOINT` | `endpoint` | string | 필수·민감 출력 | 없음 | Milvus 연결 endpoint. `MILVUS_URI`는 지원하지 않는다. |
| `MILVUS_TOKEN` | `token` | string | 선택·민감 | 미설정 | Milvus 인증 token. |
| `MILVUS_DB_NAME` | `db_name` | string | 선택 | `default` | database 이름. |
| `MILVUS_COLLECTION` | `collection` | string | 선택 | 미설정 | 기본 collection metadata. |
| `MILVUS_SECURE` | `secure` | bool | 선택 | `false` | production에서는 `true` 필수. |
| `MILVUS_CONNECT_TIMEOUT_SECONDS` | `connect_timeout_seconds` | int | 선택 | `10` | 1 이상. |
| `MILVUS_REQUEST_TIMEOUT_SECONDS` | `request_timeout_seconds` | int | 선택 | `30` | 1 이상. |
| `MILVUS_MAX_RETRIES` | `max_retries` | int | 선택 | `3` | 0 이상. |

이전 Python 필드 `MilvusConfig.uri`와 환경변수 `MILVUS_URI`에는 compatibility alias가 없다.

## 8. Ollama

### `OllamaConfig` (`OLLAMA_`)

| 환경변수 | 필드 | 타입 | 필수 여부 | 기본값 | 설명·제약 |
| --- | --- | --- | --- | --- | --- |
| `OLLAMA_HOST` | `host` | string | 필수·민감 출력 | 없음 | Ollama server URL/host. |
| `OLLAMA_VERIFY_SSL` | `verify_ssl` | bool | 선택 | `true` | production에서 `false` 금지. |
| `OLLAMA_FOLLOW_REDIRECTS` | `follow_redirects` | bool | 선택 | `true` | redirect follow metadata. |
| `OLLAMA_GENERATION_MODEL` | `generation_model` | string | 선택 | 미설정 | 기본 generation model. |
| `OLLAMA_EMBEDDING_MODEL` | `embedding_model` | string | 선택 | 미설정 | 기본 embedding model. |
| `OLLAMA_REQUEST_TIMEOUT_SECONDS` | `request_timeout_seconds` | int | 선택 | `120` | 1 이상. |
| `OLLAMA_MAX_RETRIES` | `max_retries` | int | 선택 | `2` | 0 이상. |

## 9. Langfuse

### `LangfuseConfig` (`LANGFUSE_`)

| 환경변수 | 필드 | 타입 | 필수 여부 | 기본값 | 설명·제약 |
| --- | --- | --- | --- | --- | --- |
| `LANGFUSE_ENABLED` | `enabled` | bool | 선택 | `true` | `true`이면 host/public key/secret key 필수. |
| `LANGFUSE_HOST` | `host` | string | 조건부·민감 출력 | 미설정 | Langfuse host. enabled일 때 필수. |
| `LANGFUSE_PUBLIC_KEY` | `public_key` | string | 조건부 | 미설정 | enabled일 때 필수. production placeholder 검사 대상. |
| `LANGFUSE_SECRET_KEY` | `secret_key` | string | 조건부·민감 | 미설정 | enabled일 때 필수. |
| `LANGFUSE_RELEASE` | `release` | string | 선택 | 미설정 | release metadata. |
| `LANGFUSE_ENVIRONMENT` | `environment` | string | 선택 | `DOCMESH_ENV` | 미설정 시 `CommonConfig.env` 사용. |
| `LANGFUSE_REQUEST_TIMEOUT_SECONDS` | `request_timeout_seconds` | int | 선택 | `10` | 1 이상. |
| `LANGFUSE_MAX_RETRIES` | `max_retries` | int | 선택 | `3` | 0 이상. |
| `LANGFUSE_DEBUG` | `debug` | bool | 선택 | `false` | debug metadata. |
| `LANGFUSE_TRACING_ENABLED` | `tracing_enabled` | bool | 선택 | `true` | tracing 활성화 metadata. |
| `LANGFUSE_FLUSH_AT` | `flush_at` | int | 선택 | 미설정 | 설정 시 1 이상. |
| `LANGFUSE_FLUSH_INTERVAL_SECONDS` | `flush_interval_seconds` | float | 선택 | 미설정 | 설정 시 0보다 큼. |
| `LANGFUSE_SAMPLE_RATE` | `sample_rate` | float | 선택 | 미설정 | 설정 시 0~1. |

`LANGFUSE_ENABLED=false`이면 host와 key를 생략할 수 있다.

## 10. NATS

### `NatsConfig` (`NATS_`)

| 환경변수 | 필드 | 타입 | 필수 여부 | 기본값 | 설명·제약 |
| --- | --- | --- | --- | --- | --- |
| `NATS_SERVERS` | `servers` | CSV | 필수·민감 출력 | 빈 목록 | 하나 이상의 server URL. |
| `NATS_USER` | `user` | string | 조건부 | 미설정 | username/password 인증 방식. password와 함께 제공. |
| `NATS_PASSWORD` | `password` | string | 조건부·민감 | 미설정 | username/password 인증 방식. user와 함께 제공. |
| `NATS_TOKEN` | `token` | string | 조건부·민감 | 미설정 | token 인증 방식. |
| `NATS_CREDS_FILE` | `creds_file` | string | 조건부 | 미설정 | credentials file 인증 방식. |
| `NATS_NAME` | `name` | string | 선택 | `docmesh-config` | client name metadata. |
| `NATS_CONNECT_TIMEOUT_SECONDS` | `connect_timeout_seconds` | int | 선택 | `10` | 1 이상. |
| `NATS_MAX_RECONNECT_ATTEMPTS` | `max_reconnect_attempts` | int | 선택 | `10` | 0 이상. |
| `NATS_RECONNECT_TIME_WAIT_SECONDS` | `reconnect_time_wait_seconds` | float | 선택 | `2.0` | 0보다 큼. |
| `NATS_PING_INTERVAL_SECONDS` | `ping_interval_seconds` | int | 선택 | `120` | 1 이상. |
| `NATS_MAX_OUTSTANDING_PINGS` | `max_outstanding_pings` | int | 선택 | `2` | 1 이상. |
| `NATS_NO_ECHO` | `no_echo` | bool | 선택 | `false` | no-echo metadata. |

인증 방식은 다음 중 최대 하나만 사용한다.

1. `NATS_USER` + `NATS_PASSWORD`
2. `NATS_TOKEN`
3. `NATS_CREDS_FILE`

## 11. Production 보안 규칙

`DOCMESH_SECURITY_MODE=production` 또는 production alias에 해당하는 `DOCMESH_ENV`에서는 다음 값이 금지된다.

| 금지 설정 | 필요한 값 |
| --- | --- |
| `KEYCLOAK_VERIFY_SSL=false` | `true` |
| `MINIO_SECURE=false` | `true` |
| `MINIO_CERT_CHECK=false` | `true` |
| `MILVUS_SECURE=false` | `true` |
| `OLLAMA_VERIFY_SSL=false` | `true` |

secret의 `replace-me`, `changeme`, `change-me`, `placeholder` 값과 endpoint의 `example.com`, `localhost`, `127.0.0.1`도 production 진단에서 placeholder 문제로 보고한다.

## 12. `.env.example` 사용 지침

`.env.example`은 모든 canonical 환경변수를 나열한 추적 가능한 템플릿이다.

1. 필요한 서비스 block만 복사하거나 주석을 해제한다.
2. placeholder credential을 실제 secret으로 교체한다.
3. 실제 `.env`와 secret은 저장소에 커밋하지 않는다.
4. production에서는 Secret manager, container secret 또는 orchestrator를 통해 프로세스 환경변수로 주입한다.
5. 라이브러리는 `.env` 파일을 자동으로 읽지 않는다.
