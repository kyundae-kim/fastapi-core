# 테스트 가이드

## 개요

테스트는 **단위 테스트(mock 기반)**와 **통합 테스트(실제 Keycloak 연결)**로 분리됩니다.

- **단위 테스트**: 외부 서비스(Keycloak, DB) 없이 `unittest.mock`으로 의존성을 교체하여 빠른 피드백 제공
- **통합 테스트**: 실제 Keycloak 인스턴스에 연결하여 실환경 문제 조기 탐지

pytest 설정은 `pyproject.toml`의 `[tool.pytest.ini_options]`에 정의되어 있으며, 테스트 루트는 `test_fastapi_template/`입니다.

---

## 테스트 구조

```
test_fastapi_template/
├── core/
│   ├── test_config.py                  # 설정 단위 테스트
│   ├── test_security.py                # core.security mock 단위 테스트
│   ├── test_security_integration.py    # core.security Keycloak 연동 통합 테스트
│   ├── test_storage_mock.py            # core.storage mock 단위 테스트
│   └── test_storage_integration.py     # core.storage MinIO 연동 통합 테스트
├── dependencies/
│   └── test_security.py                # dependencies.security mock 단위 테스트
├── routes/
│   ├── test_auth.py                    # 인증 라우트 mock 단위 테스트
│   ├── test_auth_integration.py        # 인증 라우트 Keycloak 연동 통합 테스트
│   ├── test_database.py                # DB 라우트 mock 단위 테스트
│   ├── test_database_integration.py    # DB 라우트 PostgreSQL 연동 통합 테스트
│   ├── test_health.py                  # 헬스체크 라우트 테스트
│   ├── test_storage.py                 # MinIO 라우트 mock 단위 테스트
│   └── test_storage_integration.py     # MinIO 라우트 연동 통합 테스트
└── services/
    ├── test_security.py                # 서비스 계층 보안 mock 단위 테스트
    ├── test_security_integration.py    # 서비스 계층 Keycloak 연동 통합 테스트
    ├── test_database_mock.py           # 서비스 계층 DB mock 단위 테스트
    └── test_database_integration.py    # 서비스 계층 DB PostgreSQL 연동 통합 테스트
    
```

---

## 단위 테스트 (mock 기반)

외부 의존성(Keycloak, DB) 없이 실행됩니다.

```bash
source .venv/bin/activate && pytest -q
```

### 파일별 설명

| 파일 | 설명 |
| --- | --- |
| `core/test_config.py` | `DatabaseConfig.sqlalchemy_database_url` 생성 로직, 인증 방식(password/trust) 테스트 |
| `core/test_security.py` | `extract_roles`, `extract_scopes` 순수 함수 및 `KeycloakAuthProvider` 메서드 전체 mock 테스트 |
| `dependencies/test_security.py` | `get_current_user`, `require_permissions` 의존성 함수 mock 테스트 |
| `services/test_security.py` | `authenticate`, `refresh_token`, `decode_token` 서비스 함수 및 오류 경로 mock 테스트 |
| `routes/test_auth.py` | 인증 라우트 mock 단위 테스트 (`dependency_overrides` 활용) |
| `services/test_database_mock.py` | `create_db_engine`, `check_database_connection`, `get_database_version` 서비스 함수 mock 테스트 |
| `routes/test_database.py` | DB 예시 라우트 mock 단위 테스트 |
| `routes/test_health.py` | 헬스체크 라우트 테스트 |
| `services/test_storage_mock.py` | `create_minio_client`, `check_minio_connection`, `ensure_bucket_exists`, `list_buckets` mock 테스트 |
| `routes/test_storage.py` | MinIO 라우트 mock 단위 테스트 |

### `core/test_security.py` 검증 항목

| 테스트 함수 | 검증 내용 |
| --- | --- |
| `test_extract_roles_*` | `realm_access.roles` 파싱 및 엣지 케이스 |
| `test_extract_scopes_*` | `scope` 문자열 / `scp` 리스트 파싱 및 엣지 케이스 |
| `test_keycloak_auth_provider_*_raises` | 잘못된 URL·realm·client_id 입력 시 `ValueError` |
| `test_to_user_*` | payload → `User` 모델 매핑 검증 |
| `test_decode_token_insecure_*` | 서명 검증 없는 디코드 정상/오류 경로 |
| `test_decode_token_*` | RS256 서명 검증 디코드 정상/오류 경로 |
| `test_authenticate_*` | Keycloak 토큰 발급 정상/HTTP 오류 경로 |
| `test_refresh_access_token_*` | 토큰 갱신 정상/오류 경로 |
| `test_dummy_authenticate_*` | 개발용 더미 토큰 반환 검증 |

### `dependencies/test_security.py` 검증 항목

