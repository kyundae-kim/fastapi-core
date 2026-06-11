---
title: NatsConnectionBuilder
created: 2026-06-11
updated: 2026-06-11
type: concept
tags: [queue, integration, api, sdk, convention]
sources: [raw/articles/docmesh-py-core-sdk-2026-06-11.md, raw/articles/docmesh-py-core-api-2026-06-11.md]
confidence: medium
---
# NatsConnectionBuilder

## Definition
`NatsConnectionBuilder` 는 NATS 연결 인자를 보관하고, 명시적인 async 호출 시 실제 연결을 생성하는 빌더다. `ServiceFactoryRegistry.create_client("nats")` 의 반환값은 연결된 동기 client가 아니라 이 빌더다.

## Runtime Contract
호출자는 `await builder.connect()` 또는 `await builder.check()` 를 사용해야 한다. `check()` 는 연결 생성 뒤 `flush()` 까지 수행하므로 readiness 확인에 적합하다. 이 동작은 일반 서비스 래퍼와 다르며, [[service-client-wrapper]] 기반 통합과 구분되는 예외 케이스다.

## Why It Matters
문서에서 NATS는 가장 주의가 필요한 서비스로 분류된다. 애플리케이션이 이를 동기 client처럼 취급하면 잘못된 사용이 되므로, FastAPI startup 이나 worker bootstrap 에서 async lifecycle 을 명시적으로 설계해야 한다. 이 점은 [[service-factory-registry]] 의 반환 타입이 완전히 균질하지 않다는 대표 사례다.

## Integration Notes
전체 서비스 헬스 패턴과 함께 사용할 때는 [[sdk-health-check-patterns]] 의 일반 `check()` 예시와 달리 async 경로를 따로 고려해야 한다. 환경 선택 자체는 [[environment-driven-service-selection]] 처럼 환경에 의해 결정될 수 있지만, 사용 계약은 별도 학습이 필요하다.

## Related Topics
- [[service-factory-registry]] 는 `nats` 서비스명에 대해 이 객체를 반환한다.
- [[docmesh-py-core]] 의 비동기 예외 케이스를 보여준다.
- [[sdk-health-check-patterns]] 와 함께 readiness 흐름을 설계할 때 주의점이 된다.
