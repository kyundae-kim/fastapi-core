# 제품 요구사항 정의서 (PRD)

## 개요

`fastapi-core`는 DocMesh 계열 FastAPI 서비스에서 공통으로 사용하는 Python SDK 패키지입니다.
현재 코드베이스는 다음 영역을 제공합니다.

- Keycloak 인증/인가
- PostgreSQL 엔진 및 세션
- MinIO 스토리지
- Milvus / Async Milvus
- Ollama
- Langfuse
- NATS 메시징
- FastAPI 앱 팩토리, lifecycle, 내장 health/auth 라우터

---

## 배경 및 목적

여러 서비스가 인증, 설정, readiness, 외부 서비스 클라이언트 초기화 로직을 반복 구현하지 않도록 공통 SDK로 분리합니다.

목표:

- **중복 제거**: 인증/스토리지/DB/메시징 초기화 코드 공통화
- **일관성 보장**: 설정 모델, readiness 정책, dependency 패턴 통일
- **빠른 서비스 개발**: 서비스는 비즈니스 로직에 집중하고 공통 인프라는 SDK 재사용
- **운영 단순화**: `create_app()` + managed lifespan 조합으로 기본 앱 조립 표준화

---

## 대상 사용자

| 사용자 | 설명 |
| --- | --- |
| 백엔드 개발자 | `fastapi-core`를 의존성으로 사용하는 FastAPI 서비스 개발자 |
| 플랫폼/인프라 엔지니어 | Keycloak, Postgres, MinIO, Milvus, Ollama, Langfuse, NATS 연결 정보 운영 담당 |

---

## 주요 기능 요구사항

### 1. 인증 / 인가

- `KeycloakAuthProvider` 제공
- Password grant 토큰 발급(`authenticate`)
- Refresh token 갱신(`refresh_access_token`)
- JWT RS256 검증(`decode_token`)
- 개발용 비검증 decode(`decode_token_insecure`)
- Introspection 지원(`introspect_token`)
- JWT payload → `UserInfo` 변환(`to_user`)
- FastAPI dependency:
  - `get_auth_provider`
  - `get_current_user`
  - `require_permissions(*roles)`

### 2. 설정 관리

- 환경 변수 레이어: `EnvConfig`
- YAML 레이어: `ServiceSettings`
- 중첩 환경 변수 지원 (`__` delimiter)
- 설정 파일 미존재 시 기본값 fallback
- lifecycle / health 정책을 설정으로 제어

### 3. 데이터베이스

- `DatabaseConfig` 기반 SQLAlchemy `Engine` 생성
- 연결 확인(`check_database_connection`)
- DB 버전 조회(`get_database_version`)
- 트랜잭션 컨텍스트(`run_in_transaction`)
- FastAPI dependency:
  - `set_db_engine`
  - `get_db_engine`
  - `get_db_session`

### 4. MinIO

- `create_minio_client`
- 연결 확인(`check_minio_connection`)
- 버킷 존재 보장(`ensure_bucket_exists`)
- 버킷 이름 조회(`list_bucket_names`)
- presigned GET/PUT URL 생성
- FastAPI dependency:
  - `set_minio_client`
  - `get_minio_client`

### 5. Milvus

- `create_milvus_client`
- `create_async_milvus_client`
- 연결 확인(sync/async)
- 컬렉션 목록 조회(sync/async)
- 컬렉션 존재 보장(sync/async)
- FastAPI dependency:
  - `set_milvus_client`
  - `get_milvus_client`
  - `set_async_milvus_client`
  - `get_async_milvus_client`

### 6. Ollama

- `create_ollama_client`
- 연결 확인(`check_ollama_connection`)
- 모델 목록 조회(`list_model_names`)
- 텍스트 생성(`generate_text`)
- FastAPI dependency:
  - `set_ollama_client`
  - `get_ollama_client`

### 7. Langfuse

- core helper: `get_langfuse_client(config | None)`
- public health endpoint readiness 확인(`check_langfuse_connection`)
- FastAPI dependency:
  - `set_langfuse_client`
  - `get_langfuse_client`
- shutdown 시 `flush()` 지원

### 8. NATS 메시징

- `create_nats_client`
- subject 검증/조합 (`validate_event_subject`, `build_event_subject`)
- JSON publish / subscribe helper
- queue group subscribe helper
- FastAPI dependency:
  - `set_nats_client`
  - `get_nats_client`

### 9. FastAPI 앱 조립

- `create_app()` 제공
- `CORSMiddleware` 자동 등록
- `AuthError` 핸들러 등록
- `/health/liveness`, `/health/readiness` 내장
- 선택적으로 `/token`, `/user` 라우터 포함
- 기본 lifespan은 `create_managed_lifespan(config, settings)` 사용

