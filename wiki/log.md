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
