---
title: Optional observability services
created: 2026-06-11
updated: 2026-06-11
type: concept
tags: [observability, config, integration, risk, convention]
sources: [raw/articles/docmesh-py-core-config-2026-06-11.md]
confidence: medium
---
# Optional observability services

## Definition
이 주제는 Langfuse 같은 관측성 서비스를 핵심 애플리케이션 기능과 분리해 설정·운영하는 원칙을 다룬다. 문서는 선택 기능 장애가 핵심 서비스 장애로 전파되지 않도록 비활성화 가능성을 명시적으로 요구한다.

## Langfuse Contract
`LANGFUSE_ENABLED` 는 기본적으로 `true` 지만, `false` 일 때는 나머지 Langfuse 값들을 선택적으로 처리할 수 있어야 한다. host, public key, secret key, release, environment, timeout, retry 설정은 tracing 기능을 위해 쓰이지만, 이 기능은 필수 데이터 경로나 인증 경로와는 분리된다.

## Why It Matters
이 계약은 [[service-factory-registry]] 의 `langfuse` 반환값이 비활성화 시 `None` 일 수 있다는 API 규칙과 직접 연결된다. 또한 [[check-all-services]] 와 [[sdk-health-check-patterns]] 에서 required/optional 서비스를 구분하는 운영 모델을 정당화한다.

## Operational Notes
Langfuse health check는 인증 API 요청 또는 클라이언트 검증 방식으로 수행될 수 있다. 운영에서 tracing 이 일시적으로 불안정하더라도 핵심 기능을 중단시키지 않는 것이 우선이며, 환경 식별자는 기본적으로 `DOCMESH_ENV` 와 정렬된다.

## Related Topics
- [[service-factory-registry]] 는 Langfuse를 선택적 client로 노출할 수 있다.
- [[check-all-services]] 는 optional 서비스 집계에 적합하다.
- [[configuration-principles]] 는 선택 기능을 핵심 경로와 분리하는 운영 철학을 설명한다.
