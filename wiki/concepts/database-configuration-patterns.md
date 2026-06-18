---
title: Database configuration patterns
created: 2026-06-11
updated: 2026-06-17
type: concept
tags: [database, repository, config, sdk, convention]
sources: [raw/articles/docmesh-py-core-config-2026-06-11.md, raw/articles/fastapi-core-config-2026-06-17.md]
confidence: medium
---
# Database configuration patterns

## Definition
이 패턴은 PostgreSQL과 SQLite를 환경변수 조합으로 선택·검증하는 방식을 다룬다. 저장소 선택 자체는 [[environment-driven-service-selection]] 에 의해 이뤄지고, 이 페이지는 그 전제가 되는 설정 규칙을 정리한다.

## PostgreSQL Rules
`docmesh-py-core` 쪽에서는 `POSTGRES_DSN` 우선 규칙을 사용하지만, `fastapi-core` 는 `DB__URL` 이 있으면 이를 그대로 사용하고 그렇지 않으면 `DB__HOST`, `DB__PORT`, `DB__NAME`, `DB__USER`, `DB__PASSWORD`, `DB__AUTH_METHOD`, `DB__SSLMODE`, `DB__CONNECT_TIMEOUT` 조합으로 DSN을 만든다. `password` 와 `trust` 인증 방식에 따라 userinfo 포함 방식이 달라지며, health check 기본 계약은 `SELECT 1` 이다.

또한 `fastapi-core` 설정 문서는 SQLAlchemy 운영 파라미터를 명시적으로 노출한다. `DB__ECHO`, `DB__POOL_SIZE`, `DB__MAX_OVERFLOW`, `DB__POOL_TIMEOUT`, `DB__POOL_RECYCLE` 값이 연결 생성 동작과 테스트/운영 진단 경험에 직접 영향을 준다.

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
- [[layered-configuration-model]] 은 DB 연결 정보가 환경변수 레이어에 속함을 설명한다.
