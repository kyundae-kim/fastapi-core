---
title: ServiceClientWrapper
created: 2026-06-11
updated: 2026-06-11
type: concept
tags: [sdk, api, integration, observability, convention]
sources: [raw/articles/docmesh-py-core-api-2026-06-11.md]
confidence: medium
---
# ServiceClientWrapper

## Definition
`ServiceClientWrapper` 는 서비스별 원본 SDK client 위에 공통 `ping()`, `check()`, `close()` 인터페이스를 제공하는 래퍼다. 동시에 원본 client 메서드는 그대로 위임해 소비 애플리케이션이 고유 기능도 계속 사용할 수 있게 한다.

## Role in the Architecture
[[service-factory-registry]] 는 대부분의 서비스에 대해 이 래퍼를 반환한다. 이 덕분에 PostgreSQL, SQLite, MinIO, Milvus, Ollama, Keycloak, Langfuse 같은 상이한 통합을 일정한 lifecycle 인터페이스로 다룰 수 있다. 단, NATS는 예외적으로 [[nats-connection-builder]] 를 반환한다.

## Default Health Contracts
문서 기준 기본 `check()` 동작은 서비스별로 다르다: Keycloak은 `fetch_access_token()`, PostgreSQL/SQLite는 `SELECT 1`, MinIO는 `list_buckets()`, Milvus는 `list_collections()`, Ollama는 `ps()`, Langfuse는 `auth_check()` 를 수행한다. 이 공통 래퍼는 [[sdk-health-check-patterns]] 와 [[check-all-services]] 를 구현 가능한 형태로 만드는 중요한 추상화다.

## Trade-offs
장점은 lifecycle 제어와 health semantics를 표준화한다는 점이다. 반면 서비스별 실제 동작은 내부적으로 서로 다르므로, 호출자는 `check()` 의 의미가 서비스마다 동일한 세부 작업을 뜻하지는 않는다는 점을 이해해야 한다.

## Related Topics
- [[service-factory-registry]] 가 이 래퍼를 생성한다.
- [[sdk-health-check-patterns]] 는 이 래퍼의 `check()` 계약에 의존한다.
- [[docmesh-py-core]] 는 이를 통해 다양한 외부 연동을 단일 패턴으로 노출한다.
