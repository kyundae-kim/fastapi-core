---
source_url: https://github.com/kyundae-kim/docmesh-py-core/blob/v0.3.0/.env.example
ingested: 2026-07-17
sha256: fbad2be17a8f7fac7bce427ab1d87f24dc59ee1d28fb4df50949548a6fcf0a4e
---
# DocMesh Python Core example environment
# Replace placeholder values with real deployment values.
# Never commit real secrets.
#
# Configure only the services your application selects. For direct factory use,
# call load_service_configs(services={...}) with the matching service names so
# unrelated placeholder values are not validated. See docs/config.md for the
# required, optional, and conditional settings for each service.

# Common
DOCMESH_ENV=development
DOCMESH_HEALTHCHECK_ENABLED=true
DOCMESH_SECURITY_MODE=
DOCMESH_PRODUCTION_ALIASES=prod,production
DOCMESH_LOG_LEVEL=INFO

# Keycloak
# Required: KEYCLOAK_URL, KEYCLOAK_REALM, KEYCLOAK_CLIENT_ID, and normally
# KEYCLOAK_CLIENT_SECRET. Password-grant startup checks also need token username
# and password; public clients set KEYCLOAK_CLIENT_PUBLIC=true instead.
KEYCLOAK_URL=https://keycloak.example.com
KEYCLOAK_REALM=docmesh
KEYCLOAK_CLIENT_ID=docmesh-backend
KEYCLOAK_CLIENT_SECRET=
KEYCLOAK_VERIFY_SSL=true
KEYCLOAK_AUDIENCE=
KEYCLOAK_TOKEN_GRANT_TYPE=password
KEYCLOAK_TOKEN_SCOPE=
KEYCLOAK_TOKEN_USERNAME=
KEYCLOAK_TOKEN_PASSWORD=
KEYCLOAK_REQUEST_TIMEOUT_SECONDS=10
KEYCLOAK_MAX_RETRIES=3
KEYCLOAK_JWKS_CACHE_TTL_SECONDS=300
KEYCLOAK_PROVISIONING_ENABLED=false
KEYCLOAK_PROVISIONING_DRY_RUN=false
KEYCLOAK_ADMIN_REALM=master
KEYCLOAK_ADMIN_CLIENT_ID=admin-cli
KEYCLOAK_ADMIN_CLIENT_SECRET=
KEYCLOAK_ADMIN_USERNAME=
KEYCLOAK_ADMIN_PASSWORD=
KEYCLOAK_REALM_ENABLED=true
KEYCLOAK_REALM_DISPLAY_NAME=
KEYCLOAK_CLIENT_PUBLIC=false
KEYCLOAK_CLIENT_REDIRECT_URIS=
KEYCLOAK_CLIENT_WEB_ORIGINS=
KEYCLOAK_REALM_ROLES=
KEYCLOAK_CLIENT_ROLES=

# PostgreSQL
# Required: POSTGRES_HOST, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD.
# Do not add the deprecated legacy connection-URI setting to new deployments.
POSTGRES_HOST=postgres.example.com
POSTGRES_PORT=5432
POSTGRES_DB=docmesh
POSTGRES_USER=docmesh
POSTGRES_PASSWORD=
POSTGRES_SSLMODE=prefer
POSTGRES_CONNECT_TIMEOUT_SECONDS=10
POSTGRES_POOL_SIZE=5
POSTGRES_MAX_OVERFLOW=10

# SQLite
# Required: SQLITE_PATH. Use :memory: for a local smoke test.
SQLITE_PATH=':memory:'
SQLITE_READONLY=false
SQLITE_ENABLE_WAL=false
SQLITE_BUSY_TIMEOUT_MS=5000

# MinIO
# Required: MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY.
MINIO_ENDPOINT=minio.example.com:9000
MINIO_ACCESS_KEY=minio-access-key
MINIO_SECRET_KEY=
MINIO_SECURE=true
MINIO_REGION=
MINIO_BUCKET=
MINIO_REQUEST_TIMEOUT_SECONDS=30
MINIO_MAX_RETRIES=3

# Milvus
# Required: MILVUS_URI. Production deployments must set MILVUS_SECURE=true.
MILVUS_URI=http://milvus.example.com:19530
MILVUS_TOKEN=
MILVUS_DB_NAME=default
MILVUS_COLLECTION=
MILVUS_SECURE=false
MILVUS_CONNECT_TIMEOUT_SECONDS=10
MILVUS_REQUEST_TIMEOUT_SECONDS=30
MILVUS_MAX_RETRIES=3

# Ollama
# Required: OLLAMA_HOST.
OLLAMA_HOST=http://ollama.example.com:11434
OLLAMA_GENERATION_MODEL=
OLLAMA_EMBEDDING_MODEL=
OLLAMA_REQUEST_TIMEOUT_SECONDS=120
OLLAMA_MAX_RETRIES=2

# Langfuse
# Set LANGFUSE_ENABLED=false when tracing is not used; otherwise host and both
# keys are required.
LANGFUSE_HOST=https://langfuse.example.com
LANGFUSE_PUBLIC_KEY=pk-live-placeholder
LANGFUSE_SECRET_KEY=
LANGFUSE_ENABLED=true
LANGFUSE_RELEASE=
LANGFUSE_ENVIRONMENT=
LANGFUSE_REQUEST_TIMEOUT_SECONDS=10
LANGFUSE_MAX_RETRIES=3

# NATS
# Required: NATS_SERVERS. Choose at most one authentication mode: user/password,
# token, or credentials file.
NATS_SERVERS=nats://n1.example.com:4222,nats://n2.example.com:4222
NATS_USER=
NATS_PASSWORD=
NATS_TOKEN=
NATS_CREDS_FILE=
NATS_NAME=docmesh-py-core
NATS_CONNECT_TIMEOUT_SECONDS=10
NATS_MAX_RECONNECT_ATTEMPTS=10
