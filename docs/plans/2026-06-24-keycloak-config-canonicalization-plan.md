# 2026-06-24 KeycloakConfig canonicalization plan

## Goal
`fastapi_core.core.config.KeycloakConfig` 를 docmesh 쪽 canonical 설정 모델에 더 가깝게 정리하되, 한 번에 drop-in replacement 하지 않고 **adapter + overlay** 전략으로 단계적으로 전환한다.

핵심 목표는 다음과 같다.

1. Keycloak connection/auth 설정의 source of truth 를 `docmesh_py_core.config.KeycloakConfig` 쪽으로 이동할 수 있게 한다.
2. fastapi-core 고유 책임(`manage_url` 등)은 별도 overlay 로 분리한다.
3. runtime 동작(`docmesh_bridge`, auth dependency, health router)을 깨지 않고 테스트 가능하게 전환한다.

---

## Current repo-grounded context

### Current native model
`fastapi_core/core/config.py` 의 native `KeycloakConfig` 는 현재 아래 필드만 가진다.

- `http_url`
- `manage_url`
- `realm`
- `client_id`
- `client_secret`

참조:
- `fastapi_core/core/config.py:22`

### Current native/runtime usages
현재 레포에서 Keycloak 설정이 직접 쓰이는 핵심 지점은 아래 두 군데다.

1. `fastapi_core/docmesh_bridge.py:92`
   - `config.keycloak.http_url`, `realm`, `client_id`, `client_secret` 를 docmesh env 로 변환
   - `KEYCLOAK_VERIFY_SSL` 도 `http_url` 스킴으로부터 유도

2. `fastapi_core/routers/health.py:59`
   - `config.keycloak.manage_url` 를 이용해 health endpoint 확인

추가로 native auth provider 계약은 다음과 같다.
- `fastapi_core/core/auth.py:23`
- 생성자 시그니처: `KeycloakAuthProvider(http_url, realm, client_id, client_secret)`

### docmesh model shape
`docmesh_py_core.config.KeycloakConfig` 는 다음 성격을 가진다.

- 기본 연결 필드: `url`, `realm`, `client_id`, `client_secret`
- runtime/auth 필드: `verify_ssl`, `audience`, `token_grant_type`, `token_scope`, `token_username`, `token_password`, `request_timeout_seconds`, `max_retries`
- provisioning 필드: `provisioning_enabled`, `admin_*`, `realm_enabled`, `client_public`, `client_redirect_uris`, `client_web_origins`, `realm_roles`, `client_roles`

참조:
- `.venv/lib/python3.11/site-packages/docmesh_py_core/config.py:69`

### Why direct replacement is unsafe today
아래 이유 때문에 지금 즉시 `fastapi_core.core.config.KeycloakConfig = docmesh_py_core.config.KeycloakConfig` 로 치환하면 위험하다.

1. **명명 차이**
   - fastapi-core: `http_url`
   - docmesh: `url`

2. **fastapi-only field 존재**
   - `manage_url` 는 docmesh 모델에 없음
   - `health` router 가 직접 의존 중

3. **native auth provider 계약 차이**
   - `KeycloakAuthProvider` 는 `http_url` 기반 생성자 계약을 가짐

4. **env loading boundary 차이**
   - 현재 `EnvConfig` 는 nested settings (`keycloak__http_url`) 구조를 사용
   - docmesh는 flat env prefix (`KEYCLOAK_URL`) 구조를 사용

---

## Proposed target architecture

### Target split
Keycloak 설정 책임을 아래 3층으로 나눈다.

1. **Canonical auth config**
   - source: `docmesh_py_core.config.KeycloakConfig`
   - 의미: 인증/토큰/introspection/provisioning에 필요한 표준 Keycloak 설정

2. **FastAPI overlay**
   - 새 모델 후보: `FastAPIKeycloakSettings` 또는 `KeycloakOverlayConfig`
   - 책임:
     - `manage_url`
     - 향후 fastapi-core 전용 endpoint override 나 health-specific 옵션

