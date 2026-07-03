---
title: Service health check aggregation
created: 2026-06-25
updated: 2026-07-02
type: concept
tags: [service, api, observability, test, implementation]
sources: [raw/articles/docmesh-py-core-api-reference-2026.md, raw/articles/docmesh-py-core-examples-guide-2026.md]
confidence: medium
---

# Service health check aggregation

`check_all_services(service_checks, *, required_services=None, timer=time.perf_counter, parallel=False)`는 여러 서비스의 헬스체크를 묶어서 실행하고 결과를 집계하는 API다.^[raw/articles/docmesh-py-core-api-reference-2026.md]

## Reported outputs

현재 API 레퍼런스는 반환형을 `HealthCheckResult(ok: bool, services: list[ServiceHealthStatus])`로 설명한다. 다만 `HealthCheckResult`와 `ServiceHealthStatus`는 `docmesh_py_core.health` 모듈에 존재하지만 패키지 루트 `__all__`에는 포함되지 않는다.^[raw/articles/docmesh-py-core-api-reference-2026.md]

서비스별 세부 항목에는 성공 여부, 지연 시간, 마스킹된 오류 메시지가 들어간다.

- 전체 성공 여부
- 서비스별 성공 여부
- 서비스별 지연 시간
- 마스킹된 오류 메시지

## Failure model

필수 서비스가 실패하면 `HealthCheckError`가 발생한다. 따라서 선택 서비스 실패와 필수 의존성 실패를 구분하는 운영 정책을 구현할 수 있다.

- `parallel=False`에서는 입력 순서대로 순차 실행한다.
- `parallel=True`에서는 `ThreadPoolExecutor`로 병렬 실행하지만 반환 순서는 입력 순서를 유지한다.
- required 서비스가 실패하면 `HealthCheckError`를 발생시킨다.
- 오류 문자열은 `mask_sensitive_value()`를 거쳐 민감정보를 숨긴다.^[raw/articles/docmesh-py-core-api-reference-2026.md]

## Input shape

입력은 서비스명에서 check callable로 매핑되는 dict다. 최신 examples는 registry를 거치지 않고 `request.app.state.postgres`, `request.app.state.minio`, `request.app.state.ollama`에서 직접 꺼낸 client의 `check` 메서드를 넘기는 패턴을 보여준다. `required_services={"postgres", "minio"}`와 `parallel=True` 조합도 예시로 제시된다.^[raw/articles/docmesh-py-core-examples-guide-2026.md]

FastAPI health endpoint 예시는 반환값을 `{ok, services[]}` 형태로 변환해 readiness/liveness 응답 본문으로 직접 노출하는 패턴을 보여준다. 이때 서비스별 `ok`, `latency_ms`, `error`를 그대로 전달할 수 있다.

## Related pages

- [[docmesh-py-core]]: 이 집계 API는 패키지 운영 인터페이스의 일부다.
- [[service-factory-registry]]: older registry 경로든 current direct `create_*_client()` 경로든, 최종적으로 wrapper/builder의 `check()`가 집계 입력이 된다.
- [[keycloak-authentication-api]]: Keycloak 기본 확인은 access token 발급 기반으로 동작한다.
- [[operational-logging-and-retry-utilities]]: 오류 마스킹과 구조화 로그 규칙이 헬스체크 실패 표현에 영향을 준다.

## Operational implication

fastapi-core는 이 API를 사용해 readiness/diagnostics 엔드포인트를 단일 서비스 체크의 나열이 아니라 표준 포맷의 집계 결과로 노출할 가능성이 높다.
