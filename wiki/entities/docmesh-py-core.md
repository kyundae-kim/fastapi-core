---
title: docmesh-py-core
created: 2026-06-25
updated: 2026-08-02
type: entity
tags: [module, api, integration, implementation]
sources: [raw/articles/docmesh-py-core-api-reference-2026.md, raw/articles/docmesh-py-core-api-reference-v0.2.0.md, raw/articles/docmesh-py-core-api-reference-v0.3.0.md, raw/articles/docmesh-py-core-api-reference-v0.4.0.md, raw/articles/docmesh-py-core-api-reference-v0.5.0.md, raw/articles/docmesh-py-core-configuration-guide-2026.md, raw/articles/docmesh-py-core-configuration-guide-v0.2.0.md, raw/articles/docmesh-py-core-configuration-guide-v0.3.0.md, raw/articles/docmesh-py-core-configuration-guide-v0.4.0.md, raw/articles/docmesh-py-core-configuration-guide-v0.5.0.md, raw/articles/docmesh-py-core-examples-guide-2026.md, raw/articles/docmesh-py-core-examples-guide-v0.2.0.md, raw/articles/docmesh-py-core-examples-guide-v0.3.0.md, raw/articles/docmesh-py-core-examples-guide-v0.4.0.md, raw/articles/docmesh-py-core-examples-guide-v0.5.0.md, raw/articles/docmesh-config-api-reference-v0.1.0.md, raw/articles/docmesh-config-configuration-v0.1.0.md, raw/articles/docmesh-config-examples-v0.1.0.md, raw/articles/docmesh-config-env-example-v0.1.0.md, raw/articles/docmesh-py-core-api-reference-v0.6.0.md, raw/articles/docmesh-py-core-configuration-guide-v0.6.0.md, raw/articles/docmesh-py-core-examples-guide-v0.6.0.md, raw/articles/docmesh-py-core-env-example-v0.6.0.md, pyproject.toml]
confidence: medium
---

# docmesh-py-core

`docmesh-py-core`는 fastapi-core가 외부 서비스 연결, 설정 로딩, 인증, 헬스체크, 공통 운영 유틸리티를 일관된 공개 API와 환경변수 계약으로 소비할 수 있게 하는 핵심 백엔드 라이브러리다.

## What it exposes

v0.6.0 API 레퍼런스는 `docmesh_py_core.__all__`을 공개 계약으로 삼고, 하위 모듈의 비공개 이름을 호환성 범위 밖으로 둔다. 69개 공개 이름의 핵심 축은 `assemble_service_runtime`, `service_lifespan`, `assemble_services`, `create_empty_service_runtime`, `ServiceBundle`, `ServiceRuntime`, `RuntimeHealthDescriptor`, 서비스별 `create_*_client`, `NatsConnectionBuilder`, `KeycloakAuthService`, `KeycloakProvisioner`, health/cleanup, `serialize_error`, lifecycle observer, `SERVICE_CATALOG` 및 설정 문서 생성 helper다. 설정 모델·`RuntimePlan`·`Service`·`HealthcheckPolicy`는 `docmesh_config`가 소유한다.^[raw/articles/docmesh-py-core-api-reference-v0.6.0.md]

`HealthCheckResult`, `ServiceHealthStatus`, `ProvisioningResult`, `RuntimeHealthDescriptor`, `LifecycleEvent`, `SERVICE_CATALOG`와 structured error 결과가 루트 공개 import 목록에 포함된다. 반대로 `docmesh_config` 심볼을 `docmesh_py_core` root가 재노출하지 않으므로 두 package-root import 경계를 섞지 않아야 한다.^[raw/articles/docmesh-py-core-api-reference-v0.6.0.md]

## Recommended consumption flow

v0.6.0 API 문서는 설정과 plan을 `docmesh_config`에서 import하고, 일반 애플리케이션 lifecycle은 `docmesh_py_core.service_lifespan()`으로 소유하는 경로를 권장한다. 동기 CLI·배치에는 `assemble_services()`를 쓰고, direct config와 `create_*_client()`는 특정 SDK를 직접 제어할 때만 사용한다.^[raw/articles/docmesh-py-core-api-reference-v0.6.0.md]^[raw/articles/docmesh-py-core-examples-guide-v0.6.0.md]

