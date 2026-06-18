---
title: SDK health check patterns
created: 2026-06-11
updated: 2026-06-11
type: concept
tags: [sdk, observability, testing, integration, convention]
sources: [raw/articles/docmesh-py-core-sdk-2026-06-11.md, raw/articles/docmesh-py-core-api-2026-06-11.md]
confidence: medium
---
# SDK health check patterns

## Definition
이 문맥에서 health check 패턴은 설정이 문법적으로 유효한지 확인하는 수준을 넘어, 실제 외부 서비스에 연결 가능한지 startup 시점이나 readiness 경로에서 검증하는 운영 규칙을 뜻한다.

## Core Pattern
문서는 client 생성 직후 `check()` 를 호출해 실제 연결 가능성을 확인하는 흐름을 권장한다. PostgreSQL과 SQLite는 `SELECT 1`, MinIO는 `list_buckets()` 가 기본 health check 계약으로 제시된다. API 문서까지 합치면 Milvus는 `list_collections()`, Ollama는 `ps()`, Langfuse는 `auth_check()`, Keycloak은 `fetch_access_token()` 기반으로 점검된다는 점도 드러난다.

여러 서비스를 한 번에 점검할 때는 [[check-all-services]] 로 결과를 집계하고, 핵심 서비스와 선택 서비스를 구분한다. 예시에서는 PostgreSQL을 required 로 두고 MinIO나 Langfuse 같은 서비스를 optional 로 분리할 수 있다.

## Integration Style
FastAPI 애플리케이션에서는 lifespan 에서 [[load-settings-and-settings-model]] 로 설정을 로드하고, registry 생성, 필요한 서비스의 `check()` 호출, app state 저장, 종료 시 `close_all()` 을 수행하는 형태가 권장된다. 배치/CLI 역시 시작 시 검증하고 종료 시 정리하는 동일한 lifecycle 패턴을 따른다.

이 구조는 [[service-factory-registry]] 와 함께 동작하며, 어떤 서비스가 점검 대상인지에 대해서는 [[environment-driven-service-selection]] 의 결과를 따른다. 인증 검증 흐름은 [[keycloak-auth-integration]] 과도 연결되지만, 문서상 예시는 저장소/인프라 readiness 에 초점을 둔다.

## Why It Matters
startup 초기에 실패를 드러내면 디버깅이 쉬워지고, optional 서비스와 required 서비스를 분리해 readiness 기준을 더 현실적으로 설계할 수 있다. 반면 health check 구현이 무거워지면 startup latency 가 늘 수 있어 서비스별 계약을 명확히 유지할 필요가 있다.

특히 공통 인터페이스는 [[service-client-wrapper]] 가 제공하고, 집계·예외 정책은 [[check-all-services]] 가 제공하며, NATS는 [[nats-connection-builder]] 처럼 별도 async 계약을 가진다는 점을 함께 이해해야 전체 health 설계가 정확해진다.
