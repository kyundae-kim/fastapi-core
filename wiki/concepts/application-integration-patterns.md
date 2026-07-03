---
title: Application integration patterns
created: 2026-06-29
updated: 2026-07-02
type: concept
tags: [integration, workflow, implementation, observability]
sources: [raw/articles/docmesh-py-core-api-reference-2026.md, raw/articles/docmesh-py-core-examples-guide-2026.md]
confidence: medium
---

# Application integration patterns

`docmesh-py-core` 문서는 개별 API 설명을 넘어서, 실제 애플리케이션이 설정 로딩·서비스 생성·헬스체크·종료 정리를 어떤 수명주기 패턴으로 묶어야 하는지 보여준다.

## Canonical lifecycle

최신 examples와 API 레퍼런스는 이제 같은 방향을 가리킨다.

- `load_service_configs()` 또는 필요한 경우 개별 `*Config()` 생성으로 설정을 준비한다.
- 필요한 서비스만 `create_*_client()`로 조립한다.
- startup 시 필수 서비스만 `check()`하거나 `check_all_services()`로 확인한다.
- shutdown 시 `close_service_clients()` 또는 개별 `close()`를 호출한다.^[raw/articles/docmesh-py-core-api-reference-2026.md]^[raw/articles/docmesh-py-core-examples-guide-2026.md]

예시 문서는 FastAPI lifespan 안에서 `postgres`, `minio`를 직접 생성해 `app.state`에 보관하고, 종료 시 `close_service_clients([postgres, minio])`로 정리하는 패턴을 제시한다. 즉 이전 registry 중심 수명주기 설명보다 direct client ownership 모델이 현재 canonical path에 가깝다.^[raw/articles/docmesh-py-core-examples-guide-2026.md]

## Direct config and auth flows

예시 문서는 aggregate `ServiceConfigs` 전체 없이도 `CommonConfig()`와 `KeycloakConfig()`를 직접 생성해 `KeycloakAuthService`를 붙이는 패턴을 보여준다. 또한 password grant에서는 환경변수 자동 주입이 아니라 `fetch_access_token(username=..., password=...)` 함수 인자를 넘겨야 한다는 점을 예제로 못 박는다.^[raw/articles/docmesh-py-core-examples-guide-2026.md]

이 패턴은 [[keycloak-authentication-api]]와 [[service-configuration-contracts]]의 설명을 실제 호출 형태로 구체화한다.

## Optional and selective dependencies

`load_service_configs(services={...})`는 필요한 서비스만 선택 로딩해 불필요한 env 검증을 피하는 패턴을 보여준다. 또한 `create_langfuse_client()` 결과가 `None`일 수 있음을 전제로 optional dependency처럼 분기한다.

이 패턴은 [[service-configuration-contracts]]의 조건부 필수 규칙과 연결되며, 특히 로컬 개발이나 기능 토글 기반 배포에서 유용하다.

## HTTP and messaging integration

readiness/liveness 용도에서는 `check_all_services()` 결과를 `{ok, services[]}` 형태로 변환해 API 응답에 노출하는 패턴이 제시된다. 비동기 메시징 쪽에서는 `nats`가 일반 wrapper가 아니라 `NatsConnectionBuilder`라는 점을 받아들여, `check()`로 연결 가능성만 검사하거나 `connect()` 결과를 애플리케이션이 직접 장기 관리해야 한다.

즉 동기 서비스 클라이언트와 비동기 연결 빌더를 동일 인터페이스로 가정하면 안 되며, [[service-health-check-aggregation]]와 [[service-factory-registry]]를 함께 읽고 통합해야 한다.

## Security and operational guidance

Keycloak 예시는 `password` grant 사용자 credential을 설정 객체에 고정하지 않고 토큰 요청 시점 인자로 전달하는 방식을 권장한다. 로깅 예시는 `configure_logging()`과 `DOCMESH_LOG_LEVEL` 기반 초기화를 보여주며, direct factory 경로에서는 여러 optional client 정리를 `close_service_clients()`로 통일할 수 있다.^[raw/articles/docmesh-py-core-examples-guide-2026.md]

이런 지침은 [[keycloak-authentication-api]]와 [[operational-logging-and-retry-utilities]]의 운영 원칙을 실제 코드 형태로 구체화한 것이다.
