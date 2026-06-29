---
title: docmesh-py-core
created: 2026-06-25
updated: 2026-06-29
type: entity
tags: [module, api, integration, implementation]
sources: [raw/articles/docmesh-py-core-api-reference-2026.md, raw/articles/docmesh-py-core-configuration-guide-2026.md, raw/articles/docmesh-py-core-examples-guide-2026.md]
confidence: medium
---

# docmesh-py-core

`docmesh-py-core`는 fastapi-core가 외부 서비스 연결, 설정 로딩, 인증, 헬스체크, 공통 운영 유틸리티를 일관된 공개 API와 환경변수 계약으로 소비할 수 있게 하는 핵심 백엔드 라이브러리다.

## What it exposes

2026-06-29 기준 공개 루트 import는 `docmesh_py_core/__init__.py`의 `__all__`을 기준으로 하며, 대표적으로 `Settings`, `SqliteConfig`, `load_settings`, `ServiceFactoryRegistry`, `ServiceClientWrapper`, `NatsConnectionBuilder`, `KeycloakAuthService`, `KeycloakProvisioner`, `check_all_services`, `configure_logging`, `retry_call`, `build_service_log_event`, `mask_sensitive_value`를 포함한다.

## Recommended consumption flow

문서는 소비 애플리케이션의 기본 순서를 `환경변수 준비 → load_settings(env) → ServiceFactoryRegistry(settings) 생성 → 필요한 서비스만 create_client()로 획득 → 시작 시 check()/check_all_services() 실행 → 종료 시 close_all()`로 제시한다.

이 흐름은 fastapi-core가 서비스별 클라이언트를 ad-hoc하게 직접 만들기보다 설정 로딩, 클라이언트 생성, 헬스체크, 종료 정리를 하나의 SDK 수명주기로 묶도록 유도한다.

예제 문서는 이 흐름을 FastAPI `lifespan`, health endpoint, SQLite 로컬 개발, Keycloak 토큰 발급/JWT 검증, Langfuse optional 분기, NATS async 연결, 공용 로깅 초기화까지 실제 애플리케이션 조합 예제로 확장한다.

## Main responsibilities

- 환경변수에서 전체 설정을 읽고 검증한다.
- 서비스별 클라이언트 생성 진입점을 제공한다.
- 공통 헬스체크 집계와 오류 표준화를 지원한다.
- Keycloak 토큰 발급/검증과 사용자 정보 추출을 담당한다.
- 마스킹, 직렬화, 재시도 같은 운영 유틸리티를 제공한다.

## Notable sub-areas

- [[service-factory-registry]]: 서비스별 클라이언트 생성과 수명주기 정리
- [[service-health-check-aggregation]]: 다중 서비스 체크 결과 집계와 required service 실패 처리
- [[keycloak-authentication-api]]: 토큰 획득, JWT 검증, 사용자/역할 추출
- [[service-configuration-contracts]]: 서비스별 환경변수 계약, 보안 원칙, 옵션/조건부 필수 규칙
- [[operational-logging-and-retry-utilities]]: 로깅 초기화, 민감정보 마스킹, 재시도, 구조화 이벤트 생성 유틸리티
- [[application-integration-patterns]]: FastAPI 수명주기, optional dependency 분기, async 연결 수명 관리 같은 실전 통합 패턴

## Integration notes for fastapi-core

API 레퍼런스와 설정 가이드를 함께 보면 fastapi-core가 서비스 접근을 각 서비스별 커스텀 생성 로직 대신 registry/wrapper 패턴 위에 올리고, 인증은 Keycloak 전용 고수준 API로 분리하며, 로깅/재시도/헬스체크 오류 메시지까지 SDK 공용 유틸리티로 통일하고, 배포별 환경차이는 명시적 환경변수 계약과 선택적 서비스 로딩으로 제어하는 방향을 암시한다.

## Open questions

- fastapi-core가 실제로 어떤 공개 import만 사용하고 있는지는 코드 대조가 필요하다.
- `langfuse`와 `nats`가 runtime에서 어떤 활성화 규칙을 갖는지는 별도 문서/코드 확인이 필요하다.
