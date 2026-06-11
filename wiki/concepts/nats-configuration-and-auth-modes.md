---
title: NATS configuration and auth modes
created: 2026-06-11
updated: 2026-06-11
type: concept
tags: [queue, config, integration, security, convention]
sources: [raw/articles/docmesh-py-core-config-2026-06-11.md]
confidence: medium
---
# NATS configuration and auth modes

## Definition
이 페이지는 NATS 연결을 위한 환경변수 계약과 인증 모드 제약을 정리한다. 런타임 연결 객체는 [[nats-connection-builder]] 가 담당하지만, 그 동작 가능성은 여기 정리된 설정 규칙에 의존한다.

## Core Settings
`NATS_SERVERS` 는 필수이며 쉼표 구분 URL 목록으로 파싱된다. 추가로 연결 이름, connect timeout, 최대 재연결 횟수를 설정할 수 있다. 이 구조는 다중 서버 환경과 재연결 전략을 환경변수 수준에서 제어할 수 있게 한다.

## Auth Modes
인증 방식은 아래 셋 중 하나만 선택한다: user/password, token, creds file. 즉 환경변수 조합은 상호배타적이며, 잘못 섞이면 [[load-settings-and-settings-model]] 단계에서 오류로 드러나는 것이 바람직하다.

## Async Constraint
문서는 health check 를 connect 후 ping/pong 또는 flush 확인으로 수행하고, 비동기 SDK 특성에 맞게 이벤트 루프를 임의 생성/종료하지 말라고 명시한다. 이는 [[nats-connection-builder]] 와 [[sdk-health-check-patterns]] 에서 드러난 async 계약을 설정 관점에서 보강한다.

## Related Topics
- [[nats-connection-builder]] 는 실제 async connect/check 동작을 제공한다.
- [[service-factory-registry]] 는 `nats` 서비스명에 대해 빌더를 반환한다.
- [[configuration-principles]] 는 환경변수 검증과 secret 관리의 공통 원칙을 설명한다.
