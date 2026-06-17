---
title: Curated public API surface
created: 2026-06-17
updated: 2026-06-17
type: concept
tags: [api, sdk, architecture, convention, fastapi]
sources: [raw/articles/fastapi-core-prd-2026-06-16.md, raw/articles/fastapi-core-api-2026-06-17.md]
confidence: medium
---
# Curated public API surface

## Definition
이 개념은 `fastapi_core` 패키지 루트가 모든 helper를 무차별 재수출하지 않고, 제품 수준에서 약속하려는 일부 심볼만 curated subset으로 노출한다는 계약을 설명한다. PRD는 `__all__` 에 남길 타입과 helper를 명시하고, 나머지 helper는 모듈 경로로만 접근하도록 구분한다.

## Why it exists
이 구분은 문서화된 공개 표면과 내부 구현 유연성을 분리하기 위해 중요하다. 예를 들어 `create_app`, `EnvConfig`, `ServiceSettings`, `KeycloakAuthProvider` 같은 핵심 엔트리포인트는 패키지 루트에서 바로 import 하게 두되, `generate_text`, `run_in_transaction`, presigned URL helper, Milvus/Ollama convenience helper 일부는 각 모듈의 책임 안에 남겨 둔다.

## Architectural implication
이 정책 덕분에 `fastapi-core` 는 제품 계약을 좁고 안정적으로 유지할 수 있다. 반대로 서비스 개발자는 "루트에서 보이지 않는 helper는 내부/세부 경로일 수 있다" 는 점을 이해해야 한다. 또한 API 문서는 루트 재수출 집합을 구체적으로 열거하므로, 테스트나 문서가 이 목록을 기준으로 회귀 검증할 수 있다. 이 관점은 [[fastapi-core]] 의 제품 정의와 연결되고, dependency 및 lifecycle 경로가 더 세분화된 [[registry-backed-dependency-resolution]] 과도 맞물린다.

## Related Topics
- [[fastapi-core]] 는 이 curated 공개 표면을 외부 소비자에게 제공하는 제품 엔티티다.
- [[fastapi-app-factory-and-health-routes]] 는 루트에서 직접 노출되는 대표 엔트리포인트 `create_app()` 의 책임을 설명한다.
- [[function-style-fastapi-dependencies]] 는 루트 재수출과 별개로 dependency 공개 표면이 어떻게 유지되는지 설명한다.
- [[registry-backed-dependency-resolution]] 은 공개 helper와 실제 런타임 해석 경로가 달라질 수 있는 이유를 설명한다.
- [[fastapi-core-prd-vs-source-code-comparison]] 은 현재 코드가 이 공개 표면 계약을 얼마나 충실히 따르는지 비교한다.