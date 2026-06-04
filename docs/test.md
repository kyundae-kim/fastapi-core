# 테스트 가이드

## 개요

테스트는 **단위 테스트(mock 기반)**와 **통합 테스트(실 서비스 연결)**로 분리됩니다.

- **단위 테스트**: 외부 서비스(Keycloak, PostgreSQL, MinIO, Milvus, Ollama) 없이 `unittest.mock`으로 의존성을 교체하여 빠른 피드백 제공
- **통합 테스트**: devcontainer 환경에서 실제 인스턴스에 연결하여 실환경 문제 조기 탐지

pytest 설정은 `pyproject.toml`의 `[tool.pytest.ini_options]`에 정의되어 있으며, 테스트 루트는 `test_fastapi_core/`입니다.

---

## 테스트 실행

```bash
# 단위 테스트만 실행 (외부 서비스 불필요)
uv run pytest -q

# 통합 테스트 포함 전체 실행 (devcontainer 환경)
uv run pytest -q -m integration

# 특정 모듈만 실행
uv run pytest test_fastapi_core/core/test_security.py -v
```

---

## 테스트 구조

```
test_fastapi_core/
├── core/
│   ├── test_config.py                  # EnvConfig, DatabaseConfig, MinIOConfig 단위 테스트
│   ├── test_async_milvus.py            # core.async milvus mock 단위 테스트
│   ├── test_async_milvus_integration.py # async Milvus 연동 통합 테스트
│   ├── test_milvus.py                  # core.milvus mock 단위 테스트
│   ├── test_milvus_integration.py      # Milvus 연동 통합 테스트
│   ├── test_ollama.py                  # core.ollama mock 단위 테스트
│   ├── test_ollama_integration.py      # Ollama 연동 통합 테스트
│   ├── test_security.py                # core.auth mock 단위 테스트
│   ├── test_security_integration.py    # Keycloak 연동 통합 테스트
│   ├── test_storage.py                 # core.storage mock 단위 테스트
│   └── test_storage_integration.py     # MinIO 연동 통합 테스트
├── dependencies/
│   ├── test_config.py                  # get_config, get_settings Depends 단위 테스트
│   ├── test_database.py                # get_db_engine Depends mock 단위 테스트
│   ├── test_database_integration.py    # PostgreSQL 연동 통합 테스트
│   ├── test_async_milvus.py            # get_async_milvus_client Depends mock 단위 테스트
│   ├── test_async_milvus_integration.py # async Milvus 연동 통합 테스트
│   ├── test_messaging.py               # get_nats_client Depends mock 단위 테스트
│   ├── test_messaging_integration.py   # NATS 연동 통합 테스트
│   ├── test_milvus.py                  # get_milvus_client Depends mock 단위 테스트
│   ├── test_milvus_integration.py      # Milvus 연동 통합 테스트
│   ├── test_ollama.py                  # get_ollama_client Depends mock 단위 테스트
│   ├── test_ollama_integration.py      # Ollama 연동 통합 테스트
│   ├── test_security.py                # get_current_user, require_permissions mock 단위 테스트 (dependencies/auth.py)
│   ├── test_security_integration.py    # Keycloak 연동 통합 테스트 (dependencies/auth.py)
│   ├── test_storage.py                 # get_minio_client Depends mock 단위 테스트
│   └── test_storage_integration.py     # MinIO 연동 통합 테스트
└── routers/
    ├── test_auth.py                    # /token, /user 라우터 mock 단위 테스트
    ├── test_auth_integration.py        # /token, /user 라우터 Keycloak 연동 통합 테스트
    └── test_health.py                  # /health/liveness, /health/readiness 단위 테스트
```

---

## 단위 테스트 (mock 기반)

외부 의존성(Keycloak, DB, MinIO, Milvus, Ollama) 없이 실행됩니다.

```bash
uv run pytest -q
```

### 파일별 설명

