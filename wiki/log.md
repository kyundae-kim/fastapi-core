# Wiki Log

> Chronological record of all wiki actions. Append-only.
> Format: `## [YYYY-MM-DD] action | subject`
> Actions: ingest, update, query, lint, create, archive, delete
> When this file exceeds 500 entries, rotate: rename to log-YYYY.md, start fresh.

## [2026-06-11] create | Wiki initialized
- Domain: FastAPI 기반 재사용 SDK 프로젝트 지식베이스
- Scope: 다양한 저장소 연동, LLM 연동, Keycloak 기반 인증/인가
- Structure created with SCHEMA.md, index.md, log.md
- Directories created: raw/articles, raw/papers, raw/transcripts, raw/assets, entities, concepts, comparisons, queries

## [2026-06-11] ingest | docmesh-py-core SDK 사용 가이드
- Source captured: `raw/articles/docmesh-py-core-sdk-2026-06-11.md`
- Created: `entities/docmesh-py-core.md`
- Created: `concepts/service-factory-registry.md`
- Created: `concepts/environment-driven-service-selection.md`
- Created: `concepts/sdk-health-check-patterns.md`
- Created: `concepts/keycloak-auth-integration.md`
- Updated: `index.md`

## [2026-06-11] ingest | docmesh-py-core API 가이드
- Source captured: `raw/articles/docmesh-py-core-api-2026-06-11.md`
- Created: `concepts/load-settings-and-settings-model.md`
- Created: `concepts/service-client-wrapper.md`
- Created: `concepts/nats-connection-builder.md`
- Created: `concepts/check-all-services.md`
- Created: `concepts/keycloak-provisioner.md`
- Created: `concepts/mask-sensitive-value.md`
- Updated: `entities/docmesh-py-core.md`
- Updated: `concepts/service-factory-registry.md`
- Updated: `concepts/keycloak-auth-integration.md`
- Updated: `concepts/sdk-health-check-patterns.md`
- Updated: `index.md`

## [2026-06-11] ingest | docmesh-py-core 설정 가이드
- Source captured: `raw/articles/docmesh-py-core-config-2026-06-11.md`
- Created: `concepts/configuration-principles.md`
- Created: `concepts/keycloak-configuration-rules.md`
- Created: `concepts/database-configuration-patterns.md`
- Created: `concepts/optional-observability-services.md`
- Created: `concepts/nats-configuration-and-auth-modes.md`
- Updated: `concepts/load-settings-and-settings-model.md`
- Updated: `concepts/mask-sensitive-value.md`
- Updated: `concepts/environment-driven-service-selection.md`
- Updated: `concepts/keycloak-auth-integration.md`
- Updated: `concepts/nats-connection-builder.md`
- Updated: `index.md`

## [2026-06-11] query | docmesh-py-core refactor review
- Filed: `queries/docmesh-py-core-refactor-review.md`
- Sources synthesized: `raw/articles/docmesh-py-core-sdk-2026-06-11.md`, `raw/articles/docmesh-py-core-api-2026-06-11.md`, `raw/articles/docmesh-py-core-config-2026-06-11.md`
- Updated: `index.md`

