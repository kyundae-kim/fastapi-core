---
title: Service configuration contracts
created: 2026-06-25
updated: 2026-06-25
type: concept
tags: [config, contract, integration, implementation, security]
sources: [raw/articles/docmesh-py-core-configuration-guide-2026.md]
confidence: medium
---

# Service configuration contracts

`docmesh-py-core`의 설정 계약은 모든 런타임 구성을 환경변수로 표현하고, 빈 문자열을 미설정으로 취급하며, Boolean/숫자 타입과 범위를 검증하는 방식으로 정리된다.

## Global rules

- 공통 식별자는 `DOCMESH_ENV`와 `DOCMESH_HEALTHCHECK_ENABLED`다.
- 민감정보는 secret manager 또는 배포 플랫폼 secret 기능으로 주입하는 것이 권장된다.
- 운영 환경에서는 TLS 검증을 기본 활성화 상태로 유지해야 한다.
- timeout/retry는 전역 공통값이 아니라 서비스별 환경변수로 관리된다.

## Service-specific contracts

- Keycloak: 기본 인증/JWT 검증 변수와 별도 토큰 획득 변수, 프로비저닝 변수를 분리한다.
- PostgreSQL: `POSTGRES_DSN`이 있으면 host/db/user/password 개별 필드보다 우선한다.
- SQLite: 로컬 개발과 테스트에 적합하며 `SQLITE_PATH`, readonly, WAL, busy timeout을 노출한다.
- MinIO / Milvus / Ollama / Langfuse / NATS: 각 서비스마다 별도 timeout/retry와 연결 파라미터를 가진다.

## Operational significance

이 계약은 fastapi-core가 서비스 통합을 단순히 클라이언트 생성 API에만 의존하지 않고, 배포 환경별 설정 표면까지 명시적으로 관리해야 함을 보여준다. 특히 선택 기능(`LANGFUSE_ENABLED`), 인증 방식 선택(NATS), DSN 우선순위(PostgreSQL), 프로비저닝 활성화(Keycloak) 같은 분기점은 애플리케이션 설정 로더와 운영 문서에 그대로 반영될 가능성이 높다.

## Related pages

- [[docmesh-py-core]]: 이 설정 계약은 패키지의 핵심 운영 인터페이스다.
- [[service-factory-registry]]: 설정 계약은 registry가 생성할 서비스 클라이언트의 입력이 된다.
- [[keycloak-authentication-api]]: Keycloak 관련 환경변수와 운영 보안 원칙은 별도 중요도를 가진다.

## Security notes

- secret, token, 전체 DSN/URI는 로그에 원문 그대로 남기지 않아야 한다.
- 운영에서 TLS 검증 비활성화를 기본값으로 두지 않는 것이 권장된다.
- Keycloak 프로비저닝은 최소 권한 service account 사용이 권장된다.
