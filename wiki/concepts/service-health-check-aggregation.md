---
title: Service health check aggregation
created: 2026-06-25
updated: 2026-06-29
type: concept
tags: [service, api, observability, test, implementation]
sources: [raw/articles/docmesh-py-core-api-reference-2026.md, raw/articles/docmesh-py-core-examples-guide-2026.md]
confidence: medium
---

# Service health check aggregation

`check_all_services(service_checks, required_services=None, parallel=False)`는 여러 서비스의 헬스체크를 묶어서 실행하고 결과를 집계하는 API다.

## Reported outputs

문서상 반환 정보는 `HealthCheckResult.ok`와 `HealthCheckResult.services`를 포함한다. 서비스별 세부 항목에는 성공 여부, 지연 시간, 마스킹된 오류 메시지가 들어간다.

- 전체 성공 여부
- 서비스별 성공 여부
- 서비스별 지연 시간
- 마스킹된 오류 메시지

## Failure model

필수 서비스가 실패하면 `HealthCheckError`가 발생한다. 따라서 선택 서비스 실패와 필수 의존성 실패를 구분하는 운영 정책을 구현할 수 있다.

- `parallel=False`에서는 순차 실행 중 required 서비스 실패 시 즉시 예외를 발생시킨다.
- `parallel=True`에서는 전체 결과를 수집한 뒤 required 서비스 실패 여부를 판단한다.
- 오류 문자열은 `mask_sensitive_value()`를 거쳐 민감정보를 숨긴다.

## Input shape

입력은 서비스명에서 check callable로 매핑되는 dict이며, 예시에서는 `postgres.check`와 `minio.check`를 넘기고 `required_services={"postgres"}` 및 `parallel=True`를 함께 사용한다.

FastAPI health endpoint 예시는 반환값을 `{ok, services[]}` 형태로 변환해 readiness/liveness 응답 본문으로 직접 노출하는 패턴을 보여준다. 이때 서비스별 `ok`, `latency_ms`, `error`를 그대로 전달할 수 있다.

## Related pages

- [[docmesh-py-core]]: 이 집계 API는 패키지 운영 인터페이스의 일부다.
- [[service-factory-registry]]: registry가 생성한 wrapper의 `check()`가 대표 입력이 된다.
- [[keycloak-authentication-api]]: Keycloak 기본 확인은 access token 발급 기반으로 동작한다.

## Operational implication

fastapi-core는 이 API를 사용해 readiness/diagnostics 엔드포인트를 단일 서비스 체크의 나열이 아니라 표준 포맷의 집계 결과로 노출할 가능성이 높다.
