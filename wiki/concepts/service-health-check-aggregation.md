---
title: Service health check aggregation
created: 2026-06-25
updated: 2026-08-01
type: concept
tags: [service, api, observability, test, implementation]
sources: [raw/articles/docmesh-py-core-api-reference-2026.md, raw/articles/docmesh-py-core-api-reference-v0.2.0.md, raw/articles/docmesh-py-core-api-reference-v0.3.0.md, raw/articles/docmesh-py-core-api-reference-v0.4.0.md, raw/articles/docmesh-py-core-api-reference-v0.5.0.md, raw/articles/docmesh-py-core-examples-guide-2026.md, raw/articles/docmesh-py-core-examples-guide-v0.2.0.md, raw/articles/docmesh-py-core-examples-guide-v0.3.0.md, raw/articles/docmesh-py-core-examples-guide-v0.4.0.md, raw/articles/docmesh-py-core-examples-guide-v0.5.0.md, raw/articles/docmesh-config-api-reference-v0.1.0.md, raw/articles/docmesh-config-configuration-v0.1.0.md, raw/articles/docmesh-config-examples-v0.1.0.md, raw/articles/docmesh-py-core-api-reference-v0.6.0.md, raw/articles/docmesh-py-core-configuration-guide-v0.6.0.md, raw/articles/docmesh-py-core-examples-guide-v0.6.0.md, fastapi_core/factory.py, fastapi_core/routers/health.py]
confidence: medium
---

# Service health check aggregation

`check_all_services(service_checks, *, required_services=None, timer=time.perf_counter, parallel=False)`는 여러 서비스의 헬스체크를 묶어서 실행하고 결과를 집계하는 API다.^[raw/articles/docmesh-py-core-api-reference-2026.md]

## Reported outputs

v0.5.0 API 레퍼런스는 `HealthCheckResult`가 전체 `ok`와 서비스 결과 목록을 보유하고 `ServiceHealthStatus`가 `service`, `ok`, `latency_ms`, `required`, `error`, `error_type`를 제공한다고 설명한다. 두 타입 모두 JSON-safe `to_dict()`와 함께 패키지 루트 공개 import 목록에 포함한다.^[raw/articles/docmesh-py-core-api-reference-v0.5.0.md]

서비스별 세부 항목에는 성공 여부, 지연 시간, 마스킹된 오류 메시지가 들어간다.

- 전체 성공 여부
- 서비스별 성공 여부
- 서비스별 지연 시간
- 마스킹된 오류 메시지

## Failure model

필수 서비스가 실패하면 `HealthCheckError`가 발생한다. 비동기 lifecycle을 위해 `async_check_all_services()`도 동기·awaitable check를 함께 실행하고 per-service/overall timeout을 지원한다. 선택 서비스 실패도 aggregate `ok=False`에 반영하되, `HealthCheckError`는 필수 서비스 실패에만 발생하므로 두 운영 신호를 구분할 수 있다.^[raw/articles/docmesh-py-core-api-reference-v0.5.0.md]

## Configuration diagnosis is not a health check

`docmesh-config`의 `diagnose_services()`는 선택된 서비스의 환경변수 상태를 `absent`, `complete`, `partial`, `invalid`로 분류하지만 DNS, socket, 외부 API를 호출하지 않는다. `HealthcheckPolicy`도 timeout·retry·failure mode를 표현하는 metadata일 뿐 실제 상태 확인 실행기가 아니다.^[raw/articles/docmesh-config-api-reference-v0.1.0.md]^[raw/articles/docmesh-config-examples-v0.1.0.md]

따라서 `docmesh-config`는 client 생성과 네트워크 health check 전에 수행하는 preflight 계층이고, 이 페이지의 `check_all_services()`/`async_check_all_services()`는 실제 연결 가능성과 latency를 보고하는 downstream runtime 계층이다. 두 결과를 하나의 `ok` 의미로 합치지 않고 환경 구성 오류와 외부 서비스 장애를 별도 운영 신호로 유지해야 한다.^[raw/articles/docmesh-config-configuration-v0.1.0.md]

## v0.6.0 runtime policy and descriptors

v0.6.0의 `ServiceRuntime.check_with_policy(policy)`는 runtime을 닫지 않고 즉시 상태 확인을 실행한다. `REPORT`는 최종 required failure result를 반환하고 `FAIL`은 `HealthCheckError`를 유지하므로, startup 실패 정책과 readiness endpoint의 응답 매핑을 명시적으로 선택할 수 있다.^[raw/articles/docmesh-py-core-api-reference-v0.6.0.md]^[raw/articles/docmesh-py-core-examples-guide-v0.6.0.md]

`RuntimeHealthDescriptor`는 service, check callback, required flag를 immutable하게 묶고 runtime 생성 시 descriptor·handle·선택 서비스의 일관성을 검증한다. 따라서 health aggregation 입력은 임의 mapping뿐 아니라 assembly가 검증한 descriptor graph에서도 파생될 수 있다.^[raw/articles/docmesh-py-core-api-reference-v0.6.0.md]

서비스별 timeout은 실패 status로 변환되지만 `overall_timeout_seconds` 초과는 partial result 없이 `asyncio.TimeoutError`로 전파될 수 있다. FastAPI readiness는 `HealthCheckError`와 전체 timeout을 모두 실패 응답으로 처리해야 한다.^[raw/articles/docmesh-py-core-api-reference-v0.6.0.md]^[raw/articles/docmesh-py-core-examples-guide-v0.6.0.md]

- `parallel=False`에서는 입력 순서대로 순차 실행한다.
- `parallel=True`에서는 `ThreadPoolExecutor`로 병렬 실행하지만 반환 순서는 입력 순서를 유지한다.
- required 서비스가 실패하면 `HealthCheckError`를 발생시킨다.
- 오류 문자열은 `mask_sensitive_value()`를 거쳐 민감정보를 숨긴다.^[raw/articles/docmesh-py-core-api-reference-2026.md]

## Input shape

입력은 서비스명에서 check callable로 매핑되는 dict다. v0.5.0 예제는 `required_services={"database"}`, `parallel=True`로 실행하고 `HealthCheckError.result`에서 상태를 읽는다. 선택 서비스 실패는 `result.ok=False`로 남지만 예외를 만들지 않으며, async callable 또는 timeout이 필요하면 `async_check_all_services()`를 사용한다.^[raw/articles/docmesh-py-core-examples-guide-v0.5.0.md]

FastAPI health endpoint 예시는 반환값을 `{ok, services[]}` 형태로 변환해 readiness/liveness 응답 본문으로 직접 노출하는 패턴을 보여준다. 이때 서비스별 `ok`, `latency_ms`, `error`를 그대로 전달할 수 있다.

## Related pages

- [[docmesh-py-core]]: 이 집계 API는 패키지 운영 인터페이스의 일부다.
- [[service-factory-registry]]: older registry 경로든 current direct `create_*_client()` 경로든, 최종적으로 wrapper/builder의 `check()`가 집계 입력이 된다.
- [[keycloak-authentication-api]]: Keycloak 기본 확인은 access token 발급 기반으로 동작한다.
- [[operational-logging-and-retry-utilities]]: 오류 마스킹과 구조화 로그 규칙이 헬스체크 실패 표현에 영향을 준다.

## Operational implication

fastapi-core는 현재 이 API를 `/health/readiness`에서 사용한다. 앱 팩토리는 service client 기반 check와 필수 서비스 메타데이터를 구성하고, health router는 집계 결과를 `ok`/`degraded`/`error` 상태와 HTTP `200`/`503` 응답으로 변환한다.
