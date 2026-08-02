---
source_url: https://github.com/kyundae-kim/docmesh-config/blob/v0.1.0/.env.example
ingested: 2026-08-01
sha256: 2dba7c7874c696ea270353d3188424d161c4390994638cf952ac88de0cc6ba19
---
# docmesh-config environment template
#
# The library reads process environment variables only; it does not load this
# file automatically. Keep only the service blocks your application uses.
# Never commit real credentials. Values below are development examples.

# -----------------------------------------------------------------------------
# Common (CommonConfig)
# -----------------------------------------------------------------------------
DOCMESH_ENV=development
# DOCMESH_SECURITY_MODE=development
DOCMESH_PRODUCTION_ALIASES=prod,production

# -----------------------------------------------------------------------------
# Keycloak (KeycloakConfig)
# -----------------------------------------------------------------------------
# KEYCLOAK_URL=https://keycloak.internal
# KEYCLOAK_REALM=docmesh
# KEYCLOAK_CLIENT_ID=docmesh-api
# KEYCLOAK_CLIENT_SECRET=replace-me
# KEYCLOAK_VERIFY_SSL=true
# KEYCLOAK_AUDIENCE=docmesh-api
# KEYCLOAK_TOKEN_GRANT_TYPE=password
# KEYCLOAK_TOKEN_SCOPE=openid
# KEYCLOAK_TOKEN_USERNAME=example-user
# KEYCLOAK_TOKEN_PASSWORD=replace-me
# KEYCLOAK_REQUEST_TIMEOUT_SECONDS=10
# KEYCLOAK_MAX_RETRIES=3
# KEYCLOAK_JWKS_CACHE_TTL_SECONDS=300
# KEYCLOAK_PROVISIONING_ENABLED=false
# KEYCLOAK_PROVISIONING_DRY_RUN=false
# KEYCLOAK_ADMIN_REALM=master
# KEYCLOAK_ADMIN_CLIENT_ID=admin-cli
# KEYCLOAK_ADMIN_CLIENT_SECRET=replace-me
# KEYCLOAK_ADMIN_USERNAME=admin
# KEYCLOAK_ADMIN_PASSWORD=replace-me
# KEYCLOAK_REALM_ENABLED=true
# KEYCLOAK_REALM_DISPLAY_NAME=DocMesh
# KEYCLOAK_CLIENT_PUBLIC=false
# KEYCLOAK_CLIENT_REDIRECT_URIS=https://app.internal/callback
# KEYCLOAK_CLIENT_WEB_ORIGINS=https://app.internal
# KEYCLOAK_REALM_ROLES=reader,writer
# KEYCLOAK_CLIENT_ROLES=api-reader,api-writer

# -----------------------------------------------------------------------------
# PostgreSQL (PostgresConfig)
# -----------------------------------------------------------------------------
# POSTGRES_HOST=postgres.internal
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
# POSTGRES_APPLICATION_NAME=docmesh

# -----------------------------------------------------------------------------
# SQLite (SqliteConfig)
# -----------------------------------------------------------------------------
# SQLITE_PATH=:memory:
# SQLITE_READONLY=false
# SQLITE_ENABLE_WAL=false
# SQLITE_BUSY_TIMEOUT_MS=5000
# SQLITE_CHECK_SAME_THREAD=false
# SQLITE_ECHO=false

# -----------------------------------------------------------------------------
# MinIO (MinioConfig)
# -----------------------------------------------------------------------------
# MINIO_ENDPOINT=minio.internal:9000
# MINIO_ACCESS_KEY=replace-me
# MINIO_SECRET_KEY=replace-me
# MINIO_SECURE=true
# MINIO_CERT_CHECK=true
# MINIO_REGION=us-east-1
# MINIO_BUCKET=documents
# MINIO_REQUEST_TIMEOUT_SECONDS=30
# MINIO_MAX_RETRIES=3

# -----------------------------------------------------------------------------
# Milvus (MilvusConfig)
# MILVUS_URI is not supported; use MILVUS_ENDPOINT.
# -----------------------------------------------------------------------------
# MILVUS_ENDPOINT=https://milvus.internal:19530
# MILVUS_TOKEN=replace-me
# MILVUS_DB_NAME=default
# MILVUS_COLLECTION=documents
# MILVUS_SECURE=true
# MILVUS_CONNECT_TIMEOUT_SECONDS=10
# MILVUS_REQUEST_TIMEOUT_SECONDS=30
# MILVUS_MAX_RETRIES=3

# -----------------------------------------------------------------------------
# Ollama (OllamaConfig)
# -----------------------------------------------------------------------------
# OLLAMA_HOST=https://ollama.internal
# OLLAMA_VERIFY_SSL=true
# OLLAMA_FOLLOW_REDIRECTS=true
# OLLAMA_GENERATION_MODEL=llama3.2
# OLLAMA_EMBEDDING_MODEL=nomic-embed-text
# OLLAMA_REQUEST_TIMEOUT_SECONDS=120
# OLLAMA_MAX_RETRIES=2

# -----------------------------------------------------------------------------
# Langfuse (LangfuseConfig)
# Set LANGFUSE_ENABLED=false to omit host and keys.
# -----------------------------------------------------------------------------
# LANGFUSE_ENABLED=true
# LANGFUSE_HOST=https://langfuse.internal
# LANGFUSE_PUBLIC_KEY=replace-me
# LANGFUSE_SECRET_KEY=replace-me
# LANGFUSE_RELEASE=development
# LANGFUSE_ENVIRONMENT=development
# LANGFUSE_REQUEST_TIMEOUT_SECONDS=10
# LANGFUSE_MAX_RETRIES=3
# LANGFUSE_DEBUG=false
# LANGFUSE_TRACING_ENABLED=true
# LANGFUSE_FLUSH_AT=10
# LANGFUSE_FLUSH_INTERVAL_SECONDS=5.0
# LANGFUSE_SAMPLE_RATE=1.0

# -----------------------------------------------------------------------------
# NATS (NatsConfig)
# Choose at most one auth mode: user/password, token, or creds file.
# -----------------------------------------------------------------------------
# NATS_SERVERS=nats://nats.internal:4222
# NATS_USER=docmesh
# NATS_PASSWORD=replace-me
# NATS_TOKEN=replace-me
# NATS_CREDS_FILE=/run/secrets/nats.creds
# NATS_NAME=docmesh-config
# NATS_CONNECT_TIMEOUT_SECONDS=10
# NATS_MAX_RECONNECT_ATTEMPTS=10
# NATS_RECONNECT_TIME_WAIT_SECONDS=2.0
# NATS_PING_INTERVAL_SECONDS=120
# NATS_MAX_OUTSTANDING_PINGS=2
# NATS_NO_ECHO=false
