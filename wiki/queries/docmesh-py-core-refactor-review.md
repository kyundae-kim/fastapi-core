---
title: docmesh-py-core refactor review
created: 2026-06-11
updated: 2026-06-11
type: query
tags: [query, architecture, sdk, decision, risk]
sources: [raw/articles/docmesh-py-core-sdk-2026-06-11.md, raw/articles/docmesh-py-core-api-2026-06-11.md, raw/articles/docmesh-py-core-config-2026-06-11.md]
confidence: medium
---
# docmesh-py-core refactor review

## Executive Summary
`docmesh-py-core` 를 기반으로 리팩터링한다면, 가장 먼저 지켜야 할 중심축은 `load_settings() -> ServiceFactoryRegistry -> create_client()/auth service -> check() -> close_all()` 라는 표준 lifecycle 이다. 이 흐름이 무너지면 서비스별 초기화 코드가 다시 애플리케이션으로 새어나오고, SDK를 도입하는 이유가 약해진다. ^[raw/articles/docmesh-py-core-sdk-2026-06-11.md]

리팩터링의 방향은 기능 추가보다 경계 정리에 가까워야 한다. 특히 [[load-settings-and-settings-model]], [[service-factory-registry]], [[sdk-health-check-patterns]] 를 중심으로 bootstrap, runtime integration, health/readiness, shutdown 책임을 더 분명히 나누는 것이 우선이다. ^[raw/articles/docmesh-py-core-api-2026-06-11.md]

## What To Preserve
1. **단일 설정 진입점 유지**: 설정 로드와 검증은 계속 [[load-settings-and-settings-model]] 하나로 수렴시키는 것이 좋다. 개별 서비스가 자체적으로 env 를 읽기 시작하면 설정 검증이 분산되고 에러 메시지 일관성이 무너진다. ^[raw/articles/docmesh-py-core-config-2026-06-11.md]
2. **조립 지점의 중앙화 유지**: [[service-factory-registry]] 는 외부 client 생성 책임을 모으는 핵심 추상화다. 서비스별 초기화 로직을 다시 FastAPI startup 코드나 worker 엔트리포인트에 퍼뜨리지 않는 것이 중요하다. ^[raw/articles/docmesh-py-core-api-2026-06-11.md]
3. **환경 기반 서비스 선택 유지**: [[environment-driven-service-selection]] 처럼 backend selector 대신 설정 존재 여부로 PostgreSQL/SQLite 같은 구성을 바꾸는 모델은 유지 가치가 크다. 테스트/로컬/운영 전환 비용을 낮춘다. ^[raw/articles/docmesh-py-core-sdk-2026-06-11.md]
4. **필수/선택 서비스 분리 유지**: [[check-all-services]] 와 [[optional-observability-services]] 가 보여주듯, Langfuse 같은 관측성 구성은 핵심 기능 경로와 분리해야 한다. ^[raw/articles/docmesh-py-core-config-2026-06-11.md]

## Recommended Refactor Axes
### 1. Bootstrap Layer를 명시적으로 분리
현재 문서상 개념은 이미 분명하지만, 코드 구조도 이에 맞춰 `settings -> registry -> app wiring` 순서를 더 드러내는 편이 좋다. 예를 들어 FastAPI lifespan, CLI entrypoint, worker bootstrap 이 같은 초기화 유틸리티를 공유하게 만들면 중복이 줄고 [[sdk-health-check-patterns]] 적용도 일관돼진다. ^[raw/articles/docmesh-py-core-sdk-2026-06-11.md]

### 2. Runtime Service와 Control Plane을 분리
Keycloak은 [[keycloak-auth-integration]] 과 [[keycloak-provisioner]] 가 서로 다른 성격을 갖는다. 리팩터링 시 runtime auth(token fetch/JWT validation) 와 provisioning(admin realm/client/role 관리) 코드를 같은 모듈 계층에 섞어두기보다 패키지 경계를 분리하는 것이 좋다. 운영 권한 모델도 다르고 실패 영향도 다르다. ^[raw/articles/docmesh-py-core-api-2026-06-11.md]

### 3. 반환 계약의 불균질성을 타입 수준에서 더 드러내기
현재 [[service-factory-registry]] 는 대부분 [[service-client-wrapper]] 를 반환하지만, `langfuse` 는 `None` 가능, `nats` 는 [[nats-connection-builder]] 를 반환한다. 리팩터링 포인트는 이 차이를 숨기려 하지 말고, 문서/타입/API 계층에서 더 분명히 드러내는 것이다. 예를 들면 sync-capable services 와 async-builder services 를 registry 내부에서도 논리적으로 분리할 수 있다. ^[raw/articles/docmesh-py-core-api-2026-06-11.md]

