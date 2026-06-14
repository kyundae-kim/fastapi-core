# Registry-First Full Replacement Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Replace every FastAPI-managed service construction path that is already supported by `docmesh_py_core.ServiceFactoryRegistry` with registry-backed creation, while explicitly leaving unsupported paths on native adapters.

**Architecture:** Keep `fastapi-core` as a thin FastAPI composition layer. Treat `docmesh_py_core` as the source of truth for supported service construction (`keycloak`, `postgres`/`sqlite`, `minio`, `milvus`, `ollama`, `langfuse`, `nats`) and keep FastAPI responsibilities limited to request wiring, app state caching, and lifecycle orchestration. Introduce a small service-spec map so lifecycle/request-time/health logic all reuse the same registry metadata instead of repeating per-service `if` ladders.

**Tech Stack:** FastAPI, pydantic settings, SQLAlchemy, MinIO, Milvus, Ollama, Langfuse, NATS, pytest, pytest-asyncio/anyio, `docmesh_py_core`

---

## Scope decision

### Replace fully with registry now
- `auth_provider` via `create_client("keycloak")`
- `db_engine` via `create_client("postgres")` (and future-proof for `sqlite` if config ever exposes it)
- `minio_client` via `create_client("minio")`
- `milvus_client` via `create_client("milvus")`
- `ollama_client` via `create_client("ollama")`
- `langfuse_client` via `create_client("langfuse")`
- `nats_client` via `create_client("nats")` + `await connect()`

### Do **not** replace yet
- `async_milvus_client`

Reason: the installed `docmesh_py_core` registry builds sync `MilvusClient`, not `AsyncMilvusClient`. Forcing fake registry ownership here would blur contracts and create more special cases than it removes.

---

## Current blockers / gaps

1. `initialize_app_services()` still creates Langfuse natively with `get_langfuse_client(config.langfuse)` instead of registry-backed construction.
2. There is no `app.state.langfuse_client` ownership model, so Langfuse is outside the same lifecycle rules as other services.
3. Lifecycle startup logic repeats per-service registry calls in `_initialize_docmesh_managed_services()`.
4. Shutdown tracking is based on a string set, but the set currently excludes `nats_client` and any future `langfuse_client` ownership.
5. Health/readiness still checks Langfuse directly via `check_langfuse_connection(config.langfuse)` instead of using a registry-backed wrapper when available.
6. `async_milvus` has no explicit “unsupported-by-registry” seam, so the remaining native path is correct but under-documented.

---

## Task 1: Add failing tests for registry-backed Langfuse lifecycle ownership

**Objective:** Lock the desired behavior before refactoring: Langfuse should come from the registry when registry mode is enabled, and shutdown should treat it as registry-owned.

**Files:**
- Modify: `test_fastapi_core/test_lifecycle.py`

**Step 1: Write failing tests**

Add two tests:

```python
def test_initialize_app_services_uses_docmesh_registry_langfuse_client_when_enabled():
    ...


def test_shutdown_app_services_skips_duplicate_langfuse_flush_for_docmesh_managed_state():
    ...
```

Test assertions:
- lifecycle calls `registry.create_client("langfuse")`
- native `get_langfuse_client()` is not called in registry mode
- registry-owned Langfuse client is cached into app state
- `docmesh_managed_services` includes `langfuse_client`
- shutdown calls `docmesh_registry.close_all()` but does not separately flush/close `app.state.langfuse_client`

**Step 2: Run test to verify failure**

Run:
```bash
uv run pytest test_fastapi_core/test_lifecycle.py::test_initialize_app_services_uses_docmesh_registry_langfuse_client_when_enabled test_fastapi_core/test_lifecycle.py::test_shutdown_app_services_skips_duplicate_langfuse_flush_for_docmesh_managed_state -q
```

Expected: FAIL

**Step 3: Write minimal implementation**

Do not broad-refactor yet. Make the smallest code change to route Langfuse through the registry in lifecycle startup and mark it as managed.

**Step 4: Run test to verify pass**

Run the same command.

**Step 5: Commit**

```bash
git add test_fastapi_core/test_lifecycle.py fastapi_core/lifecycle.py
git commit -m "refactor: move lifecycle langfuse init to docmesh registry"
```