## [2026-06-11] query | fastapi-core codebase review against docmesh-py-core
- Filed: `queries/fastapi-core-codebase-review-against-docmesh-py-core.md`
- Code reviewed: `fastapi_core/factory.py`, `fastapi_core/core/config.py`, `fastapi_core/dependencies/*.py`, `fastapi_core/core/{auth,database,storage,messaging,langfuse,milvus,ollama}.py`
- Findings: duplicated service bootstrap/state management, request-time lazy init, no unified registry/close_all, readiness eager dependency creation
- Follow-up implementation: `fastapi_core/bootstrap.py` added, readiness eager DB/MinIO acquisition removed, dependency state helpers collapsed across config/auth/database/storage/ollama/milvus/async_milvus/messaging
- Follow-up implementation: `fastapi_core/lifecycle.py` added, managed app lifespan introduced, default `create_app()` wired to startup/shutdown bootstrap helpers, shutdown now disposes/drains registered resources
- Follow-up implementation: `LifecycleSettings` added, startup eager-init defaults now derive from health policy, `fastapi_core/docmesh_bridge.py` added for optional docmesh `load_settings` / `ServiceFactoryRegistry` / `check_all_services` integration, readiness can route through docmesh-style aggregated checks
- Follow-up implementation: docmesh bridge now translates `EnvConfig` to real `docmesh_py_core` flat env vars, `initialize_docmesh_registry(config=EnvConfig())` creates actual `Settings` + `ServiceFactoryRegistry`, lifecycle can populate real docmesh registry state
- Follow-up implementation: lifecycle startup now reuses `docmesh_registry.create_client(...)` for auth/database/minio/milvus/ollama/nats and tracks `docmesh_managed_services` to avoid duplicate shutdown of registry-owned stateful resources
- Follow-up implementation: request-time dependency fallback for auth/database/storage/messaging now prefers `docmesh_registry` (`keycloak`/`postgres`/`minio`/`nats`) before native client creation, using shared helpers in `fastapi_core/docmesh_bridge.py`
- Follow-up implementation: request-time fallback for `ollama` and sync `milvus` now also prefers `docmesh_registry`; `async_milvus` remains native because the current `docmesh_py_core 0.1.1` registry exposes only sync `MilvusClient`, not `AsyncMilvusClient`
- Verification: `uv run pytest -q -m 'not integration'` -> `187 passed, 44 deselected`; A-2 RED tests for ollama/milvus now pass, the broader remaining-dependency subset passes `34` tests, and the earlier registry-first fallback subset remains green; current lock/runtime package version remains `0.1.1` despite `pyproject.toml` declaring `>=0.1.4`
- Updated: `index.md`

## [2026-06-14] query | registry full replacement plan
- Filed: `queries/registry-full-replacement-plan.md`
- Sources synthesized: `queries/fastapi-core-codebase-review-against-docmesh-py-core.md`, `queries/docmesh-py-core-refactor-review.md`
- Artifact: `docs/plans/2026-06-14-registry-full-replacement.md`
- Updated: `index.md`

## [2026-06-16] ingest | fastapi-core PRD
- Source captured: `raw/articles/fastapi-core-prd-2026-06-16.md`
- Source file: `docs/prd.md`
- Created: `entities/fastapi-core.md`
- Created: `concepts/layered-configuration-model.md`
- Created: `concepts/fastapi-app-state-singletons.md`
- Created: `concepts/fastapi-app-factory-and-health-routes.md`
- Created: `queries/fastapi-core-prd-alignment-review.md`
- Updated: `index.md`

## [2026-06-16] query | fastapi-core PRD vs source code comparison
- Filed: `queries/fastapi-core-prd-vs-source-code-comparison.md`
- Sources synthesized: `raw/articles/fastapi-core-prd-2026-06-16.md`, `queries/fastapi-core-prd-alignment-review.md`, `queries/fastapi-core-codebase-review-against-docmesh-py-core.md`
- Verification: `uv run pytest -q -m 'not integration'` -> `146 passed, 26 deselected`
- Updated: `index.md`

## [2026-06-17] query | PRD gaps re-check
- Re-read: `raw/articles/fastapi-core-prd-2026-06-16.md`, `queries/fastapi-core-prd-vs-source-code-comparison.md`, `queries/fastapi-core-prd-alignment-review.md`
- Code verified: `fastapi_core/core/{auth,database,storage,milvus,langfuse}.py`, `fastapi_core/dependencies/{auth,messaging,ollama}.py`
- Verification: `uv run pytest -q -m 'not integration'` -> `146 passed, 26 deselected`
- Updated: `queries/fastapi-core-prd-vs-source-code-comparison.md`

## [2026-06-17] update | PostgreSQL helper surface
- Added tests: `test_fastapi_core/core/test_database.py`
- Updated: `fastapi_core/core/database.py`
- Verification: `uv run pytest -q test_fastapi_core/core/test_database.py` -> `4 passed`
- Verification: `uv run pytest -q test_fastapi_core/dependencies/test_database.py test_fastapi_core/core/test_database.py` -> `14 passed`
- Verification: `uv run pytest -q -m 'not integration'` -> `150 passed, 26 deselected`
- Updated: `queries/fastapi-core-prd-vs-source-code-comparison.md`

## [2026-06-17] update | MinIO helper surface
- Added tests: `test_fastapi_core/core/test_storage.py`
- Updated: `fastapi_core/core/storage.py`
- Verification: `uv run pytest -q test_fastapi_core/core/test_storage.py` -> `8 passed`
- Verification: `uv run pytest -q test_fastapi_core/dependencies/test_storage.py test_fastapi_core/core/test_storage.py` -> `15 passed`
- Verification: `uv run pytest -q -m 'not integration'` -> `155 passed, 26 deselected`
- Updated: `queries/fastapi-core-prd-vs-source-code-comparison.md`

