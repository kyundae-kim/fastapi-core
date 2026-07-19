# Wiki Log

> Chronological record of all wiki actions. Append-only.
> Format: `## [YYYY-MM-DD] action | subject`
> Actions: ingest, update, query, lint, create, archive, delete
> When this file exceeds 500 entries, rotate: rename to log-YYYY.md, start fresh.

## [2026-06-25] create | Wiki initialized
- Domain: fastapi-core engineering wiki
- Structure created with SCHEMA.md, index.md, log.md
- Directories created: raw/articles, raw/papers, raw/transcripts, raw/assets, entities, concepts, comparisons, queries

## [2026-06-25] update | Wiki domain renamed
- Domain updated from: fastapi-core engineering wiki
- Domain updated to: fastapi-core backend implementation wiki

## [2026-06-25] ingest | docmesh-py-core API Reference
- Source URL: https://github.com/kyundae-kim/docmesh-py-core/blob/main/docs/api.md
- Raw file created: raw/articles/docmesh-py-core-api-reference-2026.md
- Wiki files created: entities/docmesh-py-core.md, concepts/keycloak-authentication-api.md, concepts/service-factory-registry.md, concepts/service-health-check-aggregation.md
- Navigation updated: index.md

## [2026-06-25] ingest | docmesh-py-core Configuration Guide
- Source URL: https://github.com/kyundae-kim/docmesh-py-core/blob/main/docs/config.md
- Raw file created: raw/articles/docmesh-py-core-configuration-guide-2026.md
- Wiki files created: concepts/service-configuration-contracts.md
- Wiki files updated: entities/docmesh-py-core.md, concepts/keycloak-authentication-api.md
- Navigation updated: index.md

## [2026-06-29] ingest | docmesh-py-core API Reference
- Source URL: https://github.com/kyundae-kim/docmesh-py-core/blob/main/docs/api.md
- Raw file updated: raw/articles/docmesh-py-core-api-reference-2026.md
- Wiki file created: concepts/operational-logging-and-retry-utilities.md
- Wiki files updated: entities/docmesh-py-core.md, concepts/keycloak-authentication-api.md, concepts/service-configuration-contracts.md, concepts/service-factory-registry.md, concepts/service-health-check-aggregation.md
- Navigation updated: index.md

## [2026-06-29] ingest | docmesh-py-core Configuration Guide
- Source URL: https://github.com/kyundae-kim/docmesh-py-core/blob/main/docs/config.md
- Raw file updated: raw/articles/docmesh-py-core-configuration-guide-2026.md
- Wiki files updated: concepts/keycloak-authentication-api.md, concepts/operational-logging-and-retry-utilities.md, concepts/service-configuration-contracts.md
- Navigation updated: index.md (no entry changes required)

## [2026-06-29] ingest | docmesh-py-core Examples
- Source URL: https://github.com/kyundae-kim/docmesh-py-core/blob/main/docs/examples.md
- Raw file created: raw/articles/docmesh-py-core-examples-guide-2026.md
- Wiki file created: concepts/application-integration-patterns.md
- Wiki files updated: entities/docmesh-py-core.md, concepts/keycloak-authentication-api.md, concepts/operational-logging-and-retry-utilities.md, concepts/service-configuration-contracts.md, concepts/service-factory-registry.md, concepts/service-health-check-aggregation.md
- Navigation updated: index.md

## [2026-06-29] query | docmesh-py-core vs fastapi-core usage comparison
- Re-read orientation files: SCHEMA.md, index.md, log.md
- Compared files: pyproject.toml, .venv/lib/python3.11/site-packages/docmesh_py_core/__init__.py, fastapi_core/config.py, fastapi_core/dependencies/auth.py, fastapi_core/routers/health.py, fastapi_core/factory.py, test_fastapi_core/conftest.py
- Verification command: `uv run pytest -q` → `12 passed, 1 warning in 0.24s`
- Wiki file created: queries/docmesh-py-core-vs-fastapi-core-usage-comparison.md
- Wiki file updated: entities/docmesh-py-core.md
- Navigation updated: index.md

