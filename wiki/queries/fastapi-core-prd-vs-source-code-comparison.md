---
title: fastapi-core PRD vs source code comparison
created: 2026-06-16
updated: 2026-06-17
type: query
tags: [query, architecture, decision, sdk, risk]
sources: [raw/articles/fastapi-core-prd-2026-06-16.md, queries/fastapi-core-prd-alignment-review.md, queries/fastapi-core-codebase-review-against-docmesh-py-core.md]
confidence: medium
---
# fastapi-core PRD vs source code comparison

## Verdict
현재 소스코드는 PRD의 큰 방향성은 상당 부분 구현했지만, 서비스별 기능 표면은 PRD보다 좁다. 특히 설정 분리, `create_app()`, health routes, `app.state` 기반 dependency 재사용, Keycloak 기본 인증 흐름, PostgreSQL/MinIO/Milvus/Langfuse/NATS의 기본 연결 구조는 구현돼 있다. 반면 PRD가 명시한 여러 convenience helper 와 일부 아키텍처 규칙은 아직 빠져 있거나 다른 방식으로 구현돼 있다.

## Implemented and aligned well
### 1. App assembly and configuration layering
소스코드는 `create_app(config, settings, lifespan, include_auth_router)` 를 제공하고, 기본적으로 `EnvConfig()` 와 `ServiceSettings.from_yaml()` 를 사용해 앱을 조립한다. 이는 [[layered-configuration-model]] 및 [[fastapi-app-factory-and-health-routes]] 에 정리한 PRD 구조와 잘 맞는다.

`EnvConfig` 는 `env_nested_delimiter="__"`, `.env` 파일, `dev/stage/prod` 환경 enum, Keycloak/DB/MinIO/Milvus/Ollama/Langfuse/NATS 설정 모델을 포함한다. 따라서 설정 계층화 자체는 PRD 요구와 대체로 정렬된다.

### 2. FastAPI state-based singleton dependencies
`set_auth_provider`, `set_db_engine`, `set_minio_client`, `set_milvus_client`, `set_async_milvus_client`, `set_ollama_client`, `set_nats_client` 와 대응되는 getter 가 존재하며, 대부분 `app.state` 캐시 + fallback 생성 패턴을 따른다. 이 구조는 [[fastapi-app-state-singletons]] 과 일치한다.

또한 lifecycle 계층은 startup/shutdown 관리와 docmesh registry 연계를 제공한다. 이는 PRD의 "앱 시작 시 한 번 생성" 원칙을 향한 구현으로 볼 수 있다.

### 3. Core auth and health surface
Keycloak 쪽은 password grant 기반 토큰 발급, JWT RS256 검증, `sub`/`preferred_username`/`email`/`name` 추출, realm role 과 scope 파싱, `get_current_user`, `require_permissions`, `/token`, `/user` 라우터가 구현돼 있다. readiness 는 Keycloak, PostgreSQL, MinIO, Langfuse(옵션) 체크를 제공한다. 이 범위는 PRD의 인증/health 최소 요구와 잘 맞는다.

### 4. Verified test baseline
현재 코드 상태는 `uv run pytest -q -m 'not integration'` 기준 `165 passed, 26 deselected` 로 통과했다. 즉 아래 비교는 단순 추정이 아니라 실제 테스트 가능한 현재 구현 기준이다.

### 5. PostgreSQL helper surface now mostly aligns
`fastapi_core.core.database` 는 이제 `create_db_engine`, `check_database_connection(SELECT 1)`, `get_database_version(SELECT version())`, `run_in_transaction(...)` 를 제공한다. 따라서 PRD가 요구한 DB 버전 조회와 트랜잭션 helper 는 최소 형태로 구현되었다.

### 6. MinIO helper surface now mostly aligns
`fastapi_core.core.storage` 는 이제 `create_minio_client`, `check_minio_connection`, `ensure_bucket_exists`, `list_bucket_names`, `generate_presigned_get_url`, `generate_presigned_put_url` 를 제공한다. 따라서 PRD가 요구한 버킷 자동 생성, 버킷 목록 조회, presigned URL helper 도 최소 형태로 구현되었다.

### 7. Milvus helper surface now mostly aligns
`fastapi_core.core.milvus` 는 이제 sync/async 클라이언트 생성 외에도 `check_milvus_connection`, `check_async_milvus_connection`, `list_collection_names`, `list_async_collection_names`, `ensure_collection_exists`, `ensure_async_collection_exists` 를 제공한다. 따라서 PRD가 요구한 컬렉션 목록 조회, 연결 확인, 컬렉션 존재 보장 helper 도 최소 형태로 구현되었다.

