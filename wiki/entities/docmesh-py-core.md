---
title: docmesh-py-core
created: 2026-06-11
updated: 2026-06-11
type: entity
tags: [sdk, fastapi, architecture, integration, config]
sources: [raw/articles/docmesh-py-core-sdk-2026-06-11.md, raw/articles/docmesh-py-core-api-2026-06-11.md]
confidence: medium
---
# docmesh-py-core

## Overview
`docmesh-py-core`는 DocMesh 계열 Python 서비스에서 반복되는 초기화·설정·연결 검증 코드를 공통화하는 SDK다. 소비 프로젝트는 환경변수 로드, 서비스 client 생성, health check, 종료 정리를 공통 흐름으로 적용할 수 있다.

핵심 진입 흐름은 `load_settings()` → `ServiceFactoryRegistry(settings)` → `create_client()` → `check()` → `close_all()` 순서다. 이 구조는 애플리케이션 코드가 서비스별 초기화 세부사항에 과도하게 결합되지 않도록 돕는다.

## Responsibilities
- 환경변수 기반 설정 로드와 검증 제공
- 외부 서비스 client 생성 책임의 중앙화
- 서비스별 health check 통합
- Keycloak 토큰 발급과 JWT 검증 지원
- Keycloak realm/client/role 프로비저닝 지원
- 민감정보 마스킹 유틸리티 제공
- 종료 시점의 공통 자원 정리 지원

## Supported Integration Pattern
문서상 대표 통합 대상은 PostgreSQL, SQLite, MinIO, Milvus, Ollama, Langfuse, NATS, Keycloak이다. 이들 통합은 [[service-factory-registry]] 를 중심으로 조립되며, 저장소 선택은 [[environment-driven-service-selection]] 패턴을 따른다.

FastAPI lifespan, 배치/CLI 진입점, startup readiness 검증은 [[sdk-health-check-patterns]] 및 [[check-all-services]] 와 밀접하게 연결된다. 인증 관련 사용 사례는 [[keycloak-auth-integration]] 에, 프로비저닝은 [[keycloak-provisioner]] 에 별도로 정리한다.

## Design Notes
이 SDK는 명시적인 backend selector보다 실제 환경변수 존재 여부를 통해 서비스 구성을 결정하는 접근을 선호한다. 따라서 소비 프로젝트는 같은 코드 경로를 유지하면서 로컬에서는 SQLite, 운영에서는 PostgreSQL 같은 구성을 유연하게 전환할 수 있다.

공개 API 관점에서는 [[load-settings-and-settings-model]] 이 초기 진입점을 제공하고, 서비스별 통합은 [[service-client-wrapper]] 와 [[nats-connection-builder]] 같은 서로 다른 반환 계약 위에 노출된다. 운영 안전성 측면에서는 [[mask-sensitive-value]] 같은 보안 유틸리티도 SDK 표면의 중요한 일부다.

## Open Questions
- LLM provider abstraction 이 이 SDK의 직접 범위에 포함되는지, 아니면 별도 패키지 계층으로 분리되는지 추가 문서가 필요하다.
- 외부 서비스별 에러 모델과 retry 정책이 어느 수준까지 공통화되어 있는지는 후속 문서 확인이 필요하다.
