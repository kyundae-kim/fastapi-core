---
title: docmesh-py-core vs fastapi-core usage comparison
created: 2026-06-29
updated: 2026-06-29
type: query
tags: [query, comparison, implementation, api]
sources: [raw/articles/docmesh-py-core-api-reference-2026.md, raw/articles/docmesh-py-core-configuration-guide-2026.md, raw/articles/docmesh-py-core-examples-guide-2026.md, pyproject.toml, fastapi_core/config.py, fastapi_core/dependencies/auth.py, fastapi_core/routers/health.py, fastapi_core/factory.py, test_fastapi_core/conftest.py]
confidence: high
---

# docmesh-py-core vs fastapi-core usage comparison

## Question

`[[docmesh-py-core]]` 엔티티 페이지가 현재 fastapi-core 코드베이스와 비교했을 때 갱신이 필요한지 검토한다.

## Verification baseline

- Dependency pin: `pyproject.toml`의 `tool.uv.sources.docmesh-py-core.rev = "v0.1.3"`
- Installed package version: `uv run python` + `importlib.metadata.version("docmesh-py-core")` → `0.1.3`
- Root export inspection: `/workspaces/fastapi-core/.venv/lib/python3.11/site-packages/docmesh_py_core/__init__.py`
- Verification command: `uv run pytest -q` → `12 passed, 1 warning in 0.24s`

## Implemented / aligned

- `fastapi_core/config.py`와 `test_fastapi_core/conftest.py`는 `load_settings()`와 `Settings`를 사용해 환경변수 기반 설정 로딩 계약을 그대로 소비한다. 이는 `[[service-configuration-contracts]]` 및 `[[docmesh-py-core]]`의 핵심 설명과 일치한다.
- `fastapi_core/dependencies/auth.py`는 `KeycloakAuthService`, `TokenValidationError`, `AuthenticatedUser`를 사용해 토큰 검증과 사용자 변환을 구현한다. 따라서 `[[keycloak-authentication-api]]`와 연결된 인증 책임 설명은 현재 코드와 정렬되어 있다.
- `fastapi_core/routers/health.py`는 `check_all_services()`와 `HealthCheckError`를 사용해 readiness 집계를 수행한다. `required_services`와 `parallel` 인자를 함께 전달하므로 `[[service-health-check-aggregation]]` 연결도 실제 코드로 확인된다.

## Partially implemented

- `[[docmesh-py-core]]` 페이지의 "Recommended consumption flow"는 registry 기반 수명주기(`ServiceFactoryRegistry(...) → create_client() → close_all()`)를 기본 소비 경로로 설명하지만, 현재 fastapi-core 코드는 그 흐름을 채택하지 않는다. 실제 앱 팩토리(`fastapi_core/factory.py`)는 `Settings`만 state에 저장하고 있으며 registry/wrapper를 생성하지 않는다.
- 예제 문서 기반으로 정리된 Langfuse/NATS/공용 로깅/재시도 유틸리티는 `[[docmesh-py-core]]` 페이지에서 중요한 통합 축으로 서술돼 있지만, 현재 fastapi-core import 지점에서는 사용되지 않는다. 따라서 "라이브러리가 제공한다"는 설명은 맞지만 "현재 fastapi-core가 그렇게 통합한다"는 뉘앙스는 약화가 필요하다.

## Changes applied to the entity page

- `[[docmesh-py-core]]`에 현재 버전 pin(`v0.1.3`)과 설치 버전(`0.1.3`)을 반영했다.
- 최신 `__all__` 기준으로 누락돼 있던 결과/오류 타입(`AccessTokenResult`, `ConfigError`, `ServiceClientError`, `ServiceClientWrapperError`, `UnsupportedServiceError`, `KeycloakTokenAuthenticationError`, `KeycloakTokenConfigurationError`, `KeycloakTokenError`, `KeycloakTokenTemporaryError`, `TokenValidationError`, `AuthenticatedUser`) 노출 사실을 보강했다.
- 기존 "Open questions"를 실제 코드 대조 결과 기반의 "Observed fastapi-core usage"로 교체했다.

## Divergent / architecturally changed

- 없음. 다만 엔티티 페이지가 라이브러리의 전체 권장 사용 흐름과 fastapi-core의 실제 채택 범위를 충분히 구분하지 않아, 과도한 adoption처럼 읽힐 수 있다.

## Remaining watchpoints

- `[[docmesh-py-core]]`는 여전히 라이브러리 capability와 현재 fastapi-core adoption을 함께 다루므로, 이후 registry/wrapper 또는 NATS/Langfuse 경로가 실제로 도입되면 이 비교 페이지와 엔티티 페이지를 함께 재검토하는 것이 좋다.
- fastapi-core가 향후 `ServiceFactoryRegistry` 또는 공용 로깅/재시도 유틸리티를 직접 사용하기 시작하면 `[[service-factory-registry]]`, `[[operational-logging-and-retry-utilities]]`와의 연결 강도를 다시 높일 수 있다.

## Verdict

검토 결과 `[[docmesh-py-core]]` 페이지의 큰 방향성은 유지 가능했고, 버전 pin(`v0.1.3`)·최신 export·실제 fastapi-core 채택 범위를 반영하도록 갱신했다. 현재 기준 가장 중요한 해석은 "라이브러리는 registry 중심의 더 넓은 통합 능력을 제공하지만, fastapi-core는 아직 설정/인증/헬스체크 일부만 직접 채택하고 있다"는 점이다.
