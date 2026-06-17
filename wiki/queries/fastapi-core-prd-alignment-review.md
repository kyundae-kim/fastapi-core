---
title: fastapi-core PRD alignment review
created: 2026-06-16
updated: 2026-06-17
type: query
tags: [query, architecture, decision, sdk, risk]
sources: [raw/articles/fastapi-core-prd-2026-06-16.md, queries/fastapi-core-codebase-review-against-docmesh-py-core.md, queries/registry-full-replacement-plan.md]
confidence: medium
---
# fastapi-core PRD alignment review

## Summary
2026-06-17 기준 `docs/prd.md` 는 초기 제품 비전 문서라기보다 현재 `fastapi-core` 구현이 채택한 운영 모델을 상당 부분 반영한 기준 문서에 가까워졌다. 인증/저장소/벡터 DB/LLM/관측성/메시징 helper 범위뿐 아니라 managed lifespan, curated public API, registry-backed dependency 경로, 현재 패키지 구조까지 명시한다.

## Alignment Points
PRD가 강조하는 공통화 축은 설정 분리, `create_app()` 중심 조립, `app.state` singleton 재사용, lifecycle 정책, readiness 표준화다. 이는 [[layered-configuration-model]], [[fastapi-app-factory-and-health-routes]], [[fastapi-app-state-singletons]] 로 정리한 구조와 일관되며, 최근 비교 메모에서 좁혀진 문서/코드 차이도 잘 반영한다.

또한 새 PRD는 공개 루트 API가 curated subset 만 export 한다는 점과 주요 dependency 가 registry-backed 경로를 따른다는 점을 문서 수준으로 끌어올렸다. 그래서 예전처럼 "문서가 단순 helper 중심이고 코드는 registry/lifecycle 중심" 이라고 보기보다는, 이제 문서도 [[curated-public-api-surface]] 와 [[registry-backed-dependency-resolution]] 수준의 구조를 공식 계약 일부로 받아들이기 시작했다고 보는 편이 정확하다.

## Remaining Tensions
남은 긴장은 기능 미구현보다는 설명 수준의 선택에 가깝다. startup eager-init 과 request-time fallback 을 동시에 허용하는 구조는 여전히 운영 상 trade-off 를 만든다. 또한 async milvus 는 registry 완전 위임 범위 밖에 남아 있으므로, 모든 서비스가 동일한 소유 모델을 따르는 것은 아니다.

## Recommended Use
이 PRD는 앞으로 `fastapi-core` 관련 위키 문서의 기준 출처로 계속 사용하기 적합하다. 다만 운영 디테일이 변할 때는 [[fastapi-core-prd-vs-source-code-comparison]] 과 함께 다시 읽어, registry/lifecycle 실제 구현이 문서보다 더 앞서가거나 뒤처지지 않았는지 주기적으로 확인해야 한다.

## Related Topics
- [[fastapi-core]] 는 PRD가 설명하는 제품 엔티티다.
- [[fastapi-app-state-singletons]] 은 PRD의 lifecycle/state 규칙을 구조화한다.
- [[layered-configuration-model]] 은 설정 분리 요구를 정리한다.
- [[fastapi-app-factory-and-health-routes]] 는 앱 조립 및 readiness 요구를 정리한다.
- [[curated-public-api-surface]] 는 루트 공개 표면의 경계를 설명한다.
- [[registry-backed-dependency-resolution]] 은 PRD가 반영하기 시작한 현재 구현의 운영 해석 경로를 설명한다.
- [[registry-full-replacement-plan]] 은 PRD 목표를 구현적으로 어디까지 registry에 위임할지 판단한 문서다.
