---
title: fastapi-core PRD alignment review
created: 2026-06-16
updated: 2026-06-16
type: query
tags: [query, architecture, decision, sdk, risk]
sources: [raw/articles/fastapi-core-prd-2026-06-16.md, queries/fastapi-core-codebase-review-against-docmesh-py-core.md, queries/registry-full-replacement-plan.md]
confidence: medium
---
# fastapi-core PRD alignment review

## Summary
`docs/prd.md` 는 `fastapi-core` 를 DocMesh 계열 FastAPI 서비스용 공통 SDK로 정의하고, 인증/저장소/LLM/관측성/메시징 연동과 앱 조립 패턴을 제품 요구사항으로 명시한다. 기존 코드 리뷰 문서들과 함께 보면, 현재 코드베이스는 이 PRD의 상당 부분을 이미 향해 이동했지만 아직 완전히 수렴한 상태는 아니다.

## Alignment Points
PRD가 강조하는 공통화 축은 설정 분리, `app.state` singleton 관리, `create_app()` 중심 조립, health route 표준화다. 이는 [[fastapi-app-state-singletons]], [[layered-configuration-model]], [[fastapi-app-factory-and-health-routes]] 로 정리한 구조와 일관되며, 기존 [[fastapi-core-codebase-review-against-docmesh-py-core]] 에서 지적했던 startup/lifecycle 일원화 요구와도 맞물린다.

또한 registry 관련 최근 계획은 PRD의 목표를 더 얇은 composition layer 쪽으로 밀어준다. 즉 제품 요구사항은 다양한 외부 연동을 fastapi-core가 제공한다고 말하지만, 구현 수준에서는 그 책임을 전부 직접 구현하기보다 [[service-factory-registry]] 를 재사용하는 편이 더 유지보수에 유리하다.

## Gaps and Tensions
PRD는 `app.state` fallback 생성 정책을 허용하면서도, 동시에 애플리케이션 시작 시 단 한 번 생성하는 singleton 패턴을 핵심 원칙으로 적는다. 이 둘은 공존 가능하지만 운영적으로는 startup 실패 조기 노출과 request-time lazy init 사이의 긴장을 만든다. 이 부분은 기존 리뷰 문서가 이미 위험지점으로 식별한 영역이다.

또 하나의 긴장은 Milvus 비동기 경로다. PRD는 sync/async 둘 다 state singleton으로 다루라고 요구하지만, [[registry-full-replacement-plan]] 기준 현재 registry가 완전 대체 가능한 범위에는 `async_milvus` 가 포함되지 않는다. 따라서 제품 문서와 현재 통합 추상화의 범위를 명시적으로 연결해 둘 필요가 있다.

## Recommended Use
이 PRD는 앞으로 위키 내 `fastapi-core` 관련 문서들의 기준 출처로 삼기에 적합하다. 특히 제품 책임 범위, 공개 API 기대치, 서비스별 통합 범위를 설명하는 기준선으로 쓰고, 실제 구현 세부사항과 차이가 나는 지점은 [[fastapi-core-codebase-review-against-docmesh-py-core]] 와 함께 읽는 것이 좋다.

## Related Topics
- [[fastapi-core]] 는 PRD가 설명하는 제품 엔티티다.
- [[fastapi-app-state-singletons]] 은 PRD의 lifecycle/state 규칙을 구조화한다.
- [[layered-configuration-model]] 은 설정 분리 요구를 정리한다.
- [[fastapi-app-factory-and-health-routes]] 는 앱 조립 및 readiness 요구를 정리한다.
- [[registry-full-replacement-plan]] 은 PRD 목표를 구현적으로 어디까지 registry에 위임할지 판단한 문서다.