| 파일 | 설명 |
| --- | --- |
| `core/test_config.py` | `DatabaseConfig.sqlalchemy_database_url` 조합 로직, `trust`/`password` 인증 방식, `DB__URL` 직접 지정 케이스, DB pool 기본값 및 MinIO presigned 만료 기본값 검증 |
| `core/test_security.py` | `extract_roles`, `extract_scopes` 순수 함수 및 `KeycloakAuthProvider` 메서드 전체 mock 테스트 (`core.auth`) |
| `core/test_milvus.py` | `create_milvus_client`, `check_milvus_connection`, `list_collection_names`, `ensure_collection_exists` mock 테스트 |
| `core/test_async_milvus.py` | `create_async_milvus_client`, `check_async_milvus_connection`, `list_async_collection_names`, `ensure_async_collection_exists` mock 테스트 |
| `core/test_ollama.py` | `create_ollama_client`, `check_ollama_connection`, `list_model_names`, `generate_text` mock 테스트 |
| `core/test_storage.py` | `create_minio_client`, `ensure_bucket_exists`, `list_buckets`, presigned GET/PUT URL 생성 mock 테스트 |
| `dependencies/test_config.py` | `get_config`, `get_settings` Depends 반환값 검증 (`settings.health.*` 기본값 포함) |
| `dependencies/test_database.py` | `create_db_engine`·`check_database_connection` mock 테스트, `get_db_engine`/`get_db_session` Depends mock 테스트, `run_in_transaction` commit/rollback 검증 — `app.state.db_engine` 우선 반환 및 fallback 동작 포함 |
| `dependencies/test_milvus.py` | `create_milvus_client`·`get_milvus_client`·`set_milvus_client` mock 테스트 — `app.state.milvus_client` 우선 반환 및 fallback 동작 검증 포함 |
| `dependencies/test_async_milvus.py` | `create_async_milvus_client`·`get_async_milvus_client`·`set_async_milvus_client` mock 테스트 — `app.state.async_milvus_client` 우선 반환 및 fallback 동작 검증 포함 |
| `dependencies/test_ollama.py` | `create_ollama_client`·`get_ollama_client`·`set_ollama_client` mock 테스트 — `app.state.ollama_client` 우선 반환 및 fallback 동작 검증 포함 |
| `dependencies/test_security.py` | `set_auth_provider`·`get_auth_provider`·`get_current_user`·`require_permissions` mock 테스트 — `app.state.auth_provider` 우선 반환 및 fallback 동작 검증 포함 |
| `dependencies/test_storage.py` | `create_minio_client`·`get_minio_client`·`set_minio_client` mock 테스트 — `app.state.minio_client` 우선 반환 및 fallback 동작 검증 포함 |
| `routers/test_health.py` | `/health/liveness` 200 응답, `/health/readiness` Keycloak/DB/MinIO 종합 readiness mock 검증 |
| `routers/test_auth.py` | `/token` 발급 및 오류 응답, `/user` 인증 사용자 정보 반환 mock 테스트 |

---

## FastAPI State 기반 싱글톤 테스트 전략

`app.state`에 객체를 등록하는 싱글톤 패턴은 다음 두 가지 관점에서 테스트한다.

### 1. state 우선 조회 (singleton path)

lifespan이 `app.state`에 객체를 주입한 상황을 시뮬레이션하여 `Depends` 함수가 **재생성 없이 동일 인스턴스를 반환**하는지 검증한다.

```python
# 예시: dependencies/test_database.py
def test_get_db_engine_returns_state_engine():
    app = FastAPI()
    mock_engine = MagicMock(spec=Engine)
    app.state.db_engine = mock_engine          # state에 미리 주입

    client = TestClient(app)
    # get_db_engine이 create_db_engine을 호출하지 않고
    # app.state.db_engine을 그대로 반환하는지 검증
    with patch("fastapi_core.core.database.create_db_engine") as m:
        result = get_db_engine(Request({"type": "http", "app": app}))
        m.assert_not_called()
    assert result is mock_engine
```

각 모듈별 state 속성과 검증 포인트:

| 모듈 | state 속성 | 검증 포인트 |
| --- | --- | --- |
| `dependencies/test_security.py` | `app.state.auth_provider` | `KeycloakAuthProvider` 생성자 미호출, 동일 인스턴스 반환 |
| `dependencies/test_database.py` | `app.state.db_engine` | `create_db_engine` 미호출, 동일 인스턴스 반환 |
| `dependencies/test_storage.py` | `app.state.minio_client` | `create_minio_client` 미호출, 동일 인스턴스 반환 |
| `dependencies/test_milvus.py` | `app.state.milvus_client` | `create_milvus_client` 미호출, 동일 인스턴스 반환 |
| `dependencies/test_async_milvus.py` | `app.state.async_milvus_client` | `create_async_milvus_client` 미호출, 동일 인스턴스 반환 |
| `dependencies/test_ollama.py` | `app.state.ollama_client` | `create_ollama_client` 미호출, 동일 인스턴스 반환 |

### 2. fallback 동작 (state 미설정 path)

