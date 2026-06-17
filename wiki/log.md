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