v0.6.0 예제는 `service_lifespan(plan=...)`이 runtime을 생성·종료하도록 하고, `ServiceRuntime.check_with_policy()`로 startup 이후 상태 확인 정책을 재실행할 수 있음을 보여준다. `create_empty_service_runtime()`은 설정·factory·network를 호출하지 않는 별도 경로이며, 동기 `assemble_services()`는 NATS나 timeout startup policy를 허용하지 않는다.^[raw/articles/docmesh-py-core-examples-guide-v0.6.0.md]^[raw/articles/docmesh-py-core-api-reference-v0.6.0.md]

## Main responsibilities

- 모든 config 객체와 factory는 프로세스 환경변수/검증된 `docmesh_config` config만 사용하며 mapping, 개별 연결값, 임의 SDK kwargs 주입을 허용하지 않는다. 선택 서비스 묶음은 `load_service_configs()` 또는 `load_available_service_configs()`로 로드한다.^[raw/articles/docmesh-py-core-configuration-guide-v0.6.0.md]
- startup 전에 `diagnose_services(plan=...)`로 complete/partial/invalid 상태와 production placeholder를 secret-safe하게 확인할 수 있다. startup healthcheck 자체는 환경변수가 아니라 `RuntimePlan.healthcheck`로 제어하고, 실제 실행은 `service_lifespan()`/`ServiceRuntime.check_with_policy()`가 담당한다.^[raw/articles/docmesh-py-core-configuration-guide-v0.6.0.md]^[raw/articles/docmesh-py-core-api-reference-v0.6.0.md]
- 서비스별 direct client factory와 동기 `ServiceBundle`·비동기 `ServiceRuntime` assembly 진입점을 제공한다.
- 공통 헬스체크 집계와 오류 표준화를 지원한다.
- Keycloak 토큰 발급/검증과 프로비저닝을 담당한다.
- 마스킹, 구조화 로그, 재시도, 런타임 보안 검증 같은 운영 유틸리티를 제공한다.

## Notable sub-areas

- [[service-configuration-contracts]]: `CommonConfig`, `ServiceConfigs`, `load_service_configs()`, production 보안 제약
- [[docmesh-config]]: 별도 환경변수 전용 구성 계층과 `RuntimePlan` preflight 계약
- [[service-catalog-and-configuration-document-generation]]: catalog metadata와 deterministic 환경/설정 문서 생성
- [[service-factory-registry]]: older examples에 남아 있는 historical registry 패턴과 현재 canonical direct factory 표면의 차이
- [[service-health-check-aggregation]]: `HealthCheckResult`, `ServiceHealthStatus`, required service 실패 처리
- [[keycloak-authentication-api]]: 토큰 획득, JWT 검증, 사용자/역할 추출, 프로비저닝
- [[operational-logging-and-retry-utilities]]: 로깅 초기화, 민감정보 마스킹, 구조화 이벤트, 재시도, client close helper
- [[application-integration-patterns]]: startup/shutdown 조립, optional dependency, async 연결 수명 관리

## Integration notes for fastapi-core

v0.6.0 예시는 `RuntimePlan`으로 `ServiceRuntime`을 조립하고 `service_lifespan()`이 정상·예외 종료 모두에서 runtime cleanup을 소유하도록 한다. NATS builder가 별도로 만든 persistent connection은 애플리케이션이 직접 `drain()`해야 하며, catalog metadata와 generated reference는 client 연결을 실행하지 않는다.^[raw/articles/docmesh-py-core-examples-guide-v0.6.0.md]^[raw/articles/docmesh-py-core-api-reference-v0.6.0.md]

즉 이 엔티티 페이지는 SDK capability 자체를 설명하고, 저장소별 채택 범위 판정은 [[docmesh-py-core-vs-fastapi-core-usage-comparison]] 같은 비교 페이지에서 별도 검증하는 구조가 맞다.

소비자 구현 소스를 줄이기 위한 다음 개선 우선순위는 [[docmesh-py-core-consumer-implementation-minimization]]에서 runtime health registry, generic resource lifecycle, operation policy, auth domain helper 관점으로 별도 분석했다.

`docmesh-config` v0.1.0은 설정 모델·환경 진단·runtime-plan 메타데이터를 별도 패키지로 소유하고, `docmesh-py-core` v0.6.0은 그 검증된 설정을 받아 factory·container·lifecycle·health를 제공한다. 현재 fastapi-core의 `pyproject.toml`과 설치 환경은 두 package를 각각 v0.1.0/v0.6.0으로 pin하고 있으므로, 이전 v0.5.0 adoption 기록은 historical baseline으로 읽어야 한다.^[raw/articles/docmesh-config-api-reference-v0.1.0.md]^[raw/articles/docmesh-py-core-api-reference-v0.6.0.md]^[pyproject.toml]
