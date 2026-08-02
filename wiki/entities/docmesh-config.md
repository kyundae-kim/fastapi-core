---
title: docmesh-config
created: 2026-08-01
updated: 2026-08-02
type: entity
tags: [module, config, api, contract, security, integration, implementation]
sources: [raw/articles/docmesh-config-api-reference-v0.1.0.md, raw/articles/docmesh-config-configuration-v0.1.0.md, raw/articles/docmesh-config-examples-v0.1.0.md, raw/articles/docmesh-config-env-example-v0.1.0.md, raw/articles/docmesh-py-core-api-reference-v0.6.0.md, raw/articles/docmesh-py-core-configuration-guide-v0.6.0.md, raw/articles/docmesh-py-core-examples-guide-v0.6.0.md, raw/articles/docmesh-py-core-env-example-v0.6.0.md]
confidence: medium
---

# docmesh-config

`docmesh-config` v0.1.0은 DocMesh 서비스 통합에서 사용할 설정 모델, 선택적 로딩, 환경 진단, runtime plan 메타데이터를 제공하는 환경변수 전용 구성 라이브러리다. 공개 API는 package root의 `docmesh_config.__all__`을 기준으로 하며, 설정 객체는 생성자 인자가 아니라 프로세스 환경변수에서 값을 읽는다.^[raw/articles/docmesh-config-api-reference-v0.1.0.md]

## Scope and public surface

`CommonConfig`와 Keycloak, PostgreSQL, SQLite, MinIO, Milvus, Ollama, Langfuse, NATS의 8개 서비스 설정 모델이 문서화된 98개 canonical 환경변수를 구성한다. `ServiceConfigs`는 공통 설정과 선택적으로 로드된 서비스 설정을 묶고, `SERVICE_CONFIG_TYPES`와 `SUPPORTED_SERVICES`가 서비스 registry의 기준을 제공한다.^[raw/articles/docmesh-config-configuration-v0.1.0.md]^[raw/articles/docmesh-config-api-reference-v0.1.0.md]

핵심 함수는 `load_service_configs()`, `load_available_service_configs()`, `diagnose_services()`, `validate_service_requirements()`, `require_minio_bucket()`, `build_runtime_plan_metadata()`, `mask_sensitive_value()`, `validate_runtime_security()`다. 지정 서비스의 불완전한 환경은 조용히 건너뛰지 않고 구조화된 `ConfigError` 또는 `ConfigIssue`로 보고한다.^[raw/articles/docmesh-config-api-reference-v0.1.0.md]^[raw/articles/docmesh-config-examples-v0.1.0.md]

## Runtime-plan boundary

`RuntimePlan`은 선택 서비스, required 여부, `one_of` 대안 그룹, MinIO bucket 요구, `HealthcheckPolicy`를 immutable하게 표현한다. `HealthcheckPolicy`는 startup 확인의 timeout·retry·실패 모드 같은 정책 메타데이터일 뿐, 네트워크 연결이나 실제 health check를 실행하지 않는다.^[raw/articles/docmesh-config-api-reference-v0.1.0.md]^[raw/articles/docmesh-config-examples-v0.1.0.md]

`diagnose_services()`도 DNS, socket, 외부 API에 연결하지 않고 환경변수만 검사한다. 따라서 이 패키지는 실제 client 생성·외부 연결·health aggregation을 담당하는 런타임 계층에 선행하는 preflight 계약으로 읽어야 한다.^[raw/articles/docmesh-config-examples-v0.1.0.md]

## Security and deployment contract

설정 출력과 진단 결과는 URL userinfo, query/fragment secret, bearer/JWT, password/token/secret assignment를 마스킹한다. production에서는 Keycloak SSL, MinIO secure/certificate check, Milvus secure, Ollama SSL 검증을 비활성화할 수 없고 placeholder secret 및 example/localhost endpoint도 진단 대상이다.^[raw/articles/docmesh-config-api-reference-v0.1.0.md]^[raw/articles/docmesh-config-configuration-v0.1.0.md]^[raw/articles/docmesh-config-examples-v0.1.0.md]

`.env.example`은 추적 가능한 개발용 템플릿일 뿐 자동 로더가 아니다. 애플리케이션·container·orchestrator가 필요한 값만 프로세스 환경변수로 주입해야 하며, 실제 credential은 저장소에 커밋하지 않는다. Milvus의 canonical 입력은 `MILVUS_ENDPOINT`이고 `MILVUS_URI` compatibility alias는 없다.^[raw/articles/docmesh-config-configuration-v0.1.0.md]^[raw/articles/docmesh-config-env-example-v0.1.0.md]^[raw/articles/docmesh-config-examples-v0.1.0.md]

## v0.6.0 canonical package split

`docmesh-py-core` v0.6.0은 `docmesh_config`를 설정·plan의 canonical package로 명시하고, `docmesh_py_core` root는 client factory, container, lifecycle, health, Keycloak, error/observability helper만 공개한다. `docmesh_py_core.config`, `.settings`, `.runtime_plan`, `.factories`는 호환 facade이며 새 코드의 import 경계를 바꾸지 않는다.^[raw/articles/docmesh-py-core-api-reference-v0.6.0.md]^[raw/articles/docmesh-py-core-configuration-guide-v0.6.0.md]

v0.6.0 예제의 `service_lifespan()`과 `SERVICE_CATALOG`는 이 분리를 실제 사용 흐름으로 구체화한다. 설정은 `docmesh_config`에서 읽고, catalog는 factory/documentation metadata를 제공하며, 외부 연결과 runtime cleanup은 `docmesh_py_core`가 소유한다.^[raw/articles/docmesh-py-core-examples-guide-v0.6.0.md]^[raw/articles/docmesh-py-core-api-reference-v0.6.0.md]

## Relationships

- [[service-configuration-contracts]]: 서비스별 환경변수, 선택 로딩, production 보안 제약의 상위 계약
- [[application-integration-patterns]]: preflight 진단과 runtime assembly 사이의 수명주기 경계
- [[service-health-check-aggregation]]: 정책/환경 진단과 실제 외부 서비스 health check의 구분
- [[docmesh-py-core]]: client·runtime capability를 제공하는 인접 DocMesh 백엔드 라이브러리
- [[service-catalog-and-configuration-document-generation]]: 설정 metadata와 generated reference/template 경계
- [[docmesh-config-consumer-implementation-minimization]]: one-pass configuration snapshot, plan builder, generic access, config catalog 개선안
