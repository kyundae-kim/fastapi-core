---
title: Service configuration contracts
created: 2026-06-25
updated: 2026-06-29
type: concept
tags: [config, contract, integration, implementation, security]
sources: [raw/articles/docmesh-py-core-api-reference-2026.md, raw/articles/docmesh-py-core-configuration-guide-2026.md, raw/articles/docmesh-py-core-examples-guide-2026.md]
confidence: medium
---

# Service configuration contracts

`docmesh-py-core`의 설정 계약은 모든 런타임 구성을 환경변수로 표현하고, `load_settings(env, *, services=None)`가 선택된 서비스 집합에 대해서만 설정을 검증·구성할 수 있게 하는 방식으로 정리된다.

## Global rules

- 공통 식별자는 `DOCMESH_ENV`와 `DOCMESH_HEALTHCHECK_ENABLED`다.
- 공용 로깅 기본 레벨은 `DOCMESH_LOG_LEVEL`로 제어할 수 있고, 명시 설정이 없으면 `INFO`를 사용한다.
- 민감정보는 secret manager 또는 배포 플랫폼 secret 기능으로 주입하는 것이 권장된다.
- 운영 환경에서는 TLS 검증을 기본 활성화 상태로 유지해야 한다.
- timeout/retry는 전역 공통값이 아니라 서비스별 환경변수로 관리된다.
- `LANGFUSE_ENVIRONMENT`가 비어 있으면 `DOCMESH_ENV` 값을 상속한다.

## Loader behavior

- `services=None`이면 지원 서비스 전체를 검증한다.
- `services={...}`를 주면 지정한 서비스만 로드하고 나머지 상위 설정 필드는 `None`으로 둔다.
- 선택적 설정(`postgres`, `sqlite`)은 선택된 경우에도 관련 env가 없으면 `None`일 수 있다.
- 검증 실패는 `ConfigError`로 통일되며, 필수값 누락, bool/정수 파싱 실패, 범위 위반, 상호배타 조건 실패를 포함한다.

## Service-specific contracts

- Keycloak: 기본 인증/JWT 검증 변수와 별도 토큰 획득 변수, 프로비저닝 변수를 분리한다. `password` grant 사용자명/비밀번호는 설정에 고정하기보다 실제 `fetch_access_token(username=..., password=...)` 호출 인자로 넘기는 방식을 권장한다.
- PostgreSQL: `POSTGRES_DSN`이 있으면 host/db/user/password 개별 필드보다 우선한다.
- SQLite: 로컬 개발과 테스트에 적합하며 `SQLITE_PATH`, readonly, WAL, busy timeout을 노출한다.
- MinIO / Milvus / Ollama / Langfuse / NATS: 각 서비스마다 별도 timeout/retry와 연결 파라미터를 가진다. 특히 Langfuse는 `LANGFUSE_ENABLED=true`일 때만 host/public/secret key가 필수이고, NATS는 user/password · token · creds file 중 하나의 인증 모드만 허용한다.

## Minimum activation sets

- Keycloak 기본 인증: `KEYCLOAK_URL`, `KEYCLOAK_REALM`, `KEYCLOAK_CLIENT_ID`, 그리고 기본 confidential client 전제에서는 `KEYCLOAK_CLIENT_SECRET`이 필요하다.
- PostgreSQL: `POSTGRES_DSN` 단일 방식 또는 `POSTGRES_HOST`/`POSTGRES_DB`/`POSTGRES_USER`/`POSTGRES_PASSWORD` 조합 중 하나를 선택한다.
- SQLite: 최소 `SQLITE_PATH`가 필요하다.
- Langfuse 비활성화: `LANGFUSE_ENABLED=false`만으로 host/key 계열 요구사항을 제거할 수 있다.
- NATS: `NATS_SERVERS`와 함께 user/password, token, creds file 중 하나만 선택해야 한다.
- 예제 기준 로컬 경량 개발 구성은 `SQLITE_PATH`, `LANGFUSE_ENABLED=false`, `NATS_SERVERS=nats://localhost:4222` 같은 조합으로 표현된다.

## Failure patterns and enforcement

- 빈 문자열도 미설정으로 취급되므로 export는 되었지만 값이 비어 있는 경우에도 `ConfigError`가 발생할 수 있다.
- Keycloak public client가 아니라면 `KEYCLOAK_CLIENT_SECRET` 누락이 대표적 실패 원인이다.
- Keycloak provisioning은 service account 방식과 username/password 방식을 동시에 주거나 둘 다 주지 않으면 실패한다.
- production/prod 환경에서는 `KEYCLOAK_VERIFY_SSL=false`, `MINIO_SECURE=false`, `MILVUS_SECURE=false` 같은 비보안 설정이 허용되지 않는다.

## Operational significance

이 계약은 fastapi-core가 서비스 통합을 단순히 클라이언트 생성 API에만 의존하지 않고, 배포 환경별 설정 표면까지 명시적으로 관리해야 함을 보여준다. 특히 선택 기능(`LANGFUSE_ENABLED`), 인증 방식 선택(NATS), DSN 우선순위(PostgreSQL), 프로비저닝 활성화(Keycloak) 같은 분기점은 애플리케이션 설정 로더와 운영 문서에 그대로 반영될 가능성이 높다.

## Related pages

- [[docmesh-py-core]]: 이 설정 계약은 패키지의 핵심 운영 인터페이스다.
- [[service-factory-registry]]: 설정 계약은 registry가 생성할 서비스 클라이언트의 입력이 된다.
- [[keycloak-authentication-api]]: Keycloak 관련 환경변수와 운영 보안 원칙은 별도 중요도를 가진다.
- [[operational-logging-and-retry-utilities]]: 로그 레벨 초기화와 민감정보 마스킹도 동일한 운영 계약의 일부다.

## Security notes

- secret, token, 전체 DSN/URI는 로그에 원문 그대로 남기지 않아야 한다.
- 운영에서 TLS 검증 비활성화를 기본값으로 두지 않는 것이 권장된다.
- Keycloak 프로비저닝은 최소 권한 service account 사용이 권장된다.
