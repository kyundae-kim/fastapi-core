---
title: fastapi-core codebase review against docmesh-py-core
created: 2026-06-11
updated: 2026-06-11
type: query
tags: [query, architecture, sdk, refactor, risk]
sources: [raw/articles/docmesh-py-core-sdk-2026-06-11.md, raw/articles/docmesh-py-core-api-2026-06-11.md, raw/articles/docmesh-py-core-config-2026-06-11.md]
confidence: medium
---
# fastapi-core codebase review against docmesh-py-core

## Executive Summary
현재 `fastapi-core` 는 `docmesh-py-core` 를 dependency 로 선언하고도 실제 구현에서는 거의 사용하지 않고, Keycloak/DB/MinIO/Milvus/Ollama/NATS/Langfuse 조립 로직을 자체적으로 다시 구현하고 있다. 따라서 가장 큰 리팩터링 포인트는 기능 추가보다 **중복 제거와 lifecycle 일원화** 다.

문서 기준 `docmesh-py-core` 의 권장 축은 `load_settings() -> ServiceFactoryRegistry -> create/check -> close_all()` 인데, 현재 `fastapi-core` 는 `EnvConfig()` / `ServiceSettings.from_yaml()` / 서비스별 `set_*` / request-time lazy init 구조를 사용한다. 이 차이 때문에 설정 검증, 서비스 생성, health check, shutdown 정책이 여러 모듈로 분산되어 있다. ^[raw/articles/docmesh-py-core-sdk-2026-06-11.md]

## Concrete Findings
### 1. docmesh-py-core dependency is declared but not actually integrated
`pyproject.toml` 에서는 `docmesh-py-core>=0.1.4` 를 의존성으로 선언하지만, 현재 Python 코드에서는 `docmesh_py_core` import 사용 흔적이 없다. 이는 wrapper SDK가 아니라 사실상 parallel implementation 에 가깝다는 뜻이다.

### 2. Configuration entrypoint is split, not unified
`fastapi_core/factory.py` 는 `EnvConfig()` 와 `ServiceSettings.from_yaml()` 를 직접 생성한다. 이는 [[load-settings-and-settings-model]] 에서 강조한 단일 진입점 철학과 다르다. 검증 규칙이 늘어나면 env/yaml/route 수준에서 책임이 더 쉽게 분산된다. ^[raw/articles/docmesh-py-core-config-2026-06-11.md]

### 3. Dependency modules duplicate the same app.state pattern
`dependencies/auth.py`, `database.py`, `storage.py`, `milvus.py`, `async_milvus.py`, `ollama.py`, `messaging.py` 는 모두 거의 동일한 `set_*` / `get_*` / state key 패턴을 반복한다. 이는 [[service-factory-registry]] 가 담당할 중앙 조립 책임이 현재 서비스별 복제 코드로 흩어져 있음을 보여준다. ^[raw/articles/docmesh-py-core-api-2026-06-11.md]

### 4. Readiness dependency injection eagerly constructs services even when checks are disabled
`routers/health.py` 의 `readiness()` 는 `Engine` 과 `Minio` 를 dependency 로 미리 주입받는다. 따라서 `settings.health.check_database=False` 또는 `check_minio=False` 여도 request 진입 시점에 엔진/클라이언트 생성이 일어날 수 있다. 이는 [[check-all-services]] 의 required/optional 정책보다 거친 방식이며, disabled check 가 truly disabled 가 아니다. ^[raw/articles/docmesh-py-core-api-2026-06-11.md]

### 5. Lifecycle is implicit and request-driven, not bootstrap-driven
`get_config()`, `get_settings()`, `get_db_engine()`, `get_minio_client()`, `get_auth_provider()` 등은 state 가 없으면 request 처리 중 생성한다. 즉 startup 에서 실패를 드러내는 구조보다, 첫 요청에서 lazy initialization 되는 경향이 있다. 이는 [[sdk-health-check-patterns]] 의 startup readiness 중심 운영 모델과는 약간 어긋난다. ^[raw/articles/docmesh-py-core-sdk-2026-06-11.md]

