---
title: Service configuration contracts
created: 2026-06-25
updated: 2026-07-19
type: concept
tags: [config, contract, integration, implementation, security]
sources: [raw/articles/docmesh-py-core-api-reference-2026.md, raw/articles/docmesh-py-core-api-reference-v0.2.0.md, raw/articles/docmesh-py-core-api-reference-v0.3.0.md, raw/articles/docmesh-py-core-api-reference-v0.4.0.md, raw/articles/docmesh-py-core-configuration-guide-2026.md, raw/articles/docmesh-py-core-configuration-guide-v0.2.0.md, raw/articles/docmesh-py-core-configuration-guide-v0.3.0.md, raw/articles/docmesh-py-core-configuration-guide-v0.4.0.md, raw/articles/docmesh-py-core-env-example-v0.3.0.md, raw/articles/docmesh-py-core-examples-guide-2026.md, raw/articles/docmesh-py-core-examples-guide-v0.3.0.md]
confidence: medium
---

# Service configuration contracts

`docmesh-py-core`의 현재 설정 표면은 일반 lifecycle의 assembly-first 경로와 direct-api-when-needed 경로를 함께 제공한다. 모든 `*Config`와 선택 loader는 프로세스 환경변수만 읽으며, 직접 config 생성자에 값을 주입하는 경로는 허용하지 않는다.^[raw/articles/docmesh-py-core-configuration-guide-v0.4.0.md]

## Global rules

- 공통 식별자는 `CommonConfig().env`와 `DOCMESH_HEALTHCHECK_ENABLED` 축이다.
- 공용 로깅 기본 레벨은 `DOCMESH_LOG_LEVEL`로 제어할 수 있고, 명시 설정이 없으면 `INFO`를 사용한다.
- 공백 문자열은 미설정(`None`)으로 처리되고, boolean·숫자는 Pydantic coercion 및 범위 제약으로 검증한다.^[raw/articles/docmesh-py-core-configuration-guide-v0.4.0.md]
- 민감정보는 secret manager 또는 배포 플랫폼 secret 기능으로 주입하는 것이 권장된다.
- 서비스별 timeout/retry는 전역 공통값이 아니라 서비스별 환경변수로 관리된다.
- `LANGFUSE_ENVIRONMENT`가 비어 있으면 `CommonConfig().env` 값을 상속한다.^[raw/articles/docmesh-py-core-configuration-guide-2026.md]

## Loader behavior

- v0.4.0 API 계약에서 각 `*Config`는 인자 없이 생성하고 실행 프로세스 환경변수에서만 읽는다. `KeycloakDiscoveryConfig`는 issuer discovery에 필요한 URL/realm만 읽고, 나머지는 서비스 연결 설정 전체를 검증한다.^[raw/articles/docmesh-py-core-api-reference-v0.4.0.md]
- `load_service_configs(services=...)`는 선택된 서비스 설정을 모두 요구하고, `load_available_service_configs(services=...)`는 접두 환경변수가 전혀 없는 선택 서비스만 건너뛴다. 둘 다 불완전한 설정은 `ConfigError`로 처리한다.^[raw/articles/docmesh-py-core-api-reference-v0.4.0.md]
- 서비스 이름은 대소문자와 무관하게 `keycloak`, `postgres`, `sqlite`, `minio`, `milvus`, `ollama`, `langfuse`, `nats`를 사용한다. `services=None`이면 전체를 검증하고, 지정하면 나머지는 `None`으로 둔다.^[raw/articles/docmesh-py-core-configuration-guide-v0.4.0.md]
- 이전 API 자료에는 `env` mapping 전달 경로가 기록돼 있지만, v0.4.0 공개 레퍼런스는 설정 모델과 loader를 실행 프로세스 환경변수 기반 API로 제시한다. 따라서 새 소비 코드는 최신 공개 계약의 인자 없는 config 생성과 `services=` 선택만 전제로 하고, mapping 기반 호출은 실제 설치 버전 소스로 별도 검증해야 한다.^[raw/articles/docmesh-py-core-api-reference-v0.4.0.md]
- v0.3.0 `.env.example`은 deployment template이며 placeholder를 실제 배포값으로 교체해야 한다. 필요한 서비스만 선택하고 direct factory에서는 `load_service_configs(services={...})`로 같은 서비스 이름을 전달해 무관한 placeholder가 검증되지 않도록 한다.^[raw/articles/docmesh-py-core-env-example-v0.3.0.md]
- 마지막 단계에서 `validate_runtime_security()`를 호출해 production 계열 런타임 보안 제약을 확인한다. v0.3.0은 `load_available_service_configs()`가 관련 prefix가 전혀 없는 후보는 `None`으로 두되, 관련 키가 하나라도 있는 불완전한 설정은 `ConfigError`로 처리한다고 명시한다.^[raw/articles/docmesh-py-core-api-reference-v0.3.0.md]
- production 보안 제약은 `DOCMESH_SECURITY_MODE`가 있으면 그 값을 우선 사용하고, 없으면 `CommonConfig.env`를 `DOCMESH_PRODUCTION_ALIASES`(기본 `prod,production`)와 비교해 활성화한다.^[raw/articles/docmesh-py-core-api-reference-v0.2.0.md]

## Service-specific contracts

