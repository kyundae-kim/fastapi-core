# Config Dedup Refactor Plan

## Goal
`fastapi_core/core/config.py` 에 섞여 있는 설정 모델 책임과 `docmesh_py_core` 적응 책임을 분리해서, 설정의 단일 진실 공급원(source of truth)을 더 명확하게 만든다. 이번 리팩터링의 1차 목표는 다음 세 가지다.

1. `core/config.py` 를 **fastapi-core의 canonical 설정 모델**로 축소한다.
2. docmesh 관련 변환/적응 로직을 **`docmesh_bridge.py` 계층으로 이동**한다.
3. 코드와 문서 간 drift를 잡을 수 있도록 **설정 계약 검증 테스트**를 추가한다.

## Current Context
현재 `fastapi_core/core/config.py` 는 아래 네 가지 책임을 동시에 갖고 있다.

- `EnvConfig`, `ServiceSettings` 및 하위 `BaseModel` 정의
- `.env` / YAML 기반 설정 로드 (`load_env_config`, `load_service_settings`)
- docmesh settings 초기화 (`load_docmesh_settings`)
- docmesh settings 를 참조한 Milvus 설정 적응 (`resolve_milvus_config`)

추가로, `fastapi_core/docmesh_bridge.py` 는 이미 `build_docmesh_env()` 와 `initialize_docmesh_registry()` 를 통해 docmesh 적응 계층 역할을 수행하고 있다. 즉 현재 구조는 **config module + bridge module 이 docmesh integration 책임을 나눠 들고 있는 상태**다.

## Observed Duplication Targets

### 1. Internal responsibility overlap
- `fastapi_core/core/config.py`
  - `load_docmesh_settings()`
  - `_adapt_docmesh_milvus_config()`
  - `resolve_milvus_config()`
  - `ApplicationSettings`
- `fastapi_core/docmesh_bridge.py`
  - `build_docmesh_env()`
  - `initialize_docmesh_registry()`
  - app.state 에 `docmesh_settings` / `docmesh_registry` 저장

### 2. Domain-model overlap with docmesh
`fastapi-core` 의 `KeycloakConfig`, `DatabaseConfig`, `MinIOConfig`, `MilvusConfig`, `OllamaConfig`, `LangfuseConfig`, `NatsConfig` 는 `docmesh_py_core.Settings` 의 대응 서비스 설정들과 의미상 크게 겹친다. 이 자체를 즉시 제거할 필요는 없지만, **fastapi-core 내부 모델**과 **docmesh adapter** 의 경계를 분리해 두는 것이 우선이다.

### 3. Documentation drift risk
- 코드: `fastapi_core/core/config.py`
- 문서: `docs/config.md`

기본값/필드명 변경 시 문서가 쉽게 stale 해질 수 있다.

## Non-Goals
이번 단계에서 하지 않을 것:

- `EnvConfig` / `ServiceSettings` 를 즉시 제거하고 docmesh `Settings` 로 완전 통합
- `docs/config.md` 자동 생성 시스템까지 한 번에 도입
- 모든 서비스 설정을 docmesh 기반 타입으로 대체
- FastAPI dependency public surface 변경

## Proposed End State (Phase 1)

### A. `core/config.py` 에 남길 것
`fastapi_core/core/config.py` 는 아래만 책임진다.

- 환경 enum 및 fastapi-core 고유 설정 모델
  - `Environment`
  - `LoggingConfig`
  - `KeycloakConfig`
  - `DatabaseConfig`
  - `MinIOConfig`
  - `OllamaConfig`
  - `MilvusConfig`
  - `LangfuseConfig`
  - `NatsConfig`
  - `CORSSettings`
  - `AuthSettings`
  - `HealthSettings`
  - `LifecycleSettings`
  - `ServiceSettings`
  - `EnvConfig`
- 기본 로딩 함수
  - `load_env_config()`
  - `load_service_settings()`

### B. `docmesh_bridge.py` 로 이동할 것
아래는 bridge/integration 책임으로 재배치한다.

- `load_docmesh_settings()` → 이름 재검토 후 `docmesh_bridge.py` 로 이동
- `_adapt_docmesh_milvus_config()` → `docmesh_bridge.py` 로 이동
- `resolve_milvus_config()` → `docmesh_bridge.py` 로 이동
- `ApplicationSettings` → 사용처가 없으므로 제거 후보
- `load_application_settings()` → 사용처가 없으므로 제거 후보

### C. Milvus resolution contract 정리
Milvus 는 현재 유일하게 `docmesh_settings` 를 직접 읽어 native config 로 역적응하는 특수 경로다. 이 경로는 `config.py` 가 아니라 **bridge helper** 로 보이도록 바꾼다.

예상 함수 형태:
- `docmesh_bridge.resolve_milvus_config(config: EnvConfig, docmesh_settings: Any | None) -> MilvusConfig`
- 또는 더 명확하게 `resolve_effective_milvus_config(...)`

## Why This Split Is Safe
현재 코드 usage 기준으로:

- `load_docmesh_settings()` 는 `core/config.py` 내부에서만 쓰인다.
- `load_application_settings()` 는 현재 repo 내 사용처가 없다.
- `ApplicationSettings` 도 현재 repo 내 사용처가 없다.
- `resolve_milvus_config()` 의 직접 사용처는 `dependencies/milvus.py`, `dependencies/async_milvus.py` 두 곳뿐이다.

즉 public API 파장을 작게 유지하면서 분리 가능하다.

## Implementation Steps