### 10. lifecycle / registry / state 관리

- 외부 서비스 객체는 `app.state`에 캐시
- auth/db/minio/milvus/ollama/langfuse/nats는 registry-backed helper 경로를 사용
- async milvus는 직접 생성 경로 유지
- startup에서 lifecycle 정책에 따라 eager-init
- shutdown에서 `close` / `dispose` / `drain` / `flush` 정리 수행

---

## 현재 구현상의 아키텍처 제약

### 1. 공개 루트 API는 curated subset만 export

패키지 루트 `fastapi_core`의 `__all__`은 다음 심볼만 재수출합니다.

- `AuthError`
- `DatabaseConfig`
- `EnvConfig`
- `HealthResponse`
- `KeycloakAuthProvider`
- `KeycloakConfig`
- `LangfuseConfig`
- `LifecycleSettings`
- `MilvusConfig`
- `MinIOConfig`
- `OllamaConfig`
- `ServiceSettings`
- `TokenResponse`
- `UserInfo`
- `check_langfuse_connection`
- `create_async_milvus_client`
- `create_milvus_client`
- `create_app`
- `get_langfuse_client`

즉, `run_in_transaction`, `check_milvus_connection`, `generate_text` 같은 helper는 **모듈 경로로는 사용 가능하지만 패키지 루트에서는 재수출되지 않습니다.**

### 2. 함수형 dependency 정책

FastAPI dependency는 모두 함수형으로 유지합니다.

- `get_config`, `get_settings`
- `get_auth_provider`, `get_current_user`
- `get_db_engine`, `get_db_session`
- `get_minio_client`
- `get_milvus_client`, `get_async_milvus_client`
- `get_ollama_client`
- `get_langfuse_client`
- `get_nats_client`

`Get*Dependency` callable class나 `get_* = Get*Dependency()` alias는 공개 API가 아닙니다.

### 3. registry-backed dependency 경로

현재 FastAPI dependency 계층에서 다음 서비스는 `docmesh_bridge`를 통해 registry에서 해석됩니다.

- `auth_provider`
- `db_engine`
- `minio_client`
- `milvus_client`
- `ollama_client`
- `langfuse_client`
- `nats_client`

따라서 core 레이어의 `create_db_engine`, `create_minio_client`, `create_milvus_client`, `create_ollama_client`, `create_nats_client`는 **standalone helper**로는 유효하지만, 기본 FastAPI dependency 구현이 직접 호출하는 경로와는 다를 수 있습니다.

---

## 패키지 구조

```text
fastapi_core/
├── __init__.py
├── bootstrap.py
├── docmesh_bridge.py
├── lifecycle.py
├── factory.py
├── core/
│   ├── auth.py
│   ├── config.py
│   ├── database.py
│   ├── exceptions.py
│   ├── langfuse.py
│   ├── logging.py
│   ├── messaging.py
│   ├── milvus.py
│   ├── ollama.py
│   └── storage.py
├── dependencies/
│   ├── async_milvus.py
│   ├── auth.py
│   ├── config.py
│   ├── database.py
│   ├── langfuse.py
│   ├── messaging.py
│   ├── milvus.py
│   ├── ollama.py
│   └── storage.py
├── routers/
│   ├── auth.py
│   └── health.py
└── schemas/
    ├── health.py
    ├── token.py
    └── user.py
```

---

## 품질 및 테스트 요구사항

- 테스트 러너: `pytest`
- 비동기 테스트: `pytest-asyncio` / anyio 사용
- 단위 테스트와 통합 테스트를 marker로 분리
- public API export 집합에 대한 회귀 테스트 유지
- lifecycle / docmesh bridge / factory 동작에 대한 회귀 테스트 유지

실행 예:

```bash
# 단위 테스트만
uv run pytest -q -m "not integration"

# 통합 테스트만
uv run pytest -q -m integration

# 전체
uv run pytest -q
```

---

## 기술 스택

| 항목 | 내용 |
| --- | --- |
| 런타임 | Python >= 3.11 |
| 웹 프레임워크 | FastAPI |
| 설정 | pydantic, pydantic-settings, YAML |
| 인증 | Keycloak, PyJWT |
| DB | SQLAlchemy, psycopg |
| 스토리지 | MinIO |
| 벡터 DB | Milvus / AsyncMilvusClient |
| 로컬 LLM | Ollama |
| 관측 | Langfuse |
| 메시징 | NATS |
| 테스트 | pytest, pytest-asyncio, anyio |
| 린터 | Ruff |
