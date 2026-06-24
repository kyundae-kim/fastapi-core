---
title: config duplication analysis
created: 2026-06-24
updated: 2026-06-24
type: query
tags: [query, config, architecture, comparison, decision]
sources: [raw/articles/fastapi-core-config-2026-06-17.md, raw/articles/docmesh-py-core-config-2026-06-11.md]
confidence: medium
---
# config duplication analysis

## Summary
`fastapi_core/core/config.py` 의 중복 문제는 단순히 필드가 많다는 수준이 아니라, **같은 설정 도메인을 fastapi-core 설정 모델, docmesh adapter, 사용자 문서가 각각 반복 표현하고 있다는 점**에 있다. 특히 `core/config.py` 가 pure config module 역할을 넘어 docmesh 적응 책임까지 떠안고 있어 `[[layered-configuration-model]]` 과 `[[load-settings-and-settings-model]]` 사이의 경계가 흐려져 있다.

## Main duplication buckets
1. **문서 중복**: `docs/config.md` 가 `EnvConfig` 와 `ServiceSettings` 의 필드/기본값을 사실상 재서술하고 있어 drift 위험이 있다. 이는 [[configuration-principles]] 와 [[layered-configuration-model]] 이 설명하는 계약을 코드와 문서 양쪽에서 수동 유지하고 있다는 뜻이다.
2. **도메인 모델 중복**: `KeycloakConfig`, `DatabaseConfig`, `MinIOConfig`, `MilvusConfig`, `OllamaConfig`, `LangfuseConfig`, `NatsConfig` 는 `docmesh_py_core.Settings` 의 대응 서비스 설정과 의미상 크게 겹친다. 단기적으로는 제거 대상이 아니라도, 최소한 fastapi-core 내부 모델과 docmesh 변환 계층은 분리되어야 한다.
3. **모듈 책임 중복**: `core/config.py` 의 `load_docmesh_settings()`, `_adapt_docmesh_milvus_config()`, `resolve_milvus_config()` 는 이미 `docmesh_bridge.py` 가 맡고 있는 integration 책임과 같은 축에 있다. 이 상태는 `[[registry-backed-dependency-resolution]]` 이 지향하는 registry/bridge 경계를 흐린다.

## Safe first-step refactor
가장 안전한 1차 리팩터링은 `core/config.py` 를 **fastapi-core canonical 설정 모델 + 로더** 로 축소하고, docmesh-specific helper를 `docmesh_bridge.py` 로 이동하는 것이다. `ApplicationSettings` 와 `load_application_settings()` 는 현재 repo 내 사용처가 보이지 않아 제거 후보이며, `resolve_milvus_config()` 는 `dependencies/milvus.py`, `dependencies/async_milvus.py` 쪽 import만 조정하면 이동 가능하다. 이 단계는 [[fastapi-core]] 의 public dependency surface 를 건드리지 않고도 경계를 더 명확하게 만든다.

## Artifact
상세 실행 계획은 `docs/plans/2026-06-24-config-dedup-refactor-plan.md` 에 저장했다. 이 계획은 dead surface 확인 → docmesh helper 이동 → `core/config.py` 정리 → 설정 계약 테스트 추가 → 문서 sync 순서를 권장한다.

## Implemented first slice
첫 번째 리팩터링 slice는 실제로 적용되었다. `fastapi_core/core/config.py` 에서 `ApplicationSettings`, `load_application_settings()`, `load_docmesh_settings()`, `resolve_milvus_config()` 를 제거해 pure config loader/module 쪽으로 축소했고, docmesh-specific helper는 `fastapi_core/docmesh_bridge.py` 로 이동했다. Milvus dependency 경로도 `docmesh_bridge.resolve_milvus_config()` 를 사용하도록 바뀌었다.

검증은 `uv run pytest -q test_fastapi_core/core/test_config.py test_fastapi_core/dependencies/test_milvus.py test_fastapi_core/dependencies/test_async_milvus.py test_fastapi_core/test_public_api.py` 에서 `34 passed`, 이어 `uv run pytest -q -m 'not integration'` 에서 `189 passed, 26 deselected` 로 확인했다.

