---
title: Function-style FastAPI dependencies
created: 2026-06-17
updated: 2026-06-17
type: concept
tags: [fastapi, api, convention, sdk, architecture]
sources: [raw/articles/fastapi-core-api-2026-06-17.md]
confidence: medium
---
# Function-style FastAPI dependencies

## Definition
이 개념은 `fastapi-core` 가 FastAPI dependency 표면을 callable class 인스턴스가 아니라 함수형 getter/setter 집합으로 유지한다는 계약을 설명한다. `docs/api.md` 는 `get_config`, `get_settings`, `get_auth_provider`, `get_current_user`, `get_db_engine`, `get_db_session`, `get_minio_client`, `get_milvus_client`, `get_async_milvus_client`, `get_ollama_client`, `get_langfuse_client`, `get_nats_client` 같은 함수형 API를 공식 공개 표면으로 다룬다.

## Contract
이 정책 아래에서 `Get*Dependency` callable class나 `get_* = Get*Dependency()` 형태의 alias 는 공개 API가 아니다. 서비스 개발자는 `Depends(get_db_engine)` 처럼 함수 기반으로만 의존성을 연결하고, state 키나 내부 adapter 타입을 직접 알 필요가 없다.

## Why it matters
함수형 dependency 표면은 문서화된 사용법을 단순하게 유지하고, 내부에서 registry-backed 해석, state 캐시, fallback 생성 정책이 바뀌더라도 외부 호출 문법을 안정적으로 유지하게 해준다. 따라서 이 개념은 [[curated-public-api-surface]] 와 외부 계약 측면에서 맞물리고, 실제 자원 해석 경로 측면에서는 [[registry-backed-dependency-resolution]] 및 [[fastapi-app-state-singletons]] 와 연결된다.

## Related Topics
- [[curated-public-api-surface]] 는 루트 재수출과 모듈 경로 공개 표면의 경계를 설명한다.
- [[registry-backed-dependency-resolution]] 은 함수형 dependency 뒤에서 실제 서비스가 어떻게 해석되는지 설명한다.
- [[fastapi-app-state-singletons]] 은 dependency getter/setter가 어떤 state 키를 재사용하는지 설명한다.
- [[fastapi-app-factory-and-health-routes]] 는 이 dependency 함수들이 앱 조립과 readiness 에서 어떻게 사용되는지 보여준다.
- [[fastapi-core]] 는 이 정책을 채택하는 제품 엔티티다.