### 6. No unified close_all / check_all_services abstraction
README 의 lifespan 예시는 직접 `dispose()`, `close()`, `drain()` 을 호출한다. 이는 [[sdk-health-check-patterns]] / [[check-all-services]] / [[service-factory-registry]] 조합으로 모을 수 있는 정리 책임이 아직 수작업이라는 뜻이다. ^[raw/articles/docmesh-py-core-api-2026-06-11.md]

### 7. Auth path is tightly bound to current Keycloak provider shape
`core/auth.py` 는 password grant 와 refresh token 을 직접 구현하고, `dependencies/auth.py` 는 provider 를 즉시 조립한다. 반면 wiki에서 정리한 `docmesh-py-core` 방향은 runtime auth 와 provisioning 분리, 설정 규칙 통합, default grant 정책 명확화에 더 가깝다. 리팩터링 시 이 영역은 직접 wrapper 로 두되 경계를 더 선명히 만드는 편이 좋다. ^[raw/articles/docmesh-py-core-config-2026-06-11.md]

## Recommended Refactor Plan
1. `bootstrap` 계층을 새로 만들고 앱 시작 시 설정 로드/검증/서비스 조립을 한곳으로 이동
2. 현재 반복되는 `set_*` / `get_*` 패턴을 registry 또는 provider container 로 수렴
3. readiness 를 request-time lazy init 에서 startup-built resources 기준으로 재구성
4. 정리 루틴을 `shutdown_services()` 같은 단일 진입점으로 모으기
5. 가능하면 `docmesh-py-core` 의 설정/registry/health abstraction 을 직접 재사용하고, `fastapi-core` 는 FastAPI wiring 에 집중

## High-Value First Fixes
- `readiness()` 에서 disabled 서비스도 생성되는 구조 제거
- 설정 로딩을 `create_app()` 외부 bootstrap 또는 lifespan 에서 명시화
- service state 관리 중복 제거
- `docmesh-py-core` 직접 재사용 가능한 부분과 `fastapi-core` 고유 FastAPI wiring 부분 분리

## Review Verdict
현재 구조는 "FastAPI adapter" 라기보다 "서비스 통합 SDK를 한 번 더 구현한 패키지" 에 가깝다. 따라서 리팩터링의 핵심은 새 기능 추가보다 **docmesh-py-core 와 fastapi-core 의 역할을 다시 분리하는 것** 이다. 가장 바람직한 방향은 `fastapi-core` 를 `docmesh-py-core` 위의 얇은 FastAPI composition layer 로 재정의하는 것이다.

## Refactor Progress Update
### Implemented slice 1 — readiness conditional resource acquisition
`routers/health.py` 의 readiness 경로는 이제 `check_database` 와 `check_minio` 플래그가 `True` 일 때만 각각 `get_db_engine()` 과 `get_minio_client()` 를 호출한다. 즉 disabled health check 가 더 이상 엔진/클라이언트 생성을 유발하지 않는다. 이는 [[check-all-services]] 와 [[optional-observability-services]] 가 요구하는 optional service semantics 에 더 가까운 구조다.

### Implemented slice 2 — duplicated app.state helpers partially collapsed
새 `fastapi_core/bootstrap.py` 에 `set_state_value()`, `get_state_value()`, `get_or_create_state_value()`, `set_state_value_async()`, `get_or_create_state_value_async()` helper 를 도입했고, `dependencies/config.py`, `database.py`, `storage.py`, `ollama.py`, `milvus.py`, `async_milvus.py`, `messaging.py`, `auth.py`, 그리고 `factory.py` 일부가 이 helper 를 사용하도록 바뀌었다. 이는 [[service-factory-registry]] 로 수렴하기 전 단계로서, 반복되는 state key / fallback / cache 로직을 공통화한 것이다.

### Verified impact
비통합 테스트 기준으로 `uv run pytest -q -m 'not integration'` 가 `164 passed, 44 deselected` 로 통과했다. 또한 bootstrap helper 전용 테스트와 각 dependency 모듈 테스트가 통과하여 동기/비동기 state caching 경로가 유지됨을 확인했다. 통합 테스트 전체는 환경 문제로 Langfuse host name resolution 이 실패해 1건이 남아 있었지만, 이는 이번 리팩터링 슬라이스의 코드 경로와는 별개였다.

