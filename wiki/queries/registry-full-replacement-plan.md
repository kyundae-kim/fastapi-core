---
title: registry full replacement plan
created: 2026-06-14
updated: 2026-06-14
type: query
tags: [query, architecture, migration, sdk, decision]
sources: [queries/fastapi-core-codebase-review-against-docmesh-py-core.md, queries/docmesh-py-core-refactor-review.md]
confidence: medium
---
# registry full replacement plan

## Summary
`fastapi-core` 에서 `docmesh_py_core.ServiceFactoryRegistry` 로 **완전 대체 가능한 부분은 즉시 대체**하고, registry가 아직 직접 지원하지 않는 경로는 의도적으로 native로 남기는 전략이 가장 안전하다. 현재 기준 완전 대체 대상은 `keycloak`, `postgres`, `minio`, `milvus`(sync), `ollama`, `langfuse`, `nats` 이고, `async_milvus` 는 제외해야 한다. 이 방향은 [[service-factory-registry]], [[sdk-health-check-patterns]], [[fastapi-core-codebase-review-against-docmesh-py-core]], [[docmesh-py-core-refactor-review]] 와 정렬된다.

## What can be fully registry-backed now
- `auth_provider` → `create_client("keycloak")`
- `db_engine` → `create_client("postgres")`
- `minio_client` → `create_client("minio")`
- `milvus_client` → `create_client("milvus")`
- `ollama_client` → `create_client("ollama")`
- `langfuse_client` → `create_client("langfuse")`
- `nats_client` → `create_client("nats")` 후 `connect()`

현재 실행 환경에서 `docmesh_py_core.ServiceFactoryRegistry` 소스를 확인한 결과, 위 서비스들은 builder/wrapper 수준에서 이미 지원된다. 특히 `langfuse_builder` 와 `nats_builder` 도 registry에 포함되어 있으므로, FastAPI 쪽 lifecycle에서 native 생성기를 계속 직접 호출할 이유가 줄어든다.

## What should stay native for now
`async_milvus_client` 는 아직 registry 완전 대체 대상이 아니다. 현재 설치된 `docmesh_py_core` registry는 sync `MilvusClient` 를 감싸는 builder 는 제공하지만 `AsyncMilvusClient` builder 는 제공하지 않는다. 따라서 이 경로를 억지로 registry처럼 보이게 감싸기보다는, native path 로 남겨 두고 upstream registry 확장을 기다리는 편이 맞다. 이는 [[service-client-wrapper]] 와 [[nats-connection-builder]] 에서 보인 "비동기/특수 계약은 숨기지 말고 드러내라"는 원칙과도 일치한다.

## Highest-value implementation slices
1. lifecycle startup 의 `langfuse` 생성도 registry 경로로 이동
2. registry 지원 서비스 메타데이터를 한곳에 모아 startup/shutdown 중복 분기 제거
3. shutdown ownership 을 `docmesh_managed_services` 기준으로 더 일관되게 처리
4. 필요하면 `dependencies/langfuse.py` 를 추가해 request-time/state caching 도 registry-first 로 정렬
5. readiness 의 Langfuse check 도 registry-backed state 가 있으면 그 경로를 우선 사용
6. `async_milvus` 는 "현재는 native 유지"를 테스트와 문서로 명시

## Recommended end state
최종 구조는 "지원되는 서비스 생성은 registry가 전부 담당하고, FastAPI는 state/cache/lifespan/route wiring만 담당" 하는 형태다. 즉 `fastapi-core` 는 [[docmesh-py-core]] 위의 얇은 composition layer 로 수렴해야 한다. 다만 이 목표를 위해 unsupported service 까지 추상화로 덮어쓰지는 말고, `async_milvus` 같은 예외는 예외로 남겨 두는 것이 더 정직하고 유지보수에도 유리하다.

## Artifact
상세 실행 계획은 `docs/plans/2026-06-14-registry-full-replacement.md` 에 저장했다.
