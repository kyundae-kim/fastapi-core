---
title: docmesh-py-core
created: 2026-06-25
updated: 2026-07-23
type: entity
tags: [module, api, integration, implementation]
sources: [raw/articles/docmesh-py-core-api-reference-2026.md, raw/articles/docmesh-py-core-api-reference-v0.2.0.md, raw/articles/docmesh-py-core-api-reference-v0.3.0.md, raw/articles/docmesh-py-core-api-reference-v0.4.0.md, raw/articles/docmesh-py-core-api-reference-v0.5.0.md, raw/articles/docmesh-py-core-configuration-guide-2026.md, raw/articles/docmesh-py-core-configuration-guide-v0.2.0.md, raw/articles/docmesh-py-core-configuration-guide-v0.3.0.md, raw/articles/docmesh-py-core-configuration-guide-v0.4.0.md, raw/articles/docmesh-py-core-configuration-guide-v0.5.0.md, raw/articles/docmesh-py-core-examples-guide-2026.md, raw/articles/docmesh-py-core-examples-guide-v0.2.0.md, raw/articles/docmesh-py-core-examples-guide-v0.3.0.md, raw/articles/docmesh-py-core-examples-guide-v0.4.0.md, raw/articles/docmesh-py-core-examples-guide-v0.5.0.md]
confidence: medium
---

# docmesh-py-core

`docmesh-py-core`는 fastapi-core가 외부 서비스 연결, 설정 로딩, 인증, 헬스체크, 공통 운영 유틸리티를 일관된 공개 API와 환경변수 계약으로 소비할 수 있게 하는 핵심 백엔드 라이브러리다.

## What it exposes

v0.5.0 API 레퍼런스는 패키지 루트 `__all__`을 공개 계약으로 삼고, 하위 모듈의 비공개 이름을 호환성 범위 밖으로 둔다. 86개 공개 이름은 계약 테스트와 대조되며, 핵심 공개 축은 `CommonConfig`, 서비스별 `*Config`, aggregate `ServiceConfigs`, `load_service_configs`/`diagnose_services`, `RuntimePlan`, 서비스별 `create_*_client`, `assemble_services`, `assemble_service_runtime`, `ServiceBundle`, `ServiceRuntime`, `ServiceClientWrapper`, `NatsConnectionBuilder`, `KeycloakAuthService`, `KeycloakProvisioner`, health/cleanup 및 운영 helper다.^[raw/articles/docmesh-py-core-api-reference-v0.5.0.md]

`HealthCheckResult`, `ServiceHealthStatus`, `ProvisioningResult`와 structured configuration diagnosis 결과도 루트 공개 import 목록에 포함된다. 따라서 이 타입들을 하위 모듈 전용으로 취급하던 이전 문서 상태는 최신 공개 표면을 반영하지 않는다.^[raw/articles/docmesh-py-core-api-reference-v0.5.0.md]

## Recommended consumption flow

v0.5.0 API 문서는 일반 애플리케이션 lifecycle에 `RuntimePlan` + `assemble_service_runtime()` assembly-first 경로를 권장한다. 동기 CLI·배치에는 `assemble_services()`를 쓰고, direct config와 `create_*_client()`는 특정 SDK를 직접 제어할 때만 쓴다.^[raw/articles/docmesh-py-core-api-reference-v0.5.0.md]

v0.5.0 예제는 `diagnose_services()` 후 `RuntimePlan` 기반 async bootstrap을 표준 경로로 제시하고, `ServiceRuntime`이 wrapper와 engine을 context-managed 종료로 소유함을 확인한다. 동기 direct API는 NATS를 쓰지 않는 CLI·배치·단위 테스트에 한정한다.^[raw/articles/docmesh-py-core-examples-guide-v0.5.0.md]

## Main responsibilities

- 모든 config 객체와 factory는 프로세스 환경변수/검증된 config만 사용하며 mapping, 개별 연결값, 임의 SDK kwargs 주입을 허용하지 않는다. 선택 서비스 묶음은 `load_service_configs()` 또는 `load_available_service_configs()`로 로드한다.^[raw/articles/docmesh-py-core-configuration-guide-v0.5.0.md]
- startup 전에 `diagnose_services(plan=...)`로 complete/partial/invalid 상태와 production placeholder를 secret-safe하게 확인할 수 있다. startup healthcheck 자체는 환경변수가 아니라 `RuntimePlan.healthcheck`로 제어한다.^[raw/articles/docmesh-py-core-configuration-guide-v0.5.0.md]
- 서비스별 direct client factory와 동기 `ServiceBundle`·비동기 `ServiceRuntime` assembly 진입점을 제공한다.
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

v0.5.0 예시는 `RuntimePlan`으로 `ServiceRuntime`을 조립하고 async context manager가 wrapper와 engine 종료를 소유하도록 한다. NATS builder가 별도로 만든 지속 연결은 애플리케이션이 직접 `drain()`해야 한다. 따라서 fastapi-core 쪽 채택 상태는 "업스트림 최신 assembly 표면"과 "현재 저장소가 소비 중인 패키지 버전·실제 코드"를 분리해 판정해야 한다.^[raw/articles/docmesh-py-core-examples-guide-v0.5.0.md]

즉 이 엔티티 페이지는 SDK capability 자체를 설명하고, 저장소별 채택 범위 판정은 [[docmesh-py-core-vs-fastapi-core-usage-comparison]] 같은 비교 페이지에서 별도 검증하는 구조가 맞다.
