---
title: Environment-driven service selection
created: 2026-06-11
updated: 2026-06-11
type: concept
tags: [sdk, config, repository, database, convention]
sources: [raw/articles/docmesh-py-core-sdk-2026-06-11.md, raw/articles/docmesh-py-core-config-2026-06-11.md]
confidence: medium
---
# Environment-driven service selection

## Definition
이 패턴은 별도 backend selector를 두기보다, 실제 서비스 환경변수가 존재하는지에 따라 어떤 저장소나 외부 연결을 활성화할지 결정하는 방식이다. 문서에서는 PostgreSQL과 SQLite를 대표 예시로 사용한다.

## Recommended Pattern
소비 프로젝트는 먼저 `load_settings()`로 환경변수를 검증하고, 이후 설정 객체에서 어떤 서비스 설정이 채워졌는지를 기준으로 `ServiceFactoryRegistry` 에서 client를 선택 생성한다. 예를 들어 `settings.sqlite is not None` 이면 SQLite를, 그렇지 않고 `settings.postgres is not None` 이면 PostgreSQL을 선택하는 흐름이 권장된다.

이 접근은 [[docmesh-py-core]] 의 재사용성을 높이며, 로컬/테스트에서는 SQLite, 운영에서는 PostgreSQL을 쓰는 식의 전환을 단순하게 만든다. 실제 client 조립은 [[service-factory-registry]] 가 담당하고, startup 검증은 [[sdk-health-check-patterns]] 와 결합된다.

## Operational Notes
SQLite는 `SQLITE_PATH=:memory:` 같은 설정으로 테스트 환경에서 매우 가볍게 사용할 수 있으며, `SQLITE_ENABLE_WAL`, `SQLITE_BUSY_TIMEOUT_MS` 로 동작을 조정할 수 있다. PostgreSQL은 `POSTGRES_DSN` 이 있으면 개별 host/user/password 보다 우선한다. 이 상세 규칙은 [[database-configuration-patterns]] 에 정리되어 있다.

## Trade-offs
장점은 설정과 코드 경로가 자연스럽게 정렬된다는 점이다. 단점은 어떤 서비스가 활성화되는지 코드보다 환경에 더 많이 의존하므로, 배포 설정 관리와 검증 메시지가 중요해진다는 점이다.

## Related Topics
- [[docmesh-py-core]] 는 이 패턴을 기본 소비 모델로 제시한다.
- [[configuration-principles]] 는 환경변수 중심 운영 철학을 제공한다.
- [[database-configuration-patterns]] 는 PostgreSQL/SQLite 설정 규칙을 구체화한다.
- [[service-factory-registry]] 는 이 결정 결과를 실제 client 생성으로 연결한다.
- [[sdk-health-check-patterns]] 는 선택된 서비스들의 readiness 판단을 담당한다.
