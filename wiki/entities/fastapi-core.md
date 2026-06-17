---
title: fastapi-core
created: 2026-06-16
updated: 2026-06-17
type: entity
tags: [sdk, fastapi, architecture, integration, config]
sources: [raw/articles/fastapi-core-prd-2026-06-16.md, raw/articles/fastapi-core-api-2026-06-17.md, raw/articles/fastapi-core-config-2026-06-17.md]
confidence: medium
---
# fastapi-core

## Overview
`fastapi-core` 는 DocMesh 계열 FastAPI 서비스에서 공통으로 사용하는 Python SDK 패키지다. 2026-06-17 기준 PRD는 이 패키지를 인증, 데이터베이스, 스토리지, 벡터 DB, 로컬 LLM, 관측성, 메시징, 그리고 FastAPI 앱 조립을 함께 표준화하는 공통 인프라 레이어로 정의한다.

이 제품의 목표는 단순 helper 모음이 아니라 반복되는 부트스트랩/설정/readiness 로직을 SDK로 모아 서비스 개발자가 비즈니스 로직에 집중하게 만드는 데 있다. 특히 `create_app()` + managed lifespan, registry-backed dependency 경로, `app.state` 캐시, curated public API surface 가 현재 제품 설명의 중요한 축으로 드러난다.

API 명세 문서는 여기에 한 가지 경계를 더 분명히 추가한다. 패키지 루트는 curated subset 만 재수출하고, 실제 사용되는 FastAPI dependency 표면은 함수형 getter/setter 집합으로 유지된다. 즉 제품은 "무엇을 제공하는가" 뿐 아니라 "어떤 import 경로와 dependency 스타일을 공식 계약으로 삼는가" 도 함께 정의한다.

설정 가이드는 제품의 또 다른 축을 보강한다. `EnvConfig` 와 `ServiceSettings` 의 이중 레이어, `.env` + YAML 조합, 그리고 readiness 와 eager-init 사이를 잇는 lifecycle policy 계산 규칙이 문서화되면서, 이 SDK는 단순 연결 helper 집합이 아니라 설정-부트스트랩-운영 정책을 함께 제공하는 프레임워크성 패키지라는 점이 더 분명해졌다.

## Responsibilities
- Keycloak 기반 토큰 발급, JWT 검증, introspection, 권한 검사 지원
- PostgreSQL, MinIO, Milvus/Async Milvus, Ollama, Langfuse, NATS 연결과 health/helper 표면 제공
- `EnvConfig` 와 `ServiceSettings` 를 분리한 설정 모델 제공
- `create_app()` 기반 FastAPI 앱 조립, health/auth 라우터, managed lifespan 표준화
- registry-backed dependency 해석과 shutdown 정리 규칙(`close` / `dispose` / `drain` / `flush`) 문서화
- 패키지 루트에서는 일부 심볼만 재수출하는 curated 공개 표면 유지

## Architectural Notes
PRD는 외부 서비스 객체를 요청마다 새로 만들기보다 startup/lifecycle 과정과 dependency fallback 을 조합해 재사용하는 방향을 분명히 한다. 이 운영 모델은 [[fastapi-app-state-singletons]] 과 [[registry-backed-dependency-resolution]] 에서 더 구체적으로 설명된다.

또한 설정은 [[layered-configuration-model]] 처럼 접속 정보와 서비스 동작 정책을 분리하고, 앱 엔트리포인트는 [[fastapi-app-factory-and-health-routes]] 에 정리된 `create_app()`/health route 조립 흐름으로 노출된다. 한편 외부 소비자에게는 [[curated-public-api-surface]] 가 설명하듯 제한된 루트 API만 직접 재수출한다.

## Related Topics
- [[layered-configuration-model]] 은 `EnvConfig` 와 `ServiceSettings` 의 역할 분리를 다룬다.
- [[fastapi-app-state-singletons]] 은 서비스 객체의 state 저장/재사용 규칙을 다룬다.
- [[fastapi-app-factory-and-health-routes]] 는 FastAPI 조립과 readiness 범위를 정리한다.
- [[curated-public-api-surface]] 는 패키지 루트 공개 표면의 경계와 의도를 설명한다.
- [[function-style-fastapi-dependencies]] 는 공식 dependency 표면이 함수형 API로 유지되는 이유를 설명한다.
- [[lifecycle-policy-resolution]] 은 health 설정과 eager-init 설정이 startup 정책으로 결합되는 방식을 설명한다.
- [[registry-backed-dependency-resolution]] 은 기본 dependency 구현이 registry를 우선 경유하는 이유를 설명한다.
- [[docmesh-py-core]] 는 현재 코드베이스가 정렬하려는 상위 SDK 철학을 보여준다.
- [[fastapi-core-prd-vs-source-code-comparison]] 은 실제 구현이 이 PRD와 얼마나 일치하는지 점검한 문서다.