---

## Task 2: Introduce a shared registry service-spec map

**Objective:** Replace repeated service-specific lifecycle branching with one source of truth for registry-managed services.

**Files:**
- Modify: `fastapi_core/docmesh_bridge.py`
- Modify: `fastapi_core/lifecycle.py`
- Test: `test_fastapi_core/test_docmesh_bridge.py`

**Step 1: Write failing tests**

Add a focused test that verifies a helper returns service metadata for supported services and excludes unsupported ones.

Suggested helper shape:

```python
@dataclass(frozen=True)
class RegistryServiceSpec:
    registry_name: str
    state_key: str
    mode: Literal["sync", "async_builder"]
```

Suggested registry table keys:
- `auth_provider`
- `db_engine`
- `minio_client`
- `milvus_client`
- `ollama_client`
- `langfuse_client`
- `nats_client`

And explicitly omit:
- `async_milvus_client`

**Step 2: Run test to verify failure**

Run:
```bash
uv run pytest test_fastapi_core/test_docmesh_bridge.py -q
```

Expected: FAIL

**Step 3: Write minimal implementation**

In `fastapi_core/docmesh_bridge.py` add:
- `RegistryServiceSpec`
- `REGISTRY_SERVICE_SPECS`
- helpers like `get_registry_service_spec(state_key)` and/or `iter_enabled_registry_services(policy)`

Use this metadata from lifecycle instead of hardcoding repeated `if policy.init_*` branches.

**Step 4: Run test to verify pass**

Run the same command.

**Step 5: Commit**

```bash
git add fastapi_core/docmesh_bridge.py test_fastapi_core/test_docmesh_bridge.py fastapi_core/lifecycle.py
git commit -m "refactor: centralize docmesh registry service metadata"
```

---

## Task 3: Refactor lifecycle startup to loop over registry-managed specs

**Objective:** Make startup uniformly registry-first for all supported services, including Langfuse and NATS.

**Files:**
- Modify: `fastapi_core/lifecycle.py`
- Test: `test_fastapi_core/test_lifecycle.py`

**Step 1: Write/extend failing tests**

Extend `test_initialize_app_services_uses_docmesh_registry_clients_for_supported_services()` so the expected call order also includes `langfuse` and confirms the app state setter path.

**Step 2: Run test to verify failure**

Run:
```bash
uv run pytest test_fastapi_core/test_lifecycle.py::test_initialize_app_services_uses_docmesh_registry_clients_for_supported_services -q
```

Expected: FAIL

**Step 3: Write minimal implementation**

Refactor `_initialize_docmesh_managed_services()` to:
- iterate over enabled specs
- use one sync helper for wrapped `.client` services
- use one async helper for builder services like NATS
- cache the resolved client under the existing state key
- record every registry-owned state key into `docmesh_managed_services`

Important detail:
- `nats_client` should now also be marked registry-managed, because its connect path is still registry-owned even though the final client instance is not the wrapper object.

**Step 4: Run test to verify pass**

Run the same command.

**Step 5: Commit**

```bash
git add fastapi_core/lifecycle.py test_fastapi_core/test_lifecycle.py
git commit -m "refactor: drive lifecycle startup from registry service specs"
```

---

## Task 4: Refactor shutdown ownership rules to use service metadata

**Objective:** Ensure shutdown is deterministic and registry-owned services are never double-closed or double-flushed.

**Files:**
- Modify: `fastapi_core/lifecycle.py`
- Test: `test_fastapi_core/test_lifecycle.py`

**Step 1: Write failing tests**

Add/extend tests for:
- registry-owned `nats_client` does not get an extra `drain()` if policy marks it registry-owned
- registry-owned `langfuse_client` does not get an extra `flush()`/`close()` path
- native-owned `nats_client` still drains
- native-owned `async_milvus_client` still closes

**Step 2: Run test to verify failure**

Run:
```bash
uv run pytest test_fastapi_core/test_lifecycle.py -q
```

Expected: at least one new failure

**Step 3: Write minimal implementation**

Use a shutdown table instead of open-coded tuples, for example:

```python
SHUTDOWN_METHODS = {
    "docmesh_registry": "close_all",
    "nats_client": "drain",
    "async_milvus_client": "close",
    "milvus_client": "close",
    "db_engine": "dispose",
    "langfuse_client": "flush",
}
```

Rules:
- always run `docmesh_registry.close_all()` first if present
- skip per-resource shutdown for any state key in `docmesh_managed_services`
- preserve native cleanup for unsupported or non-registry-managed resources

**Step 4: Run test to verify pass**

Run the same command.

**Step 5: Commit**

```bash
git add fastapi_core/lifecycle.py test_fastapi_core/test_lifecycle.py
git commit -m "refactor: unify shutdown ownership for registry managed services"
```

---

## Task 5: Add request-time registry fallback for Langfuse state access

**Objective:** Remove the last supported service whose runtime acquisition bypasses the registry.

**Files:**
- Modify: `fastapi_core/core/langfuse.py`
- Or create: `fastapi_core/dependencies/langfuse.py`
- Modify: `fastapi_core/lifecycle.py`
- Modify: `fastapi_core/routers/health.py`
- Test: `test_fastapi_core/core/test_langfuse.py` and/or new `test_fastapi_core/dependencies/test_langfuse.py`

**Step 1: Write failing tests**

Choose one explicit runtime contract:
- preferred: add `dependencies/langfuse.py` with `set_langfuse_client()` / `get_langfuse_client_dependency()` using app-state + registry fallback
- alternate: extend the existing core helper and keep lifecycle-only ownership

Recommended failing test behavior:
- if `app.state.langfuse_client` exists, return it
- else if `docmesh_registry` exists, use `create_client("langfuse")` and cache the unwrapped client
- else fallback to native `create_langfuse_client(config.langfuse)`

**Step 2: Run test to verify failure**

Run a narrow target, e.g.:
```bash
uv run pytest test_fastapi_core/core/test_langfuse.py -q
```

Expected: FAIL

**Step 3: Write minimal implementation**

Keep one ownership model:
- `core/langfuse.py` should be pure construction/check helpers
- FastAPI state caching should live in a dependency module, consistent with other services

**Step 4: Run test to verify pass**

Run the same target.

**Step 5: Commit**

```bash
git add fastapi_core/core/langfuse.py fastapi_core/dependencies/langfuse.py test_fastapi_core/core/test_langfuse.py test_fastapi_core/dependencies/test_langfuse.py fastapi_core/routers/health.py
git commit -m "refactor: add registry-aware langfuse dependency wiring"
```

---

## Task 6: Make readiness use registry-backed Langfuse health when available

**Objective:** Keep health semantics aligned with registry ownership instead of bypassing it for supported services.

**Files:**
- Modify: `fastapi_core/routers/health.py`
- Modify: `fastapi_core/docmesh_bridge.py`
- Test: `test_fastapi_core/routers/test_health.py`

**Step 1: Write failing tests**

Add a test proving:
- when `use_docmesh_registry=True` and a registry-backed Langfuse client is present, readiness uses the wrapper/client health path instead of direct raw HTTP fallback
- when registry is absent, current HTTP health behavior remains unchanged

**Step 2: Run test to verify failure**

Run:
```bash
uv run pytest test_fastapi_core/routers/test_health.py -q
```

Expected: FAIL

**Step 3: Write minimal implementation**

Two acceptable implementations:
1. build a Langfuse-specific readiness callable from cached/registry service state; or
2. extend the docmesh bridge with a helper that extracts wrapper healthchecks for cached registry services.

Prefer the smallest change that preserves existing response semantics.

**Step 4: Run test to verify pass**

Run the same target.

**Step 5: Commit**

```bash
git add fastapi_core/routers/health.py fastapi_core/docmesh_bridge.py test_fastapi_core/routers/test_health.py
git commit -m "refactor: align langfuse readiness with registry-backed services"
```

---

## Task 7: Document unsupported async Milvus explicitly

**Objective:** Make the remaining native path intentional, discoverable, and easy to revisit when upstream registry support lands.

**Files:**
- Modify: `fastapi_core/dependencies/async_milvus.py`
- Modify: `fastapi_core/lifecycle.py`
- Modify: `docs/config.md` or `docs/api.md`
- Test: `test_fastapi_core/dependencies/test_async_milvus.py`