## [2026-06-17] update | Milvus helper surface
- Added tests: `test_fastapi_core/core/test_milvus.py`, `test_fastapi_core/core/test_async_milvus.py`
- Updated: `fastapi_core/core/milvus.py`
- Verification: `uv run pytest -q test_fastapi_core/core/test_milvus.py test_fastapi_core/core/test_async_milvus.py` -> `13 passed`
- Verification: `uv run pytest -q test_fastapi_core/dependencies/test_milvus.py test_fastapi_core/dependencies/test_async_milvus.py test_fastapi_core/core/test_milvus.py test_fastapi_core/core/test_async_milvus.py` -> `26 passed`
- Verification: `uv run pytest -q -m 'not integration'` -> `165 passed, 26 deselected`
- Updated: `queries/fastapi-core-prd-vs-source-code-comparison.md`

## [2026-06-17] update | Ollama helper surface
- Added tests: `test_fastapi_core/core/test_ollama.py`
- Added: `fastapi_core/core/ollama.py`
- Verification: `uv run pytest -q test_fastapi_core/core/test_ollama.py` -> `6 passed`
- Verification: `uv run pytest -q test_fastapi_core/dependencies/test_ollama.py test_fastapi_core/core/test_ollama.py` -> `11 passed`
- Verification: `uv run pytest -q -m 'not integration'` -> `171 passed, 26 deselected`
- Updated: `docs/api.md`, `queries/fastapi-core-prd-vs-source-code-comparison.md`

## [2026-06-17] query | PRD gaps quick answer
- Re-read: `docs/prd.md`, `queries/fastapi-core-prd-vs-source-code-comparison.md`, `queries/fastapi-core-prd-alignment-review.md`
- Code verified: `fastapi_core/dependencies/{auth,messaging,langfuse}.py`, `fastapi_core/core/{config,langfuse}.py`, `fastapi_core/{factory,__init__}.py`, `fastapi_core/routers/health.py`
- Verification: `uv run pytest -q -m 'not integration'` -> `171 passed, 26 deselected`
- Result: no new gaps beyond previously filed NATS feature layer, unused introspection setting, and Langfuse lifecycle divergence

## [2026-06-17] update | PRD gap prioritization
- Updated: `queries/fastapi-core-prd-vs-source-code-comparison.md`
- Added: prioritized order P0(NATS), P1(introspection), P2(Langfuse contract), P3(PRD/docs refresh)
- Basis: code review of `fastapi_core/dependencies/{messaging,auth,langfuse}.py`, `fastapi_core/core/{config,langfuse}.py`

## [2026-06-17] update | NATS feature layer
- Added: `fastapi_core/core/messaging.py`
- Added tests: `test_fastapi_core/core/test_messaging.py`
- Updated: `docs/api.md`, `docs/messaging.md`, `README.md`, `queries/fastapi-core-prd-vs-source-code-comparison.md`
- RED verification: `uv run pytest -q test_fastapi_core/core/test_messaging.py::test_build_event_subject_formats_domain_entity_action` -> `ModuleNotFoundError: No module named 'fastapi_core.core.messaging'`
- Verification: `uv run pytest -q test_fastapi_core/core/test_messaging.py` -> `6 passed`
- Verification: `uv run pytest -q test_fastapi_core/core/test_messaging.py test_fastapi_core/dependencies/test_messaging.py test_fastapi_core/test_public_api.py` -> `13 passed`
- Verification: `uv run pytest -q -m 'not integration'` -> `177 passed, 26 deselected`

## [2026-06-17] query | PRD vs code re-check
- Re-read: `docs/prd.md`, `queries/fastapi-core-prd-vs-source-code-comparison.md`, `queries/fastapi-core-prd-alignment-review.md`
- Code verified: `fastapi_core/dependencies/auth.py`, `fastapi_core/core/config.py`, `fastapi_core/dependencies/langfuse.py`, `fastapi_core/core/langfuse.py`, `fastapi_core/lifecycle.py`, `fastapi_core/core/messaging.py`, `fastapi_core/dependencies/messaging.py`, `fastapi_core/factory.py`, `fastapi_core/routers/health.py`, `fastapi_core/__init__.py`
- Verification: `uv run pytest -q -m 'not integration'` -> `177 passed, 26 deselected`
- Result: broad alignment remains good; remaining gaps are Keycloak introspection runtime wiring and PRD/code divergence around Langfuse and package structure

