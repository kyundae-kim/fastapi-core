---
title: Application integration patterns
created: 2026-06-29
updated: 2026-06-29
type: concept
tags: [integration, workflow, implementation, observability]
sources: [raw/articles/docmesh-py-core-examples-guide-2026.md]
confidence: medium
---

# Application integration patterns

`docmesh-py-core` 예제 문서는 라이브러리의 개별 API 설명을 넘어서, 실제 애플리케이션이 설정 로딩·서비스 생성·헬스체크·종료 정리를 어떤 수명주기 패턴으로 묶어야 하는지 보여준다.

## Canonical lifecycle

가장 기본 패턴은 `load_settings(environ)`으로 설정을 1회 로드하고, `ServiceFactoryRegistry(settings)`를 생성한 뒤, 앱 시작 시 필수 서비스만 `check()`하거나 `check_all_services()`로 검증하고, 종료 시 `close_all()`로 정리하는 것이다.

FastAPI 예시에서는 이 registry를 `app.state.registry`에 보관해 요청 처리 중 재사용하고, `lifespan` 종료 구간에서 정리한다. 이는 [[service-factory-registry]]를 앱 전역 싱글톤처럼 다루는 방향과 맞닿아 있다.

## Optional and selective dependencies

예제는 `services={"sqlite", "langfuse"}`처럼 필요한 서비스만 선택 로딩해, 불필요한 env 검증을 피하는 패턴을 보여준다. 또한 `create_client("langfuse")` 결과가 `None`일 수 있음을 전제로 optional dependency처럼 분기한다.

이 패턴은 [[service-configuration-contracts]]의 조건부 필수 규칙과 연결되며, 특히 로컬 개발이나 기능 토글 기반 배포에서 유용하다.

## HTTP and messaging integration

readiness/liveness 용도에서는 `check_all_services()` 결과를 `{ok, services[]}` 형태로 변환해 API 응답에 노출하는 패턴이 제시된다. 비동기 메시징 쪽에서는 `nats`가 일반 wrapper가 아니라 `NatsConnectionBuilder`라는 점을 받아들여, `check()`로 연결 가능성만 검사하거나 `connect()` 결과를 애플리케이션이 직접 장기 관리해야 한다.

즉 동기 서비스 클라이언트와 비동기 연결 빌더를 동일 인터페이스로 가정하면 안 되며, [[service-health-check-aggregation]]과 [[service-factory-registry]]를 함께 읽고 통합해야 한다.

## Security and operational guidance

Keycloak 예시는 `password` grant 사용자 credential을 설정 객체에 고정하지 않고 토큰 요청 시점 인자로 전달하는 방식을 권장한다. 로깅 예시는 `configure_logging()`과 `DOCMESH_LOG_LEVEL` 기반 초기화를 보여주며, 재시도 예시는 영구 오류와 일시적 오류를 분리하라고 강조한다.

이런 지침은 [[keycloak-authentication-api]]와 [[operational-logging-and-retry-utilities]]의 운영 원칙을 실제 코드 형태로 구체화한 것이다.