## [2026-06-29] update | doc and wiki sync after source comparison
- Re-verified source/docs alignment for README.md, docs/api.md, docs/config.md, docs/messaging.md, docs/test.md, docs/srs.md, docs/examples.md
- Re-read comparison artifact: queries/docmesh-py-core-vs-fastapi-core-usage-comparison.md
- Wiki files updated: queries/docmesh-py-core-vs-fastapi-core-usage-comparison.md, entities/docmesh-py-core.md
- Verification command: `uv run pytest -q` → `25 passed, 1 warning`

## [2026-07-02] ingest | docmesh-py-core API Reference
- Source URL: https://github.com/kyundae-kim/docmesh-py-core/blob/main/docs/api.md
- Raw file updated after sha drift detected: raw/articles/docmesh-py-core-api-reference-2026.md
- Wiki files updated: entities/docmesh-py-core.md, concepts/application-integration-patterns.md, concepts/keycloak-authentication-api.md, concepts/operational-logging-and-retry-utilities.md, concepts/service-configuration-contracts.md, concepts/service-factory-registry.md, concepts/service-health-check-aggregation.md
- Navigation updated: index.md (total pages unchanged)
- Notes: latest API reference now emphasizes direct config classes + `create_*_client()` / `close_service_clients()` and no longer documents `ServiceFactoryRegistry` in the root export list

## [2026-07-02] ingest | docmesh-py-core Configuration Guide
- Source URL: https://github.com/kyundae-kim/docmesh-py-core/blob/main/docs/config.md
- Raw file updated after sha drift detected: raw/articles/docmesh-py-core-configuration-guide-2026.md
- Wiki files updated: concepts/keycloak-authentication-api.md, concepts/operational-logging-and-retry-utilities.md, concepts/service-configuration-contracts.md
- Navigation updated: index.md (no entry changes required)
- Notes: latest config guide now documents direct config classes, `load_service_configs()`, `KEYCLOAK_CLIENT_PUBLIC`, production-only security enforcement, and several config fields that exist in models but are not consumed directly by current client factories

## [2026-07-02] ingest | docmesh-py-core Examples
- Source URL: https://github.com/kyundae-kim/docmesh-py-core/blob/main/docs/examples.md
- Raw file updated after sha drift detected: raw/articles/docmesh-py-core-examples-guide-2026.md
- Wiki files updated: entities/docmesh-py-core.md, concepts/application-integration-patterns.md, concepts/service-factory-registry.md, concepts/service-health-check-aggregation.md
- Navigation updated: index.md (no entry changes required)
- Notes: latest examples now align with direct `load_service_configs()` + `create_*_client()` + `close_service_clients()` flows and no longer present registry-first examples as the main integration path

## [2026-07-02] query | docmesh-py-core vs fastapi-core usage comparison
- Re-read comparison artifact: queries/docmesh-py-core-vs-fastapi-core-usage-comparison.md
- Compared files: pyproject.toml, .venv/lib/python3.11/site-packages/docmesh_py_core/__init__.py, fastapi_core/docmesh_settings.py, fastapi_core/factory.py, test_fastapi_core/conftest.py, test_fastapi_core/test_factory.py, test_fastapi_core/test_health_router.py
- Verification commands:
  - `uv run python - <<'PY' ... importlib.metadata.version('docmesh-py-core') ... PY` → `0.1.3`
  - `uv run python - <<'PY' ... __all__ membership check ... PY` → `Settings/load_settings/ServiceFactoryRegistry=True`, `load_service_configs/create_postgres_client/close_service_clients/CommonConfig/KeycloakConfig=False`
  - `uv run pytest -q` → `25 passed, 1 warning in 0.37s`
- Wiki file updated: queries/docmesh-py-core-vs-fastapi-core-usage-comparison.md
- Notes: fastapi-core remains aligned with the installed pinned v0.1.3 package surface, while the latest upstream docs on main have moved ahead to direct config/direct factory patterns

