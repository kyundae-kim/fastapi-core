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
현재 소스코드는 PRD의 큰 방향성과 공개 문서 기준에서 상당 부분 정렬됐다. 특히 설정 분리, `create_app()`, health routes, `app.state` 기반 dependency 재사용, Keycloak 기본 인증 흐름, PostgreSQL/MinIO/Milvus/Ollama/Langfuse/NATS의 기본 연결 구조는 구현돼 있다. 또한 PostgreSQL/MinIO/Milvus/Ollama/NATS convenience helper 와 Keycloak introspection runtime wiring 이 반영됐고, 2026-06-17 문서 동기화로 Langfuse 수명주기 및 패키지 구조 설명도 현재 구현 기준으로 갱신됐다. 현재 남은 이슈는 기능 공백보다는 registry/lifecycle 중심 구조를 얼마나 공식 아키텍처로 강조할지에 대한 설명 수준의 선택에 가깝다.

## Implemented and aligned well
### 1. App assembly and configuration layering
소스코드는 `create_app(config, settings, lifespan, include_auth_router)` 를 제공하고, 기본적으로 `EnvConfig()` 와 `ServiceSettings.from_yaml()` 를 사용해 앱을 조립한다. 이는 [[layered-configuration-model]] 및 [[fastapi-app-factory-and-health-routes]] 에 정리한 PRD 구조와 잘 맞는다.

`EnvConfig` 는 `env_nested_delimiter="__"`, `.env` 파일, `dev/stage/prod` 환경 enum, Keycloak/DB/MinIO/Milvus/Ollama/Langfuse/NATS 설정 모델을 포함한다. 따라서 설정 계층화 자체는 PRD 요구와 대체로 정렬된다.

### 2. FastAPI state-based singleton dependencies
`set_auth_provider`, `set_db_engine`, `set_minio_client`, `set_milvus_client`, `set_async_milvus_client`, `set_ollama_client`, `set_nats_client`, `set_langfuse_client` 와 대응되는 getter 가 존재하며, 대부분 `app.state` 캐시 + fallback 생성 패턴을 따른다. 이 구조는 [[fastapi-app-state-singletons]] 과 일치한다.

또한 lifecycle 계층은 startup/shutdown 관리와 docmesh registry 연계를 제공한다. 이는 PRD의 "앱 시작 시 한 번 생성" 원칙을 향한 구현으로 볼 수 있다.

### 3. Core auth and health surface
Keycloak 쪽은 password grant 기반 토큰 발급, JWT RS256 검증, `sub`/`preferred_username`/`email`/`name` 추출, realm role 과 scope 파싱, `get_current_user`, `require_permissions`, `/token`, `/user` 라우터가 구현돼 있다. readiness 는 Keycloak, PostgreSQL, MinIO, Langfuse(옵션) 체크를 제공한다. 이 범위는 PRD의 인증/health 최소 요구와 잘 맞는다.

### 4. Verified test baseline
현재 코드 상태는 `uv run pytest -q -m 'not integration'` 기준 `179 passed, 26 deselected` 로 통과했다. 또한 Langfuse/라이프사이클 비교에 직접 관련된 테스트인 `uv run pytest -q test_fastapi_core/core/test_langfuse.py test_fastapi_core/dependencies/test_langfuse.py test_fastapi_core/test_lifecycle.py` 도 `17 passed` 로 확인했다. 즉 아래 비교는 단순 추정이 아니라 실제 테스트 가능한 현재 구현 기준이다.

### 5. PostgreSQL helper surface now mostly aligns
`fastapi_core.core.database` 는 이제 `create_db_engine`, `check_database_connection(SELECT 1)`, `get_database_version(SELECT version())`, `run_in_transaction(...)` 를 제공한다. 따라서 PRD가 요구한 DB 버전 조회와 트랜잭션 helper 는 최소 형태로 구현되었다.

### 6. MinIO helper surface now mostly aligns
`fastapi_core.core.storage` 는 이제 `create_minio_client`, `check_minio_connection`, `ensure_bucket_exists`, `list_bucket_names`, `generate_presigned_get_url`, `generate_presigned_put_url` 를 제공한다. 따라서 PRD가 요구한 버킷 자동 생성, 버킷 목록 조회, presigned URL helper 도 최소 형태로 구현되었다.

### 7. Milvus helper surface now mostly aligns
`fastapi_core.core.milvus` 는 이제 sync/async 클라이언트 생성 외에도 `check_milvus_connection`, `check_async_milvus_connection`, `list_collection_names`, `list_async_collection_names`, `ensure_collection_exists`, `ensure_async_collection_exists` 를 제공한다. 따라서 PRD가 요구한 컬렉션 목록 조회, 연결 확인, 컬렉션 존재 보장 helper 도 최소 형태로 구현되었다.

### 8. Ollama helper surface now mostly aligns
`fastapi_core.core.ollama` 는 이제 `create_ollama_client`, `check_ollama_connection`, `list_model_names`, `generate_text` 를 제공한다. 따라서 PRD가 요구한 HTTP 클라이언트 생성, 모델 목록 조회, 연결 확인, 프롬프트 기반 텍스트 생성 helper 도 최소 형태로 구현되었다.