## [2026-06-17] update | Keycloak introspection runtime wiring
- Added tests first: `test_fastapi_core/dependencies/test_security.py::test_get_current_user_uses_introspection_when_enabled`, `test_fastapi_core/core/test_security.py::test_introspect_token_returns_payload_for_active_token`
- RED verification: `uv run pytest -q test_fastapi_core/dependencies/test_security.py::test_get_current_user_uses_introspection_when_enabled` -> `401 != 200`
- RED verification: `uv run pytest -q test_fastapi_core/core/test_security.py::test_introspect_token_returns_payload_for_active_token` -> `AttributeError: 'KeycloakAuthProvider' object has no attribute 'introspect_token'`
- Updated: `fastapi_core/core/auth.py`, `fastapi_core/dependencies/auth.py`, `docs/api.md`, `wiki/queries/fastapi-core-prd-vs-source-code-comparison.md`
- Verification: `uv run pytest -q test_fastapi_core/core/test_security.py::test_introspect_token_returns_payload_for_active_token` -> `1 passed`
- Verification: `uv run pytest -q test_fastapi_core/dependencies/test_security.py::test_get_current_user_uses_introspection_when_enabled` -> `1 passed`
- Verification: `uv run pytest -q test_fastapi_core/core/test_security.py test_fastapi_core/dependencies/test_security.py` -> `29 passed`
- Verification: `uv run pytest -q -m 'not integration'` -> `179 passed, 26 deselected`
- Updated: `wiki/queries/fastapi-core-prd-vs-source-code-comparison.md` now treats introspection gap as closed and reprioritizes remaining doc/architecture differences

## [2026-06-17] query | PRD vs code re-check (Langfuse + package structure)
- Re-read: `docs/prd.md`, `wiki/queries/fastapi-core-prd-vs-source-code-comparison.md`, `wiki/SCHEMA.md`, `wiki/index.md`
- Code verified: `fastapi_core/core/langfuse.py`, `fastapi_core/dependencies/langfuse.py`, `fastapi_core/lifecycle.py`, `fastapi_core/factory.py`, `fastapi_core/__init__.py`
- Tree verified: `fastapi_core/bootstrap.py`, `fastapi_core/docmesh_bridge.py`, `fastapi_core/lifecycle.py`, `fastapi_core/dependencies/langfuse.py`
- Verification: `uv run pytest -q test_fastapi_core/core/test_langfuse.py test_fastapi_core/dependencies/test_langfuse.py test_fastapi_core/test_lifecycle.py` -> `17 passed, 1 warning`
- Verification: `uv run pytest -q -m 'not integration'` -> `179 passed, 26 deselected, 5 warnings`
- Updated: `wiki/queries/fastapi-core-prd-vs-source-code-comparison.md`
- Result: remaining PRD/code gaps are primarily Langfuse lifecycle contract divergence and package-structure documentation drift, not missing runtime features

## [2026-06-17] update | PRD/API docs sync for Langfuse and package structure
- Updated: `docs/prd.md`, `docs/api.md`, `wiki/queries/fastapi-core-prd-vs-source-code-comparison.md`
- Synced: Langfuse state/dependency lifecycle contract, package structure (`bootstrap.py`, `docmesh_bridge.py`, `lifecycle.py`, `dependencies/langfuse.py`), and `create_app()` managed lifespan behavior
- Verification: `uv run pytest -q test_fastapi_core/core/test_langfuse.py test_fastapi_core/dependencies/test_langfuse.py test_fastapi_core/test_lifecycle.py` -> `17 passed, 1 warning`
- Stale-doc search: no remaining matches for old claims about "no Langfuse dependency module" or "lifespan 없이 생성" in `docs/*.md`
- Result: PRD/code comparison now reads as broad alignment with remaining differences mostly at documentation detail / architecture emphasis level

## [2026-06-17] ingest | fastapi-core PRD refresh
- Source re-ingested with drift: `raw/articles/fastapi-core-prd-2026-06-16.md`
- Source file: `docs/prd.md`
- Updated: `entities/fastapi-core.md`
- Updated: `concepts/layered-configuration-model.md`
- Updated: `concepts/fastapi-app-state-singletons.md`
- Updated: `concepts/fastapi-app-factory-and-health-routes.md`
- Created: `concepts/curated-public-api-surface.md`
- Created: `concepts/registry-backed-dependency-resolution.md`
- Updated: `queries/fastapi-core-prd-alignment-review.md`
- Updated: `index.md`