## [2026-07-02] query | docmesh-py-core vs fastapi-core usage comparison
- Re-read comparison artifact: queries/docmesh-py-core-vs-fastapi-core-usage-comparison.md
- Compared files: pyproject.toml, .venv/lib/python3.11/site-packages/docmesh_py_core/__init__.py, .venv/lib/python3.11/site-packages/docmesh_py_core/config.py, .venv/lib/python3.11/site-packages/docmesh_py_core/factories.py, .venv/lib/python3.11/site-packages/docmesh_py_core/keycloak.py, fastapi_core/docmesh_settings.py, fastapi_core/factory.py, fastapi_core/dependencies/config.py, fastapi_core/dependencies/auth.py, test_fastapi_core/conftest.py, test_fastapi_core/test_factory.py, test_fastapi_core/test_dependencies.py, test_fastapi_core/test_config.py, test_fastapi_core/test_auth_router.py, test_fastapi_core/test_health_router.py
- Verification commands:
  - `uv run python - <<'PY' ... importlib.metadata.version('docmesh-py-core') ... PY` → `0.1.4`
  - `uv run python - <<'PY' ... __all__ membership check ... PY` → `Settings/load_settings/ServiceFactoryRegistry=False`, `load_service_configs/CommonConfig/ServiceConfigs/create_*_client/close_service_clients=True`
  - `uv run python - <<'PY' ... inspect.signature(...) ... PY` → `load_service_configs(*, services: set[str] | None = None)`, `create_keycloak_client(config: KeycloakConfig)`, `close_service_clients(clients: Iterable[Any])`, `KeycloakAuthService(config: KeycloakConfig, ...)`
  - `uv run pytest -q` → `ImportError while loading conftest ... cannot import name 'load_settings' from 'docmesh_py_core'`
- Wiki file updated: queries/docmesh-py-core-vs-fastapi-core-usage-comparison.md
- Notes: after the v0.1.4 bump, fastapi-core is no longer aligned with the installed runtime package; the app/test wiring must migrate from `Settings`/`load_settings`/`ServiceFactoryRegistry` to `ServiceConfigs`/`load_service_configs`/`create_*_client` + `close_service_clients`

## [2026-07-02] query | docmesh-py-core vs fastapi-core usage comparison
- Re-read comparison artifact: queries/docmesh-py-core-vs-fastapi-core-usage-comparison.md
- Compared files: fastapi_core/docmesh_settings.py, fastapi_core/factory.py, fastapi_core/dependencies/config.py, fastapi_core/dependencies/auth.py, test_fastapi_core/conftest.py, test_fastapi_core/test_factory.py, test_fastapi_core/test_dependencies.py, test_fastapi_core/test_config.py
- Verification commands:
  - `uv run pytest -q test_fastapi_core/test_factory.py test_fastapi_core/test_dependencies.py test_fastapi_core/test_config.py` → `13 passed, 1 warning in 0.08s`
  - `uv run pytest -q` → `25 passed, 1 warning in 0.14s`
  - `search_files 'load_settings|ServiceFactoryRegistry|\bSettings\b|state\.registry' ...` → no remaining source references
- Wiki file updated: queries/docmesh-py-core-vs-fastapi-core-usage-comparison.md
- Notes: fastapi-core now matches the installed `docmesh-py-core v0.1.4` direct `ServiceConfigs` / `create_*_client` / `close_service_clients` integration model

## [2026-07-02] query | docs/api.md current-implementation caveats
- Re-read orientation files earlier in session: SCHEMA.md, index.md, log.md
- Reviewed source document: docs/api.md
- Reviewed implementation files: fastapi_core/factory.py, fastapi_core/routers/auth.py, fastapi_core/routers/health.py, fastapi_core/dependencies/auth.py, fastapi_core/dependencies/config.py, fastapi_core/config.py, fastapi_core/docmesh_settings.py
- Verification command: `uv run pytest -q` → `38 passed, 2 warnings in 20.47s`
- No new wiki page filed: answered from the source document plus direct code re-check