### 9. NATS helper surface now mostly aligns
`fastapi_core.core.messaging` 가 이제 `create_nats_client`, `build_event_subject`, `validate_event_subject`, `publish_event`, `subscribe_event`, `subscribe_queue_event` 를 제공한다. 따라서 PRD가 요구한 비동기 연결/종료를 위한 기반뿐 아니라 publish/subscribe helper, queue group 소비 패턴, `<domain>.<entity>.<action>` subject 규칙 표준화도 최소 형태로 구현되었다.

## Partially implemented or diverged
### 1. Registry-backed implementation is more explicit in code than in high-level product language
현재 구현은 docmesh registry 와 bridge 를 통해 auth/database/minio/milvus/ollama/langfuse/nats 를 startup 및 fallback 경로에서 재사용하려는 방향이 강하다. PRD와 API 문서는 2026-06-17 기준으로 이 구조를 반영하도록 갱신됐지만, 여전히 실제 코드는 문서보다 더 구체적인 운영 디테일(예: registry 우선 fallback, shutdown flush/close 순서)을 담고 있다. 즉 남은 차이는 계약 충돌이라기보다 설명 밀도의 차이다.

### 2. `allow_insecure_jwt_decode` 는 이제 PRD와 정렬됨
이전 비교 메모와 달리 현재 구현의 `get_current_user()` 는 `settings.auth.verify_jwt` 가 꺼져 있고 `settings.auth.allow_insecure_jwt_decode` 가 켜져 있으면 `provider.decode_token_insecure()` 로 분기한다. 따라서 개발환경용 서명 검증 생략 모드는 이제 실제 런타임 경로에 연결되어 있다.

## Missing or clearly under-implemented versus PRD
현재 재검토 기준으로 이전의 핵심 미구현 항목이던 Keycloak introspection runtime wiring 은 해소됐고, Langfuse 계약/패키지 구조에 대한 문서 차이도 2026-06-17 문서 동기화로 크게 줄었다. 남아 있는 차이는 기능 결손보다는 문서가 코드의 운영 디테일을 어디까지 공식 계약으로 끌어올릴지에 대한 표현 수준 문제에 가깝다.

### 1. PRD package structure and current source tree are now documented more faithfully
`docs/prd.md` 는 이제 `bootstrap.py`, `docmesh_bridge.py`, `lifecycle.py`, `dependencies/langfuse.py`, `core/database.py` 까지 포함해 현재 소스 트리의 핵심 조립 계층을 설명한다. 따라서 이전의 큰 문서 차이는 상당 부분 해소됐다.

남아 있는 차이는 파일 존재 여부가 아니라, registry 기반 fallback 과 shutdown 정리 같은 운영 디테일을 PRD 수준에서 얼마나 자세히 설명할지에 가깝다.

## Recommended interpretation
이 PRD는 "제품이 장기적으로 제공해야 하는 표면" 을 설명하고, 현재 소스는 그중 공통 wiring 과 lifecycle 기반을 먼저 구현한 뒤 서비스별 helper 표면을 점진적으로 채워온 상태로 보는 것이 가장 정확하다. 이제는 Keycloak introspection 까지 런타임 경로에 연결됐고, `fastapi-core` 는 부트스트랩/상태관리/기본 health/readiness 와 PostgreSQL/MinIO/Milvus/Ollama/NATS convenience API 를 대부분 갖췄다. 2026-06-17 문서 동기화 이후 PRD/API 문서도 이 구조를 상당 부분 반영하므로, 남은 과제는 계약 충돌 해소보다는 설명 깊이와 유지보수 일관성 확보에 가깝다.

## Prioritized implementation order
### P0 — Keep docs and implementation synchronized around registry/lifecycle details
즉시 구현 공백은 크지 않다. 이제 중요한 것은 PRD/API 문서가 registry 기반 fallback, state 캐시, shutdown 정리 같은 운영 계약을 계속 따라가도록 유지하는 것이다. 새 기능이나 lifecycle 정책이 바뀔 때마다 PRD, API 문서, 비교 메모를 함께 갱신해야 한다.

### P1 — Decide how strongly to elevate registry/lifecycle to product-level architecture
현재 코드와 문서는 정렬됐지만, registry/lifecycle 계층을 단순 구현 세부로 둘지 아니면 제품 아키텍처의 핵심 축으로 승격할지는 여전히 선택 사항이다. 이 결정은 이후 README, 설계 문서, 외부 서비스 통합 예제의 서술 깊이에 영향을 준다.

## Highest-priority documentation or implementation gaps
1. registry 기반 fallback, state 캐시, shutdown flush/close 순서처럼 운영 디테일이 변경될 때 PRD/API/wiki 비교 문서가 함께 갱신되는지 지속 확인
2. registry/lifecycle 계층을 README 및 상위 설계 문서에서 어느 정도까지 전면에 드러낼지 결정

## Related Topics
- [[fastapi-core]] 는 비교 대상이 되는 제품 엔티티다.
- [[fastapi-core-prd-alignment-review]] 는 제품 책임 범위 차원의 정렬 상태를 먼저 정리한다.
- [[fastapi-core-codebase-review-against-docmesh-py-core]] 는 코드 구조와 상위 SDK 철학 차이를 분석한다.
- [[fastapi-app-state-singletons]] 은 PRD와 소스가 가장 잘 맞는 영역 중 하나다.
- [[registry-full-replacement-plan]] 은 현재 구현이 왜 PRD보다 더 registry 중심으로 진화했는지 설명한다.