**Step 1: Write failing test**

Add a test that proves registry presence does **not** change async Milvus acquisition today.

**Step 2: Run test to verify failure**

Run:
```bash
uv run pytest test_fastapi_core/dependencies/test_async_milvus.py -q
```

Expected: FAIL if the behavior is not yet locked in with an explicit test.

**Step 3: Write minimal implementation**

Add a brief code comment/doc note:
- `docmesh_py_core` currently exposes only sync Milvus via registry
- `async_milvus_client` intentionally remains native
- revisit when registry grows async support

**Step 4: Run test to verify pass**

Run the same target.

**Step 5: Commit**

```bash
git add fastapi_core/dependencies/async_milvus.py fastapi_core/lifecycle.py docs/config.md test_fastapi_core/dependencies/test_async_milvus.py
git commit -m "docs: document native async milvus boundary"
```

---

## Task 8: Run widening-ring verification

**Objective:** Prove the refactor preserves non-integration behavior and the registry-first contract.

**Files:**
- No code changes required unless failures reveal regressions

**Step 1: Run focused lifecycle/docmesh subset**

```bash
uv run pytest \
  test_fastapi_core/test_docmesh_bridge.py \
  test_fastapi_core/test_lifecycle.py \
  test_fastapi_core/routers/test_health.py \
  test_fastapi_core/dependencies/test_database.py \
  test_fastapi_core/dependencies/test_storage.py \
  test_fastapi_core/dependencies/test_messaging.py \
  test_fastapi_core/dependencies/test_security.py \
  test_fastapi_core/dependencies/test_ollama.py \
  test_fastapi_core/dependencies/test_milvus.py \
  test_fastapi_core/dependencies/test_async_milvus.py \
  test_fastapi_core/core/test_langfuse.py \
  -q
```

Expected: PASS

**Step 2: Run full non-integration suite**

```bash
uv run pytest -q -m 'not integration'
```

Expected: PASS

**Step 3: Smoke-check real registry activation**

```bash
uv run python - <<'PY'
from fastapi import FastAPI
import anyio
from fastapi_core.core.config import EnvConfig, HealthSettings, LifecycleSettings, ServiceSettings
from fastapi_core.lifecycle import initialize_app_services

app = FastAPI()
settings = ServiceSettings(
    health=HealthSettings(
        check_keycloak=False,
        check_database=False,
        check_minio=False,
        check_langfuse=False,
    ),
    lifecycle=LifecycleSettings(
        use_docmesh_registry=True,
        eager_milvus=False,
        eager_ollama=False,
        eager_nats=False,
    ),
)

anyio.run(lambda: initialize_app_services(app, EnvConfig(), settings=settings))
print(type(app.state.docmesh_registry).__name__)
print(hasattr(app.state, 'docmesh_settings'))
PY
```

Expected output includes:
- `ServiceFactoryRegistry`
- `True`

---

## End-state definition

After this refactor, the architecture should be:

- **Registry-owned services:** keycloak, database, minio, sync milvus, ollama, langfuse, nats
- **Native-only services:** async milvus
- **FastAPI-owned responsibilities only:**
  - dependency injection
  - app.state caching
  - lifecycle orchestration
  - HTTP route wiring
- **Single source of truth for service creation:** `docmesh_py_core.ServiceFactoryRegistry` for every supported service

---

## Practical implementation notes

- Do **not** create a fake registry adapter for `async_milvus` just to say everything is “registry-backed”. That would hide the real upstream boundary.
- Prefer introducing `dependencies/langfuse.py` rather than teaching `core/langfuse.py` about FastAPI app state. The current package convention is that `core/*` constructs/checks and `dependencies/*` own request wiring.
- Mark `nats_client` as registry-managed when created from registry. Even though the final object is a connected client rather than the builder wrapper, ownership still belongs to the registry path.
- If readiness starts using cached registry clients for Langfuse, keep the current direct HTTP fallback for non-registry mode to avoid surprising deployments.
- If `docmesh_py_core` is upgraded and later exposes async Milvus, add a new slice rather than over-generalizing now.
