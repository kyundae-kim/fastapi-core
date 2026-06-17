---
title: FastAPI app factory and health routes
created: 2026-06-16
updated: 2026-06-17
type: concept
tags: [fastapi, architecture, api, observability, sdk]
sources: [raw/articles/fastapi-core-prd-2026-06-16.md]
confidence: medium
---
# FastAPI app factory and health routes

## Definition
이 개념은 `fastapi-core` 가 제공해야 하는 앱 조립 엔트리포인트와 내장 health route 계약을 설명한다. 2026-06-17 PRD 기준 핵심은 `create_app()` 이 `CORSMiddleware`, `AuthError` 핸들러, `/health/liveness`, `/health/readiness`, 선택적 `/token`·`/user` 라우터, 그리고 기본 managed lifespan 까지 하나의 표준 진입점으로 묶는다는 점이다.

## App Assembly Responsibilities
`create_app()` 는 단순 FastAPI 생성 헬퍼가 아니라 공통 서비스 구성을 조립하는 표준 엔트리포인트다. 설정 로드, lifecycle 연결, 재사용 가능한 라우터 등록을 한곳에서 처리함으로써 개별 마이크로서비스가 같은 부트스트랩 패턴을 따르게 한다. 이 점은 [[fastapi-core]] 의 제품 목표와 [[layered-configuration-model]] 의 설정 주입 모델을 연결한다.

또한 PRD는 기본 lifespan 이 `create_managed_lifespan(config, settings)` 를 사용한다고 명시해, 앱 조립과 리소스 소유권이 더 긴밀하게 결합됐음을 보여준다. 이 부분은 [[fastapi-app-state-singletons]] 및 [[registry-backed-dependency-resolution]] 과 함께 읽어야 한다.

## Health Scope
PRD는 readiness가 Keycloak뿐 아니라 PostgreSQL, MinIO, Langfuse(옵션) 상태를 포함한 종합 준비 상태를 제공해야 한다고 명시한다. 따라서 health는 단순 프로세스 생존 확인이 아니라 외부 의존성 가용성과 lifecycle 준비 상태를 점검하는 운영 API다. 이 부분은 [[sdk-health-check-patterns]] 및 [[optional-observability-services]] 와 직접 연결된다.

## Related Topics
- [[fastapi-core]] 는 이 조립 흐름을 외부에 제공하는 SDK다.
- [[fastapi-app-state-singletons]] 은 app.state 기반 자원 재사용 규칙을 설명한다.
- [[sdk-health-check-patterns]] 은 readiness가 어떤 서비스 계약을 확인해야 하는지 설명한다.
- [[optional-observability-services]] 은 Langfuse 같은 선택 서비스의 health 의미를 정리한다.
- [[curated-public-api-surface]] 는 `create_app()` 이 루트 공개 API에서 어떤 위치를 갖는지 설명한다.
- [[registry-backed-dependency-resolution]] 은 lifespan 아래에서 주요 dependency 가 어떤 해석 경로를 따르는지 보여준다.