## [2026-07-13] ingest | docmesh-py-core v0.2.0 API reference
- Captured immutable versioned source: raw/articles/docmesh-py-core-api-reference-v0.2.0.md
- Updated existing pages: entities/docmesh-py-core.md, concepts/application-integration-patterns.md, concepts/service-configuration-contracts.md, concepts/service-health-check-aggregation.md, concepts/keycloak-authentication-api.md, concepts/operational-logging-and-retry-utilities.md
- Updated navigation: index.md (last-updated date retained page count at 8)
- Notes: v0.2.0 documents assembly-first integration (`assemble_services()` / `assemble_service_runtime()`), async health and cleanup helpers, `DOCMESH_SECURITY_MODE` precedence, and password-grant config fallback.

## [2026-07-13] ingest | docmesh-py-core v0.2.0 configuration guide
- Captured immutable versioned source: raw/articles/docmesh-py-core-configuration-guide-v0.2.0.md
- Updated existing pages: entities/docmesh-py-core.md, concepts/service-configuration-contracts.md, concepts/application-integration-patterns.md, concepts/keycloak-authentication-api.md
- Updated navigation: index.md (last-updated date and page count remain current at 8)
- Notes: configuration guidance confirms assembly-first lifecycle, mapping-only config loading, explicit startup-health policy ownership, and password-grant credential fallback.

## [2026-07-13] ingest | docmesh-py-core v0.2.0 examples
- Captured immutable versioned source: raw/articles/docmesh-py-core-examples-guide-v0.2.0.md
- Updated existing pages: entities/docmesh-py-core.md, concepts/application-integration-patterns.md, concepts/service-health-check-aggregation.md, concepts/operational-logging-and-retry-utilities.md
- Updated navigation: index.md (last-updated date and page count remain current at 8)
- Notes: examples provide concrete `ServiceBundle`/`ServiceRuntime` FastAPI lifespan usage, current health endpoint handling, password-grant fallback, and logging setup.

## [2026-07-13] ingest | fastapi-core PRD v0.4
- Source URL: file:///workspaces/fastapi-core/docs/prd.md
- Raw file created: raw/articles/fastapi-core-prd-v0.4.md
- Body sha256: `77f9caf8820ec2d803606f2445d2019777a1969a8e976287cda012fee267fab6`

## [2026-07-13] query | fastapi-core PRD vs source-code comparison
- Re-read orientation files: SCHEMA.md, index.md, log.md
- Compared document: docs/prd.md v0.4
- Inspected implementation: pyproject.toml, fastapi_core/config.py, fastapi_core/docmesh_settings.py, fastapi_core/factory.py, fastapi_core/dependencies/, fastapi_core/routers/, fastapi_core/schemas/
- Inspected tests: test_fastapi_core unit tests and integration tests for Keycloak, NATS, PostgreSQL readiness, and custom lifespan
- Verification commands:
  - `uv run pytest -q` → `45 passed, 8 warnings in 21.52s`
  - installed API inspection → `docmesh-py-core 0.2.0`; `assemble_service_runtime()` and `ServiceRuntime.close()` are async, while `close_service_clients()` is sync
- Wiki file created: queries/fastapi-core-prd-vs-source-code-comparison.md
- Navigation updated: index.md (total pages 9)
- Verdict: capabilities are broadly aligned; FR-051 remains partial because NATS async close is not awaited and cleanup is not exception-safe.

## [2026-07-13] query | docmesh-py-core v0.2.0 reflection points
- Refreshed existing comparison: queries/docmesh-py-core-vs-fastapi-core-usage-comparison.md
- Compared installed v0.2.0 signatures/source with fastapi_core/factory.py, docmesh_settings.py, health router, dependencies, docs, and tests.
- Verification command: `uv run pytest -q` → `45 passed, 8 warnings in 21.52s`
- Key finding: direct APIs remain compatible, but NATS async close is not awaited; native async runtime/readiness and mapping-based config loading remain to be adopted.
- Navigation summary updated: index.md (total pages unchanged at 9)

