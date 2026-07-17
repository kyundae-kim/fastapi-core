---
title: docmesh-py-core vs fastapi-core usage comparison
created: 2026-06-29
updated: 2026-07-17
type: query
tags: [query, comparison, implementation, api]
sources: [raw/articles/docmesh-py-core-api-reference-v0.2.0.md, raw/articles/docmesh-py-core-configuration-guide-v0.2.0.md, raw/articles/docmesh-py-core-examples-guide-v0.2.0.md, pyproject.toml, .venv/lib/python3.11/site-packages/docmesh_py_core/__init__.py, .venv/lib/python3.11/site-packages/docmesh_py_core/config.py, .venv/lib/python3.11/site-packages/docmesh_py_core/factories.py, .venv/lib/python3.11/site-packages/docmesh_py_core/health.py, fastapi_core/config.py, fastapi_core/docmesh_settings.py, fastapi_core/dependencies/auth.py, fastapi_core/dependencies/services.py, fastapi_core/routers/auth.py, fastapi_core/routers/health.py, fastapi_core/factory.py, test_fastapi_core/conftest.py, test_fastapi_core/test_factory.py, test_fastapi_core/test_health_router.py, test_fastapi_core/test_auth_router.py, test_fastapi_core/test_dependencies.py, test_fastapi_core/test_config.py, test_fastapi_core/integration/]
confidence: high
---

# docmesh-py-core vs fastapi-core usage comparison

## Question

`docmesh-py-core`를 `v0.2.0`으로 올린 뒤, fastapi-core가 새 assembly-first 및 async lifecycle API를 어디까지 반영했는지 점검한다.

## Verification baseline

- Dependency pin: `pyproject.toml`의 `tool.uv.sources.docmesh-py-core.rev = "v0.2.0"`
- Installed package version: `uv run python` + `importlib.metadata.version("docmesh-py-core")` → `0.2.0`
- Installed export inspection: `.venv/lib/python3.11/site-packages/docmesh_py_core/__init__.py`
- v0.2.0 핵심 공개 표면:
  - assembly: `assemble_services`, async `assemble_service_runtime`, `ServiceBundle`, `ServiceRuntime`
  - async lifecycle: `async_check_all_services`, `async_close_service_clients`
  - direct API: `load_service_configs`, `create_*_client`, `check_all_services`, `close_service_clients`
- Key runtime signatures:
  - `load_service_configs(env: Mapping[str, str] | None = None, *, services: set[str] | None = None)`
  - `async assemble_service_runtime(env, *, services=None, required=None, one_of=(), check_on_startup=False, ...) -> ServiceRuntime`
  - `async_check_all_services(..., timeout_seconds=None, overall_timeout_seconds=None)`
  - `async_close_service_clients(clients) -> None`
  - `async ServiceRuntime.check(...)` / `async ServiceRuntime.close()`
- Verification commands:
  - installed API signature/source inspection with `uv run python`
  - `uv run pytest -q` → `78 passed, 2 third-party deprecation warnings`
  - NATS unawaited-close runtime warning is no longer present

## Implemented / aligned

