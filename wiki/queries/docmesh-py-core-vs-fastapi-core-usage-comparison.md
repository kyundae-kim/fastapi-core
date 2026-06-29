---
title: docmesh-py-core vs fastapi-core usage comparison
created: 2026-06-29
updated: 2026-06-29
type: query
tags: [query, comparison, implementation, api]
sources: [raw/articles/docmesh-py-core-api-reference-2026.md, raw/articles/docmesh-py-core-configuration-guide-2026.md, raw/articles/docmesh-py-core-examples-guide-2026.md, pyproject.toml, fastapi_core/config.py, fastapi_core/docmesh_settings.py, fastapi_core/dependencies/auth.py, fastapi_core/routers/auth.py, fastapi_core/routers/health.py, fastapi_core/factory.py, test_fastapi_core/conftest.py, test_fastapi_core/test_factory.py, test_fastapi_core/test_auth_router.py, test_fastapi_core/test_health_router.py, test_fastapi_core/test_dependencies.py, test_fastapi_core/test_config.py]
confidence: high
---

# docmesh-py-core vs fastapi-core usage comparison

## Question

`[[docmesh-py-core]]` 엔티티 페이지가 현재 fastapi-core 코드베이스와 비교했을 때 갱신이 필요한지 검토한다.

## Verification baseline

- Dependency pin: `pyproject.toml`의 `tool.uv.sources.docmesh-py-core.rev = "v0.1.3"`
- Installed package version: `uv run python` + `importlib.metadata.version("docmesh-py-core")` → `0.1.3`
- Root export inspection: `/workspaces/fastapi-core/.venv/lib/python3.11/site-packages/docmesh_py_core/__init__.py`
- Verification command: `uv run pytest -q` → `25 passed, 1 warning`

## Implemented / aligned

- `fastapi_core/docmesh_settings.py`와 `test_fastapi_core/conftest.py`는 `load_settings()`와 `Settings`를 사용해 환경변수 기반 설정 로딩 계약을 그대로 소비한다. 이는 `[[service-configuration-contracts]]` 및 `[[docmesh-py-core]]`의 핵심 설명과 일치한다.
- `fastapi_core/factory.py`는 이제 `ServiceFactoryRegistry(settings)`를 생성하고 `registry.close_all()`까지 shutdown 경로에 연결한다. 따라서 registry 기반 수명주기 설명은 더 이상 fastapi-core 외부 capability에만 머물지 않는다.
- `fastapi_core/factory.py`는 `configure_logging(...)`를 사용해 앱 로깅을 초기화하고, JSON formatter를 덧씌우는 구조를 가진다. 공용 운영 로깅 유틸리티 채택이 실제 코드로 확인된다.
- `fastapi_core/dependencies/auth.py`와 `fastapi_core/routers/auth.py`는 `KeycloakAuthService`, `AuthenticatedUser`, `TokenValidationError`, `KeycloakTokenAuthenticationError`, `KeycloakTokenConfigurationError`, `KeycloakTokenTemporaryError`, `KeycloakTokenError`를 사용해 토큰 발급/검증 흐름과 실패 매핑을 구현한다.
- `fastapi_core/routers/health.py`는 `check_all_services()`와 `HealthCheckError`를 사용해 readiness 집계를 수행한다. `required_services`, `parallel`, optional failure의 `degraded` 상태까지 실제 테스트로 확인된다.
- `fastapi_core/factory.py`의 readiness 기본 구성은 `enabled_services` 목록에 대해 `registry.create_client(service_name).check()`를 생성한다. 즉 registry 기반 서비스 health check 소비도 현재 코드에 존재한다.

## Partially implemented

- `docmesh-py-core`가 제공하는 더 넓은 서비스 군(Langfuse, NATS builder, MinIO/Milvus 개별 helper 등)은 fastapi-core에서 모두 1차 공개 API로 승격되지는 않았다. 현재 채택은 주로 settings, registry, auth, health, logging 층에 집중돼 있다.
- 메시징/NATS는 settings와 readiness 확장 지점으로는 연결되지만, `get_nats_connection` 같은 FastAPI dependency나 publisher/subscriber helper는 fastapi-core에서 직접 제공하지 않는다.
- `docmesh-py-core`의 재시도 유틸리티(`retry_call`)와 일부 고수준 helper는 현재 fastapi-core 공개 표면에서 직접 사용되지 않는다.

## Changes applied to the entity page

- `[[docmesh-py-core]]`의 fastapi-core 채택 범위를 최신 코드 기준으로 갱신했다.
- registry / logging / readiness 기본 구성이 실제로 사용된다는 점을 반영했다.
- 기존의 "registry를 채택하지 않는다"는 서술을 제거했다.
- 메시징/NATS는 settings/readiness 확장 지점으로 설명하고, 1차 FastAPI 공개 API가 아님을 명확히 했다.

## Divergent / architecturally changed

- 없음. 다만 라이브러리의 전체 capability와 fastapi-core의 현재 채택 범위는 여전히 구분해서 읽어야 한다.

## Remaining watchpoints

- fastapi-core가 향후 `get_nats_connection` 같은 전용 dependency를 추가하면 `[[application-integration-patterns]]` 및 메시징 문서를 함께 갱신해야 한다.
- `retry_call` 또는 추가 서비스 helper를 실제 코드에서 채택하기 시작하면 `[[operational-logging-and-retry-utilities]]` 연결 강도를 다시 높일 수 있다.
- registry 기반 readiness 기본 구성이 더 많은 서비스에 대해 공식화되면 `[[service-factory-registry]]`, `[[service-health-check-aggregation]]`와의 관계를 더 구체적으로 기술할 수 있다.

## Verdict

검토 결과 `[[docmesh-py-core]]` 페이지는 갱신이 필요했다. 현재 기준 가장 중요한 해석은 "라이브러리는 여전히 더 넓은 capability를 제공하지만, fastapi-core도 이제 settings/인증/헬스체크 일부만 쓰는 수준을 넘어 registry, 구조화 로깅, 기본 readiness 구성까지 실제로 채택하고 있다"는 점이다.
