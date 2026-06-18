---
title: NATS configuration and auth modes
created: 2026-06-11
updated: 2026-06-18
type: concept
tags: [queue, config, integration, security, convention]
sources: [raw/articles/docmesh-py-core-config-2026-06-11.md, raw/articles/fastapi-core-config-2026-06-17.md, raw/articles/fastapi-core-messaging-2026-06-18.md]
confidence: medium
---
# NATS configuration and auth modes

## Definition
이 페이지는 NATS 연결을 위한 환경변수 계약과 인증 모드 제약을 정리한다. 런타임 연결 객체는 [[nats-connection-builder]] 와 [[nats-event-helper-layer]] 가 각자의 계층에서 담당하지만, 그 동작 가능성은 여기 정리된 설정 규칙에 의존한다.

## Core Settings
`docmesh-py-core` 쪽 일반 규칙과 달리 `fastapi-core` 는 `NATS__SERVERS`, `NATS__NAME`, `NATS__CONNECT_TIMEOUT`, `NATS__MAX_RECONNECT_ATTEMPTS`, `NATS__RECONNECT_TIME_WAIT_MS`, `NATS__QUEUE_GROUP` 을 명시적으로 문서화한다. `NatsConfig.server_list` 는 서버 문자열을 콤마로 분리해 공백을 제거한 계산 프로퍼티다. `fastapi_core.core.messaging.create_nats_client()` 는 이 계산값을 그대로 `nats.connect(servers=...)` 에 전달하므로, 다중 서버 환경과 재연결 전략이 환경변수 수준에서 직접 제어된다.

또한 `NATS__QUEUE_GROUP` 는 단순 문서 상수라기보다 queue subscription helper 의 기본 작업자 그룹 정책을 표현한다. 즉 연결 설정과 이벤트 소비자 병렬화 정책이 같은 설정 모델 안에 묶여 있으며, 메시징 helper 는 이 값을 애플리케이션 이벤트 처리 규약으로 끌어올린다.

## Auth Modes
인증 방식은 아래 셋 중 하나만 선택한다: user/password, token, creds file. 즉 환경변수 조합은 상호배타적이며, 잘못 섞이면 [[load-settings-and-settings-model]] 단계에서 오류로 드러나는 것이 바람직하다.

## Async Constraint
문서는 health check 를 connect 후 ping/pong 또는 flush 확인으로 수행하고, 비동기 SDK 특성에 맞게 이벤트 루프를 임의 생성/종료하지 말라고 명시한다. 이는 [[nats-connection-builder]] 와 [[sdk-health-check-patterns]] 에서 드러난 async 계약을 설정 관점에서 보강한다.

## Related Topics
- [[nats-connection-builder]] 는 상위 SDK의 async connect/check 동작을 제공한다.
- [[nats-event-helper-layer]] 는 fastapi-core 쪽 subject/publish/subscribe helper 와 dependency 경계를 설명한다.
- [[service-factory-registry]] 는 `nats` 서비스명에 대해 빌더를 반환한다.
- [[configuration-principles]] 는 환경변수 검증과 secret 관리의 공통 원칙을 설명한다.
- [[lifecycle-policy-resolution]] 은 NATS eager-init 여부가 YAML lifecycle 정책에서 조절된다는 점을 설명한다.