### Next recommended slice
다음 단계는 startup/shutdown 을 명시하는 `initialize_app_services()` / `shutdown_app_services()` 계층을 도입해 request-time lazy init 의 비중을 더 낮추는 것이다. 그 이후 `docmesh-py-core` 의 settings/registry/health abstraction 과 직접 매핑 가능한 부분을 교체하는 편이 안전하다.

### Implemented slice 3 — managed lifecycle bootstrap
이제 `fastapi_core/lifecycle.py` 가 `initialize_app_services()`, `shutdown_app_services()`, `create_managed_lifespan()` 을 제공한다. 기본 `create_app()` 호출은 custom lifespan 이 주어지지 않으면 이 managed lifespan 을 사용하며, startup 에서 auth/database/minio/milvus/ollama/langfuse 초기화를 수행하고 shutdown 에서 등록된 `db_engine.dispose()`, `milvus_client.close()`, `async_milvus_client.close()`, `nats_client.drain()` 을 순서대로 정리한다. NATS 는 기본적으로 startup 연결을 강제하지 않도록 `init_nats=False` 로 두어 기존 환경 의존성을 과도하게 키우지 않았다.

### Verified impact after lifecycle wiring
`uv run pytest test_fastapi_core/test_lifecycle.py -q` 와 `uv run pytest test_fastapi_core/test_factory.py -q` 가 모두 통과했고, 이어서 `uv run pytest -q -m 'not integration'` 가 `169 passed, 44 deselected` 로 통과했다. 즉 기본 app factory 가 managed lifespan 을 사용하도록 바뀐 뒤에도 비통합 회귀는 관찰되지 않았다.

### Implemented slice 4 — settings-driven lifecycle policy and docmesh bridge
`fastapi_core/core/config.py` 에 `LifecycleSettings` 를 추가해 startup eager-init 정책을 `ServiceSettings.lifecycle` 로 제어할 수 있게 만들었다. `initialize_app_services()` 는 이제 `resolve_lifecycle_policy()` 를 통해 `health.check_keycloak`, `health.check_database`, `health.check_minio`, `health.check_langfuse` 값을 기본 eager-init 정책으로 사용하며, 필요하면 lifecycle 쪽 explicit flag 로 override 할 수 있다. 이로써 health 정책과 startup 정책이 완전히 분리되지 않고, 적어도 기본값 수준에서는 서로 정렬된다.

또한 `fastapi_core/docmesh_bridge.py` 를 추가해 `docmesh-py-core` 가 설치된 환경에서는 `load_settings()` -> `ServiceFactoryRegistry(settings)` -> `close_all()` 흐름을 직접 연결할 수 있는 최소 통합 seam 을 만들었다. 현재 실행 환경에는 `docmesh_py_core` 모듈이 설치되어 있지 않아 bridge 는 optional no-op/fallback 경로로 동작하지만, `ServiceSettings.lifecycle.use_docmesh_registry` 와 `use_docmesh_healthchecks` 플래그를 통해 future direct integration 지점을 코드 차원에서 확보했다. 이는 [[load-settings-and-settings-model]], [[service-factory-registry]], [[check-all-services]] 개념을 현재 코드에 대응시키는 첫 단계다. ^[raw/articles/docmesh-py-core-sdk-2026-06-11.md] ^[raw/articles/docmesh-py-core-api-2026-06-11.md]

### Implemented slice 5 — readiness health aggregation bridge
`routers/health.py` 는 이제 native readiness check callable 들을 먼저 구성한 뒤, `use_docmesh_healthchecks=True` 이면 `run_docmesh_healthchecks()` 를 통해 docmesh의 `check_all_services()` 스타일 집계 경로를 우선 시도한다. bridge 가 실제로 사용 가능하고 집계 결과가 성공이면 native per-service branch 를 건너뛰고, 그렇지 않으면 기존 native readiness 로 안전하게 fallback 한다. 즉 현재 환경에서는 회귀 없이 동작하고, docmesh가 설치된 배포 환경에서는 더 직접적인 health abstraction 재사용이 가능하다.