`app.state`에 해당 속성이 없을 때(`AttributeError`) `Depends` 함수가 `EnvConfig`를 읽어 **즉시 생성하는 폴백**이 동작하는지 검증한다.

```python
# 예시: dependencies/test_storage.py
def test_get_minio_client_fallback_when_no_state():
    app = FastAPI()          # state에 minio_client 미설정

    with patch("fastapi_core.dependencies.storage.create_minio_client") as m:
        m.return_value = MagicMock(spec=Minio)
        result = get_minio_client(Request({"type": "http", "app": app}))
        m.assert_called_once()   # fallback으로 즉시 생성 호출 확인
```

---

## 통합 테스트

devcontainer 환경에서 실제 Keycloak·PostgreSQL·MinIO·Milvus·Ollama 인스턴스에 연결합니다.  
`KEYCLOAK_USERNAME`, `KEYCLOAK_PASSWORD` 환경 변수가 설정되어 있어야 합니다.

NATS를 적용한 경우 테스트 NATS 서버를 함께 기동하여 메시징 통합 테스트를 추가합니다.

```bash
uv run pytest -q -m integration
```

### 파일별 설명

| 파일 | 설명 |
| --- | --- |
| `core/test_security_integration.py` | 실제 Keycloak 토큰 발급, RS256 서명 검증, 클레임 추출 검증 |
| `core/test_milvus_integration.py` | 실제 Milvus 클라이언트 생성, 연결 확인, 컬렉션 목록 조회, 컬렉션 생성/정리 검증 |
| `core/test_async_milvus_integration.py` | 실제 AsyncMilvusClient 생성, 연결 확인, 컬렉션 목록 조회, 컬렉션 생성/정리 검증 |
| `core/test_ollama_integration.py` | 실제 Ollama 클라이언트 생성, 연결 확인, 모델 목록 조회 검증 |
| `core/test_storage_integration.py` | 실제 MinIO 클라이언트 생성, 버킷 자동 생성, 버킷 목록 조회, presigned GET/PUT URL 생성 |
| `dependencies/test_database_integration.py` | 실제 PostgreSQL 엔진 생성, 연결 확인(SELECT 1), DB 버전 조회, `get_db_session`/`run_in_transaction` 동작, state 싱글톤 검증 |
| `dependencies/test_milvus_integration.py` | 실제 Milvus 클라이언트로 state 싱글톤 검증, config 기반 등록, Depends 경유 연결 확인 |
| `dependencies/test_async_milvus_integration.py` | 실제 AsyncMilvusClient로 state 싱글톤 검증, config 기반 등록, Depends 경유 연결 확인 |
| `dependencies/test_ollama_integration.py` | 실제 Ollama 클라이언트로 state 싱글톤 검증, config 기반 등록, Depends 경유 연결 확인 |
| `dependencies/test_security_integration.py` | 실제 Keycloak 토큰으로 RS256 검증, `get_current_user`·`require_permissions` 실환경 동작 검증 |
| `dependencies/test_storage_integration.py` | 실제 MinIO 클라이언트로 state 싱글톤 검증, config 기반 등록, Depends 경유 버킷 접근 검증 |
| `dependencies/test_messaging.py` | `set_nats_client` 등록, `get_nats_client` state 반환 및 fallback lazy singleton 검증 (`AsyncMock` 기반) |
| `dependencies/test_messaging_integration.py` | 테스트 NATS 서버 연결, pub/sub round-trip, queue group 분배 검증 |
| `routers/test_auth_integration.py` | `/token` 실제 토큰 발급, `/user` 실제 토큰으로 사용자 정보 조회 |

---

## `core/test_security.py` 검증 항목

| 테스트 함수 | 검증 내용 |
| --- | --- |
| `test_extract_roles_*` | `realm_access.roles` 파싱 및 엣지 케이스 (키 없음, 빈 리스트) |
| `test_extract_scopes_*` | `scope` 문자열 / `scp` 리스트 파싱 및 엣지 케이스 |
| `test_keycloak_auth_provider_*_raises` | 잘못된 URL·realm·client_id 입력 시 `ValueError` |
| `test_to_user_*` | JWT payload → `UserInfo` 모델 매핑 검증 |
| `test_decode_token_insecure_*` | 서명 검증 없는 디코드 정상/오류 경로 |
| `test_decode_token_*` | RS256 서명 검증 디코드 정상/오류 경로 |
| `test_authenticate_*` | Keycloak 토큰 발급 정상/HTTP 오류 경로 |
| `test_refresh_token_*` | 토큰 갱신 정상/오류 경로 |

