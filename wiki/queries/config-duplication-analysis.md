---
title: config duplication analysis
created: 2026-06-24
updated: 2026-06-24
type: query
tags: [query, config, architecture, comparison, decision]
sources: [raw/articles/fastapi-core-config-2026-06-17.md, raw/articles/docmesh-py-core-config-2026-06-11.md]
confidence: medium
---
# config duplication analysis

## Summary
`fastapi_core/core/config.py` 의 중복 문제는 단순히 필드가 많다는 수준이 아니라, **같은 설정 도메인을 fastapi-core 설정 모델, docmesh adapter, 사용자 문서가 각각 반복 표현하고 있다는 점**에 있다. 특히 `core/config.py` 가 pure config module 역할을 넘어 docmesh 적응 책임까지 떠안고 있어 `[[layered-configuration-model]]` 과 `[[load-settings-and-settings-model]]` 사이의 경계가 흐려져 있다.

## Main duplication buckets
1. **문서 중복**: `docs/config.md` 가 `EnvConfig` 와 `ServiceSettings` 의 필드/기본값을 사실상 재서술하고 있어 drift 위험이 있다. 이는 [[configuration-principles]] 와 [[layered-configuration-model]] 이 설명하는 계약을 코드와 문서 양쪽에서 수동 유지하고 있다는 뜻이다.
2. **도메인 모델 중복**: `KeycloakConfig`, `DatabaseConfig`, `MinIOConfig`, `MilvusConfig`, `OllamaConfig`, `LangfuseConfig`, `NatsConfig` 는 `docmesh_py_core.Settings` 의 대응 서비스 설정과 의미상 크게 겹친다. 단기적으로는 제거 대상이 아니라도, 최소한 fastapi-core 내부 모델과 docmesh 변환 계층은 분리되어야 한다.
3. **모듈 책임 중복**: `core/config.py` 의 `load_docmesh_settings()`, `_adapt_docmesh_milvus_config()`, `resolve_milvus_config()` 는 이미 `docmesh_bridge.py` 가 맡고 있는 integration 책임과 같은 축에 있다. 이 상태는 `[[registry-backed-dependency-resolution]]` 이 지향하는 registry/bridge 경계를 흐린다.

## Safe first-step refactor
가장 안전한 1차 리팩터링은 `core/config.py` 를 **fastapi-core canonical 설정 모델 + 로더** 로 축소하고, docmesh-specific helper를 `docmesh_bridge.py` 로 이동하는 것이다. `ApplicationSettings` 와 `load_application_settings()` 는 현재 repo 내 사용처가 보이지 않아 제거 후보이며, `resolve_milvus_config()` 는 `dependencies/milvus.py`, `dependencies/async_milvus.py` 쪽 import만 조정하면 이동 가능하다. 이 단계는 [[fastapi-core]] 의 public dependency surface 를 건드리지 않고도 경계를 더 명확하게 만든다.

## Artifact
상세 실행 계획은 `docs/plans/2026-06-24-config-dedup-refactor-plan.md` 에 저장했다. 이 계획은 dead surface 확인 → docmesh helper 이동 → `core/config.py` 정리 → 설정 계약 테스트 추가 → 문서 sync 순서를 권장한다.

## Implemented first slice
첫 번째 리팩터링 slice는 실제로 적용되었다. `fastapi_core/core/config.py` 에서 `ApplicationSettings`, `load_application_settings()`, `load_docmesh_settings()`, `resolve_milvus_config()` 를 제거해 pure config loader/module 쪽으로 축소했고, docmesh-specific helper는 `fastapi_core/docmesh_bridge.py` 로 이동했다. Milvus dependency 경로도 `docmesh_bridge.resolve_milvus_config()` 를 사용하도록 바뀌었다.

검증은 `uv run pytest -q test_fastapi_core/core/test_config.py test_fastapi_core/dependencies/test_milvus.py test_fastapi_core/dependencies/test_async_milvus.py test_fastapi_core/test_public_api.py` 에서 `34 passed`, 이어 `uv run pytest -q -m 'not integration'` 에서 `189 passed, 26 deselected` 로 확인했다.

이후 문서도 동기화했다. `docs/config.md` 에 pure config vs docmesh bridge 경계를 명시하고, `docs/api.md` 에서 설정 dependency와 Milvus dependency가 `docmesh_bridge` 책임 분리를 따름을 반영했다.

## Related Topics
- [[layered-configuration-model]] 은 `EnvConfig` 와 `ServiceSettings` 의 책임 분리를 설명한다.
- [[load-settings-and-settings-model]] 은 docmesh `load_settings()` / `Settings` 와 fastapi-core 이중 레이어의 관계를 설명한다.
- [[registry-backed-dependency-resolution]] 은 runtime dependency 경계가 어디에 있어야 하는지 설명한다.
- [[docmesh-py-core-package-structure-summary]] 는 docmesh 쪽 설정/조립/운영 레이어를 구조적으로 요약한다.