이후 문서도 동기화했다. `docs/config.md` 에 pure config vs docmesh bridge 경계를 명시하고, `docs/api.md` 에서 설정 dependency와 Milvus dependency가 `docmesh_bridge` 책임 분리를 따름을 반영했다.

## Replacement feasibility: docmesh config as canonical model

### KeycloakConfig
`fastapi_core.core.config.KeycloakConfig` 를 `docmesh_py_core.config.KeycloakConfig` 로 **완전히 drop-in 교체**하는 것은 아직 어렵지만, **adapter를 둔 canonical source 전환**은 현실적이다.

근거:
- fastapi-core 쪽 `KeycloakConfig` 는 `http_url`, `manage_url`, `realm`, `client_id`, `client_secret` 만 가진다.
- docmesh 쪽 `KeycloakConfig` 는 `url`, `realm`, `client_id`, `client_secret` 외에도 `verify_ssl`, `audience`, `token_grant_type`, `request_timeout_seconds`, provisioning 관련 필드를 포함한다.
- 현재 bridge는 `build_docmesh_env()` 에서 fastapi-core 설정을 docmesh env 로 변환할 때 `KEYCLOAK_URL`, `KEYCLOAK_REALM`, `KEYCLOAK_CLIENT_ID`, `KEYCLOAK_VERIFY_SSL` 등을 구성한다. 즉 아직은 **fastapi-core 모델이 source이고 docmesh는 파생 결과**다.
- 동시에 auth dependency는 이미 registry-backed docmesh service를 사용하므로, runtime 관점에서는 docmesh 설정을 canonical로 삼아도 큰 방향성 충돌은 없다.

제약:
- `manage_url` 같은 fastapi-core 고유 필드는 docmesh `KeycloakConfig` 에 없다.
- `core/auth.py` 의 native `KeycloakAuthProvider` 는 `http_url` 명명과 자체 URL 조합 계약을 가진다.

결론적으로 Keycloak은 **"직접 대체"보다 "docmesh KeycloakConfig + fastapi overlay(adapter)"** 가 적절하다.

### DatabaseConfig
`fastapi_core.core.config.DatabaseConfig` 를 `docmesh_py_core.config.PostgresConfig` 로 **바로 대체하는 것은 현재 구조에서는 비추천**이다.

근거:
- fastapi-core `DatabaseConfig` 는 `sqlalchemy_database_url` 계산 프로퍼티를 제공하고, `create_db_engine()` 이 여기에 직접 의존한다.
- 또한 `auth_method`, `echo`, `pool_timeout`, `pool_recycle`, `url` 직접 override 같은 SQLAlchemy/운영 편의 필드가 있다.
- 반면 docmesh `PostgresConfig` 는 `dsn`, `host`, `db`, `user`, `password`, `sslmode`, `connect_timeout_seconds`, `pool_size`, `max_overflow` 까지만 제공한다.
- bridge도 현재 `POSTGRES_DSN` 만 docmesh 쪽으로 넘긴다. 즉 fastapi-core의 native DB 모델에는 SQLAlchemy 엔진 생성 편의 계약이 더 많이 들어 있다.

결론적으로 Database는 **현재는 adapter 없이는 교체 불가에 가깝고**, 먼저 `create_db_engine()` 이 의존하는 계약을 분리해야 한다.

### Recommendation
1. **Keycloak 먼저**: `docmesh_py_core.config.KeycloakConfig` 를 canonical source 후보로 보고, `manage_url` 같은 fastapi-only 필드를 별도 overlay로 분리
2. **Database는 2단계**: 먼저 `DatabaseConfig` 를
   - pure connection input (`dsn/host/db/user/password/...`)
   - SQLAlchemy engine tuning (`echo/pool_timeout/pool_recycle`)
   로 쪼갠 뒤, 그 다음 `PostgresConfig` canonical화 검토
3. 단기적으로는 `EnvConfig` 전체를 없애기보다, `EnvConfig` 를 **fastapi overlay + docmesh settings adapter entrypoint** 로 축소하는 편이 안전하다.