## [2026-06-17] ingest | fastapi-core API docs
- Source captured: `raw/articles/fastapi-core-api-2026-06-17.md`
- Source file: `docs/api.md`
- Updated: `entities/fastapi-core.md`
- Updated: `concepts/curated-public-api-surface.md`
- Updated: `concepts/registry-backed-dependency-resolution.md`
- Updated: `concepts/fastapi-app-state-singletons.md`
- Created: `concepts/function-style-fastapi-dependencies.md`
- Updated: `index.md`

## [2026-06-17] ingest | fastapi-core config docs
- Source captured: `raw/articles/fastapi-core-config-2026-06-17.md`
- Source file: `docs/config.md`
- Updated: `entities/fastapi-core.md`
- Updated: `concepts/layered-configuration-model.md`
- Updated: `concepts/configuration-principles.md`
- Updated: `concepts/database-configuration-patterns.md`
- Updated: `concepts/keycloak-configuration-rules.md`
- Updated: `concepts/nats-configuration-and-auth-modes.md`
- Updated: `concepts/optional-observability-services.md`
- Updated: `concepts/load-settings-and-settings-model.md`
- Created: `concepts/lifecycle-policy-resolution.md`
- Updated: `index.md`

## [2026-06-18] ingest | fastapi-core messaging docs
- Source captured: `raw/articles/fastapi-core-messaging-2026-06-18.md`
- Source file: `docs/messaging.md`
- Created: `concepts/nats-event-helper-layer.md`
- Updated: `entities/fastapi-core.md`
- Updated: `concepts/nats-configuration-and-auth-modes.md`
- Updated: `concepts/registry-backed-dependency-resolution.md`
- Updated: `index.md`

## [2026-06-18] lint | 11 issues found
- Broken wikilinks: 0
- Orphan pages: 0
- Source drift: 6
- Contested pages: 0
- Stale pages: 0
- Frontmatter/tag/style issues: 5

## [2026-06-24] query | docmesh-py-core package summary
- Filed: `queries/docmesh-py-core-package-summary.md`
- Sources synthesized: `raw/articles/docmesh-py-core-sdk-2026-06-11.md`, `raw/articles/docmesh-py-core-api-2026-06-11.md`, `raw/articles/docmesh-py-core-config-2026-06-11.md`

## [2026-06-24] query | docmesh-py-core package structure summary
- Filed: `queries/docmesh-py-core-package-structure-summary.md`
- Sources synthesized: `raw/articles/docmesh-py-core-sdk-2026-06-11.md`, `raw/articles/docmesh-py-core-api-2026-06-11.md`, `raw/articles/docmesh-py-core-config-2026-06-11.md`

## [2026-06-24] query | docmesh-py-core quick summary
- Re-read: `entities/docmesh-py-core.md`, `queries/docmesh-py-core-package-summary.md`, `queries/docmesh-py-core-package-structure-summary.md`
- Filed: none (reused existing query pages)

## [2026-06-24] query | config duplication analysis
- Filed: `queries/config-duplication-analysis.md`
- Code reviewed: `fastapi_core/core/config.py`, `fastapi_core/docmesh_bridge.py`, `fastapi_core/dependencies/{config,milvus,async_milvus}.py`, `fastapi_core/factory.py`, `fastapi_core/lifecycle.py`, `fastapi_core/__init__.py`
- Artifact: `docs/plans/2026-06-24-config-dedup-refactor-plan.md`
- Updated: `index.md`

## [2026-06-24] update | config dedup first slice
- Updated: `fastapi_core/core/config.py`, `fastapi_core/docmesh_bridge.py`, `fastapi_core/dependencies/milvus.py`, `fastapi_core/dependencies/async_milvus.py`, `test_fastapi_core/core/test_config.py`, `wiki/queries/config-duplication-analysis.md`
- Removed dead surface: `ApplicationSettings`, `load_application_settings()`
- Moved: `load_docmesh_settings()` and `resolve_milvus_config()` from `core/config.py` to `docmesh_bridge.py`
- Verification: `uv run pytest -q test_fastapi_core/core/test_config.py test_fastapi_core/dependencies/test_milvus.py test_fastapi_core/dependencies/test_async_milvus.py test_fastapi_core/test_public_api.py` -> `34 passed`
- Verification: `uv run pytest -q -m 'not integration'` -> `189 passed, 26 deselected`