### 4. 서비스별 설정 스키마를 더 독립적으로 유지
[[configuration-principles]] 가 말하듯 공통 timeout/retry/pool 을 억지로 올리지 말고 서비스별 설정을 독립적으로 유지하는 쪽이 좋다. PostgreSQL, NATS, Keycloak, Langfuse 는 실패 모드와 운영 tuning 포인트가 다르기 때문이다. 리팩터링 시 공통화 욕심이 과하면 오히려 설정 모델이 흐려질 수 있다. ^[raw/articles/docmesh-py-core-config-2026-06-11.md]

### 5. Health Contract를 얇고 예측 가능하게 유지
[[sdk-health-check-patterns]] 와 [[check-all-services]] 는 readiness 정책의 장점이 크지만, 각 서비스 `check()` 가 무거워지면 startup latency 와 장애 전파가 커질 수 있다. 리팩터링에서는 `check()` 를 "최소 유효 연결 확인"으로 유지하고, 상세 진단은 별도 diagnostics 계층으로 분리하는 방향이 좋다. ^[raw/articles/docmesh-py-core-api-2026-06-11.md]

## High-Risk Areas During Refactor
### NATS
[[nats-connection-builder]] 와 [[nats-configuration-and-auth-modes]] 가 보여주듯 NATS는 예외 케이스다. 동기 client처럼 다루거나 이벤트 루프 생명주기를 SDK 내부에서 임의로 감추면, 오히려 프레임워크 통합이 더 어려워질 수 있다. NATS는 별도 async boundary로 유지하는 쪽이 안전하다. ^[raw/articles/docmesh-py-core-config-2026-06-11.md]

### Keycloak
[[keycloak-configuration-rules]] 에는 grant type, audience, SSL 검증, admin credential 방식 등 조건부 규칙이 많다. 리팩터링 중 설정 단순화를 시도하다가 runtime auth 와 provisioning 규칙을 섞으면 가장 먼저 문제가 날 가능성이 높다. ^[raw/articles/docmesh-py-core-config-2026-06-11.md]

### Observability Optionality
[[optional-observability-services]] 에서 정리한 대로 Langfuse는 실패 시 핵심 기능을 막지 않아야 한다. tracing 편의를 위해 registry/health 정책을 강결합시키면 운영 복원력이 오히려 떨어질 수 있다. ^[raw/articles/docmesh-py-core-config-2026-06-11.md]

## Suggested Refactor Order
1. [[load-settings-and-settings-model]] 와 서비스별 config 모델 정리
2. [[service-factory-registry]] 책임 정리
3. [[service-client-wrapper]] / [[nats-connection-builder]] 계약 명확화
4. [[sdk-health-check-patterns]] / [[check-all-services]] 정리
5. [[keycloak-auth-integration]] 와 [[keycloak-provisioner]] 경계 분리
6. [[optional-observability-services]] 정책 재확인

이 순서를 추천하는 이유는 설정과 생성 책임이 가장 상위 레이어이고, 그 위에 health/readiness 와 서비스별 특수 케이스가 쌓이기 때문이다. 아래 레이어부터 손보면 상위 API가 계속 흔들릴 가능성이 크다. ^[raw/articles/docmesh-py-core-sdk-2026-06-11.md]

## Practical Review Verdict
좋은 리팩터링 방향은 **"SDK 소비자가 알아야 할 표면은 단순하게 유지하되, 내부 경계는 더 명확하게 만드는 것"** 이다. 즉 외부에서 보는 사용 패턴은 가능한 한 유지하고, 내부적으로는 설정/조립/운영/인증/옵저버빌리티 경계를 분리하는 쪽이 적합하다. [[docmesh-py-core]] 는 이미 그 방향의 문서 신호를 가지고 있으므로, 전면 재설계보다 구조 정리형 리팩터링이 더 맞아 보인다. ^[raw/articles/docmesh-py-core-sdk-2026-06-11.md]

## Follow-up Questions
- LLM provider abstraction 이 이 패키지 안에 계속 있어야 하는가, 아니면 별도 패키지로 분리할 것인가?
- ServiceFactoryRegistry 를 단일 registry 로 유지할지, sync/async 혹은 data/auth/observability registry 로 나눌지?
- health check 를 startup readiness 와 운영 diagnostics 로 분리할지?
- Keycloak provisioning 을 core 패키지에 둘지 별도 admin extension 으로 뺄지?