| 테스트 함수 | 검증 내용 |
| --- | --- |
| `test_get_current_user_uses_decode_token_with_mock` | `provider.decode_token` 호출 및 반환값 검증 |
| `test_get_current_user_invalid_token_raises_auth_error` | `InvalidTokenError` → 401 `invalid_token` |
| `test_get_current_user_key_error_raises_auth_error` | `KeyError` → 401 `invalid_token` |
| `test_require_permissions_role_and_scope_success` | 충분한 역할/스코프 보유 시 통과 |
| `test_require_permissions_role_and_scope_failure` | 누락된 역할/스코프 시 403 `insufficient_scope` |

### `services/test_security.py` 검증 항목

| 테스트 함수 | 검증 내용 |
| --- | --- |
| `test_get_auth_provider_returns_keycloak_instance` | `get_auth_provider()`가 `KeycloakAuthProvider` 반환 |
| `test_authenticate_returns_token` | 정상 인증 시 `Token` 반환 및 메서드 호출 확인 |
| `test_authenticate_invalid_credentials_raises_auth_error` | HTTP 401 → `AuthError(status=401, error="invalid_grant")` |
| `test_authenticate_timeout_raises_auth_error` | 타임아웃 → `AuthError(status=504, error="temporarily_unavailable")` |
| `test_authenticate_request_error_raises_auth_error` | 네트워크 오류 → `AuthError(status=502, error="server_error")` |
| `test_authenticate_empty_*_raises_value_error` | 빈 username/password 시 `ValueError` |
| `test_refresh_token_returns_token` | 정상 갱신 시 `Token` 반환 |
| `test_refresh_token_http_error_raises_auth_error` | HTTP 오류 → `AuthError(status=401)` |
| `test_refresh_token_timeout_raises_auth_error` | 타임아웃 → `AuthError(status=504)` |
| `test_refresh_token_empty_raises_value_error` | 빈 토큰 시 `ValueError` |
| `test_decode_token_verify_jwt_true_calls_decode_token` | `verify_jwt=True` 시 `decode_token` 호출 |
| `test_decode_token_verify_jwt_false_calls_insecure` | `verify_jwt=False` 시 `decode_token_insecure` 호출 |
| `test_decode_token_empty_token_raises_value_error` | 빈 토큰 시 `ValueError` |

### `services/test_database_mock.py` 검증 항목

| 테스트 함수 | 검증 내용 |
| --- | --- |
| `test_create_db_engine_calls_create_engine_with_url` | `create_engine`이 올바른 DSN·`echo`·`pool_pre_ping` 인자로 호출되는지 확인 |
| `test_check_database_connection_returns_true` | `execute` 정상 실행 시 `True` 반환 확인 |
| `test_check_database_connection_returns_false_on_sqlalchemy_error` | `SQLAlchemyError` 발생 시 `False` 반환 확인 |
| `test_get_database_version_returns_version_string` | `scalar_one()` 반환값이 문자열로 전달되는지 확인 |

### `core/test_storage_mock.py` 검증 항목

`core.storage` 함수를 대상으로 하며 실제 MinIO 연결 없이 실행됩니다.

| 테스트 함수 | 검증 내용 |
| --- | --- |
| `test_create_minio_client_calls_minio_with_config` | `Minio()`가 설정값 그대로 호출되는지 확인 |
| `test_check_minio_connection_returns_true` | `bucket_exists()` 정상 시 `True` 반환 확인 |
| `test_check_minio_connection_returns_false_on_exception` | 예외 발생 시 `False` 반환 확인 |
| `test_ensure_bucket_exists_creates_bucket_when_not_present` | 버킷 없을 때 `make_bucket()` 호출 확인 |
| `test_ensure_bucket_exists_skips_creation_when_already_present` | 버킷 있을 때 `make_bucket()` 미호출 확인 |
| `test_list_buckets_returns_bucket_names` | 버킷 이름 목록 반환 확인 |
| `test_list_buckets_empty` | 빈 목록 반환 확인 |

### `routes/test_storage.py` 검증 항목

| 테스트 함수 | 검증 내용 |
| --- | --- |
| `test_storage_ping_ready` | MinIO 연결 정상 시 `/storage/ping` 200 및 `status`·`endpoint`·`bucket` 응답 확인 |
| `test_storage_ping_not_ready` | MinIO 연결 실패 시 503 반환 확인 |
| `test_storage_list_buckets` | `/storage/buckets` 버킷 목록 반환 확인 |
| `test_storage_list_buckets_empty` | 빈 버킷 목록 반환 확인 |

---

## 통합 테스트 (실제 Keycloak 연결)

실제 Keycloak 인스턴스가 필요합니다.  
인증 자격 증명은 `KEYCLOAK_USERNAME` / `KEYCLOAK_PASSWORD` 환경 변수로 주입합니다 (기본값: `test` / `test`).  
자세한 환경 변수 설정은 [config.md](config.md)를 참고하세요.

Keycloak 연동 통합 테스트:

```bash
source .venv/bin/activate && pytest -q \
  test_fastapi_template/core/test_security_integration.py \
  test_fastapi_template/services/test_security_integration.py \
  test_fastapi_template/routes/test_auth_integration.py
```

PostgreSQL 연동 통합 테스트:

```bash
source .venv/bin/activate && pytest -q \
  test_fastapi_template/services/test_database_integration.py \
  test_fastapi_template/routes/test_database_integration.py
```

