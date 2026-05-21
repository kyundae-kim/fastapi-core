When writing or editing code in this workspace, consult and follow docs/prd.md first.
Treat docs/prd.md as the source of product requirements and implementation intent.
If a code change appears to conflict with docs/prd.md, prefer the PRD and call out the discrepancy.

When handling environment variables or service settings, consult and follow docs/config.md first.
Treat docs/config.md as the source of truth for EnvConfig, ServiceSettings, and .env / YAML configuration rules.

When writing or editing tests, consult and follow docs/test.md first.
Treat docs/test.md as the source of truth for test structure, mock vs integration boundaries, and test-related environment requirements.

When writing or editing SDK API code in this workspace, consult and follow docs/api.md first.
Treat docs/api.md as the source of truth for all public interface signatures, behaviors, and error conditions in fastapi_core.
If a code change appears to conflict with docs/api.md, prefer the API spec and call out the discrepancy.
