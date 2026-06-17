# Wiki Index

> Content catalog. Every wiki page listed under its type with a one-line summary.
> Read this first to find relevant pages for any query.
> Last updated: 2026-06-16 | Total pages: 24

## Entities
<!-- Alphabetical within section -->
- [[docmesh-py-core]] — 서비스 설정 로드, client 생성, health check, 종료 정리를 공통화하는 DocMesh 계열 Python SDK.
- [[fastapi-core]] — DocMesh 계열 FastAPI 마이크로서비스가 공통으로 사용하는 앱 조립·외부 연동 SDK.

## Concepts
- [[check-all-services]] — 필수/선택 서비스를 구분해 다중 health check 결과를 집계하는 API.
- [[configuration-principles]] — 환경변수 중심 설정, secret 주입, 환경 분리 원칙을 정의하는 운영 규칙.
- [[database-configuration-patterns]] — PostgreSQL DSN 우선 규칙과 SQLite 테스트/로컬 설정 패턴.
- [[environment-driven-service-selection]] — 환경변수 존재 여부로 PostgreSQL/SQLite 같은 서비스 구성을 선택하는 패턴.
- [[fastapi-app-factory-and-health-routes]] — `create_app()` 조립 책임과 `/health/*` readiness 범위를 정리한 FastAPI 패턴.
- [[fastapi-app-state-singletons]] — 외부 서비스 객체를 `app.state` 에 저장·재사용하는 singleton 계약.
- [[keycloak-auth-integration]] — KeycloakAuthService 기반 토큰 발급과 JWT 검증 통합 방식.
- [[keycloak-configuration-rules]] — Keycloak 인증·grant·프로비저닝 환경변수 계약.
- [[keycloak-provisioner]] — realm/client/role 상태를 선언적으로 맞추는 Keycloak 관리 평면 API.
- [[layered-configuration-model]] — `EnvConfig` 와 `ServiceSettings` 를 분리하는 설정 계층 모델.
- [[load-settings-and-settings-model]] — 환경변수 검증과 최상위 Settings 객체 생성을 담당하는 초기 진입점.
- [[mask-sensitive-value]] — 로그와 오류 메시지에서 token/secret/DSN 등을 마스킹하는 보안 유틸리티.
- [[nats-configuration-and-auth-modes]] — NATS 서버 목록, 인증 모드, async 제약을 담은 설정 규칙.
- [[nats-connection-builder]] — NATS 연결을 즉시 생성하지 않고 async connect/check 계약을 제공하는 빌더.
- [[optional-observability-services]] — Langfuse 같은 선택적 관측성 서비스를 핵심 경로와 분리하는 원칙.
- [[sdk-health-check-patterns]] — startup/readiness 에서 `check()` 와 `check_all_services()` 를 사용하는 운영 패턴.
- [[service-client-wrapper]] — 서비스별 SDK 위에 공통 ping/check/close 인터페이스를 제공하는 래퍼.
- [[service-factory-registry]] — 서비스별 client 생성과 종료 정리를 중앙화하는 핵심 조립 지점.

## Comparisons

## Queries
- [[docmesh-py-core-refactor-review]] — docmesh-py-core 기반 리팩터링 시 유지할 축, 위험지점, 권장 순서를 정리한 검토 메모.
- [[fastapi-core-codebase-review-against-docmesh-py-core]] — 현재 fastapi-core 코드가 docmesh-py-core 철학과 어디서 어긋나는지 정리한 코드베이스 리뷰.
- [[fastapi-core-prd-alignment-review]] — PRD 기준 제품 책임과 현재 구현/registry 방향의 정렬 상태를 정리한 검토 메모.
- [[fastapi-core-prd-vs-source-code-comparison]] — PRD의 요구사항과 현재 소스코드 구현 범위를 기능별로 대조한 비교 메모.
- [[registry-full-replacement-plan]] — registry가 완전 대체 가능한 서비스 범위와 남겨야 할 native 경계를 정리한 리팩터링 실행안.
