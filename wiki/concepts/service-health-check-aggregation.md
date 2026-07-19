---
title: Service health check aggregation
created: 2026-06-25
updated: 2026-07-19
type: concept
tags: [service, api, observability, test, implementation]
sources: [raw/articles/docmesh-py-core-api-reference-2026.md, raw/articles/docmesh-py-core-api-reference-v0.2.0.md, raw/articles/docmesh-py-core-api-reference-v0.3.0.md, raw/articles/docmesh-py-core-api-reference-v0.4.0.md, raw/articles/docmesh-py-core-examples-guide-2026.md, raw/articles/docmesh-py-core-examples-guide-v0.2.0.md, raw/articles/docmesh-py-core-examples-guide-v0.3.0.md, raw/articles/docmesh-py-core-examples-guide-v0.4.0.md, fastapi_core/factory.py, fastapi_core/routers/health.py]
confidence: medium
---

# Service health check aggregation

`check_all_services(service_checks, *, required_services=None, timer=time.perf_counter, parallel=False)`는 여러 서비스의 헬스체크를 묶어서 실행하고 결과를 집계하는 API다.^[raw/articles/docmesh-py-core-api-reference-2026.md]

## Reported outputs

v0.4.0 API 레퍼런스는 `HealthCheckResult`가 전체 `ok`와 서비스 결과 목록을 보유하고 `ServiceHealthStatus`가 `service`, `ok`, `latency_ms`, `required`, `error`, `error_type`를 제공한다고 설명한다. 두 타입 모두 패키지 루트 공개 import 목록에 포함한다.^[raw/articles/docmesh-py-core-api-reference-v0.4.0.md]

서비스별 세부 항목에는 성공 여부, 지연 시간, 마스킹된 오류 메시지가 들어간다.

- 전체 성공 여부
- 서비스별 성공 여부
- 서비스별 지연 시간
- 마스킹된 오류 메시지

## Failure model

필수 서비스가 실패하면 `HealthCheckError`가 발생한다. 비동기 lifecycle을 위해 `async_check_all_services()`도 동기·awaitable check를 함께 실행하고 per-service/overall timeout을 지원한다. 선택 서비스 실패도 aggregate `ok=False`에 반영하되, `HealthCheckError`는 필수 서비스 실패에만 발생하므로 두 운영 신호를 구분할 수 있다.^[raw/articles/docmesh-py-core-api-reference-v0.4.0.md]

- `parallel=False`에서는 입력 순서대로 순차 실행한다.
- `parallel=True`에서는 `ThreadPoolExecutor`로 병렬 실행하지만 반환 순서는 입력 순서를 유지한다.
- required 서비스가 실패하면 `HealthCheckError`를 발생시킨다.
- 오류 문자열은 `mask_sensitive_value()`를 거쳐 민감정보를 숨긴다.^[raw/articles/docmesh-py-core-api-reference-2026.md]

## Input shape

입력은 서비스명에서 check callable로 매핑되는 dict다. v0.4.0 예제는 `required_services={"postgres"}`, `parallel=True`로 실행하고 `HealthCheckError.result`에서 서비스 상태를 읽으며, finally에서 모든 client를 닫고 `ServiceCloseError.failures`를 순회한다.^[raw/articles/docmesh-py-core-examples-guide-v0.4.0.md]

FastAPI health endpoint 예시는 반환값을 `{ok, services[]}` 형태로 변환해 readiness/liveness 응답 본문으로 직접 노출하는 패턴을 보여준다. 이때 서비스별 `ok`, `latency_ms`, `error`를 그대로 전달할 수 있다.

## Related pages

- [[docmesh-py-core]]: 이 집계 API는 패키지 운영 인터페이스의 일부다.
- [[service-factory-registry]]: older registry 경로든 current direct `create_*_client()` 경로든, 최종적으로 wrapper/builder의 `check()`가 집계 입력이 된다.
- [[keycloak-authentication-api]]: Keycloak 기본 확인은 access token 발급 기반으로 동작한다.
- [[operational-logging-and-retry-utilities]]: 오류 마스킹과 구조화 로그 규칙이 헬스체크 실패 표현에 영향을 준다.

## Operational implication

fastapi-core는 현재 이 API를 `/health/readiness`에서 사용한다. 앱 팩토리는 service client 기반 check와 필수 서비스 메타데이터를 구성하고, health router는 집계 결과를 `ok`/`degraded`/`error` 상태와 HTTP `200`/`503` 응답으로 변환한다.