- dependency pin과 설치 패키지는 모두 v0.2.0으로 정렬되어 있다.
- 기존 direct `ServiceConfigs` + `create_*_client()` 경로는 v0.2.0에서도 지원되므로 현재 import와 client 생성은 깨지지 않는다.
- `ServiceConfigs`, typed service dependency, auth provider 및 readiness 결과 모델은 기존 테스트를 통과한다.
- `load_service_configs()`가 production 보안 검증을 수행하므로 `DOCMESH_SECURITY_MODE` / production alias 기반 제약은 로더를 통해 적용된다.
- password grant endpoint는 함수 인자로 username/password를 전달하므로 v0.2.0의 config fallback과 호환된다.
- shutdown은 `finally`에서 `await ServiceRuntime.close()`를 실행하며, runtime 내부의 async cleanup으로 sync/async client와 custom lifespan 예외를 모두 처리한다.
- readiness는 `await async_check_all_services(...)`를 사용하며 필수 실패 시 `HealthCheckError.result`의 전체 서비스 상태를 보존한다.
- 기본 `create_app()` 경로는 lifespan startup에서 `assemble_service_runtime(...)`을 사용하고 runtime/configs/clients를 `app.state`에 설치한다.
- 외부 조립·테스트 경로는 완성된 `ServiceRuntime`을 `create_app(runtime=...)`으로 주입할 수 있다. 기존 `settings=` direct factory 경로는 deprecated 호환 경계이며 두 주입 인자는 함께 사용할 수 없다.
- `load_docmesh_settings()`는 overlay mapping을 `load_service_configs(env, ...)`에 직접 전달하며 프로세스 환경을 변경하지 않는다.
- `DOCMESH_HEALTHCHECK_ENABLED`는 기본값 `False`인 `AppConfig.startup_healthcheck`로 연결된다.
- fastapi-core v0.3의 managed resource와 typed readiness registry는 Py Core runtime 위에 애플리케이션 고유 자원을 합성하며, 기존 `ServiceRuntime` 소유권을 중복하지 않는다.

## Resolved in P0

### P0 — async cleanup 결함 해소

- `factory._build_lifespan()`이 `try/finally`에서 `await ServiceRuntime.close()`를 호출한다.
- async client close await와 custom lifespan shutdown 실패 시 cleanup을 각각 회귀 테스트로 고정했다.
- 전체 테스트에서 NATS unawaited-coroutine warning이 제거됐다.

### P0 — readiness를 native async 경로로 전환

- health router가 `await async_check_all_services(...)`를 사용한다.
- `_run_awaitable_synchronously()`와 별도 thread/event-loop bridge를 제거했다.
- required 실패 시 `HealthCheckError.result`를 사용해 성공한 선택 서비스를 포함한 전체 details를 반환한다.

## Resolved in P1

### P1 — mapping 기반 설정 로딩

- `load_docmesh_settings()`가 `build_docmesh_env_overlay()` 결과를 `load_service_configs(env, ...)`에 직접 전달한다.
- `_apply_missing_docmesh_defaults()`와 프로세스 환경 임시 변경을 제거했고, 환경 불변성을 회귀 테스트로 고정했다.

### P1 — 정책 연결

- 기본 앱 경로는 `assemble_service_runtime(...)`에 `enabled_services`, `required_services`, startup healthcheck, 병렬 정책을 전달한다.
- `DOCMESH_HEALTHCHECK_ENABLED`를 `AppConfig.startup_healthcheck`에 연결했으며 기본값은 `False`다.
- 명시적 `settings` 주입 경로도 `ServiceRuntime`으로 감싸 동일한 check/close lifecycle을 사용한다.

## Resolved in P2

### P2 — 운영 정책과 검증

- per-service/overall healthcheck timeout을 startup runtime과 readiness endpoint에 동일하게 연결했다.
- `DOCMESH_SERVICE_ALTERNATIVES`를 assembly `one_of` 검증으로 연결하고 명시적 settings 주입 경로에서도 대안 정책을 검증한다.
- startup healthcheck 실패 시 생성 client rollback과 custom lifespan 미진입을 실제 assembly 경로로 검증했다.
- `ServiceCloseError`는 실패 개수만 담은 `service_runtime_close_failed` 이벤트로 기록한 뒤 전파한다.
- `docs/config.md`에 `DOCMESH_SECURITY_MODE`, `DOCMESH_PRODUCTION_ALIASES`, healthcheck 정책, password-grant fallback을 반영했다.

## Verdict

P0의 async cleanup/readiness, P1의 assembly/config 정책, P2의 timeout/`one_of`/rollback/close-failure 운영 정책이 모두 반영됐다. fastapi-core v0.3은 그 위에 managed resource와 typed readiness 확장을 제공하며 현재 기준선은 `78 passed, 2 third-party deprecation warnings`다. Py Core v0.2.0 반영 관점의 P0~P2 격차는 해소됐다.
