---
title: docmesh-py-core vs fastapi-core usage comparison
created: 2026-06-29
updated: 2026-07-12
type: query
tags: [query, comparison, implementation, api]
sources: [raw/articles/docmesh-py-core-api-reference-2026.md, raw/articles/docmesh-py-core-configuration-guide-2026.md, raw/articles/docmesh-py-core-examples-guide-2026.md, pyproject.toml, .venv/lib/python3.11/site-packages/docmesh_py_core/__init__.py, .venv/lib/python3.11/site-packages/docmesh_py_core/config.py, .venv/lib/python3.11/site-packages/docmesh_py_core/factories.py, .venv/lib/python3.11/site-packages/docmesh_py_core/keycloak.py, fastapi_core/config.py, fastapi_core/docmesh_settings.py, fastapi_core/dependencies/auth.py, fastapi_core/dependencies/services.py, fastapi_core/routers/auth.py, fastapi_core/routers/health.py, fastapi_core/factory.py, test_fastapi_core/conftest.py, test_fastapi_core/test_factory.py, test_fastapi_core/test_health_router.py, test_fastapi_core/test_auth_router.py, test_fastapi_core/test_dependencies.py, test_fastapi_core/test_config.py, test_fastapi_core/integration/]
confidence: high
---

# docmesh-py-core vs fastapi-core usage comparison

## Question

`docmesh-py-core`를 `v0.1.4`로 올린 뒤, fastapi-core 소스가 새 public API에 맞게 실제로 마이그레이션되었는지 점검한다.

## Verification baseline

- Dependency pin: `pyproject.toml`의 `tool.uv.sources.docmesh-py-core.rev = "v0.1.4"`
- Installed package version: `uv run python` + `importlib.metadata.version("docmesh-py-core")` → `0.1.4`
- Installed export inspection: `.venv/lib/python3.11/site-packages/docmesh_py_core/__init__.py`
- Root export presence check:
  - absent: `Settings`, `load_settings`, `ServiceFactoryRegistry`
  - present: `CommonConfig`, `ServiceConfigs`, `load_service_configs`, `create_keycloak_client`, `create_sqlite_client`, `create_postgres_client`, `create_minio_client`, `create_milvus_client`, `create_ollama_client`, `create_langfuse_client`, `create_nats_client`, `close_service_clients`, `check_all_services`, `configure_logging`
- Key runtime signatures:
  - `load_service_configs(*, services: set[str] | None = None) -> ServiceConfigs`
  - `create_keycloak_client(config: KeycloakConfig) -> ServiceClientWrapper`
  - `close_service_clients(clients: Iterable[Any]) -> None`
  - `KeycloakAuthService(config: KeycloakConfig, ...)`
- Verification commands:
  - `uv run pytest --collect-only -q` → `45 tests collected`
  - `uv run pytest -q` → `45 passed, 2 warnings in 20.55s`

## Implemented / aligned

- `fastapi_core/docmesh_settings.py`는 이제 `Settings` / `load_settings` 대신 `ServiceConfigs` / `load_service_configs()`를 사용한다.
- 이 모듈은 기존 테스트/개발 편의를 유지하기 위해 누락된 환경변수 기본값만 임시로 주입한 뒤 `load_service_configs()`를 호출한다. 즉 old in-memory settings object 생성은 제거됐지만, 기존 overlay 기반 기본값 정책은 유지됐다.
- `fastapi_core/factory.py`는 `ServiceFactoryRegistry`를 제거하고 enabled service별로 `create_*_client()`를 직접 호출해 `app.state.service_clients`를 구성한다.
- readiness check wiring은 이제 `registry.create_client(service).check()`가 아니라 생성된 wrapper/builder의 `check` 메서드를 직접 사용한다.
- lifespan 종료 시 `registry.close_all()` 대신 `close_service_clients(app.state.service_clients.values())`를 호출한다.
- `fastapi_core/dependencies/config.py`와 `fastapi_core/dependencies/auth.py`는 `ServiceConfigs` 타입으로 전환됐다.
- auth provider fallback은 이제 `KeycloakAuthService(settings.keycloak, allowed_algorithms=["RS256"])`를 사용하므로 `v0.1.4` 생성 시그니처와 맞는다.
- 테스트 fixture도 `load_settings({...})`를 제거하고 `load_docmesh_settings(("keycloak", "sqlite"))` 기반으로 전환됐다.

## Resolved gaps from the initial v0.1.4 bump

- import 단계에서 깨지던 `load_settings` / `Settings` / `ServiceFactoryRegistry` 의존은 모두 제거됐다.
- `app.state.registry` 기반 테스트/런타임 가정은 `app.state.service_clients` 기반으로 대체됐다.
- auth dependency의 registry lookup 경로는 제거되고, cached provider 또는 `service_clients["keycloak"]`를 우선 사용하는 구조로 정리됐다.
- 전체 테스트 스위트가 다시 GREEN 상태로 돌아왔다.

## Remaining nuances

- readiness 계층은 `check_all_services()`의 동기 `CheckFn` 계약 위에 서 있다. `factory._wrap_readiness_check()`는 awaitable 결과를 동기 callable로 정규화하므로 `NatsConnectionBuilder.check()` 같은 async check도 현재 readiness 경로에서 처리한다. 이 동작은 factory 및 live NATS integration 테스트로 검증된다.
- 현재 변경은 `v0.1.4` public surface 적응을 목표로 한 것이므로, 이후 upstream에서 direct factory 표면이 더 바뀌면 `factory.py`의 서비스 매핑 테이블을 다시 점검해야 한다.

## Verdict

이번 마이그레이션 이후 fastapi-core는 더 이상 제거된 `Settings` / `load_settings` / `ServiceFactoryRegistry` 표면에 기대지 않는다. 현재 코드는 설치된 `docmesh-py-core v0.1.4`의 direct `ServiceConfigs` + `create_*_client()` + `close_service_clients()` 방향과 정합적이며, 2026-07-12 검증에서 `uv run pytest -q` 전체 스위트 `45 passed, 2 warnings`를 확인했다.
