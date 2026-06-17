# 테스트 가이드

## 개요

테스트 루트는 `test_fastapi_core/`이며 `pyproject.toml`의 pytest 설정을 따릅니다.

현재 테스트는 marker 기준으로 두 그룹으로 나뉩니다.

- **단위 테스트**: 기본 그룹. mock / fake 중심으로 빠르게 검증
- **통합 테스트**: `@pytest.mark.integration`이 붙은 테스트. 외부 서비스가 필요할 수 있음

`pytest -q`는 **전체 테스트를 모두 수집/실행**합니다.
단위 테스트만 돌리고 싶다면 `-m "not integration"`를 사용해야 합니다.

---

## 실행 명령

```bash
# 단위 테스트만
uv run pytest -q -m "not integration"

# 통합 테스트만
uv run pytest -q -m integration

# 전체 테스트
uv run pytest -q

# 특정 파일
uv run pytest -q test_fastapi_core/core/test_messaging.py
```

---

## 현재 테스트 구조

```text
test_fastapi_core/
├── conftest.py
├── test_bootstrap.py
├── test_docmesh_bridge.py
├── test_factory.py
├── test_lifecycle.py
├── test_public_api.py
├── core/
│   ├── test_async_milvus.py
│   ├── test_async_milvus_integration.py
│   ├── test_config.py
│   ├── test_database.py
│   ├── test_langfuse.py
│   ├── test_langfuse_integration.py
│   ├── test_messaging.py
│   ├── test_milvus.py
│   ├── test_milvus_integration.py
│   ├── test_ollama.py
│   ├── test_security.py
│   ├── test_security_integration.py
│   ├── test_storage.py
│   └── test_storage_integration.py
├── dependencies/
│   ├── test_async_milvus.py
│   ├── test_async_milvus_integration.py
│   ├── test_class_dependencies.py
│   ├── test_config.py
│   ├── test_database.py
│   ├── test_database_integration.py
│   ├── test_langfuse.py
│   ├── test_messaging.py
│   ├── test_milvus.py
│   ├── test_milvus_integration.py
│   ├── test_ollama.py
│   ├── test_security.py
│   ├── test_security_integration.py
│   ├── test_storage.py
│   └── test_storage_integration.py
└── routers/
    ├── test_auth.py
    ├── test_auth_integration.py
    └── test_health.py
```

> 현재 저장소에는 `core/test_ollama_integration.py`나 `dependencies/test_messaging_integration.py` 파일이 없습니다.

---

## 파일별 역할

### 루트 레벨

| 파일 | 설명 |
| --- | --- |
| `test_bootstrap.py` | `app.state` bootstrap 유틸리티 동작 검증 |
| `test_docmesh_bridge.py` | registry env 변환, registry 초기화, healthcheck bridge 검증 |
| `test_factory.py` | `create_app()`의 기본 조립 동작 검증 |
| `test_lifecycle.py` | lifecycle policy 계산, startup/shutdown 정리 검증 |
| `test_public_api.py` | 패키지 루트 `__all__` curated export 검증 |

### `core/`

| 파일 | 설명 |
| --- | --- |
| `core/test_config.py` | `EnvConfig`, `ServiceSettings`, 설정 모델 기본값/파싱 검증 |
| `core/test_database.py` | `create_db_engine`, `check_database_connection`, `get_database_version`, `run_in_transaction` 검증 |
| `core/test_storage.py` | MinIO helper (`ensure_bucket_exists`, `list_bucket_names`, presigned URL) 검증 |
| `core/test_milvus.py` | sync Milvus helper 검증 |
| `core/test_async_milvus.py` | async Milvus helper 검증 |
| `core/test_ollama.py` | Ollama helper 검증 |
| `core/test_langfuse.py` | Langfuse helper 검증 |
| `core/test_messaging.py` | NATS helper 및 subject 규칙 검증 |
| `core/test_security.py` | `KeycloakAuthProvider` 및 payload 변환 검증 |
| `core/*_integration.py` | 실제 외부 서비스에 붙는 통합 검증 |

### `dependencies/`

| 파일 | 설명 |
| --- | --- |
| `dependencies/test_class_dependencies.py` | callable class dependency 미노출 정책 검증 |
| `dependencies/test_config.py` | `get_config`, `get_settings` 검증 |
| `dependencies/test_database.py` | `set_db_engine`, `get_db_engine`, `get_db_session` 검증 |
| `dependencies/test_storage.py` | `set_minio_client`, `get_minio_client` 검증 |
| `dependencies/test_milvus.py` | `set_milvus_client`, `get_milvus_client` 검증 |
| `dependencies/test_async_milvus.py` | `set_async_milvus_client`, `get_async_milvus_client` 검증 |
| `dependencies/test_ollama.py` | `set_ollama_client`, `get_ollama_client` 검증 |
| `dependencies/test_langfuse.py` | `set_langfuse_client`, `get_langfuse_client` 검증 |
| `dependencies/test_messaging.py` | `set_nats_client`, `get_nats_client` 및 함수형 dependency 정책 검증 |
| `dependencies/test_security.py` | `get_auth_provider`, `get_current_user`, `require_permissions` 검증 |
| `dependencies/*_integration.py` | 실제 서비스 연결 + state 캐시 동작 검증 |

### `routers/`

| 파일 | 설명 |
| --- | --- |
| `routers/test_health.py` | `/health/liveness`, `/health/readiness` 검증 |
| `routers/test_auth.py` | `/token`, `/user` mock 테스트 |
| `routers/test_auth_integration.py` | 실제 Keycloak 기반 auth 라우터 검증 |

---

## integration marker가 붙은 현재 테스트 파일

현재 `@pytest.mark.integration`가 사용되는 파일:

- `test_fastapi_core/core/test_async_milvus_integration.py`
- `test_fastapi_core/core/test_langfuse_integration.py`
- `test_fastapi_core/core/test_milvus_integration.py`
- `test_fastapi_core/core/test_security_integration.py`
- `test_fastapi_core/core/test_storage_integration.py`
- `test_fastapi_core/dependencies/test_async_milvus_integration.py`
- `test_fastapi_core/dependencies/test_database_integration.py`
- `test_fastapi_core/dependencies/test_milvus_integration.py`
- `test_fastapi_core/dependencies/test_security_integration.py`
- `test_fastapi_core/dependencies/test_storage_integration.py`
- `test_fastapi_core/routers/test_auth_integration.py`

NATS와 Ollama는 현재 저장소에 별도 integration test 파일이 없습니다.

---

## 권장 실행 순서

### 빠른 회귀 확인

```bash
uv run pytest -q -m "not integration"
```

### 특정 영역만 확인

```bash
uv run pytest -q test_fastapi_core/test_public_api.py
uv run pytest -q test_fastapi_core/test_lifecycle.py
uv run pytest -q test_fastapi_core/core/test_messaging.py test_fastapi_core/dependencies/test_messaging.py
```

### 외부 서비스 포함 검증

```bash
uv run pytest -q -m integration
```

---

## 문서와 맞춰 기억할 점

- 패키지 루트 export는 `test_public_api.py`가 강하게 제한합니다.
- dependency는 callable class가 아니라 함수형 API라는 점을 `test_class_dependencies.py`가 검증합니다.
- readiness / lifecycle / registry 동작은 루트 레벨 테스트들이 별도로 커버합니다.
