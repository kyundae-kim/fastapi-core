---
title: FastAPI app factory and health routes
created: 2026-06-16
updated: 2026-06-16
type: concept
tags: [fastapi, architecture, api, observability, sdk]
sources: [raw/articles/fastapi-core-prd-2026-06-16.md]
confidence: medium
---
# FastAPI app factory and health routes

## Definition
이 개념은 `fastapi-core` 가 제공해야 하는 앱 조립 엔트리포인트와 내장 health route 계약을 설명한다. PRD 기준 핵심은 로깅, CORS, lifespan, 라우터 등록을 수행하는 `create_app()` 팩토리 함수와 `/health/liveness`, `/health/readiness` 엔드포인트 제공이다.

## App Assembly Responsibilities
`create_app()` 는 단순 FastAPI 생성 헬퍼가 아니라 공통 서비스 구성을 조립하는 표준 진입점이다. 로깅 초기화, CORS 정책 적용, lifespan 연결, 재사용 가능한 라우터 등록을 한곳에서 처리함으로써, 개별 마이크로서비스가 같은 부트스트랩 패턴을 따르게 한다. 이 점은 [[fastapi-core]] 의 제품 목표와 [[layered-configuration-model]] 의 설정 주입 모델을 연결한다.

## Health Scope
PRD는 readiness가 Keycloak뿐 아니라 PostgreSQL, MinIO, Langfuse(선택적) 상태까지 포함한 종합 준비 상태를 제공해야 한다고 명시한다. 따라서 health는 단순 프로세스 생존 확인이 아니라 외부 의존성 가용성을 점검하는 운영 API이며, 이 부분은 [[sdk-health-check-patterns]] 및 [[optional-observability-services]] 와 직접 연결된다.

## Design Tension
PRD는 startup 시 생성한 singleton을 health와 dependency 에서 재사용하는 방향을 제시하지만, 실제 구현에서는 fallback lazy init 도 허용한다. 그래서 readiness가 startup-built resource를 기준으로 동작할지, request-time 생성 경로까지 허용할지는 중요한 설계 지점이 된다. 이 긴장은 [[fastapi-app-state-singletons]] 과 [[fastapi-core-codebase-review-against-docmesh-py-core]] 에서 더 자세히 드러난다.

## Related Topics
- [[fastapi-core]] 는 이 조립 흐름을 외부에 제공하는 SDK다.
- [[fastapi-app-state-singletons]] 은 app.state 기반 자원 재사용 규칙을 설명한다.
- [[sdk-health-check-patterns]] 은 readiness가 어떤 서비스 계약을 확인해야 하는지 설명한다.
- [[optional-observability-services]] 은 Langfuse 같은 선택 서비스의 health 의미를 정리한다.
- [[service-factory-registry]] 는 장기적으로 앱 조립이 수렴할 수 있는 서비스 중앙화 방향을 보여준다.