### Verified impact after policy/docmesh slices
`uv run pytest test_fastapi_core/test_docmesh_bridge.py -q` 가 `3 passed` 로 통과했고, 관련 회귀 묶음 `uv run pytest test_fastapi_core/test_docmesh_bridge.py test_fastapi_core/test_lifecycle.py test_fastapi_core/test_factory.py test_fastapi_core/routers/test_health.py test_fastapi_core/dependencies/test_config.py test_fastapi_core/test_bootstrap.py -q` 가 `33 passed` 로 통과했다. 전체 비통합 스위트도 `uv run pytest -q -m 'not integration'` 기준 `175 passed, 44 deselected` 로 통과했다.

### Implemented slice 6 — real docmesh package activation path
실행 환경을 `python3` 대신 `uv run python` 기준으로 확인하자 실제 가상환경에는 `docmesh-py-core` 가 설치되어 있었고, `import docmesh_py_core` 도 성공했다. 다만 설치된 실제 버전은 `0.1.1` 이며 `uv.lock` 은 git source `5643e4c1...` 에 pin 되어 있다. 즉 `pyproject.toml` 의 `docmesh-py-core>=0.1.4` 표기와 현재 lock/runtime 상태 사이에는 불일치가 있다.

코드 차원에서는 `fastapi_core/docmesh_bridge.py` 가 이제 `EnvConfig` 를 `docmesh_py_core` 가 기대하는 flat env (`DOCMESH_ENV`, `KEYCLOAK_URL`, `POSTGRES_DSN`, `OLLAMA_GENERATION_MODEL`, `NATS_CONNECT_TIMEOUT_SECONDS` 등) 로 번역한다. Langfuse key 가 없으면 `LANGFUSE_ENABLED=false` 로 낮추고, Keycloak client secret 이 없으면 `KEYCLOAK_CLIENT_PUBLIC=true` 로 바꿔 current fastapi-core 기본 설정에서도 `load_settings()` 가 실제로 통과하도록 만들었다. 그 결과 `initialize_docmesh_registry(config=EnvConfig())` 가 실제 `docmesh_py_core.Settings` 와 `ServiceFactoryRegistry` 를 생성하는 live path 가 열렸다.

또한 `initialize_app_services()` 는 `use_docmesh_registry=True` 일 때 patched fake 가 아니라 실제 `docmesh_py_core` registry 를 `app.state.docmesh_settings` 와 `app.state.docmesh_registry` 에 넣는 경로를 테스트로 검증했다. 이는 최소한 settings/registry seam 이 더 이상 이론적 hook 이 아니라, 현재 런타임에서 실제 import 가능한 활성 경로임을 의미한다.

### Verified impact after real activation
`uv run pytest test_fastapi_core/test_docmesh_bridge.py test_fastapi_core/test_lifecycle.py::test_initialize_app_services_populates_real_docmesh_registry_when_enabled -q` 가 `7 passed` 로 통과했고, 이어서 관련 회귀 묶음 `uv run pytest test_fastapi_core/test_docmesh_bridge.py test_fastapi_core/test_lifecycle.py test_fastapi_core/test_factory.py test_fastapi_core/routers/test_health.py test_fastapi_core/dependencies/test_config.py test_fastapi_core/test_bootstrap.py -q` 가 `37 passed` 로 통과했다. 전체 비통합 스위트도 `uv run pytest -q -m 'not integration'` 기준 `179 passed, 44 deselected` 로 통과했다. 실동작 확인용으로 `uv run python` 에서 `initialize_docmesh_registry(config=EnvConfig())` 실행 결과가 `Settings ServiceFactoryRegistry` 로 출력되었고, lifecycle 경유 app state 등록도 `True True` 로 확인됐다.

