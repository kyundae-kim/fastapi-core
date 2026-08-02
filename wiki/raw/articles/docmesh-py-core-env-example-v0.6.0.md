---
source_url: https://github.com/kyundae-kim/docmesh-py-core/blob/v0.6.0/.env.example
ingested: 2026-08-01
sha256: 4fd9b8289d75c805800a31162d24368ccbd3ba6b67348ce6151546890210b996
---
# docmesh-py-core v0.6.0 environment template
#
# 1. Copy this file to .env.
# 2. Uncomment only the service sections selected by your RuntimePlan.
# 3. Replace every replace-me value through your secret-management path.
# 4. Inject the values into the process environment; the library does not load .env files.
# 5. Production rejects placeholder endpoints/secrets and insecure transport flags.

# Common runtime mode
DOCMESH_ENV=development
# DOCMESH_SECURITY_MODE=development
# DOCMESH_PRODUCTION_ALIASES=prod,production
# DOCMESH_LOG_LEVEL=INFO

# Keycloak: KEYCLOAK_CLIENT_SECRET is required unless KEYCLOAK_CLIENT_PUBLIC=true.
# Password grant credentials may be supplied at call time instead of the two TOKEN_* keys.
# Provisioning admin auth must use exactly one mode: client secret OR username+password.
# KEYCLOAK_URL=https://keycloak.example.invalid
# KEYCLOAK_REALM=docmesh
# KEYCLOAK_CLIENT_ID=backend
# KEYCLOAK_CLIENT_SECRET=replace-me
# KEYCLOAK_VERIFY_SSL=true
# KEYCLOAK_AUDIENCE=
# KEYCLOAK_TOKEN_GRANT_TYPE=password
# KEYCLOAK_TOKEN_SCOPE=
# KEYCLOAK_TOKEN_USERNAME=
# KEYCLOAK_TOKEN_PASSWORD=replace-me
# KEYCLOAK_REQUEST_TIMEOUT_SECONDS=10
# KEYCLOAK_MAX_RETRIES=3
# KEYCLOAK_JWKS_CACHE_TTL_SECONDS=300
# KEYCLOAK_PROVISIONING_ENABLED=false
# KEYCLOAK_PROVISIONING_DRY_RUN=false
# KEYCLOAK_ADMIN_REALM=master
# KEYCLOAK_ADMIN_CLIENT_ID=admin-cli
# KEYCLOAK_ADMIN_CLIENT_SECRET=replace-me
# KEYCLOAK_ADMIN_USERNAME=
# KEYCLOAK_ADMIN_PASSWORD=replace-me
# KEYCLOAK_REALM_ENABLED=true
# KEYCLOAK_REALM_DISPLAY_NAME=
# KEYCLOAK_CLIENT_PUBLIC=false
# KEYCLOAK_CLIENT_REDIRECT_URIS=https://app.example.invalid/callback
# KEYCLOAK_CLIENT_WEB_ORIGINS=https://app.example.invalid
# KEYCLOAK_REALM_ROLES=reader,writer
# KEYCLOAK_CLIENT_ROLES=viewer,editor

# PostgreSQL
# POSTGRES_HOST=postgres.example.invalid
# POSTGRES_PORT=5432
# POSTGRES_DB=docmesh
# POSTGRES_USER=docmesh
# POSTGRES_PASSWORD=replace-me
# POSTGRES_SSLMODE=prefer
# POSTGRES_CONNECT_TIMEOUT_SECONDS=10
# POSTGRES_POOL_SIZE=5
# POSTGRES_MAX_OVERFLOW=10
# POSTGRES_POOL_PRE_PING=false
# POSTGRES_POOL_RECYCLE_SECONDS=-1
# POSTGRES_ECHO=false
# POSTGRES_APPLICATION_NAME=docmesh-app

# SQLite
# SQLITE_PATH=:memory:
# SQLITE_READONLY=false
# SQLITE_ENABLE_WAL=false
# SQLITE_BUSY_TIMEOUT_MS=5000
# SQLITE_CHECK_SAME_THREAD=false
# SQLITE_ECHO=false

# MinIO: MINIO_BUCKET is conditional on RuntimePlan.minio_bucket_required.
# MINIO_ENDPOINT=minio.example.invalid:9000
# MINIO_ACCESS_KEY=replace-me
# MINIO_SECRET_KEY=replace-me
# MINIO_SECURE=true
# MINIO_CERT_CHECK=true
# MINIO_REGION=
# MINIO_BUCKET=
# MINIO_REQUEST_TIMEOUT_SECONDS=30
# MINIO_MAX_RETRIES=3

# Milvus
# MILVUS_ENDPOINT=https://milvus.example.invalid:19530
# MILVUS_TOKEN=replace-me
# MILVUS_DB_NAME=default
# MILVUS_COLLECTION=
# MILVUS_SECURE=true
# MILVUS_CONNECT_TIMEOUT_SECONDS=10
# MILVUS_REQUEST_TIMEOUT_SECONDS=30
# MILVUS_MAX_RETRIES=3

# Ollama
# OLLAMA_HOST=https://ollama.example.invalid
# OLLAMA_VERIFY_SSL=true
# OLLAMA_FOLLOW_REDIRECTS=true
# OLLAMA_GENERATION_MODEL=
# OLLAMA_EMBEDDING_MODEL=
# OLLAMA_REQUEST_TIMEOUT_SECONDS=120
# OLLAMA_MAX_RETRIES=2

# Langfuse: HOST/PUBLIC_KEY/SECRET_KEY are required when enabled=true.
# LANGFUSE_ENABLED=false
# LANGFUSE_HOST=https://langfuse.example.invalid
# LANGFUSE_PUBLIC_KEY=replace-me
# LANGFUSE_SECRET_KEY=replace-me
# LANGFUSE_RELEASE=
# LANGFUSE_ENVIRONMENT=
# LANGFUSE_REQUEST_TIMEOUT_SECONDS=10
# LANGFUSE_MAX_RETRIES=3
# LANGFUSE_DEBUG=false
# LANGFUSE_TRACING_ENABLED=true
# LANGFUSE_FLUSH_AT=
# LANGFUSE_FLUSH_INTERVAL_SECONDS=
# LANGFUSE_SAMPLE_RATE=

# NATS: authentication is zero-or-one of user/password, token, or creds file.
# NATS_SERVERS=nats://nats.example.invalid:4222
# NATS_USER=
# NATS_PASSWORD=replace-me
# NATS_TOKEN=replace-me
# NATS_CREDS_FILE=
# NATS_NAME=docmesh-py-core
# NATS_CONNECT_TIMEOUT_SECONDS=10
# NATS_MAX_RECONNECT_ATTEMPTS=10
# NATS_RECONNECT_TIME_WAIT_SECONDS=2.0
# NATS_PING_INTERVAL_SECONDS=120
# NATS_MAX_OUTSTANDING_PINGS=2
# NATS_NO_ECHO=false