## [2026-07-13] update | docmesh-py-core v0.2.0 P0 lifecycle and readiness alignment
- Updated implementation: fastapi_core/factory.py, fastapi_core/routers/health.py
- Added regression coverage: test_fastapi_core/test_factory.py, test_fastapi_core/test_health_router.py
- Synced docs: README.md, docs/api.md, docs/examples.md, docs/messaging.md, docs/srs.md, docs/test.md
- Refreshed comparisons: queries/docmesh-py-core-vs-fastapi-core-usage-comparison.md, queries/fastapi-core-prd-vs-source-code-comparison.md
- Verification commands:
  - `uv run pytest -q -m 'not integration'` → `37 passed, 11 deselected, 2 warnings in 0.32s`
  - `uv run pytest -q -m integration` → `11 passed, 37 deselected, 2 warnings in 20.50s`
  - `uv run pytest -q` → `48 passed, 2 warnings in 20.63s`
- Outcome: async client close is awaited in a finally block, readiness uses native async aggregation, required failures preserve all service results, and the NATS unawaited-coroutine warning is removed.

## [2026-07-13] update | docmesh-py-core v0.2.0 P1 assembly and config alignment
- Updated implementation: fastapi_core/config.py, fastapi_core/docmesh_settings.py, fastapi_core/factory.py, fastapi_core/dependencies/config.py
- Added regression coverage: test_fastapi_core/test_config.py, test_fastapi_core/test_factory.py, test_fastapi_core/test_dependencies.py
- Default app path now assembles `ServiceRuntime` during lifespan startup and exposes it through `app.state.service_runtime` while preserving settings/service_clients state keys.
- Mapping-based config loading no longer mutates `os.environ`; enabled/required/startup-health/parallel policies are passed to the v0.2.0 runtime assembly API.
- Synced docs: README.md, docs/api.md, docs/config.md, docs/examples.md, docs/messaging.md, docs/srs.md, docs/test.md
- Refreshed comparisons and navigation: queries/docmesh-py-core-vs-fastapi-core-usage-comparison.md, queries/fastapi-core-prd-vs-source-code-comparison.md, index.md
- Verification commands:
  - `uv run pytest -q -m 'not integration'` → `41 passed, 11 deselected, 2 warnings in 0.33s`
  - `uv run pytest -q -m integration` → `11 passed, 41 deselected, 2 warnings in 20.41s`
  - `uv run pytest -q` → `52 passed, 2 warnings in 20.65s`

## [2026-07-13] update | docmesh-py-core v0.2.0 P2 operational policy alignment
- Updated implementation: fastapi_core/config.py, fastapi_core/factory.py, fastapi_core/routers/health.py
- Added regression coverage: test_fastapi_core/test_config.py, test_fastapi_core/test_factory.py, test_fastapi_core/test_health_router.py
- Added per-service/overall healthcheck timeout policy to startup checks and readiness responses.
- Added `DOCMESH_SERVICE_ALTERNATIVES` parsing and runtime `one_of` validation for default and explicit-settings paths.
- Verified startup healthcheck rollback before custom lifespan entry and structured `ServiceCloseError` logging without client/error payloads.
- Synced docs: README.md, docs/api.md, docs/config.md, docs/examples.md, docs/messaging.md, docs/srs.md, docs/test.md
- Refreshed comparisons and navigation: queries/docmesh-py-core-vs-fastapi-core-usage-comparison.md, queries/fastapi-core-prd-vs-source-code-comparison.md, index.md
- Verification commands:
  - `uv run pytest -q -m 'not integration'` → `46 passed, 11 deselected, 2 warnings in 0.36s`
  - `uv run pytest -q -m integration` → `11 passed, 46 deselected, 2 warnings in 20.43s`
  - `uv run pytest -q` → `57 passed, 2 warnings in 20.75s`

## [2026-07-17] ingest | docmesh-py-core v0.3.0 API Reference
- Captured immutable source: raw/articles/docmesh-py-core-api-reference-v0.3.0.md
- Refreshed entity and concept pages: entities/docmesh-py-core.md, concepts/service-configuration-contracts.md, concepts/service-factory-registry.md, concepts/service-health-check-aggregation.md, concepts/application-integration-patterns.md, concepts/keycloak-authentication-api.md, concepts/operational-logging-and-retry-utilities.md
- Updated index.md navigation date; no new wiki page was needed because the source updated existing central topics.
- Corrected superseded claims: health/provisioning result types are package-root imports in v0.3.0; the canonical lifecycle is assembly-first; Keycloak token acquisition defaults to password grant.

