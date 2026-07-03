---
title: Service configuration contracts
created: 2026-06-25
updated: 2026-07-02
type: concept
tags: [config, contract, integration, implementation, security]
sources: [raw/articles/docmesh-py-core-api-reference-2026.md, raw/articles/docmesh-py-core-configuration-guide-2026.md, raw/articles/docmesh-py-core-examples-guide-2026.md]
confidence: medium
---

# Service configuration contracts

`docmesh-py-core`의 현재 설정 표면은 환경변수에서 직접 서비스별 config class를 만들거나, `load_service_configs(*, services=None)`로 선택 서비스 묶음을 로드하는 방식으로 정리된다.^[raw/articles/docmesh-py-core-api-reference-2026.md]^[raw/articles/docmesh-py-core-configuration-guide-2026.md]

## Global rules

- 공통 식별자는 `CommonConfig().env`와 `DOCMESH_HEALTHCHECK_ENABLED` 축이다.
- 공용 로깅 기본 레벨은 `DOCMESH_LOG_LEVEL`로 제어할 수 있고, 명시 설정이 없으면 `INFO`를 사용한다.
- 공백 문자열은 미설정(`None`)으로 처리된다.
- Boolean 값은 `true` / `false`만 허용된다.
- 민감정보는 secret manager 또는 배포 플랫폼 secret 기능으로 주입하는 것이 권장된다.
- 서비스별 timeout/retry는 전역 공통값이 아니라 서비스별 환경변수로 관리된다.
- `LANGFUSE_ENVIRONMENT`가 비어 있으면 `CommonConfig().env` 값을 상속한다.^[raw/articles/docmesh-py-core-configuration-guide-2026.md]

## Loader behavior

- `CommonConfig()`, `KeycloakConfig()`, `PostgresConfig()` 같은 직접 생성 경로는 pydantic `ValidationError`를 그대로 노출한다.
- `load_service_configs()`는 선택된 서비스만 읽고, 지원하지 않는 서비스명/필수값 누락/타입·범위 위반을 `ConfigError`로 감싸서 반환한다.
- `services=None`이면 `keycloak`, `postgres`, `sqlite`, `minio`, `milvus`, `ollama`, `langfuse`, `nats` 전체를 검증한다.
- `services={...}`를 주면 지정한 서비스만 로드하고 나머지는 `None`으로 둔다.
- 마지막 단계에서 `validate_runtime_security()`를 호출해 production 계열 런타임 보안 제약을 확인한다.
- production 보안 제약은 `DOCMESH_ENV`가 `production` 또는 `prod`일 때만 활성화된다.^[raw/articles/docmesh-py-core-api-reference-2026.md]^[raw/articles/docmesh-py-core-configuration-guide-2026.md]

## Service-specific contracts

- Keycloak: `KeycloakDiscoveryConfig()`와 `KeycloakConfig()`를 구분하며, `KEYCLOAK_CLIENT_PUBLIC=false`면 `KEYCLOAK_CLIENT_SECRET`가 필요하다. `password` grant 사용자명/비밀번호는 환경변수에 넣더라도 자동 사용되지 않고 실제 `fetch_access_token(username=..., password=...)` 함수 인자로 넘겨야 한다.^[raw/articles/docmesh-py-core-configuration-guide-2026.md]
- PostgreSQL: `config.dsn`이 있으면 host/db/user/password 개별 필드보다 우선한다.
- SQLite: 로컬 개발과 테스트에 적합하며 `:memory:`를 지원한다. 상위 디렉터리 자동 생성은 하지 않고, 파일 경로 문제는 설정 로딩이 아니라 실제 연결 단계에서 드러난다.^[raw/articles/docmesh-py-core-configuration-guide-2026.md]
- MinIO / Milvus / Ollama: 여러 timeout/retry/model 관련 env가 설정 모델에는 존재하지만, 현재 팩토리 구현이 일부 값을 생성자에 직접 전달하지 않는다고 문서가 명시한다.
- Langfuse: `enabled=False`면 client 생성이 `None`이 될 수 있고, `enabled=True`일 때만 host/public_key/secret_key가 필수다.
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
- password grant는 설정 로딩 단계에서 username/password를 강제하지 않지만, 실제 토큰 요청 함수 호출 시에는 반드시 전달해야 한다.
- production/prod 환경에서는 `KEYCLOAK_VERIFY_SSL=false`, `MINIO_SECURE=false`, `MILVUS_SECURE=false` 같은 비보안 설정이 `validate_runtime_security()`에 의해 거부된다.

## Operational significance

이 계약은 fastapi-core가 서비스 통합을 단순히 클라이언트 생성 API에만 의존하지 않고, 배포 환경별 설정 표면과 런타임 보안 가드레일까지 명시적으로 관리해야 함을 보여준다. 특히 선택 로딩, direct config 생성 시 `ValidationError`와 aggregate loader의 `ConfigError` 차이, production 전용 보안 제약, 그리고 "설정 모델에 있으나 현재 팩토리에서 직접 소비하지 않는 필드"의 존재는 애플리케이션 설정 로더와 운영 문서에 그대로 반영될 가능성이 높다.

## Related pages

- [[docmesh-py-core]]: 이 설정 계약은 패키지의 핵심 운영 인터페이스다.
- [[service-factory-registry]]: examples 기반 registry 패턴과 direct factory 패턴의 차이가 이 계약 해석에 영향을 준다.
- [[keycloak-authentication-api]]: Keycloak 관련 환경변수와 운영 보안 원칙은 별도 중요도를 가진다.
- [[operational-logging-and-retry-utilities]]: 로그 레벨 초기화와 민감정보 마스킹도 동일한 운영 계약의 일부다.
