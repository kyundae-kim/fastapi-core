---
title: fastapi-core PRD vs source-code comparison
created: 2026-07-13
updated: 2026-07-13
type: query
tags: [query, comparison, requirement, implementation, test]
sources: [raw/articles/fastapi-core-prd-v0.4.md, pyproject.toml, fastapi_core/config.py, fastapi_core/docmesh_settings.py, fastapi_core/factory.py, fastapi_core/dependencies/auth.py, fastapi_core/dependencies/config.py, fastapi_core/dependencies/services.py, fastapi_core/routers/auth.py, fastapi_core/routers/health.py, fastapi_core/schemas/token.py, fastapi_core/schemas/user.py, fastapi_core/schemas/health.py, test_fastapi_core/test_factory.py, test_fastapi_core/test_dependencies.py, test_fastapi_core/test_auth_router.py, test_fastapi_core/test_health_router.py, test_fastapi_core/test_config.py, test_fastapi_core/test_schemas.py, test_fastapi_core/integration/]
confidence: high
---

# fastapi-core PRD vs source-code comparison

## Question

`docs/prd.md` v0.4가 현재 `fastapi-core` 구현과 테스트에 실제로 정렬되어 있는지 점검한다. PRD의 capability 경계를 유지하면서 구현 여부를 **정렬**, **부분 구현**, **누락**, **아키텍처 차이**로 분류한다. 이 비교는 [[docmesh-py-core]]와 [[application-integration-patterns]]의 최신 통합 맥락도 함께 고려한다.

## Verification baseline

- PRD 원문: `docs/prd.md` (`문서 상태: aligned-to-source`, v0.4)
- 패키지: `fastapi-core 0.2.0`, `docmesh-py-core` source pin `v0.2.0`
- 설치 버전/공개 표면 확인:
  - `docmesh-py-core` → `0.2.0`
  - `assemble_services(...)`와 async `assemble_service_runtime(...)`가 공개됨
  - `close_service_clients(...)`는 동기 함수이며, `ServiceRuntime.close()`는 async 메서드임
- 전체 검증: `uv run pytest -q` → **57 passed, 2 third-party deprecation warnings in 20.75s**
- NATS `NatsConnectionBuilder.close` unawaited-coroutine runtime warning은 P0 반영 후 제거됨.

## Implemented / aligned

| PRD 요구 | 판정 | 구현 및 검증 증거 |
|---|---|---|
| FR-001~003 | 정렬 | `fastapi_core/factory.py:create_app()`이 공통 앱 팩토리이며 `AppConfig`, `ServiceConfigs`, custom lifespan을 받고 `CORSMiddleware`를 등록한다. `test_factory.py`가 기본 조립, 설정된 token URL, custom lifespan을 검증한다. |
| FR-004~006 | 정렬 | health router는 항상 포함되고 auth router는 `include_auth_router`로 제어된다. 인증 경로는 token 발급 실패를 401/500/502/503으로, token 누락·검증 실패를 401로 변환한다. 관련 factory/auth/dependency 테스트가 통과한다. |
| FR-010~013 | 정렬 | `routers/auth.py`가 token 발급과 현재 사용자 조회를, `routers/health.py`가 liveness/readiness를 제공한다. 네 라우팅 표면 모두 테스트로 확인된다. |
| FR-020~025 | 정렬 | `get_config`, `get_settings`, `get_auth_provider`, `get_current_user`, `require_permissions`와 generic/typed service-client dependency가 구현되어 있다. `test_dependencies.py`는 401, 403, concrete client 반환, 미활성 서비스 503을 검증한다. |
| FR-030~033 | 정렬 | `OAuth2PasswordBearer(auto_error=False)`로 bearer token을 읽고, 누락·무효 token은 401, 권한 부족은 403, `AuthenticatedUser`는 `UserInfo`로 변환된다. unit 및 live Keycloak integration 테스트가 이를 다룬다. |
| FR-040~042 | 정렬 | `TokenResponse`, `UserInfo`, `HealthResponse`가 Pydantic 모델로 제공되고 router `response_model`에 직접 사용된다. `test_schemas.py`와 router 테스트가 통과한다. |
| FR-050, FR-052~053 | 정렬 | `AppConfig`와 `ServiceConfigs`가 설정 계약을 담당한다. enabled/required 서비스 메타데이터와 `check_all_services()`를 통해 readiness가 `ok`/`degraded`/`error` 및 200/503으로 구분된다. [[service-configuration-contracts]]와 [[service-health-check-aggregation]] 참조. |

