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