3. **Runtime adapter**
   - 위치 후보: `fastapi_core/docmesh_bridge.py` 또는 `fastapi_core/core/keycloak_adapter.py`
   - 책임:
     - docmesh canonical model ↔ fastapi-core native consumer 간 변환
     - `KeycloakAuthProvider` 생성 인자 정규화

### Desired end state
최종적으로는 다음 그림을 목표로 한다.

- `EnvConfig` 는 `keycloak` 전체를 native bespoke model 로 들고 있지 않음
- 대신 `EnvConfig` 는:
  - docmesh canonical keycloak settings source
  - fastapi overlay (`manage_url` 등)
  를 함께 조립하는 thin entrypoint 가 됨
- `docmesh_bridge.build_docmesh_env()` 는 더 이상 `http_url -> KEYCLOAK_URL` 같은 재매핑을 많이 하지 않거나, 최소한 adapter layer 하나만 보게 됨

---

## Recommended migration strategy

### Phase 1 — Introduce overlay without breaking public API
목표: 기존 public API 를 깨지 않고, 내부적으로 canonicalization 준비를 끝낸다.

#### Changes
1. `fastapi_core/core/config.py`
   - 기존 `KeycloakConfig` 는 유지하되 deprecated surface 로 취급
   - 새 overlay 모델 추가:
     - 예: `KeycloakOverlayConfig`
     - 필드: `manage_url`

2. `fastapi_core/docmesh_bridge.py`
   - helper 추가:
     - `build_docmesh_keycloak_config(config: EnvConfig) -> docmesh_py_core.config.KeycloakConfig`
   - 현재 `build_docmesh_env()` 의 Keycloak 관련 매핑 근거를 이 helper 로 집중

3. `fastapi_core/core/auth.py`
   - helper 추가 후보:
     - `create_keycloak_auth_provider_from_docmesh_config(...)`
   - `url` / `client_secret` / `realm` 기반으로 native provider 생성 가능하게 정리

4. `fastapi_core/routers/health.py`
   - `manage_url` 소비를 overlay 로 명시화

#### Verification
- 기존 auth 관련 테스트 유지
- bridge 변환 테스트 추가
- `manage_url` health check 테스트 유지

### Phase 2 — Move `EnvConfig.keycloak` toward canonical+overlay composition
목표: `EnvConfig.keycloak` 전체를 native 모델 하나로 들고 있지 않도록 축소한다.

#### Changes
옵션 A:
- `EnvConfig.keycloak` 는 docmesh canonical 모델
- `EnvConfig.keycloak_overlay` 추가

옵션 B:
- `EnvConfig` 에서 `keycloak` 을 제거
- `load_docmesh_settings()` 또는 dedicated loader 가 canonical keycloak config 제공
- fastapi-only overlay 는 별도 필드로 유지

이 레포에서는 **옵션 A** 가 더 안전하다.
이유:
- 현재 `EnvConfig` 를 직접 읽는 코드가 존재
- 한 번에 loader contract 를 바꾸면 파급이 큼

#### Verification
- `EnvConfig()` 기본값/override 테스트
- nested env → canonical model 매핑 테스트
- auth provider compatibility 테스트

### Phase 3 — Public API cleanup
목표: deprecated native shape 제거 여부를 결정한다.

#### Candidate removals
- `fastapi_core.core.config.KeycloakConfig` 의 bespoke 필드 구조
- `http_url` naming

#### Conditions before removal
- public import users 확인 필요 (`fastapi_core/__init__.py` export 포함)
- migration note / changelog 필요
- 최소 1회 deprecation window 확보 권장

---

## Concrete file plan

### Must inspect/edit
1. `fastapi_core/core/config.py`
   - 현재 `KeycloakConfig` 정의 위치
   - overlay/canonical composition 도입 지점

2. `fastapi_core/docmesh_bridge.py`
   - 현재 Keycloak env 변환 집중 지점
   - canonical adapter 추가 1순위

