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

현재 fastapi-core 저장소는 `pyproject.toml`에서 `docmesh-py-core`를 `v0.1.3`으로 고정하고 있으며, 설치된 패키지 버전도 `uv run python` 기준 `0.1.3`이다.

2026-06-29 기준 공개 루트 import는 `docmesh_py_core/__init__.py`의 `__all__`을 기준으로 한다. 핵심 설정/통합 API(`Settings`, `SqliteConfig`, `load_settings`, `ServiceFactoryRegistry`, `ServiceClientWrapper`, `NatsConnectionBuilder`, `KeycloakAuthService`, `KeycloakProvisioner`, `check_all_services`, `configure_logging`, `retry_call`, `build_service_log_event`, `mask_sensitive_value`) 외에도 `AccessTokenResult`, `ConfigError`, `ServiceClientError`, `ServiceClientWrapperError`, `UnsupportedServiceError`, `KeycloakTokenAuthenticationError`, `KeycloakTokenConfigurationError`, `KeycloakTokenError`, `KeycloakTokenTemporaryError`, `TokenValidationError`, `AuthenticatedUser` 같은 결과/오류 타입을 함께 노출한다.

## Recommended consumption flow

라이브러리 문서는 소비 애플리케이션의 기본 순서를 `환경변수 준비 → load_settings(env) → ServiceFactoryRegistry(settings) 생성 → 필요한 서비스만 create_client()로 획득 → 시작 시 check()/check_all_services() 실행 → 종료 시 close_all()`로 제시한다.

현재 fastapi-core 코드베이스는 이 흐름의 상당 부분을 실제로 채택한다.
- `fastapi_core/docmesh_settings.py`는 `load_settings()`를 감싸는 로더를 제공한다.
- `fastapi_core/factory.py`는 `ServiceFactoryRegistry(settings)`를 생성한다.
- readiness 기본 구성은 `registry.create_client(service_name).check()`를 사용한다.
- shutdown 경로에서 `registry.close_all()`을 호출한다.

다만 라이브러리 예제 문서에 있는 모든 capability가 fastapi-core의 1차 공개 API가 된 것은 아니다. 예를 들어 NATS 전용 dependency, publisher/subscriber helper, 특정 서비스의 고수준 helper는 여전히 서비스별 확장 지점으로 보는 편이 정확하다.

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

API 레퍼런스와 설정 가이드를 함께 보면 fastapi-core가 장기적으로는 서비스 접근을 registry/wrapper 패턴 위에 올리고, 인증을 Keycloak 전용 고수준 API로 분리하며, 로깅/헬스체크 오류 메시지까지 SDK 유틸리티로 통일할 수 있는 방향을 제공한다.

현재 fastapi-core에서 실제 코드로 확인되는 채택 범위는 다음과 같다.
- `fastapi_core/docmesh_settings.py`, `test_fastapi_core/conftest.py`: `Settings`, `load_settings()`
- `fastapi_core/factory.py`: `ServiceFactoryRegistry`, `configure_logging`, 서비스별 readiness check 구성, `close_all()`
- `fastapi_core/dependencies/auth.py`, `fastapi_core/routers/auth.py`: `KeycloakAuthService`, `AuthenticatedUser`, `TokenValidationError`, 각종 token error 타입
- `fastapi_core/routers/health.py`: `HealthCheckError`, `check_all_services()`, optional failure의 `degraded` 처리

반면 현재도 직접 확인되지 않은 채택 범위는 있다.
- `retry_call`의 직접 사용
- NATS builder를 1차 FastAPI dependency/API로 노출하는 경로
- Langfuse/NATS/기타 서비스별 고수준 helper를 패키지 공개 표면으로 승격하는 경로

## Observed fastapi-core usage

- 현재 확인된 공개 import 사용 항목은 `Settings`, `load_settings`, `ServiceFactoryRegistry`, `configure_logging`, `AuthenticatedUser`, `KeycloakAuthService`, `TokenValidationError`, `HealthCheckError`, `check_all_services`, token error 타입들이다.
- 현재 앱 팩토리는 `settings`, `registry`, `root_logger`, readiness state를 app state에 저장한다.
- 기본 readiness는 `enabled_services`를 기준으로 registry-backed service check를 자동 구성한다.
- `langfuse`, `nats` 같은 서비스는 settings/registry/readiness 층에서 간접 채택될 수 있지만, 현재 fastapi-core가 이들 각각에 대해 별도 FastAPI dependency를 제공하지는 않는다.