### Implemented slice 7 — registry-backed startup client creation
`initialize_app_services()` 는 이제 `use_docmesh_registry=True` 이고 실제 registry 가 준비된 경우, auth/database/minio/milvus/ollama/nats 초기화를 native `set_* (config=...)` 경로 대신 `docmesh_registry.create_client(...)` 경로로 수행한다. keycloak/postgres/minio/milvus/ollama 는 registry wrapper 에서 `.client` 를 unwrap 한 뒤 각각 `set_auth_provider(..., provider=...)`, `set_db_engine(..., engine=...)`, `set_minio_client(..., client=...)`, `set_milvus_client(..., client=...)`, `set_ollama_client(..., client=...)` 로 state 에 등록한다. NATS 는 `NatsConnectionBuilder.connect()` 를 await 해 실제 연결 객체를 얻은 뒤 `set_nats_client(..., client=...)` 로 연결한다. 이로써 startup 조립 경로에서 service factory registry 재사용이 실질적으로 시작됐다. ^[raw/articles/docmesh-py-core-api-2026-06-11.md]

또한 lifecycle 은 `app.state.docmesh_managed_services` 를 기록해 registry 가 소유한 stateful 자원(`db_engine`, `milvus_client` 등)에 대해 shutdown 시 중복 `dispose()/close()` 를 피한다. 대신 `docmesh_registry.close_all()` 이 registry-managed wrapper 정리를 맡고, state 쪽에서는 NATS drain 과 async_milvus close 같은 non-registry/extra cleanup 만 계속 수행한다. 이는 [[service-factory-registry]] 의 중앙 종료 책임과 현재 FastAPI state wiring 을 충돌 없이 연결하는 중간 단계다. ^[raw/articles/docmesh-py-core-sdk-2026-06-11.md]

### Verified impact after registry-backed startup
새 RED 테스트로 registry-backed startup 과 duplicate shutdown 방지 시나리오를 먼저 추가했고, `uv run pytest test_fastapi_core/test_lifecycle.py::test_initialize_app_services_uses_docmesh_registry_clients_for_supported_services test_fastapi_core/test_lifecycle.py::test_shutdown_app_services_skips_duplicate_close_for_docmesh_managed_state -q` 가 처음에는 실패한 뒤 구현 후 `2 passed` 로 통과했다. 이어서 관련 회귀 묶음 `uv run pytest test_fastapi_core/test_docmesh_bridge.py test_fastapi_core/test_lifecycle.py test_fastapi_core/test_factory.py test_fastapi_core/routers/test_health.py test_fastapi_core/dependencies/test_database.py test_fastapi_core/dependencies/test_storage.py test_fastapi_core/dependencies/test_messaging.py test_fastapi_core/dependencies/test_security.py -q` 가 `61 passed` 로 통과했고, 전체 비통합 스위트도 `uv run pytest -q -m 'not integration'` 기준 `181 passed, 44 deselected` 로 통과했다.

### Implemented slice 8 — registry-first request-time dependency fallback
startup 이전 또는 custom lifespan 환경에서도 registry 재사용을 유지하기 위해, request-time fallback 경로 역시 이제 `docmesh_registry` 를 먼저 본다. `get_db_engine()` 는 `postgres`, `get_minio_client()` 는 `minio`, `get_auth_provider()` 는 `keycloak`, `get_nats_client()` 는 `nats` 를 각각 registry 에서 우선 가져오고, registry 가 없을 때만 기존 native `create_db_engine()` / `create_minio_client()` / `KeycloakAuthProvider(...)` / `create_nats_client()` 경로로 fallback 한다. `nats` 는 async builder 의 `connect()` 를 await 하도록 맞췄다. 이로써 startup 경로뿐 아니라 request-time lazy init 경로까지도 [[service-factory-registry]] 중심으로 더 일관되게 정렬됐다. ^[raw/articles/docmesh-py-core-api-2026-06-11.md]