PRD의 핵심 제품 표면인 앱 조립, 인증, health, dependency, 표준 schema는 현재 소스에 모두 존재하며 테스트 증거도 있다. ^[raw/articles/fastapi-core-prd-v0.4.md]

## Resolved alignment gap

### FR-051 — 메시징/NATS의 startup/shutdown 연계

- **startup 확장 지점:** `create_app(..., lifespan=...)`이 사용자 lifespan을 감싸고, NATS builder는 `app.state.service_clients` 및 typed dependency로 노출된다.
- **기본 연결 소유권은 제한적:** `fastapi_core` 자체는 `NatsConnectionBuilder.connect()`를 호출하지 않는다. `integration/test_nats_lifespan.py`도 실제 builder 연결을 수행하기보다 사용자 lifespan에서 probe 상태를 기록하고 readiness를 호출한다.
- **shutdown 정리 정렬:** `_build_lifespan()`이 `finally`에서 `await ServiceRuntime.close()`를 실행한다. async NATS close await와 custom lifespan shutdown 실패 시 cleanup이 회귀 테스트로 검증된다.
- **readiness 정렬:** `async_check_all_services()`를 await하고 필수 실패 시에도 전체 서비스 결과를 보존한다.

따라서 PRD가 요구하는 startup/shutdown 연계와 정상 종료 자원 정리는 현재 구현 및 테스트로 충족된다. 실제 NATS 장기 연결 생성은 서비스별 custom lifespan 확장 책임으로 유지된다. ^[raw/articles/fastapi-core-prd-v0.4.md]

## Missing

현재 PRD capability 중 소스에서 완전히 부재한 항목은 확인되지 않았다.

## Architecture alignment

- 기본 `create_app()` 경로는 lifespan startup에서 async `assemble_service_runtime()`을 사용해 설정 탐색, required 검증, client 생성, 선택적 startup healthcheck를 수행한다.
- 명시적 `settings` 주입은 테스트/특수 실행을 위한 direct factory seam으로 유지되지만 결과를 `ServiceRuntime`으로 감싸 동일한 check/close lifecycle을 사용한다.
- runtime은 `app.state.service_runtime`에 노출되고 기존 `settings` / `service_clients` state 계약도 유지된다.

## Test coverage caveats

- 전체 57개 테스트가 통과하며 남은 2개 warning은 third-party deprecation warning이다.
- CORS middleware 등록은 코드로 확인되나, 실제 preflight/response header 동작을 검증하는 전용 테스트는 없다.
- async service client close await와 custom lifespan shutdown 실패 시 cleanup은 전용 테스트로 검증된다.
- live integration 테스트는 Keycloak, NATS, PostgreSQL readiness를 다루지만, MinIO/Milvus/Ollama/Langfuse의 live lifecycle은 직접 검증하지 않는다.

## Verdict

**PRD capability와 v0.2.0 권장 조립 방향에 정렬됐다.** FR-001~053의 제품 capability, async shutdown/readiness, assembly-first 기본 경로, mapping 설정, startup rollback, timeout/`one_of`, close 실패 로깅이 구현과 테스트에 의해 뒷받침된다. 남은 항목은 NATS 장기 연결 소유권과 CORS 동작 테스트 같은 제품별 심화 과제다.