MinIO 연동 통합 테스트:

```bash
source .venv/bin/activate && pytest -q \
  test_fastapi_template/core/test_storage_integration.py \
  test_fastapi_template/routes/test_storage_integration.py
```

### `core/test_security_integration.py`

`KeycloakAuthProvider`를 실제 Keycloak에 연결하여 검증합니다.

| 테스트 함수 | 검증 내용 |
| --- | --- |
| `test_authenticate` | 정상 자격 증명으로 `Token` 발급 확인 |
| `test_decode_token_insecure` | 서명 검증 없이 JWT 디코드 후 `User` 반환 확인 |
| `test_decode_token` | RS256 서명 검증 후 `User` 반환 확인 |
| `test_refresh_access_token` | 리프레시 토큰으로 새 액세스 토큰 발급 확인 |

### `services/test_security_integration.py`

서비스 계층 함수를 실제 Keycloak으로 검증합니다.

| 테스트 함수 | 검증 내용 |
| --- | --- |
| `test_get_auth_provider` | `get_auth_provider()`가 `KeycloakAuthProvider` 반환 확인 |
| `test_authenticate` | 서비스 `authenticate()`로 유효한 `Token` 발급 확인 |
| `test_refresh_token` | 서비스 `refresh_token()`으로 새 `Token` 발급 확인 |
| `test_decode_token` | 서비스 `decode_token()`으로 `User` 반환 확인 |

### `routes/test_auth_integration.py`

인증 라우트를 실제 Keycloak에 연결하여 검증합니다.  
DB 엔진은 mock으로 대체하므로 PostgreSQL은 불필요합니다.

| 테스트 함수 | 검증 내용 |
| --- | --- |
| `test_get_token` | 정상 자격 증명으로 토큰 발급 확인 |
| `test_get_token_invalid_password` | 잘못된 비밀번호 → 401 `invalid_grant` |
| `test_get_token_invalid_username` | 존재하지 않는 사용자 → 401 `invalid_grant` |
| `test_get_user_info` | 실제 JWT로 `/user` 조회 |
| `test_get_user_info_no_token` | 토큰 없음 → 401 |
| `test_get_user_info_invalid_token` | 잘못된 JWT → 401 `invalid_token` |
| `test_get_user_info_malformed_header` | Authorization 헤더 형식 오류 → 401 |
| `test_example_read_with_token` | `read` 역할 보유 시 200, 미보유 시 403 |
| `test_example_create_with_token` | `create` 역할 보유 시 200, 미보유 시 403 |
| `test_example_delete_with_token` | `delete` 역할 보유 시 200, 미보유 시 403 |
| `test_example_read_no_token` | 토큰 없음 → 401 |

### `services/test_database_integration.py`

서비스 계층 DB 함수를 실제 PostgreSQL에 연결하여 검증합니다.  
DB 접속 정보는 `DB__*` 환경 변수로 주입합니다 (기본값: `localhost:5432`, 데이터베이스 `postgres`).

| 테스트 함수 | 검증 내용 |
| --- | --- |
| `test_check_database_connection` | 실제 PostgreSQL 연결 후 `True` 반환 확인 |
| `test_get_database_version` | 버전 문자열에 `"PostgreSQL"` 포함 확인 |

### `routes/test_database_integration.py`

DB 라우트를 실제 PostgreSQL에 연결하여 검증합니다.  
Keycloak auth provider는 mock으로 대체하므로 Keycloak은 불필요합니다.

| 테스트 함수 | 검증 내용 |
| --- | --- |
| `test_database_ping_ready` | 실제 DB 연결 시 `/db/example/ping` 200 및 `status`·`engine`·`auth_method` 응답 확인 |
| `test_database_version` | `/db/example/version` 에서 `"PostgreSQL"` 포함 버전 문자열 반환 확인 |

### `core/test_storage_integration.py`

`core.storage` 함수를 실제 MinIO에 연결하여 검증합니다.  
MinIO 접속 정보는 `MINIO__*` 환경 변수로 주입합니다.

| 테스트 함수 | 검증 내용 |
| --- | --- |
| `test_check_minio_connection_live` | 실제 MinIO 연결 후 `True` 반환 확인 |
| `test_ensure_bucket_exists_live` | 버킷 생성 또는 이미 존재 시 오류 없이 통과 확인 |
| `test_list_buckets_live` | 버킷 목록에 기본 버킷 포함 확인 |

### `routes/test_storage_integration.py`

MinIO 라우트를 실제 MinIO에 연결하여 검증합니다.  
DB 엔진·auth provider는 mock으로 대체하므로 PostgreSQL·Keycloak은 불필요합니다.

| 테스트 함수 | 검증 내용 |
| --- | --- |
| `test_storage_ping_ready` | 실제 MinIO 연결 시 `/storage/ping` 200 및 `status`·`endpoint`·`bucket` 응답 확인 |
| `test_storage_list_buckets` | `/storage/buckets` 에서 기본 버킷 포함 목록 반환 확인 |