## `dependencies/test_security.py` 검증 항목 (mock 단위 테스트)

| 테스트 함수 | 검증 내용 |
| --- | --- |
| `test_get_auth_provider_from_state` | `app.state.auth_provider` 가 있을 때 동일 인스턴스 반환, `KeycloakAuthProvider` 생성자 미호출 |
| `test_get_auth_provider_fallback` | `app.state`에 `auth_provider` 없을 때 `KeycloakAuthProvider` 생성 후 `app.state.auth_provider`에 등록하여 반환 |
| `test_set_auth_provider_from_config` | `config` 전달 시 `KeycloakAuthProvider` 생성 후 `app.state.auth_provider` 에 등록 |
| `test_set_auth_provider_requires_provider_or_config` | `provider`, `config` 모두 생략 시 `ValueError` 발생 |
| `test_get_current_user_valid` | 유효한 Bearer 토큰으로 `UserInfo` 반환 |
| `test_get_current_user_missing_token` | Authorization 헤더 없을 때 401 반환 |
| `test_get_current_user_invalid_token` | 잘못된 토큰으로 401 반환 |
| `test_require_permissions_allowed` | 필요 역할 보유 시 통과 |
| `test_require_permissions_forbidden` | 필요 역할 미보유 시 403 반환 |

## `dependencies/test_security_integration.py` 검증 항목 (통합 테스트)

| 테스트 함수 | 검증 내용 |
| --- | --- |
| `test_get_auth_provider_from_state_integration` | 실제 `KeycloakAuthProvider`를 `app.state`에 등록 후 `get_auth_provider` Depends가 동일 인스턴스를 반환하는지 검증 |
| `test_get_current_user_with_real_token` | 실제 Keycloak 토큰으로 RS256 서명 검증 후 `UserInfo` 반환 및 username 일치 확인 |
| `test_get_current_user_missing_token_integration` | 토큰 없이 요청 시 401 반환 |
| `test_require_permissions_forbidden_integration` | 실제 토큰이지만 필요 역할 미보유 시 403 반환 |

## `dependencies/test_database.py` 검증 항목 (mock 단위 테스트)

| 테스트 함수 | 검증 내용 |
| --- | --- |
| `test_get_db_engine_creates_engine` | `create_engine` mock — `sqlalchemy_database_url`·`echo`·pool 파라미터 인자 전달 및 반환값 검증 |
| `test_check_database_connection_success` | mock 엔진 연결 성공 시 `True` 반환 |
| `test_check_database_connection_failure` | mock 엔진 연결 예외 시 `False` 반환 |
| `test_get_db_engine_from_state` | `app.state.db_engine` 이 있을 때 동일 인스턴스 반환, `create_db_engine` 미호출 |
| `test_get_db_engine_fallback` | `app.state`에 `db_engine` 없을 때 `create_db_engine` 호출 후 `app.state.db_engine`에 등록하여 반환 |
| `test_set_db_engine_from_config` | `config` 전달 시 `create_db_engine` 호출 후 `app.state.db_engine` 에 등록 |
| `test_set_db_engine_requires_engine_or_config` | `engine`, `config` 모두 생략 시 `ValueError` 발생 |
| `test_get_db_session_closes_session` | `get_db_session`가 세션을 yield하고 종료 시 `close()` 호출을 보장 |
| `test_run_in_transaction_commit_and_return_value` | `run_in_transaction` 성공 경로에서 `commit` 호출 및 반환값 전달 |
| `test_run_in_transaction_rollback_on_error` | `run_in_transaction` 예외 경로에서 `rollback` 호출 후 예외 재전파 |

## `dependencies/test_database_integration.py` 검증 항목 (통합 테스트)

| 테스트 함수 | 검증 내용 |
| --- | --- |
| `test_create_db_engine` | 실제 PostgreSQL 엔진 생성 확인 |
| `test_check_database_connection` | 실제 DB에 SELECT 1 연결 확인 성공 |
| `test_get_database_version` | 실제 DB 버전 문자열 반환 및 `PostgreSQL` 포함 검증 |
| `test_get_db_engine_from_state_integration` | 실제 엔진을 `app.state`에 등록 후 `get_db_engine` Depends가 동일 인스턴스를 반환하는지 검증 |
| `test_get_db_session_integration` | 실제 DB 세션 의존성으로 `SELECT 1` 수행 가능 여부 검증 |
| `test_run_in_transaction_integration` | 실제 트랜잭션 헬퍼로 함수 실행 및 결과 반환 검증 |