- Keycloak: `KeycloakDiscoveryConfig()`와 `KeycloakConfig()`를 구분하며, `KEYCLOAK_CLIENT_PUBLIC=false`면 `KEYCLOAK_CLIENT_SECRET`가 필요하다. password grant에서는 함수 인자가 우선이고, 생략된 username/password는 `KEYCLOAK_TOKEN_USERNAME`/`KEYCLOAK_TOKEN_PASSWORD`에서 보완한다.^[raw/articles/docmesh-py-core-configuration-guide-v0.2.0.md]
- PostgreSQL: v0.4.0에서는 `POSTGRES_DSN`을 지원하지 않는다. host/db/user/password 개별 필드를 사용한다.^[raw/articles/docmesh-py-core-configuration-guide-v0.4.0.md]
- SQLite: 로컬 개발과 테스트에 적합하며 `:memory:`를 지원한다. 상위 디렉터리 자동 생성은 하지 않고, 파일 경로 문제는 설정 로딩이 아니라 실제 연결 단계에서 드러난다.^[raw/articles/docmesh-py-core-configuration-guide-2026.md]
- MinIO / Milvus / Ollama: 여러 timeout/retry/model 관련 env가 설정 모델에는 존재하지만, 현재 팩토리 구현이 일부 값을 생성자에 직접 전달하지 않는다고 문서가 명시한다.
- Langfuse: `enabled=False`면 client 생성이 `None`이 될 수 있고, `enabled=True`일 때만 host/public_key/secret_key가 필수다. `LANGFUSE_MAX_RETRIES`는 현재 parsing/validation에만 사용되며 기본 factory나 runtime defaults에는 자동 연결되지 않는다.^[raw/articles/docmesh-py-core-configuration-guide-v0.3.0.md]
- NATS: `NATS_SERVERS`는 쉼표 구분 목록으로 파싱되고, user/password · token · creds file 중 정확히 하나의 인증 모드만 허용된다.^[raw/articles/docmesh-py-core-configuration-guide-2026.md]

## Aggregate model

`ServiceConfigs`는 아래 필드를 묶는 dataclass다.

- `common: CommonConfig`
- `keycloak: KeycloakConfig | None`
- `postgres: PostgresConfig | None`
- `sqlite: SqliteConfig | None`
- `minio: MinioConfig | None`
- `milvus: MilvusConfig | None`
- `ollama: OllamaConfig | None`
- `langfuse: LangfuseConfig | None`
- `nats: NatsConfig | None`

추가로 `docmesh_env -> str` convenience property가 `common.env`를 그대로 노출한다.^[raw/articles/docmesh-py-core-api-reference-2026.md]

## Failure patterns and enforcement

- 빈 문자열도 미설정처럼 취급될 수 있으므로 export는 되었지만 값이 비어 있는 경우에도 검증 실패가 날 수 있다.
- Keycloak 기본값은 confidential client 전제이므로 `KEYCLOAK_CLIENT_PUBLIC=true`를 명시하지 않으면 `KEYCLOAK_CLIENT_SECRET` 누락이 대표적 실패 원인이다.
- Keycloak provisioning은 service account 방식과 username/password 방식을 동시에 주거나 둘 다 주지 않으면 `single admin auth mode` 오류가 발생한다.
- password grant는 설정 로딩 단계에서 username/password를 강제하지 않으며, 실제 토큰 요청 시 함수 인자와 config fallback을 합쳐 완전한 credential이 있어야 한다.
- `DOCMESH_HEALTHCHECK_ENABLED`는 `check_on_startup`에 자동 연결되지 않으므로, 소비 애플리케이션이 startup 정책에 반영해야 한다.^[raw/articles/docmesh-py-core-configuration-guide-v0.2.0.md]
- `DOCMESH_ENV=prod`/`production` 또는 `DOCMESH_SECURITY_MODE=production`에서는 `KEYCLOAK_VERIFY_SSL=false`, `MINIO_SECURE=false`, `MILVUS_SECURE=false`를 거부하고, 선택 서비스의 placeholder secret·endpoint도 거부한다. 진단은 secret 원문 대신 env key와 remediation만 반환한다.^[raw/articles/docmesh-py-core-configuration-guide-v0.4.0.md]
- `assemble_services()`는 `load_available_service_configs()`를 사용하므로 PostgreSQL과 SQLite처럼 대체 가능한 후보를 `one_of=({"postgres", "sqlite"},)`로 조립할 수 있다.^[raw/articles/docmesh-py-core-examples-guide-v0.3.0.md]
- `diagnose_services(plan=...)`는 startup 전 검증에 동일한 `RuntimePlan`을 재사용하며, production에서는 placeholder secret 또는 example/localhost endpoint를 원래 값을 노출하지 않는 issue로 보고한다.^[raw/articles/docmesh-py-core-configuration-guide-v0.4.0.md]

## Operational significance

이 계약은 fastapi-core가 서비스 통합을 단순히 클라이언트 생성 API에만 의존하지 않고, 배포 환경별 설정 표면과 런타임 보안 가드레일까지 명시적으로 관리해야 함을 보여준다. 특히 선택 로딩, direct config 생성 시 `ValidationError`와 aggregate loader의 `ConfigError` 차이, production 전용 보안 제약, 그리고 "설정 모델에 있으나 현재 팩토리에서 직접 소비하지 않는 필드"의 존재는 애플리케이션 설정 로더와 운영 문서에 그대로 반영될 가능성이 높다.

## Related pages

- [[docmesh-py-core]]: 이 설정 계약은 패키지의 핵심 운영 인터페이스다.
- [[service-factory-registry]]: examples 기반 registry 패턴과 direct factory 패턴의 차이가 이 계약 해석에 영향을 준다.
- [[keycloak-authentication-api]]: Keycloak 관련 환경변수와 운영 보안 원칙은 별도 중요도를 가진다.
- [[operational-logging-and-retry-utilities]]: 로그 레벨 초기화와 민감정보 마스킹도 동일한 운영 계약의 일부다.
