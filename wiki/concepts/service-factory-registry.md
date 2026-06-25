---
title: ServiceFactoryRegistry
created: 2026-06-25
updated: 2026-06-25
type: concept
tags: [service, module, integration, api, implementation]
sources: [raw/articles/docmesh-py-core-api-reference-2026.md]
confidence: medium
---

# ServiceFactoryRegistry

`ServiceFactoryRegistry(settings)`는 외부 서비스 클라이언트 생성을 위한 중앙 진입점이다. 문서상 `create_client(service_name)`, `create_clients(services)`, `close_all()`을 제공하며, 서비스별 초기화 방식을 호출부에서 직접 분기하지 않게 해준다.

## Supported service names

문서에 명시된 지원 대상은 `keycloak`, `postgres`, `sqlite`, `minio`, `milvus`, `ollama`, `langfuse`, `nats`다.

## Return model

대부분의 서비스는 `ServiceClientWrapper`를 반환하고, `nats`는 비동기 `NatsConnectionBuilder`를 반환한다. `langfuse`는 `ServiceClientWrapper | None`일 수 있어 선택적 통합 지점을 암시한다.

## Error surface

주요 예외는 `UnsupportedServiceError`, `ServiceClientWrapperError`, `ServiceClientError`다. 따라서 fastapi-core는 서비스명 검증 실패, 래핑 실패, 실제 클라이언트 오류를 분리해서 처리할 수 있다.

## Related behavior

- [[docmesh-py-core]]: 이 registry는 패키지 공개 API의 핵심 진입점 중 하나다.
- [[service-health-check-aggregation]]: registry가 만든 wrapper/builder는 집계 헬스체크의 입력이 된다.
- [[keycloak-authentication-api]]: `keycloak` 서비스 생성 경로는 Keycloak 고수준 인증 API와 맞물린다.

## Design implication

fastapi-core가 이 패턴을 채택하면 서비스별 연결 수명주기와 기본 `check()/close()` 인터페이스를 표준화할 수 있고, 서비스 추가 시 호출부 변경 범위를 줄일 수 있다.
