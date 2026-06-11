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
