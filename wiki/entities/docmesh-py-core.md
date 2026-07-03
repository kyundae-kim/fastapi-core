---
title: docmesh-py-core
created: 2026-06-25
updated: 2026-07-02
type: entity
tags: [module, api, integration, implementation]
sources: [raw/articles/docmesh-py-core-api-reference-2026.md, raw/articles/docmesh-py-core-configuration-guide-2026.md, raw/articles/docmesh-py-core-examples-guide-2026.md]
confidence: medium
---

# docmesh-py-core

`docmesh-py-core`는 fastapi-core가 외부 서비스 연결, 설정 로딩, 인증, 헬스체크, 공통 운영 유틸리티를 일관된 공개 API와 환경변수 계약으로 소비할 수 있게 하는 핵심 백엔드 라이브러리다.

## What it exposes

2026-07-02 기준 API 레퍼런스는 패키지 루트 `__all__`이 이전의 aggregate `Settings` / `ServiceFactoryRegistry` 중심 표면보다 더 직접적인 config + client factory 표면으로 재정리됐다고 설명한다. 핵심 공개 축은 `CommonConfig`, `KeycloakConfig`, `PostgresConfig`, `SqliteConfig`, `MinioConfig`, `MilvusConfig`, `OllamaConfig`, `LangfuseConfig`, `NatsConfig`, aggregate `ServiceConfigs`, `load_service_configs`, 서비스별 `create_*_client`, `ServiceClientWrapper`, `NatsConnectionBuilder`, `KeycloakAuthService`, `KeycloakProvisioner`, `check_all_services`, `close_service_clients`, `configure_logging`, `retry_call`, `build_service_log_event`, `mask_sensitive_value`, `validate_runtime_security`다.^[raw/articles/docmesh-py-core-api-reference-2026.md]

동시에 일부 타입은 루트에서 재-export되지 않는다고 명시한다. `HealthCheckResult`, `ServiceHealthStatus`는 `docmesh_py_core.health`에, `ProvisioningResult`는 `docmesh_py_core.keycloak`에 존재하지만 루트 import 목록에는 없다.^[raw/articles/docmesh-py-core-api-reference-2026.md]

## Recommended consumption flow

현재 API 레퍼런스와 examples 문서는 모두 direct factory 중심 흐름으로 수렴한다. 기본 흐름은 `환경변수 준비 → CommonConfig() 또는 load_service_configs() → 필요한 서비스만 create_*_client()로 조립 → 시작 시 check()/check_all_services() → 종료 시 close_service_clients() 또는 개별 close()`다.^[raw/articles/docmesh-py-core-api-reference-2026.md]^[raw/articles/docmesh-py-core-examples-guide-2026.md]

이전 위키에서 과도기 신호로 보았던 registry 중심 examples는 최신 examples 문서에서 사실상 사라졌다. 따라서 현재 위키는 이 SDK를 "registry 중심 소비 예시에서 direct factory 중심 공개 API로 이동 중"이라기보다, 이미 direct config/direct client factory를 canonical integration path로 문서화한 SDK로 읽는 편이 더 정확하다.^[raw/articles/docmesh-py-core-examples-guide-2026.md]

## Main responsibilities

- 환경변수 기반 config 객체를 직접 생성하거나 선택 서비스 묶음으로 로드한다.
- 서비스별 클라이언트 생성 진입점을 제공한다.
- 공통 헬스체크 집계와 오류 표준화를 지원한다.
- Keycloak 토큰 발급/검증과 프로비저닝을 담당한다.
- 마스킹, 구조화 로그, 재시도, 런타임 보안 검증 같은 운영 유틸리티를 제공한다.

## Notable sub-areas

- [[service-configuration-contracts]]: `CommonConfig`, `ServiceConfigs`, `load_service_configs()`, production 보안 제약
- [[service-factory-registry]]: older examples에 남아 있는 historical registry 패턴과 현재 canonical direct factory 표면의 차이
- [[service-health-check-aggregation]]: `HealthCheckResult`, `ServiceHealthStatus`, required service 실패 처리
- [[keycloak-authentication-api]]: 토큰 획득, JWT 검증, 사용자/역할 추출, 프로비저닝
- [[operational-logging-and-retry-utilities]]: 로깅 초기화, 민감정보 마스킹, 구조화 이벤트, 재시도, client close helper
- [[application-integration-patterns]]: startup/shutdown 조립, optional dependency, async 연결 수명 관리

## Integration notes for fastapi-core

현재 업스트림 문서는 서비스별 config class와 `create_*_client()` 조합을 우선 public 경로로 문서화하고, 최신 examples도 같은 방향으로 정렬됐다. 따라서 fastapi-core 쪽 채택 상태를 해석할 때는 이제 "업스트림 최신 공개 표면"과 "현재 저장소가 소비 중인 패키지 버전/실제 코드"의 차이를 더 명확히 분리해서 읽어야 한다.

즉 이 엔티티 페이지는 SDK capability 자체를 설명하고, 저장소별 채택 범위 판정은 [[docmesh-py-core-vs-fastapi-core-usage-comparison]] 같은 비교 페이지에서 별도 검증하는 구조가 맞다.
