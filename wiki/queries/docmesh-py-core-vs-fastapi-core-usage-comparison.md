---
title: docmesh-py-core vs fastapi-core usage comparison
created: 2026-06-29
updated: 2026-07-02
type: query
tags: [query, comparison, implementation, api]
sources: [raw/articles/docmesh-py-core-api-reference-2026.md, raw/articles/docmesh-py-core-configuration-guide-2026.md, raw/articles/docmesh-py-core-examples-guide-2026.md, pyproject.toml, .venv/lib/python3.11/site-packages/docmesh_py_core/__init__.py, fastapi_core/config.py, fastapi_core/docmesh_settings.py, fastapi_core/dependencies/auth.py, fastapi_core/routers/auth.py, fastapi_core/routers/health.py, fastapi_core/factory.py, test_fastapi_core/conftest.py, test_fastapi_core/test_factory.py, test_fastapi_core/test_health_router.py, test_fastapi_core/test_auth_router.py, test_fastapi_core/test_dependencies.py, test_fastapi_core/test_config.py]
confidence: high
contested: true
contradictions: [docmesh-py-core]
---

# docmesh-py-core vs fastapi-core usage comparison

## Question

최신 `[[docmesh-py-core]]` 문서(api/config/examples) 기준으로, fastapi-core 코드베이스에 아직 옛 `load_settings` / `Settings` / `ServiceFactoryRegistry` 패턴이 얼마나 남아 있는지 점검한다.

## Verification baseline

- Dependency pin: `pyproject.toml`의 `tool.uv.sources.docmesh-py-core.rev = "v0.1.3"`
- Installed package version: `uv run python` + `importlib.metadata.version("docmesh-py-core")` → `0.1.3`
- Installed export inspection: `.venv/lib/python3.11/site-packages/docmesh_py_core/__init__.py`
- Export presence check:
  - present: `Settings`, `load_settings`, `ServiceFactoryRegistry`
  - absent: `load_service_configs`, `create_postgres_client`, `close_service_clients`, `CommonConfig`, `KeycloakConfig`
- Verification command: `uv run pytest -q` → `25 passed, 1 warning in 0.37s`

## Implemented / aligned

- fastapi-core는 **설치된 `docmesh-py-core` v0.1.3 패키지**와는 정합적이다. `fastapi_core/docmesh_settings.py`는 `Settings`, `load_settings`를 import해서 `load_docmesh_settings()`를 구성한다.
- `fastapi_core/factory.py`는 `ServiceFactoryRegistry`, `Settings`, `configure_logging`를 import하고, 앱 생성 시 `registry = ServiceFactoryRegistry(app_settings)`를 만든 뒤 `app.state.registry`에 저장한다.
- `fastapi_core/factory.py`의 readiness check 구성은 `registry.create_client(service_name).check()`를 지연 호출하는 람다로 만들어져 있어, registry 기반 health wiring과 일치한다.
- lifespan 종료 구간에서 `registry.close_all()`을 호출하므로, old registry lifecycle도 실제로 코드에 남아 있다.
- `test_fastapi_core/conftest.py` 역시 테스트 설정 fixture를 `load_settings({...})` 기반으로 만들고 있다.
- 전체 테스트는 `uv run pytest -q` 기준 `25 passed, 1 warning in 0.37s`로 통과했다.

## Partially implemented

- 최신 위키가 정리한 upstream 문서 방향은 direct `load_service_configs()` + `create_*_client()` + `close_service_clients()` 조합이지만, fastapi-core는 아직 그 방향으로 마이그레이션되지 않았다.
- readiness endpoint 자체는 `check_all_services()` 중심 표준 포맷을 사용하므로 health aggregation 계층은 최신 문서 방향과 개념적으로 가깝다. 다만 check callable을 준비하는 상위 계층은 여전히 registry 중심이다.
- auth / health / logging 계층은 여전히 동작하고 테스트도 통과하지만, 이것은 "최신 main 문서와 정합"이라기보다 "핀된 v0.1.3 패키지와 정합"으로 읽는 편이 정확하다.

## Missing from fastapi-core relative to latest docs

- `load_service_configs()` 기반 설정 로딩 경로가 없다.
- `CommonConfig`, `KeycloakConfig` 같은 direct config class 사용 경로가 없다.
- `create_postgres_client`, `create_minio_client`, `create_langfuse_client`, `create_nats_client` 같은 direct factory 호출이 없다.
- `close_service_clients()` 기반 종료 정리 경로가 없다.
- 최신 examples가 보여주는 "개별 client를 `app.state`에 직접 저장하는 FastAPI 패턴"도 아직 채택되지 않았다.

## Divergent / architecturally changed

- 가장 중요한 차이는 **upstream 최신 문서와 installed package v0.1.3의 공개 표면이 서로 다르다**는 점이다. 최신 raw 문서들은 direct config/direct factory 표면을 canonical path로 설명하지만, 실제 fastapi-core가 설치해 사용하는 v0.1.3의 `__all__`은 여전히 `Settings`, `load_settings`, `ServiceFactoryRegistry`를 내보내고, 최신 direct APIs는 export하지 않는다.
- 따라서 fastapi-core가 "최신 docs를 안 따라간다"고 단정하기보다, 현재는 **문서가 핀된 릴리스보다 앞서 있다**고 보는 것이 더 정확하다.
- 다시 말해 현재 fastapi-core의 registry 사용은 단순한 기술부채만이 아니라, **실제 설치된 패키지 표면에 맞춘 합리적 선택**이기도 하다.

## Changes applied to the interpretation

- 이전 비교 메모에서 registry 채택은 "upstream capability의 일부 채택"처럼 읽혔지만, 현재는 설치된 v0.1.3 public API의 핵심 경로라는 점이 더 분명해졌다.
- 최신 wiki entity/concept 페이지는 upstream main 문서 기준 direct factory 방향을 반영하되, 이 비교 페이지는 fastapi-core의 실제 의존 버전과 코드 현실을 분리해서 기록한다.
- `[[service-factory-registry]]`는 now-canonical API 설명이 아니라 historical / pinned-version integration pattern으로 읽어야 한다.

## Recommended next moves

1. fastapi-core가 계속 `docmesh-py-core` `v0.1.3`에 머문다면, 현재 registry 기반 통합은 유지 가능하다.
2. 최신 upstream 문서 방향으로 이동하려면 먼저 실제 배포 가능한 릴리스에 `load_service_configs()` / `create_*_client()` / `close_service_clients()`가 포함되는지 확인해야 한다.
3. 그 릴리스가 준비되면 `fastapi_core/docmesh_settings.py`, `fastapi_core/factory.py`, `test_fastapi_core/conftest.py`를 우선 direct factory 패턴으로 재구성하는 것이 자연스러운 1차 마이그레이션 범위다.

## Verdict

현재 fastapi-core에는 옛 `load_settings` / `Settings` / `ServiceFactoryRegistry` 패턴이 **명확히 남아 있다**. 하지만 이것은 최신 upstream 문서에 비해 뒤처진 구현이라기보다, **설치되어 있는 `docmesh-py-core` v0.1.3 패키지와는 정확히 정합한 구현**이다. 따라서 오늘 기준 핵심 결론은 "fastapi-core가 old pattern에 묶여 있다"보다 "upstream main 문서와 pinned runtime package 사이에 표면 불일치가 있으며, fastapi-core는 현재 런타임 패키지 쪽에 맞춰져 있다"이다.
