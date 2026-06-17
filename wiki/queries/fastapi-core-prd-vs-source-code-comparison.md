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
현재 소스코드는 PRD의 큰 방향성은 상당 부분 구현했고, 서비스별 기능 표면도 이전보다 많이 따라잡았다. 특히 설정 분리, `create_app()`, health routes, `app.state` 기반 dependency 재사용, Keycloak 기본 인증 흐름, PostgreSQL/MinIO/Milvus/Ollama/Langfuse/NATS의 기본 연결 구조는 구현돼 있다. 또한 PostgreSQL/MinIO/Milvus/Ollama/NATS convenience helper 는 이제 최소 형태로 갖춰졌다. 반면 PRD가 명시한 일부 아키텍처 규칙과 Keycloak introspection 같은 영역은 아직 비어 있거나 다른 방식으로 구현돼 있다.

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
현재 코드 상태는 `uv run pytest -q -m 'not integration'` 기준 `171 passed, 26 deselected` 로 통과했다. 즉 아래 비교는 단순 추정이 아니라 실제 테스트 가능한 현재 구현 기준이다.

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
### 1. Langfuse architecture differs from PRD
PRD는 Langfuse를 `app.state` 가 아니라 SDK 싱글톤 `get_langfuse_client` 로 다루고, `dependencies/langfuse.py` 는 만들지 않는다고 적는다. 그러나 현재 코드는 `dependencies/langfuse.py` 를 가지고 있고, lifecycle/shutdown 에서 `app.state.langfuse_client` 와 `flush()` 를 다룬다. 즉 연결 확인 API는 맞지만 객체 수명주기 모델은 PRD와 다르다.

### 2. Registry-backed implementation is stronger than the PRD text
현재 구현은 docmesh registry 와 bridge 를 통해 auth/database/minio/milvus/ollama/langfuse/nats 를 startup 및 fallback 경로에서 재사용하려는 방향이 강하다. 이는 [[registry-full-replacement-plan]] 과는 정렬되지만, PRD 자체에는 이런 registry 우선 구조가 명시적으로 드러나지 않는다. 즉 구현은 PRD보다 더 구체적이고 더 registry 중심적이다.

### 3. `allow_insecure_jwt_decode` 는 이제 PRD와 정렬됨
이전 비교 메모와 달리 현재 구현의 `get_current_user()` 는 `settings.auth.verify_jwt` 가 꺼져 있고 `settings.auth.allow_insecure_jwt_decode` 가 켜져 있으면 `provider.decode_token_insecure()` 로 분기한다. 따라서 개발환경용 서명 검증 생략 모드는 이제 실제 런타임 경로에 연결되어 있다.

## Missing or clearly under-implemented versus PRD
### 1. Introspection option is declared but unused
PRD는 Keycloak 토큰 introspection 의 선택적 지원을 요구한다. 현재 `ServiceSettings.auth.use_introspection` 필드는 존재하지만, 실제 인증 경로에서 introspection 호출은 확인되지 않았다.

### 2. PRD package structure and current source tree are not identical
PRD가 예시한 `core/messaging.py` 같은 모듈은 이제 구현되었지만, 다른 한편 현재 소스 트리에는 `lifecycle.py`, `docmesh_bridge.py`, `bootstrap.py`, `dependencies/langfuse.py` 같은 registry/lifecycle 중심 파일이 추가로 존재한다. 즉 문서화된 구조와 실제 구조 사이에는 여전히 진화 차이가 있다.

## Recommended interpretation
이 PRD는 "제품이 장기적으로 제공해야 하는 표면" 을 설명하고, 현재 소스는 그중 공통 wiring 과 lifecycle 기반을 먼저 구현한 뒤 서비스별 helper 표면을 점진적으로 채워온 상태로 보는 것이 가장 정확하다. 다시 말해 `fastapi-core` 는 부트스트랩/상태관리/기본 health/readiness 와 PostgreSQL/MinIO/Milvus/Ollama/NATS convenience API 는 많이 구현됐고, 이제 남은 큰 갭은 introspection 같은 일부 확장 요구와 PRD/현재 아키텍처 간 불일치다.

## Prioritized implementation order
### P0 — Keycloak introspection runtime wiring
가장 먼저 채워야 할 남은 갭이다. 이미 `use_introspection` 설정 필드가 공개 모델에 존재하므로, 사용자는 이 옵션이 동작한다고 기대할 가능성이 높다. 지금은 설정만 있고 런타임 분기가 없어서 "문서상 지원" 과 "실제 지원" 이 어긋나 있다.

권장 범위:
1. `dependencies/auth.py` 의 `get_current_user()` 또는 provider 계층에 introspection 분기 추가
2. introspection 성공/실패/timeout/fallback 정책 명시
3. 기존 JWT decode 경로와의 우선순위 규칙 테스트 추가

### P1 — Langfuse lifecycle contract reconciliation
두 번째 우선순위다. 기능 공백보다는 아키텍처 불일치 문제라서, introspection보다는 긴급도가 낮다. 현재도 health check 와 client 조회는 가능하므로 즉시 제품 기능이 막히는 상황은 아니다. 다만 PRD/공개 API/실제 lifecycle 모델이 다르면 이후 유지보수 비용이 커진다.

선택지:
1. PRD를 현재 코드(state + dependency + lifecycle flush) 기준으로 갱신
2. 또는 구현을 PRD 기준(SDK singleton helper only)으로 단순화

### P2 — PRD package structure / docs refresh
마지막 우선순위다. 실제 구현이 더 진화해 있어 문서가 뒤처진 상태지만, 이 문제는 대체로 개발자 혼란 비용의 문제이지 즉각적인 런타임 기능 결손은 아니다. 따라서 기능 갭을 메운 뒤 문서를 현재 구조에 맞게 정리하는 것이 효율적이다.

## Highest-priority documentation or implementation gaps
1. `use_introspection` 의 실제 런타임 의미를 코드와 PRD 중 하나에 맞춰 정리
2. Langfuse를 PRD대로 SDK 싱글톤만 사용할지, 현재 코드처럼 state/dependency 를 유지할지 결정
3. PRD의 패키지 구조 예시와 실제 source tree 차이를 문서에 반영

## Related Topics
- [[fastapi-core]] 는 비교 대상이 되는 제품 엔티티다.
- [[fastapi-core-prd-alignment-review]] 는 제품 책임 범위 차원의 정렬 상태를 먼저 정리한다.
- [[fastapi-core-codebase-review-against-docmesh-py-core]] 는 코드 구조와 상위 SDK 철학 차이를 분석한다.
- [[fastapi-app-state-singletons]] 은 PRD와 소스가 가장 잘 맞는 영역 중 하나다.
- [[registry-full-replacement-plan]] 은 현재 구현이 왜 PRD보다 더 registry 중심으로 진화했는지 설명한다.