### Step 1. Dead-surface 확인 및 제거 준비
대상 파일:
- `fastapi_core/core/config.py`
- `fastapi_core/__init__.py`
- `test_fastapi_core/` 전체 검색

작업:
- `ApplicationSettings` 와 `load_application_settings()` 가 실제 공개 API인지 재확인
- 외부에서 import 중인 테스트/문서가 없으면 제거 대상으로 확정

검증:
- `search_files` 로 repo 사용처 0건 확인
- 필요 시 public API 테스트 추가/보정

### Step 2. Docmesh-specific helpers 이동
대상 파일:
- `fastapi_core/core/config.py`
- `fastapi_core/docmesh_bridge.py`
- `fastapi_core/dependencies/milvus.py`
- `fastapi_core/dependencies/async_milvus.py`

작업:
- `_adapt_docmesh_milvus_config()` 를 `docmesh_bridge.py` 로 이동
- `resolve_milvus_config()` 를 `docmesh_bridge.py` 로 이동
- `dependencies/milvus.py`, `dependencies/async_milvus.py` import 경로 교체
- `load_docmesh_settings()` 도 `docmesh_bridge.py` 로 옮기거나, 정말 필요 없으면 제거

검증:
- Milvus dependency/unit tests 통과
- docmesh state 존재/부재 두 케이스 모두 유지

### Step 3. `core/config.py`를 pure config module로 축소
대상 파일:
- `fastapi_core/core/config.py`

작업:
- bridge 책임 제거 후 import 정리
- `config.py` 모듈 상단/하단 helper 순서를 "모델 → loader → 끝" 구조로 단순화
- docmesh import가 남지 않도록 정리

검증:
- `read_file fastapi_core/core/config.py` 기준으로 docmesh 관련 import/function 제거 확인

### Step 4. 설정 계약 테스트 추가
대상 파일(신규 또는 기존 확장):
- `test_fastapi_core/core/test_config.py`
- 필요 시 `test_fastapi_core/test_public_api.py`

추가할 테스트 후보:
1. `load_env_config()` 가 nested env 값을 정상 파싱한다.
2. `load_service_settings()` 가 YAML 미존재 시 기본값 fallback 한다.
3. `resolve_milvus_config()` 가 docmesh settings 가 있을 때 docmesh 값을 우선한다.
4. `resolve_milvus_config()` 가 docmesh settings 가 없을 때 `EnvConfig.milvus` 를 그대로 쓴다.
5. public API에 노출해야 하는 설정 타입만 `fastapi_core.__all__` 에 남아 있는지 확인한다.

### Step 5. 문서 동기화
대상 파일:
- `docs/config.md`
- 필요 시 `docs/api.md`

작업:
- `core/config.py` 설명에서 docmesh-specific helper를 제거
- docmesh integration 관련 설명은 bridge/lifecycle 쪽으로 이동
- "설정 모델" 과 "docmesh registry integration" 을 분리해 기술

검증:
- stale 설명 검색
- `docs/config.md` 와 실제 코드 surface 일치 여부 재확인

## Suggested Test/Verification Commands
순서대로 실행 권장:

```bash
uv run pytest -q test_fastapi_core/core/test_config.py
uv run pytest -q test_fastapi_core/dependencies/test_milvus.py test_fastapi_core/dependencies/test_async_milvus.py
uv run pytest -q test_fastapi_core/test_public_api.py
uv run pytest -q -m 'not integration'
```

`test_config.py` 가 아직 없으면 Step 4에서 함께 추가한다.

## Risks
1. **암묵적 public API 파손**
   - repo 내부 사용처가 없어도 외부 소비자가 `load_application_settings()` 를 import 중일 수 있다.
   - 대응: 제거 전 `__init__.py` export 현황 확인. 현재는 export되지 않아 risk는 중간 이하.

2. **Milvus fallback 동작 변경 위험**
   - 함수 이동 과정에서 docmesh settings 우선 규칙이 바뀌면 sync/async Milvus 동작이 달라질 수 있다.
   - 대응: 이동 전후 동일 테스트 유지.

3. **문서-코드 drift 지속**
   - 구조만 분리하고 테스트가 없으면 다시 같은 drift가 생긴다.
   - 대응: 최소한 설정 기본값/핵심 surface 검증 테스트 추가.

## Open Questions
1. 중장기적으로 `EnvConfig` 일부를 docmesh `Settings` 래퍼/adapter로 축소할 것인가?
2. `DatabaseConfig.sqlalchemy_database_url` 같은 convenience 계산 프로퍼티는 fastapi-core 고유 책임으로 유지할 것인가?
3. `docs/config.md` 를 수동 유지할지, 테스트 기반 drift detection만 둘지, 완전 생성형으로 갈지?

## Recommended Execution Order
1. dead surface (`ApplicationSettings`, `load_application_settings`) 사용처 확인
2. Milvus/docmesh helper 이동
3. `core/config.py` 정리
4. 테스트 추가
5. 문서 sync

## Expected Outcome
리팩터링 후에는 아래처럼 읽히는 구조가 된다.

- `core/config.py` = fastapi-core 설정 정의 및 로딩
- `docmesh_bridge.py` = docmesh registry/settings 적응 계층
- `dependencies/*` = runtime state/dependency resolution
- `docs/config.md` = 위 구조를 반영한 사용자 문서

이 상태가 되면 향후 2단계로 **docmesh와 truly duplicated field를 더 줄일지**, 아니면 **fastapi-core의 독자 설정 표면을 유지할지**를 별도 결정하기 쉬워진다.