## Partially implemented or diverged
### 1. Langfuse architecture differs from PRD
PRD는 Langfuse를 `app.state` 가 아니라 SDK 싱글톤 `get_langfuse_client` 로 다루고, `dependencies/langfuse.py` 는 만들지 않는다고 적는다. 그러나 현재 코드는 `dependencies/langfuse.py` 를 가지고 있고, lifecycle/shutdown 에서 `app.state.langfuse_client` 와 `flush()` 를 다룬다. 즉 연결 확인 API는 맞지만 객체 수명주기 모델은 PRD와 다르다.

### 2. Registry-backed implementation is stronger than the PRD text
현재 구현은 docmesh registry 와 bridge 를 통해 auth/database/minio/milvus/ollama/langfuse/nats 를 startup 및 fallback 경로에서 재사용하려는 방향이 강하다. 이는 [[registry-full-replacement-plan]] 과는 정렬되지만, PRD 자체에는 이런 registry 우선 구조가 명시적으로 드러나지 않는다. 즉 구현은 PRD보다 더 구체적이고 더 registry 중심적이다.

### 3. `allow_insecure_jwt_decode` 는 이제 PRD와 정렬됨
이전 비교 메모와 달리 현재 구현의 `get_current_user()` 는 `settings.auth.verify_jwt` 가 꺼져 있고 `settings.auth.allow_insecure_jwt_decode` 가 켜져 있으면 `provider.decode_token_insecure()` 로 분기한다. 따라서 개발환경용 서명 검증 생략 모드는 이제 실제 런타임 경로에 연결되어 있다.

## Missing or clearly under-implemented versus PRD
### 1. Ollama module surface is incomplete relative to PRD
PRD는 `core/ollama.py` 에 클라이언트 생성, 모델 목록 조회, 연결 확인, 프롬프트 기반 텍스트 생성 helper 를 둔다. 현재 파일 목록에는 `dependencies/ollama.py` 는 존재하지만 `core/ollama.py` 자체가 없다. 즉 state wiring 은 있으나 PRD가 말한 핵심 helper 모듈 표면은 빠져 있다.

### 2. NATS messaging feature layer is missing
PRD는 비동기 연결/종료 외에 publish/subscribe, queue group 기반 소비, 도메인 이벤트 발행 규칙 표준화(`<domain>.<entity>.<action>`) 를 요구한다. 현재 확인된 구현은 config 모델, state getter/setter, lifecycle drain 중심이며 publish/subscribe helper 나 이벤트 규칙 강제 코드는 보이지 않는다.

### 3. Introspection option is declared but unused
PRD는 Keycloak 토큰 introspection 의 선택적 지원을 요구한다. 현재 `ServiceSettings.auth.use_introspection` 필드는 존재하지만, 실제 인증 경로에서 introspection 호출은 확인되지 않았다.

### 4. PRD package structure and current source tree are not identical
PRD가 예시한 `core/ollama.py`, `core/messaging.py` 같은 모듈은 현재 소스 트리에 없다. 반대로 현재 구현에는 `lifecycle.py`, `docmesh_bridge.py`, `bootstrap.py`, `dependencies/langfuse.py` 같은 PRD에 직접 나오지 않는 registry/lifecycle 중심 파일이 존재한다. 즉 문서화된 구조와 실제 구조 사이에 진화 차이가 있다.

## Recommended interpretation
이 PRD는 "제품이 장기적으로 제공해야 하는 표면" 을 설명하고, 현재 소스는 그중 공통 wiring 과 lifecycle 기반을 먼저 구현한 상태로 보는 것이 가장 정확하다. 다시 말해 `fastapi-core` 는 부트스트랩/상태관리/기본 health/readiness 는 많이 구현됐지만, 서비스별 convenience API 는 아직 PRD 수준까지 채워지지 않았다.

## Highest-priority documentation or implementation gaps
1. `use_introspection` 의 실제 런타임 의미를 코드와 PRD 중 하나에 맞춰 정리
2. Langfuse를 PRD대로 SDK 싱글톤만 사용할지, 현재 코드처럼 state/dependency 를 유지할지 결정
3. Ollama/NATS의 실제 공개 helper 표면을 문서대로 채우거나 PRD를 축소

## Related Topics
- [[fastapi-core]] 는 비교 대상이 되는 제품 엔티티다.
- [[fastapi-core-prd-alignment-review]] 는 제품 책임 범위 차원의 정렬 상태를 먼저 정리한다.
- [[fastapi-core-codebase-review-against-docmesh-py-core]] 는 코드 구조와 상위 SDK 철학 차이를 분석한다.
- [[fastapi-app-state-singletons]] 은 PRD와 소스가 가장 잘 맞는 영역 중 하나다.
- [[registry-full-replacement-plan]] 은 현재 구현이 왜 PRD보다 더 registry 중심으로 진화했는지 설명한다.
