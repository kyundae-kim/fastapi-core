---
title: fastapi-core
created: 2026-06-16
updated: 2026-06-16
type: entity
tags: [sdk, fastapi, architecture, integration, config]
sources: [raw/articles/fastapi-core-prd-2026-06-16.md]
confidence: medium
---
# fastapi-core

## Overview
`fastapi-core` 는 DocMesh 계열 FastAPI 마이크로서비스들이 공통으로 사용하는 Python SDK 패키지다. PRD 기준으로 이 패키지는 Keycloak 인증/인가, PostgreSQL, MinIO, Milvus, Ollama, Langfuse, NATS 같은 외부 연동을 표준화하고, 서비스 개발자가 비즈니스 로직에 집중할 수 있게 공통 초기화와 의존성 패턴을 제공한다.

이 SDK의 제품 방향은 중복 제거, 설정/예외/로깅 정책의 일관성 확보, 그리고 재사용 가능한 앱 조립 흐름 제공에 있다. 따라서 `fastapi-core` 는 개별 서비스의 구현 세부사항보다 공통 인프라 통합과 FastAPI wiring 에 무게중심이 있는 패키지로 이해하는 것이 맞다.

## Responsibilities
- Keycloak 기반 토큰 발급, JWT 검증, 권한 검사 지원
- PostgreSQL, MinIO, Milvus, Ollama, Langfuse, NATS 연결 생성과 재사용 패턴 제공
- `EnvConfig` 와 `ServiceSettings` 를 분리한 설정 모델 제공
- `create_app()` 기반 FastAPI 앱 조립 및 health route 제공
- `app.state` 기반 싱글톤 보관과 dependency fallback 정책 정의

## Architectural Notes
PRD는 외부 서비스 객체를 요청마다 새로 만들지 않고 애플리케이션 시작 시 한 번 생성해 `app.state` 에 저장하는 패턴을 핵심 운영 규칙으로 명시한다. 이 관점은 [[fastapi-app-state-singletons]] 에 정리된 lifecycle/state 계약과 직접 연결된다.

또한 설정은 환경별 접속 정보와 앱 동작 정책을 분리하는 [[layered-configuration-model]] 을 전제로 하며, 앱 엔트리포인트는 [[fastapi-app-factory-and-health-routes]] 에 정리된 `create_app()`/health route 조립 흐름으로 노출된다.

## Related Topics
- [[layered-configuration-model]] 은 `EnvConfig` 와 `ServiceSettings` 의 역할 분리를 다룬다.
- [[fastapi-app-state-singletons]] 은 서비스 객체의 state 저장/재사용 규칙을 다룬다.
- [[fastapi-app-factory-and-health-routes]] 는 FastAPI 조립과 readiness 범위를 정리한다.
- [[docmesh-py-core]] 는 현재 코드베이스가 정렬하려는 상위 SDK 철학을 보여준다.
- [[fastapi-core-codebase-review-against-docmesh-py-core]] 는 실제 구현이 이 PRD와 얼마나 일치하는지 점검한 문서다.
