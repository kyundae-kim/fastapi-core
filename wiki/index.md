# Wiki Index

> Content catalog. Every wiki page listed under its type with a one-line summary.
> Read this first to find relevant pages for any query.
> Last updated: 2026-06-11 | Total pages: 11

## Entities
<!-- Alphabetical within section -->
- [[docmesh-py-core]] — 서비스 설정 로드, client 생성, health check, 종료 정리를 공통화하는 DocMesh 계열 Python SDK.

## Concepts
- [[check-all-services]] — 필수/선택 서비스를 구분해 다중 health check 결과를 집계하는 API.
- [[environment-driven-service-selection]] — 환경변수 존재 여부로 PostgreSQL/SQLite 같은 서비스 구성을 선택하는 패턴.
- [[keycloak-auth-integration]] — KeycloakAuthService 기반 토큰 발급과 JWT 검증 통합 방식.
- [[keycloak-provisioner]] — realm/client/role 상태를 선언적으로 맞추는 Keycloak 관리 평면 API.
- [[load-settings-and-settings-model]] — 환경변수 검증과 최상위 Settings 객체 생성을 담당하는 초기 진입점.
- [[mask-sensitive-value]] — 로그와 오류 메시지에서 token/secret/DSN 등을 마스킹하는 보안 유틸리티.
- [[nats-connection-builder]] — NATS 연결을 즉시 생성하지 않고 async connect/check 계약을 제공하는 빌더.
- [[sdk-health-check-patterns]] — startup/readiness 에서 `check()` 와 `check_all_services()` 를 사용하는 운영 패턴.
- [[service-client-wrapper]] — 서비스별 SDK 위에 공통 ping/check/close 인터페이스를 제공하는 래퍼.
- [[service-factory-registry]] — 서비스별 client 생성과 종료 정리를 중앙화하는 핵심 조립 지점.

## Comparisons

## Queries
