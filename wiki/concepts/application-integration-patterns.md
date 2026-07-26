---
title: Application integration patterns
created: 2026-06-29
updated: 2026-07-23
type: concept
tags: [integration, workflow, implementation, observability]
sources: [raw/articles/docmesh-py-core-api-reference-2026.md, raw/articles/docmesh-py-core-api-reference-v0.2.0.md, raw/articles/docmesh-py-core-api-reference-v0.3.0.md, raw/articles/docmesh-py-core-api-reference-v0.4.0.md, raw/articles/docmesh-py-core-api-reference-v0.5.0.md, raw/articles/docmesh-py-core-configuration-guide-v0.2.0.md, raw/articles/docmesh-py-core-configuration-guide-v0.3.0.md, raw/articles/docmesh-py-core-configuration-guide-v0.4.0.md, raw/articles/docmesh-py-core-configuration-guide-v0.5.0.md, raw/articles/docmesh-py-core-examples-guide-2026.md, raw/articles/docmesh-py-core-examples-guide-v0.2.0.md, raw/articles/docmesh-py-core-examples-guide-v0.3.0.md, raw/articles/docmesh-py-core-examples-guide-v0.4.0.md, raw/articles/docmesh-py-core-examples-guide-v0.5.0.md]
confidence: medium
---

# Application integration patterns

`docmesh-py-core` 문서는 개별 API 설명을 넘어서, 실제 애플리케이션이 설정 로딩·서비스 생성·헬스체크·종료 정리를 어떤 수명주기 패턴으로 묶어야 하는지 보여준다.

## Canonical lifecycle

v0.5.0 API 레퍼런스는 일반 애플리케이션에 assembly-first, direct-api-when-needed 정책을 권장한다. 일반 bootstrap에는 `RuntimePlan`과 `await assemble_service_runtime()`을, 동기 CLI·배치 통합에는 `assemble_services()`를 우선 고려하며, 단일 SDK·특수 factory 제어 시 direct API를 사용한다.^[raw/articles/docmesh-py-core-api-reference-v0.5.0.md]

- `RuntimePlan`은 서비스 선택, one-of, `HealthcheckPolicy`를 immutable하게 선언하며 빈 선택·중복·모순 plan을 거부한다. async 조립은 이를 `plan=`으로 전달한다.
- `assemble_service_runtime()`은 factory 또는 startup check 실패 시 생성된 자원을 정리한다. 동기 `assemble_services()`는 NATS를 지원하지 않는다.^[raw/articles/docmesh-py-core-api-reference-v0.5.0.md]
- direct 경로에서는 `load_service_configs()` 또는 개별 `*Config()`으로 설정을 준비하고, 필요한 `create_*_client()`와 `close_service_clients()`를 호출한다.^[raw/articles/docmesh-py-core-api-reference-v0.2.0.md]

배포는 application `RuntimePlan`에서 선택한 서비스의 환경변수만 제공하고, 네트워크 연결 전 `diagnose_services(plan=...)`가 성공한 뒤 assembly를 시작해야 한다. startup healthcheck는 `RuntimePlan.healthcheck`로 선언하며, production에서는 TLS·인증서 검증과 placeholder 검증 오류를 먼저 해결해야 한다.^[raw/articles/docmesh-py-core-configuration-guide-v0.5.0.md]

v0.5.0 예제는 `diagnose_services(plan=...)`를 네트워크 연결 전에 실행한 뒤 `runtime = await assemble_service_runtime(plan=plan)`과 `async with runtime`으로 lifecycle을 소유한다. `ServiceRuntime`은 SQLite wrapper/engine을 종료하지만, NATS `connect()`가 반환한 지속 연결은 application이 `drain()`으로 정리한다.^[raw/articles/docmesh-py-core-examples-guide-v0.5.0.md]

## Direct config and auth flows

v0.3.0 예시 문서는 aggregate `ServiceConfigs` 전체 없이도 `CommonConfig()`와 `KeycloakConfig()`를 직접 생성해 `KeycloakAuthService`를 붙이는 direct 경로를 보여준다. password grant에서는 함수 인자가 환경변수보다 우선하며, 생략된 credential은 `KEYCLOAK_TOKEN_USERNAME`/`KEYCLOAK_TOKEN_PASSWORD`에서 fallback한다.^[raw/articles/docmesh-py-core-examples-guide-v0.3.0.md]

이 패턴은 [[keycloak-authentication-api]]와 [[service-configuration-contracts]]의 설명을 실제 호출 형태로 구체화한다.

## Optional and selective dependencies

`load_service_configs(services={...})`는 필요한 서비스만 선택 로딩해 불필요한 env 검증을 피하는 패턴을 보여준다. direct SQLite는 `configs.require_sqlite()`로 명시적으로 config를 꺼내고, `try/finally`에서 client를 닫는다. 또한 `create_langfuse_client()` 결과가 `None`일 수 있음을 전제로 optional dependency처럼 분기한다. PostgreSQL/SQLite 대안은 `assemble_services(..., one_of=...)`로 구성할 수 있다.^[raw/articles/docmesh-py-core-examples-guide-v0.5.0.md]

이 패턴은 [[service-configuration-contracts]]의 조건부 필수 규칙과 연결되며, 특히 로컬 개발이나 기능 토글 기반 배포에서 유용하다.

## HTTP and messaging integration

readiness/liveness 용도에서는 `check_all_services()` 결과를 `{ok, services[]}` 형태로 변환해 API 응답에 노출하는 패턴이 제시된다. 비동기 메시징 쪽에서는 `nats`가 일반 wrapper가 아니라 `NatsConnectionBuilder`라는 점을 받아들여, `check()`로 연결 가능성만 검사하거나 `connect()` 결과를 애플리케이션이 직접 장기 관리해야 한다. NATS factory는 즉시 연결하지 않으며, user/password 쌍, token, creds file 중 최대 하나의 인증 모드만 허용하고 user/password의 한쪽만 설정하면 오류다.^[raw/articles/docmesh-py-core-configuration-guide-v0.5.0.md]

즉 동기 서비스 클라이언트와 비동기 연결 빌더를 동일 인터페이스로 가정하면 안 되며, [[service-health-check-aggregation]]와 [[service-factory-registry]]를 함께 읽고 통합해야 한다.

## Security and operational guidance

Keycloak 예시는 `password` grant 사용자 credential을 설정 객체에 고정하지 않고 토큰 요청 시점 인자로 전달하는 방식을 권장한다. 로깅 예시는 `configure_logging()`과 `DOCMESH_LOG_LEVEL` 기반 초기화를 보여주며, direct factory 경로에서는 여러 optional client 정리를 `close_service_clients()`로 통일할 수 있다.^[raw/articles/docmesh-py-core-examples-guide-2026.md]

이런 지침은 [[keycloak-authentication-api]]와 [[operational-logging-and-retry-utilities]]의 운영 원칙을 실제 코드 형태로 구체화한 것이다.