## `dependencies/test_storage.py` 검증 항목 (mock 단위 테스트)

| 테스트 함수 | 검증 내용 |
| --- | --- |
| `test_get_minio_client_creates_client` | `Minio` 생성자 mock — `MinIOConfig` 인자 전달 및 반환값 검증 |
| `test_get_minio_client_from_state` | `app.state.minio_client` 가 있을 때 동일 인스턴스 반환, `create_minio_client` 미호출 |
| `test_get_minio_client_fallback` | `app.state`에 `minio_client` 없을 때 `create_minio_client` 호출 후 `app.state.minio_client`에 등록하여 반환 |
| `test_set_minio_client_from_config` | `config` 전달 시 `create_minio_client` 호출 후 `app.state.minio_client` 에 등록 |
| `test_set_minio_client_requires_client_or_config` | `client`, `config` 모두 생략 시 `ValueError` 발생 |

## `dependencies/test_storage_integration.py` 검증 항목 (통합 테스트)

| 테스트 함수 | 검증 내용 |
| --- | --- |
| `test_get_minio_client_from_state_integration` | 실제 MinIO 클라이언트를 `app.state`에 등록 후 `get_minio_client` Depends가 동일 인스턴스를 반환하는지 검증 |
| `test_set_minio_client_from_config_integration` | 실제 config으로 `set_minio_client` 호출 시 실제 `Minio` 인스턴스가 `app.state`에 등록됨 검증 |
| `test_get_minio_client_bucket_accessible` | Depends 경유 실제 클라이언트로 버킷 존재 여부 조회 가능 검증 |

## `core/test_storage.py` 검증 항목 (mock 단위 테스트)

| 테스트 함수 | 검증 내용 |
| --- | --- |
| `test_create_minio_client` | `Minio` 생성자 mock — `MinIOConfig` 인자 전달 및 반환값 검증 |
| `test_ensure_bucket_exists_creates_bucket` | 버킷 미존재 시 `make_bucket` 호출 검증 |
| `test_ensure_bucket_exists_no_create_if_exists` | 버킷 존재 시 `make_bucket` 미호출 검증 |
| `test_list_buckets` | 버킷 목록 이름 추출 검증 |
| `test_list_buckets_empty` | 빈 버킷 목록 처리 검증 |
| `test_check_minio_connection_success` | MinIO 연결 성공 시 `True` 반환 |
| `test_check_minio_connection_failure` | MinIO 연결 예외 시 `False` 반환 |
| `test_generate_presigned_get_url_default_expires` | presigned GET URL 생성 시 HTTP method/만료시간 기본값(900초) 전달 검증 |
| `test_generate_presigned_put_url_default_expires` | presigned PUT URL 생성 시 HTTP method/만료시간 기본값(900초) 전달 검증 |

## `core/test_storage_integration.py` 검증 항목 (통합 테스트)

| 테스트 함수 | 검증 내용 |
| --- | --- |
| `test_create_minio_client` | 실제 MinIO 클라이언트 인스턴스 생성 검증 |
| `test_ensure_bucket_exists` | 실제 버킷 생성/존재 보장 검증 |
| `test_list_buckets` | 실제 버킷 목록 조회 검증 |
| `test_generate_presigned_get_url` | 실제 presigned GET URL 생성 및 URL 형태/객체명 포함 검증 |
| `test_generate_presigned_put_url` | 실제 presigned PUT URL 생성 및 URL 형태/객체명 포함 검증 |

## `routers/test_health.py` 검증 항목 (mock 단위 테스트)

| 테스트 함수 | 검증 내용 |
| --- | --- |
| `test_liveness` | `/health/liveness` 200 및 `{ "status": "ok" }` 응답 검증 |
| `test_readiness_ok` | Keycloak/DB/MinIO 모두 정상일 때 `/health/readiness` 200 응답 검증 |
| `test_readiness_keycloak_not_ready` | Keycloak 비정상 상태(HTTP 503)에서 503 응답 검증 |
| `test_readiness_keycloak_unreachable` | Keycloak 연결 실패(RequestError)에서 503 응답 검증 |
| `test_readiness_database_not_ready` | DB readiness 실패 시 503 및 `Database not ready` 응답 검증 |
| `test_readiness_minio_not_ready` | MinIO readiness 실패 시 503 및 `MinIO not ready` 응답 검증 |
