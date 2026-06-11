---
title: ServiceFactoryRegistry
created: 2026-06-11
updated: 2026-06-11
type: concept
tags: [sdk, architecture, integration, api, convention]
sources: [raw/articles/docmesh-py-core-sdk-2026-06-11.md]
confidence: medium
---
# ServiceFactoryRegistry

## Definition
`ServiceFactoryRegistry`는 서비스별 client 생성과 종료 정리를 한곳으로 모으는 SDK의 핵심 조립 지점이다. 소비 애플리케이션은 각 서비스 SDK를 직접 초기화하기보다 registry를 통해 필요한 client만 생성한다.

## Recommended Usage Pattern
권장 흐름은 `load_settings()`로 검증된 설정을 만든 뒤 `ServiceFactoryRegistry(settings)` 를 생성하고, 필요한 서비스에 대해 `create_client("postgres")`, `create_client("minio")` 같은 호출을 수행하는 것이다. 실제 연결 검증은 [[sdk-health-check-patterns]] 에 따라 startup 시점에 `check()` 또는 서비스별 확인 루틴으로 수행한다.

registry는 전 서비스를 무조건 미리 띄우는 객체가 아니라, [[environment-driven-service-selection]] 결과에 따라 실제로 필요한 client만 선택적으로 조립하는 진입점이다. 이 때문에 소비 프로젝트의 코드가 설정 모델과 연결 정책을 한곳에서 제어할 수 있다.

## Notable Caveat
NATS는 일반 동기 client와 달리 `create_client("nats")` 가 즉시 연결된 객체를 반환하지 않고 `NatsConnectionBuilder`를 반환한다. 따라서 호출자는 `await builder.connect()` 또는 `await builder.check()` 같은 async 흐름을 명시적으로 처리해야 한다.

## Relationships
- [[docmesh-py-core]] 의 핵심 통합 패턴을 구현한다.
- [[environment-driven-service-selection]] 에 의해 어떤 서비스를 생성할지 결정된다.
- [[sdk-health-check-patterns]] 와 함께 startup readiness 및 종료 정리를 구성한다.
- [[keycloak-auth-integration]] 처럼 registry 바깥에서 직접 구성되는 인증 서비스와 경계를 이룬다.

## Trade-offs
장점은 애플리케이션 코드에서 서비스별 초기화 코드가 줄고 lifecycle 관리가 단순해진다는 점이다. 반면 서비스별 반환 타입이 완전히 균질하지 않을 수 있어, 특히 NATS 같은 비동기 연결 빌더는 호출자에게 추가 주의를 요구한다.
