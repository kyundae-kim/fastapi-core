---
title: check_all_services
created: 2026-06-11
updated: 2026-06-11
type: concept
tags: [observability, testing, api, integration, convention]
sources: [raw/articles/docmesh-py-core-sdk-2026-06-11.md, raw/articles/docmesh-py-core-api-2026-06-11.md]
confidence: medium
---
# check_all_services

## Definition
`check_all_services(service_checks, required_services=None)` 는 여러 서비스의 health check 함수를 한 번에 실행하고, 서비스별 성공 여부·지연 시간·오류를 집계하는 API다. 필수 서비스가 실패하면 `HealthCheckError` 를 발생시킨다.

## Result Model
결과 객체는 전체 성공 여부를 나타내는 `ok` 와 서비스별 상태 목록인 `services` 를 제공한다. 실패 예외는 `service` 와 마스킹된 `error` 정보를 포함하므로 운영 화면이나 readiness endpoint 에서 안전하게 노출하기 좋다. 민감정보 처리 측면에서는 [[mask-sensitive-value]] 와 철학이 맞닿아 있다.

## Recommended Usage
문서 예시는 PostgreSQL을 required 로 두고 MinIO를 optional 로 분리한다. 이 구조는 [[sdk-health-check-patterns]] 가 말하는 핵심/선택 서비스 구분을 구체적인 API 형태로 구현한 것이다. 일반적으로 각 check 함수는 [[service-client-wrapper]] 의 `check()` 메서드에서 오며, NATS 같이 async 계약이 필요한 경우는 별도 전략이 필요하다.

## Why It Matters
startup/readiness 설계에서 전체 시스템을 하나의 pass/fail 로만 보지 않고, 필수성과 관찰성을 분리할 수 있다. 이는 [[docmesh-py-core]] 를 사용하는 서비스가 운영 안정성과 장애 격리 수준을 세밀하게 조정할 수 있게 한다.

## Related Topics
- [[sdk-health-check-patterns]] 의 집계 API 구현체다.
- [[service-client-wrapper]] 의 공통 check 계약을 활용한다.
- [[docmesh-py-core]] 의 readiness 설계 원칙을 드러낸다.
