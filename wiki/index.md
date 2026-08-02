# Wiki Index

> Content catalog. Every wiki page listed under its type with a one-line summary.
> Read this first to find relevant pages for any query.
> Last updated: 2026-08-02 | Total pages: 13

## Entities
<!-- Alphabetical within section -->

- [[docmesh-config]] - 환경변수 전용 설정 모델, 선택 로딩, 서비스 진단, runtime-plan 메타데이터를 제공하는 구성 라이브러리.
- [[docmesh-py-core]] - 외부 서비스 연동, 설정, 인증, 헬스체크 유틸리티를 묶는 핵심 백엔드 라이브러리.

## Concepts

- [[application-integration-patterns]] - assembly-first 수명주기와 RuntimePlan 기반 async 통합, direct API의 제한적 사용을 정리.
- [[keycloak-authentication-api]] - Keycloak 토큰 발급, JWT 검증, 프로비저닝, 재시도/로깅 규칙을 포함한 인증 API 정리.
- [[operational-logging-and-retry-utilities]] - 로깅 초기화, 민감정보 마스킹, 구조화 이벤트, 재시도, client close helper를 묶는 운영 유틸리티.
- [[service-catalog-and-configuration-document-generation]] - SERVICE_CATALOG metadata와 deterministic 환경 템플릿·설정 reference 생성 계약을 정리.
- [[service-configuration-contracts]] - CommonConfig/ServiceConfigs, 선택 로딩, production 보안 제약을 포함한 환경설정 계약.
- [[service-factory-registry]] - older examples의 registry 패턴과 최신 assembly-first 공개 표면 사이 차이를 정리한 페이지.
- [[service-health-check-aggregation]] - 다중 서비스 체크를 집계하고 required service 실패를 표준 결과/예외로 구분하는 health API.

## Comparisons

## Queries

- [[docmesh-config-consumer-implementation-minimization]] - 환경변수·plan·preflight·설정 catalog 중복을 줄이기 위한 docmesh-config 개선 우선순위.
- [[docmesh-py-core-consumer-implementation-minimization]] - FastAPI 소비자 구현 소스를 줄이기 위한 health registry, generic resource lifecycle, operation policy, auth/NATS 개선 우선순위.
- [[docmesh-py-core-vs-fastapi-core-usage-comparison]] - docmesh-py-core v0.2.0과 대조해 P0~P2 async lifecycle, assembly, timeout, 대안 서비스, rollback 반영을 정리한 비교.
- [[fastapi-core-prd-vs-source-code-comparison]] - PRD v0.4 capability를 현재 소스·테스트와 대조하고 P0~P2 정렬 상태와 제품별 잔여 과제를 정리한 비교.