## [2026-07-17] ingest | docmesh-py-core v0.3.0 Examples
- Captured immutable source: raw/articles/docmesh-py-core-examples-guide-v0.3.0.md
- Refreshed entity and concept pages: entities/docmesh-py-core.md, concepts/application-integration-patterns.md, concepts/service-health-check-aggregation.md, concepts/keycloak-authentication-api.md, concepts/operational-logging-and-retry-utilities.md, concepts/service-configuration-contracts.md, concepts/service-factory-registry.md
- Updated index.md summaries; no new wiki page was needed because the examples corroborate and refine existing central topics.
- Recorded the typed `RuntimePlan` async lifecycle, PostgreSQL/SQLite `one_of` assembly, Keycloak startup-health credential requirement, and the current FastAPI/health/observability recipes.

## [2026-07-17] ingest | docmesh-py-core v0.3.0 Configuration Guide
- Captured immutable source: raw/articles/docmesh-py-core-configuration-guide-v0.3.0.md
- Refreshed entity and concept pages: entities/docmesh-py-core.md, concepts/service-configuration-contracts.md, concepts/keycloak-authentication-api.md, concepts/application-integration-patterns.md, concepts/operational-logging-and-retry-utilities.md
- Corrected/clarified configuration behavior: accepted boolean forms, deprecated PostgreSQL DSN migration, Langfuse retry-field scope, production placeholder diagnostics, NATS authentication exclusivity, and Keycloak startup-health failure timing.

## [2026-07-17] ingest | docmesh-py-core v0.3.0 .env.example
- Captured immutable source: raw/articles/docmesh-py-core-env-example-v0.3.0.md
- Updated concepts/service-configuration-contracts.md with template-consumption guidance.
- Recorded that the template contains placeholders, should be narrowed to selected services, and direct factory consumers should pass matching names to `load_service_configs(services={...})`.

## [2026-07-19] ingest | docmesh-py-core v0.4.0 API Reference
- Captured immutable source: raw/articles/docmesh-py-core-api-reference-v0.4.0.md
- Refreshed entity and concept pages: entities/docmesh-py-core.md, concepts/application-integration-patterns.md, concepts/service-configuration-contracts.md, concepts/service-health-check-aggregation.md, concepts/keycloak-authentication-api.md, concepts/operational-logging-and-retry-utilities.md, concepts/service-factory-registry.md
- Recorded the package-root `__all__` public-contract boundary, env-only configuration framing, RuntimePlan-first async assembly, sync NATS exclusion, and updated health aggregation semantics.
- Updated index.md navigation date; no new page was needed because this source refreshed existing central topics.

## [2026-07-19] ingest | docmesh-py-core v0.4.0 Configuration Guide
- Captured immutable source: raw/articles/docmesh-py-core-configuration-guide-v0.4.0.md
- Refreshed entity and concept pages: entities/docmesh-py-core.md, concepts/service-configuration-contracts.md, concepts/keycloak-authentication-api.md, concepts/application-integration-patterns.md, concepts/operational-logging-and-retry-utilities.md
- Corrected configuration guidance: config constructor injection is unsupported, service names are case-insensitive, `POSTGRES_DSN` is unsupported, and production diagnostics reject placeholder credentials/endpoints without exposing secrets.
- No new page was needed because this source refreshed existing central topics; index.md remains current at 9 pages.

## [2026-07-19] ingest | docmesh-py-core v0.4.0 Examples
- Captured immutable source: raw/articles/docmesh-py-core-examples-guide-v0.4.0.md
- Refreshed entity and concept pages: entities/docmesh-py-core.md, concepts/application-integration-patterns.md, concepts/service-health-check-aggregation.md, concepts/keycloak-authentication-api.md, concepts/operational-logging-and-retry-utilities.md
- Recorded the canonical preflight-to-async-runtime flow, NATS connection ownership/drain, direct SQLite scope, health/close error handling, Keycloak JWKS usage, and safe structured logging/retry examples.
- No new page was needed because this source refreshed existing central topics; index.md remains current at 9 pages.
