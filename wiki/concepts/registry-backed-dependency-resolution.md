---
title: Registry-backed dependency resolution
created: 2026-06-17
updated: 2026-06-18
type: concept
tags: [architecture, integration, sdk, fastapi, convention]
sources: [raw/articles/fastapi-core-prd-2026-06-16.md, raw/articles/fastapi-core-api-2026-06-17.md, raw/articles/fastapi-core-messaging-2026-06-18.md]
confidence: medium
---
# Registry-backed dependency resolution

## Definition
이 개념은 FastAPI dependency 계층이 auth, database, minio, milvus, ollama, langfuse, nats 같은 주요 서비스를 직접 생성하기보다 `docmesh_bridge` 와 registry를 통해 우선 해석하는 구조를 뜻한다. PRD는 이를 lifecycle / registry / state 관리의 핵심 제약으로 명시하며, async milvus만 예외적으로 직접 생성 경로를 유지한다고 적는다.

## Resolution path
핵심 아이디어는 공개 helper와 런타임 해석 경로를 분리하는 데 있다. `create_db_engine` 나 `create_minio_client` 같은 core helper는 standalone으로 유효하지만, 기본 FastAPI dependency 구현은 먼저 registry-backed helper 경로를 타고, 그 결과를 `app.state` 캐시에 보관한다. API 명세는 이 경로가 auth/database/minio/milvus/ollama/langfuse/nats 에 적용되고, `async_milvus_client` 는 예외적으로 `create_async_milvus_client(config.milvus)` 직접 경로를 유지한다고 적는다. 이 점은 [[fastapi-app-state-singletons]] 의 singleton 계약을 더 구현 친화적으로 구체화한 것이다.

메시징 가이드는 이 원칙을 더 선명하게 만든다. `fastapi_core.core.messaging.create_nats_client()` 라는 standalone helper 가 존재하더라도, 기본 FastAPI 경로의 `set_nats_client()` 와 `get_nats_client()` 는 이를 직접 호출하지 않고 docmesh registry에서 `nats_client` 를 해석해 `app.state` 에 저장한다. 즉 같은 서비스 도메인 안에서도 helper 계층과 dependency 계층이 분리되며, [[nats-event-helper-layer]] 는 이 차이를 메시징 사례로 정리한다.

## Operational significance
이 구조는 startup eager-init, request-time fallback, shutdown 정리를 하나의 composition layer에서 다루게 해준다. 따라서 서비스별 외부 연동 정책을 흩어진 dependency 함수마다 중복 구현하지 않고, [[service-factory-registry]] 같은 중앙 조립 지점과 더 잘 정렬된다. 다만 registry가 실제로 어떤 서비스를 소유하는지는 문서와 구현이 함께 진화해야 하므로 [[fastapi-core-prd-vs-source-code-comparison]] 같은 비교 문서가 계속 중요하다.

## Related Topics
- [[fastapi-core]] 는 이 registry-backed 운영 모델을 채택하는 제품 엔티티다.
- [[fastapi-app-state-singletons]] 은 registry 결과가 `app.state` 에 어떻게 캐시되는지 설명한다.
- [[function-style-fastapi-dependencies]] 는 이 해석 경로를 가리는 공식 함수형 dependency 표면을 설명한다.
- [[service-factory-registry]] 는 이 패턴의 상위 조립/소유 모델을 설명한다.
- [[curated-public-api-surface]] 는 공개 helper와 실제 런타임 해석 경로가 왜 분리될 수 있는지 보여준다.
- [[nats-event-helper-layer]] 는 메시징 영역에서 helper 표면과 registry-backed dependency 표면의 차이를 설명한다.
- [[fastapi-core-prd-vs-source-code-comparison]] 은 현재 코드에서 이 경로가 어떻게 구현되는지 추적한다.
