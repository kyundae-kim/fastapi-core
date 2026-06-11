---
title: Database configuration patterns
created: 2026-06-11
updated: 2026-06-11
type: concept
tags: [database, repository, config, sdk, convention]
sources: [raw/articles/docmesh-py-core-config-2026-06-11.md]
confidence: medium
---
# Database configuration patterns

## Definition
이 패턴은 PostgreSQL과 SQLite를 환경변수 조합으로 선택·검증하는 방식을 다룬다. 저장소 선택 자체는 [[environment-driven-service-selection]] 에 의해 이뤄지고, 이 페이지는 그 전제가 되는 설정 규칙을 정리한다.

## PostgreSQL Rules
`POSTGRES_DSN` 이 있으면 개별 host/db/user/password 설정보다 우선한다. DSN을 사용하지 않을 때는 host, db, user, password 조합이 필요하며, `POSTGRES_PORT`, `POSTGRES_SSLMODE`, connection timeout, pool size, max overflow 로 연결 동작을 조절한다. health check 기본 계약은 `SELECT 1` 이다.

## SQLite Rules
SQLite는 로컬 개발, 단위 테스트, 경량 통합 테스트에서 PostgreSQL 대체 저장소로 사용된다. `SQLITE_PATH` 는 파일 경로 또는 `:memory:` 를 받을 수 있고, readonly, WAL, busy timeout 을 통해 동작을 조정한다. 파일 기반 모드에서는 상위 디렉터리 존재 여부까지 설정 검증 대상이 된다.

## Operational Trade-offs
PostgreSQL은 운영용 주 저장소와 connection pool 기반 서버 애플리케이션에 적합하고, SQLite는 낮은 운영 복잡도와 테스트 편의성을 제공한다. 이 차이는 [[docmesh-py-core]] 가 같은 코드 경로를 유지하면서 저장소만 환경별로 바꾸도록 설계된 이유와 맞닿아 있다.

## Security and Logging
연결 문자열 원문이나 SQLite 파일 경로를 로그/예외에 그대로 남기지 않는 것이 권장된다. 필요 시에는 [[mask-sensitive-value]] 또는 축약된 표현을 사용해야 한다.

## Related Topics
- [[environment-driven-service-selection]] 은 어떤 저장소를 활성화할지 결정한다.
- [[service-factory-registry]] 는 선택된 저장소 client를 조립한다.
- [[sdk-health-check-patterns]] 는 `SELECT 1` 기반 readiness 검증과 연결된다.
