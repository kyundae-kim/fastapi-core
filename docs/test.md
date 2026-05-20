# 테스트 가이드

## 개요

테스트는 **단위 테스트(mock 기반)**와 **통합 테스트(실 서비스 연결)**로 분리됩니다.

- **단위 테스트**: 외부 서비스(Keycloak, PostgreSQL, MinIO) 없이 `unittest.mock`으로 의존성을 교체하여 빠른 피드백 제공
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
│   ├── test_security.py                # core.security mock 단위 테스트
│   ├── test_security_integration.py    # Keycloak 연동 통합 테스트
│   ├── test_storage.py                 # core.storage mock 단위 테스트
│   └── test_storage_integration.py     # MinIO 연동 통합 테스트
├── dependencies/
│   ├── test_config.py                  # get_config, get_settings Depends 단위 테스트
│   ├── test_database.py                # get_db_engine Depends 단위 테스트
│   ├── test_security.py                # get_current_user, require_permissions 단위 테스트
│   └── test_storage.py                 # get_minio_client Depends 단위 테스트
└── routers/
    ├── test_health.py                  # /health/liveness, /health/readiness 단위 테스트
    ├── test_auth.py                    # /token, /user 라우터 mock 단위 테스트
    └── test_auth_integration.py        # /token, /user 라우터 Keycloak 연동 통합 테스트
```

---

## 단위 테스트 (mock 기반)

외부 의존성(Keycloak, DB, MinIO) 없이 실행됩니다.

```bash
uv run pytest -q
```

### 파일별 설명

| 파일 | 설명 |
| --- | --- |
| `core/test_config.py` | `DatabaseConfig.sqlalchemy_database_url` 조합 로직, `trust`/`password` 인증 방식, `DB__URL` 직접 지정 케이스 |
| `core/test_security.py` | `extract_roles`, `extract_scopes` 순수 함수 및 `KeycloakAuthProvider` 메서드 전체 mock 테스트 |
| `core/test_storage.py` | `create_minio_client`, `ensure_bucket_exists`, `list_buckets` mock 테스트 |
| `dependencies/test_config.py` | `get_config`, `get_settings` Depends 반환값 검증 |
| `dependencies/test_database.py` | `get_db_engine` Depends mock 테스트 — `app.state.db_engine` 우선 반환 및 fallback 동작 검증 포함 |
| `dependencies/test_security.py` | `get_current_user`, `require_permissions` 의존성 함수 mock 테스트 — `app.state.auth_provider` 우선 반환 및 fallback 동작 검증 포함 |
| `dependencies/test_storage.py` | `get_minio_client` Depends mock 테스트 — `app.state.minio_client` 우선 반환 및 fallback 동작 검증 포함 |
| `routers/test_health.py` | `/health/liveness` 200 응답, `/health/readiness` Keycloak mock 연결 확인 |
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

devcontainer 환경에서 실제 Keycloak·PostgreSQL·MinIO 인스턴스에 연결합니다.  
`KEYCLOAK_USERNAME`, `KEYCLOAK_PASSWORD` 환경 변수가 설정되어 있어야 합니다.

```bash
uv run pytest -q -m integration
```

### 파일별 설명

| 파일 | 설명 |
| --- | --- |
| `core/test_security_integration.py` | 실제 Keycloak 토큰 발급, RS256 서명 검증, 클레임 추출 검증 |
| `core/test_storage_integration.py` | 실제 MinIO 클라이언트 생성, 버킷 자동 생성, 버킷 목록 조회 |
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

## `dependencies/test_security.py` 검증 항목

| 테스트 함수 | 검증 내용 |
| --- | --- |
| `test_get_auth_provider_from_state` | `app.state.auth_provider` 가 있을 때 동일 인스턴스 반환, `KeycloakAuthProvider` 생성자 미호출 |
| `test_get_auth_provider_fallback` | `app.state`에 `auth_provider` 없을 때 `KeycloakAuthProvider` 즉시 생성 후 반환 |
| `test_get_current_user_valid` | 유효한 Bearer 토큰으로 `UserInfo` 반환 |
| `test_get_current_user_missing_token` | Authorization 헤더 없을 때 401 반환 |
| `test_get_current_user_invalid_token` | 잘못된 토큰으로 401 반환 |
| `test_require_permissions_allowed` | 필요 역할 보유 시 통과 |
| `test_require_permissions_forbidden` | 필요 역할 미보유 시 403 반환 |

## `dependencies/test_database.py` 검증 항목

| 테스트 함수 | 검증 내용 |
| --- | --- |
| `test_get_db_engine_from_state` | `app.state.db_engine` 이 있을 때 동일 인스턴스 반환, `create_db_engine` 미호출 |
| `test_get_db_engine_fallback` | `app.state`에 `db_engine` 없을 때 `create_db_engine` 즉시 호출 후 반환 |

## `dependencies/test_storage.py` 검증 항목

| 테스트 함수 | 검증 내용 |
| --- | --- |
| `test_get_minio_client_from_state` | `app.state.minio_client` 가 있을 때 동일 인스턴스 반환, `create_minio_client` 미호출 |
| `test_get_minio_client_fallback` | `app.state`에 `minio_client` 없을 때 `create_minio_client` 즉시 호출 후 반환 |