3. `fastapi_core/core/auth.py`
   - native provider 생성 계약 정리 필요

4. `fastapi_core/routers/health.py`
   - `manage_url` 를 overlay 책임으로 고정

5. `fastapi_core/__init__.py`
   - public export surface 검토 필요

### Tests to add/update
1. `test_fastapi_core/core/test_config.py`
   - Keycloak overlay defaults
   - canonical adapter compatibility

2. `test_fastapi_core/test_docmesh_bridge.py`
   - `EnvConfig` → docmesh KeycloakConfig 변환 테스트
   - `http_url` / `verify_ssl` / `client_public` derivation 테스트

3. `test_fastapi_core/dependencies/test_auth.py`
   - docmesh canonical config 기반 provider 생성/적응 테스트

4. `test_fastapi_core/routers/test_health.py`
   - `manage_url` 가 overlay 경로로 계속 동작하는지 검증

---

## Design decisions

### Decision 1: `manage_url` is not part of canonical docmesh keycloak config
이 값은 docmesh 표준 인증 설정이 아니라 fastapi-core 운영/health 편의 설정으로 취급한다.

### Decision 2: `http_url` should converge toward `url`
장기적으로는 native naming 도 `http_url` 보다 `url` 로 수렴시키는 편이 좋다. 다만 이 변경은 public API 영향이 있으므로 deprecation 단계를 둔다.

### Decision 3: Keycloak canonicalization should happen before database canonicalization
이유:
- Keycloak은 현재 registry-backed runtime 과 더 잘 맞는다.
- DB는 SQLAlchemy tuning 계약이 섞여 있어 분해 작업이 먼저 필요하다.

---

## Risks

1. **Public API breakage**
   - 외부 사용자가 `from fastapi_core import KeycloakConfig` 를 직접 쓰고 있을 수 있음

2. **Env compatibility breakage**
   - nested env (`keycloak__http_url`) 와 flat env (`KEYCLOAK_URL`) 가 섞일 수 있음

3. **Health endpoint drift**
   - `manage_url` 분리 후 health 경로가 누락될 수 있음

4. **Auth runtime split-brain**
   - native provider 와 registry-backed provider 가 서로 다른 기본값을 읽을 위험

---

## Open questions

1. `manage_url` 를 정말 유지해야 하는가, 아니면 `url` + well-known admin path 조합으로 충분한가?
2. 외부 소비자가 `KeycloakConfig` 를 public API 로 직접 import/use 하는가?
3. `EnvConfig` 에서 Keycloak 관련 env 입력을 nested 스타일로 계속 받을지, flat env alias 를 같이 열지?

---

## Suggested first implementation slice

가장 안전한 첫 slice 는 아래다.

1. `docmesh_bridge` 에 `build_docmesh_keycloak_config(config)` 추가
2. `build_docmesh_env()` 의 Keycloak 관련 파생값 계산을 이 helper 기준으로 재정리
3. `KeycloakOverlayConfig(manage_url)` 추가
4. `health.py` 가 overlay 만 의존하도록 정리
5. 관련 단위 테스트 추가

이 slice 는 **canonicalization 방향을 굳히면서도 public API breakage를 최소화**한다.

---

## Validation commands

구현 단계에서 권장 검증 순서:

```bash
uv run pytest -q test_fastapi_core/core/test_config.py
uv run pytest -q test_fastapi_core/test_docmesh_bridge.py
uv run pytest -q test_fastapi_core/dependencies/test_auth.py
uv run pytest -q test_fastapi_core/routers/test_health.py
uv run pytest -q -m 'not integration'
```

---

## Recommendation

다음 실제 구현은 **Phase 1 / first slice** 로 시작하는 것이 가장 안전하다.

즉,
- `KeycloakConfig` 완전 교체는 하지 않고
- **docmesh canonical helper + fastapi overlay 분리** 를 먼저 도입한다.

이후 테스트가 안정되면 `http_url` → `url` deprecation 과 `EnvConfig.keycloak` 축소를 진행한다.
