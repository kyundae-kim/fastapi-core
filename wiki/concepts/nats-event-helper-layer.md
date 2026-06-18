---
title: NATS event helper layer
created: 2026-06-18
updated: 2026-06-18
type: concept
tags: [queue, api, fastapi, integration, convention]
sources: [raw/articles/fastapi-core-messaging-2026-06-18.md]
confidence: medium
---
# NATS event helper layer

## Definition
`fastapi-core` 의 메시징 문서는 NATS 연동을 두 계층으로 분리한다. 하나는 `fastapi_core.core.messaging` 이 제공하는 순수 NATS helper 계층이고, 다른 하나는 `fastapi_core.dependencies.messaging` 이 제공하는 FastAPI dependency 계층이다. 이 분리는 standalone 이벤트 발행 로직과 애플리케이션 수명주기·state 캐시 정책을 섞지 않게 해 주며, [[registry-backed-dependency-resolution]] 과 [[function-style-fastapi-dependencies]] 의 책임 경계를 메시징 영역에 구체적으로 드러낸다.

## Core helper surface
core helper 계층은 `create_nats_client()`, `validate_event_subject()`, `build_event_subject()`, `publish_event()`, `subscribe_event()`, `subscribe_queue_event()` 를 제공한다. 여기서 연결 생성은 `NatsConfig.server_list` 를 그대로 사용해 `nats.connect(...)` 를 호출하고, 발행/구독 helper 는 JSON 인코딩과 subject 검증을 공통화한다. 따라서 서비스 개발자는 subject 형식과 payload 직렬화 규칙을 매번 직접 구현하지 않아도 된다. 이 helper 계층은 [[nats-configuration-and-auth-modes]] 의 설정 계약을 실제 런타임 API로 바꿔 주는 얇은 실행 표면이다.

## Subject contract
이 문서는 이벤트 subject 를 `<domain>.<entity>.<action>` 의 3-segment 규칙으로 고정한다. 각 segment 는 소문자 영문자, 숫자, 하이픈만 허용되며, `build_event_subject()` 는 잘못된 조합에 대해 `ValueError` 를 발생시킨다. 이 규칙은 메시징 API를 단순한 raw publish wrapper 가 아니라 도메인 이벤트 명명 규약을 강제하는 표면으로 만든다. 결과적으로 subject naming 일관성은 코드 리뷰 관습이 아니라 SDK 레벨 계약이 된다.

## Publish and subscribe contract
`publish_event()` 는 유효한 subject 만 허용하고 payload 를 compact JSON UTF-8 bytes 로 직렬화해 `client.publish()` 에 전달한다. `subscribe_event()` 와 `subscribe_queue_event()` 는 수신 데이터를 JSON 으로 decode 한 뒤 `handler(subject, payload)` 를 호출하며, handler 가 async 면 await 한다. 이 구조는 도메인 서비스가 바이트 처리와 역직렬화 보일러플레이트를 반복하지 않게 만들고, queue subscription 에서는 `NATS__QUEUE_GROUP` 같은 설정값을 애플리케이션 정책으로 연결할 수 있게 한다. 설정·연결 관점의 배경은 [[nats-configuration-and-auth-modes]] 와 [[nats-connection-builder]] 에서 보완된다.

## FastAPI integration boundary
FastAPI 계층은 `set_nats_client()` 와 `get_nats_client()` 두 함수로 정리된다. 중요한 점은 이 계층이 기본적으로 `create_nats_client()` 를 직접 호출하지 않고, docmesh registry 기반 `nats_client` 해석 결과를 `app.state` 에 캐시한다는 것이다. 즉 standalone helper 계층과 기본 FastAPI dependency 계층은 같은 메시징 도메인을 다루지만 생성 책임이 다르다. 이 차이는 [[fastapi-app-state-singletons]] 의 state 재사용 규칙과 [[registry-backed-dependency-resolution]] 의 registry 우선 정책을 메시징 사례로 보여준다.

## Related Topics
- [[fastapi-core]] 는 이 메시징 helper/dependency 이중 구조를 공식 SDK 책임으로 포함한다.
- [[nats-configuration-and-auth-modes]] 는 서버 목록, 재연결, queue group 등 설정 계약을 설명한다.
- [[nats-connection-builder]] 는 상위 docmesh SDK 쪽 NATS 조립 모델과 async 특이점을 설명한다.
- [[function-style-fastapi-dependencies]] 는 `get_nats_client()` / `set_nats_client()` 같은 공식 dependency 표면을 설명한다.
- [[registry-backed-dependency-resolution]] 은 기본 FastAPI 경로가 registry를 통해 NATS client 를 해석하는 이유를 설명한다.
- [[fastapi-app-state-singletons]] 는 해석된 NATS client 가 어디에 캐시되는지 설명한다.