## Artifact
- `docs/plans/2026-06-24-keycloak-config-canonicalization-plan.md` — Keycloak canonicalization 단계별 설계안

## Implemented keycloak first slice
- `fastapi_core.core.config` 에 `KeycloakOverlayConfig` 와 `EnvConfig.keycloak_overlay` 를 추가했다.
- `EnvConfig` 는 legacy `keycloak.manage_url` override 가 있으면 overlay 기본값으로 backfill 해 backwards compatibility 를 유지한다.
- `fastapi_core.docmesh_bridge` 에 `build_docmesh_keycloak_config(config)` 를 추가해 native Keycloak 설정을 docmesh canonical config 로 적응한다.
- `fastapi_core.routers.health` 는 이제 `config.keycloak_overlay.manage_url` 을 사용해 readiness Keycloak healthcheck URL 을 결정한다.
- `fastapi_core.__all__` 에 `KeycloakOverlayConfig` 를 추가했고, `docs/config.md`, `docs/api.md` 에 새 경계를 반영했다.
- 검증은 `uv run pytest -q test_fastapi_core/core/test_config.py test_fastapi_core/test_docmesh_bridge.py test_fastapi_core/routers/test_health.py test_fastapi_core/test_public_api.py` 에서 `38 passed`, 이어 `uv run pytest -q -m 'not integration'` 에서 `192 passed, 26 deselected` 로 확인했다.

## Implemented keycloak second slice
- `fastapi_core.core.auth.create_keycloak_auth_provider_from_docmesh_config(...)` 를 추가했다.
- 이 helper 는 docmesh canonical `KeycloakConfig` 의 `url/realm/client_id/client_secret` 를 native `KeycloakAuthProvider(http_url=...)` 계약으로 변환한다.
- `audience` 가 `client_id` 와 다르면 native provider가 동일 semantics 를 표현할 수 없으므로 명시적으로 `ValueError` 를 발생시켜 silent mismatch 를 막는다.
- `test_fastapi_core/core/test_security.py` 에 canonical-config 적응 성공/거부(audience mismatch) 테스트를 추가했다.
- 검증은 `uv run pytest -q test_fastapi_core/core/test_security.py test_fastapi_core/dependencies/test_security.py test_fastapi_core/routers/test_auth.py` 에서 `36 passed`, 이어 `uv run pytest -q -m 'not integration'` 에서 `194 passed, 26 deselected` 로 확인했다.

## Implemented keycloak third slice
- `fastapi_core.core.config.KeycloakConfig` 의 canonical 입력 필드를 `url` 로 전환했다.
- legacy `http_url` 입력은 `AliasChoices("url", "http_url")` 로 계속 허용하되, 내부 canonical state 는 `keycloak.url` 로 정규화된다.
- `fastapi_core.docmesh_bridge.build_docmesh_keycloak_config(...)` 와 관련 테스트를 `config.keycloak.url` 기준으로 갱신했다.
- 통합/의존성 테스트 중 canonical 경로를 써도 되는 지점은 `config.keycloak.url` 사용으로 옮겼고, `http_url` 은 compatibility surface 로만 남겼다.
- 검증은 `uv run pytest -q test_fastapi_core/core/test_config.py test_fastapi_core/test_docmesh_bridge.py test_fastapi_core/dependencies/test_security.py test_fastapi_core/core/test_security.py test_fastapi_core/test_public_api.py` 에서 `59 passed`, 이어 `uv run pytest -q -m 'not integration'` 에서 `196 passed, 26 deselected` 로 확인했다.

## Related Topics
- [[layered-configuration-model]] 은 `EnvConfig` 와 `ServiceSettings` 의 책임 분리를 설명한다.
- [[load-settings-and-settings-model]] 은 docmesh `load_settings()` / `Settings` 와 fastapi-core 이중 레이어의 관계를 설명한다.
- [[registry-backed-dependency-resolution]] 은 runtime dependency 경계가 어디에 있어야 하는지 설명한다.
- [[docmesh-py-core-package-structure-summary]] 는 docmesh 쪽 설정/조립/운영 레이어를 구조적으로 요약한다.
