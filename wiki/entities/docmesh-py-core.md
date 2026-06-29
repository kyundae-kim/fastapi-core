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

다만 현재 fastapi-core 코드베이스는 이 전체 흐름을 채택하지 않는다. 실제 앱은 `Settings`를 app state에 저장하고, 인증에서는 `KeycloakAuthService`, readiness에서는 `check_all_services()`를 직접 사용하지만 `ServiceFactoryRegistry`, `ServiceClientWrapper`, `NatsConnectionBuilder`, `close_all()` 호출은 확인되지 않았다.

예제 문서는 이 권장 흐름을 FastAPI `lifespan`, health endpoint, SQLite 로컬 개발, Keycloak 토큰 발급/JWT 검증, Langfuse optional 분기, NATS async 연결, 공용 로깅 초기화까지 확장하지만, 이는 라이브러리 capability 설명으로 보는 편이 현재 fastapi-core의 실제 채택 상태보다 정확하다.

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

API 레퍼런스와 설정 가이드를 함께 보면 fastapi-core가 장기적으로는 서비스 접근을 registry/wrapper 패턴 위에 올리고, 인증을 Keycloak 전용 고수준 API로 분리하며, 로깅/재시도/헬스체크 오류 메시지까지 SDK 유틸리티로 통일할 수 있는 방향을 제공한다.

하지만 현재 fastapi-core에서 실제 코드로 확인되는 채택 범위는 더 좁다. `fastapi_core/config.py`와 `test_fastapi_core/conftest.py`는 `Settings`/`load_settings()`를 사용하고, `fastapi_core/dependencies/auth.py`는 `KeycloakAuthService`·`TokenValidationError`·`AuthenticatedUser`를 사용하며, `fastapi_core/routers/health.py`는 `HealthCheckError`·`check_all_services()`를 사용한다. 반면 registry/wrapper, NATS builder, 공용 로깅/재시도 유틸리티의 직접 사용은 현재 저장소에서 확인되지 않았다.

## Observed fastapi-core usage

- 현재 확인된 공개 import 사용 항목은 `Settings`, `load_settings`, `AuthenticatedUser`, `KeycloakAuthService`, `TokenValidationError`, `HealthCheckError`, `check_all_services`다.
- 현재 앱 팩토리는 `Settings`를 app state에 저장하지만 `ServiceFactoryRegistry`를 생성하지 않는다.
- 현재 코드 기준으로 `langfuse`와 `nats`는 설정 기본값에는 포함되지만, fastapi-core 내부에서 해당 클라이언트를 실제 생성/주입하는 경로는 확인되지 않았다.