`fastapi_core/docmesh_bridge.py` 에는 이를 위해 `get_docmesh_registry()`, `unwrap_docmesh_client()`, `get_docmesh_service()`, `get_docmesh_service_async()` helper 가 추가됐다. 결과적으로 lifecycle 과 dependency fallback 이 동일한 registry 접근 규약을 공유하게 됐고, registry wrapper 의 `.client` 언랩과 NATS builder connect 처리도 한곳에 모였다. 이는 이후 나머지 dependency (`ollama`, `milvus`, 가능하면 async_milvus`) 도 같은 패턴으로 수렴시키기 쉬운 기반이다. ^[raw/articles/docmesh-py-core-sdk-2026-06-11.md]

### Verified impact after registry-first fallback
새 RED 테스트로 database/storage/auth/messaging fallback 이 registry 우선 경로를 사용하는 시나리오를 먼저 추가했고, `uv run pytest test_fastapi_core/dependencies/test_database.py::test_get_db_engine_fallback_prefers_docmesh_registry test_fastapi_core/dependencies/test_storage.py::test_get_minio_client_fallback_prefers_docmesh_registry test_fastapi_core/dependencies/test_messaging.py::TestGetNatsClient::test_prefers_docmesh_registry_when_not_initialized test_fastapi_core/dependencies/test_security.py::test_get_auth_provider_fallback_prefers_docmesh_registry -q` 가 처음에는 `4 failed` 였다가 구현 후 `4 passed` 로 바뀌었다. 이어서 관련 회귀 묶음 `uv run pytest test_fastapi_core/dependencies/test_database.py test_fastapi_core/dependencies/test_storage.py test_fastapi_core/dependencies/test_messaging.py test_fastapi_core/dependencies/test_security.py test_fastapi_core/test_lifecycle.py test_fastapi_core/routers/test_health.py test_fastapi_core/test_docmesh_bridge.py -q` 가 `62 passed` 로 통과했고, 전체 비통합 스위트도 `uv run pytest -q -m 'not integration'` 기준 `185 passed, 44 deselected` 로 통과했다.

### Implemented slice 9 — registry-first fallback for ollama and sync milvus
남아 있던 request-time fallback 중 `get_ollama_client()` 와 `get_milvus_client()` 도 이제 각각 `docmesh_registry.create_client("ollama")`, `docmesh_registry.create_client("milvus")` 를 먼저 사용한다. registry 가 있으면 wrapper 의 `.client` 를 언랩해 `app.state.ollama_client`, `app.state.milvus_client` 에 캐시하고, registry 가 없을 때만 기존 native `create_ollama_client()` / `create_milvus_client()` 경로로 내려간다. 이로써 현재 docmesh registry 가 직접 생성할 수 있는 주요 sync service(auth/postgres/minio/milvus/ollama/nats)는 startup 과 request-time fallback 양쪽 모두 registry-first 로 정렬됐다. ^[raw/articles/docmesh-py-core-api-2026-06-11.md]

`async_milvus` 는 이번 슬라이스에서 의도적으로 유지했다. 현재 설치된 `docmesh_py_core 0.1.1` 의 `ServiceFactoryRegistry` 는 `MilvusClient` builder 는 제공하지만 `AsyncMilvusClient` builder 는 제공하지 않기 때문이다. 따라서 `get_async_milvus_client()` 는 아직 native `create_async_milvus_client()` 경로를 유지하고, 이 부분은 upstream registry 가 async milvus 를 노출하거나 fastapi-core 쪽에 별도 async adapter 층을 둘 때 다시 정리하는 편이 안전하다. ^[raw/articles/docmesh-py-core-sdk-2026-06-11.md]

### Verified impact after A-2 remaining dependency fallback
새 RED 테스트로 ollama/milvus fallback 의 registry 우선 시나리오를 먼저 추가했고, `uv run pytest test_fastapi_core/dependencies/test_ollama.py::TestGetOllamaClient::test_prefers_docmesh_registry_when_missing test_fastapi_core/dependencies/test_milvus.py::TestGetMilvusClient::test_prefers_docmesh_registry_when_missing -q` 가 처음에는 `2 failed` 였다가 구현 후 `2 passed` 로 바뀌었다. 이어서 관련 회귀 묶음 `uv run pytest test_fastapi_core/dependencies/test_ollama.py test_fastapi_core/dependencies/test_milvus.py test_fastapi_core/dependencies/test_async_milvus.py test_fastapi_core/test_lifecycle.py test_fastapi_core/test_docmesh_bridge.py -q` 가 `34 passed` 로 통과했고, 전체 비통합 스위트도 `uv run pytest -q -m 'not integration'` 기준 `187 passed, 44 deselected` 로 통과했다.
