---
title: docmesh-py-core consumer implementation minimization
created: 2026-08-02
updated: 2026-08-02
type: query
tags: [query, comparison, implementation, architecture, integration, refactor, decision]
sources:
  - raw/articles/docmesh-py-core-api-reference-v0.6.0.md
  - raw/articles/docmesh-py-core-configuration-guide-v0.6.0.md
  - raw/articles/docmesh-py-core-examples-guide-v0.6.0.md
  - raw/articles/docmesh-py-core-env-example-v0.6.0.md
  - README.md
  - pyproject.toml
  - fastapi_core/runtime.py
  - fastapi_core/lifecycle.py
  - fastapi_core/readiness.py
  - fastapi_core/resources.py
  - fastapi_core/dependencies/services.py
  - fastapi_core/dependencies/auth.py
  - fastapi_core/routers/auth.py
  - fastapi_core/routers/health.py
  - .venv/lib/python3.11/site-packages/docmesh_py_core/service_containers.py
  - .venv/lib/python3.11/site-packages/docmesh_py_core/health.py
  - .venv/lib/python3.11/site-packages/docmesh_py_core/keycloak.py
  - .venv/lib/python3.11/site-packages/docmesh_py_core/service_clients.py
  - .venv/lib/python3.11/site-packages/docmesh_py_core/error_utils.py
confidence: medium
---

# docmesh-py-core consumer implementation minimization

## Question

`docmesh-py-core`를 소비하는 FastAPI 서비스가 lifecycle·readiness·resource·auth·client dependency를 반복 구현하지 않도록 하려면, 다음 버전에서 어떤 framework-neutral 계약을 우선 제공해야 하는가?

## Evidence baseline

- 현재 소비 저장소는 `docmesh-config` v0.1.0과 `docmesh-py-core` v0.6.0을 사용한다. `docmesh_py_core` package root에는 69개 공개 심볼이 있다.
- `docmesh-py-core`에는 이미 `service_lifespan()`, `ServiceRuntime.check_with_policy()`, `RuntimeHealthDescriptor`, `ServiceRuntime.require_client()`, `ServiceCloseError`, `serialize_error()`, `SERVICE_CATALOG`가 있다. 따라서 소비자가 이 기능을 다시 만드는 것이 아니라, 이 계약을 FastAPI·다른 framework adapter가 재사용하기 쉬운 형태로 확장하는 것이 맞다.^[raw/articles/docmesh-py-core-api-reference-v0.6.0.md]
- fastapi-core의 관련 adapter 모듈은 `factory.py` 343줄, `lifecycle.py` 94줄, `runtime.py` 114줄, `readiness.py` 230줄, `resources.py` 288줄, `dependencies/services.py` 141줄, `dependencies/auth.py` 109줄, `routers/auth.py` 126줄, `routers/health.py` 139줄이다. 합계 1,584줄이 모두 제거 대상은 아니지만, 그중 lifecycle·health·resource·auth wiring의 상당 부분이 Py Core 계약을 framework 표면에 번역하는 코드다.
- 검증 baseline은 `uv run --frozen pytest -q` → `218 passed, 1 skipped, 1 warning`이다. 설치 패키지와 설정 버전은 `.venv` introspection으로 각각 `0.6.0`과 `0.1.0`을 확인했다.

## What is already reusable

| 영역 | 현재 Py Core 계약 | 소비자에서 재구현되는 부분 |
| --- | --- | --- |
| Runtime | `service_lifespan`, async assembly, rollback, async close | FastAPI lifespan 안에서 injected runtime과 자동 assembly를 분기하고 resource shutdown 순서를 직접 조정한다. |
| Health | `RuntimeHealthDescriptor`, `async_check_all_services`, `HealthCheckResult` | runtime check를 `ReadinessCheckSpec`으로 변환하고 nested result를 merge하며 HTTP status·redaction을 다시 계산한다. |
| Client lookup | `ServiceRuntime.require()`와 `require_client()` | 서비스별 getter 8개, wrapper unwrap, concrete type 검사, 503/500 변환을 반복한다. |
| Auth | `KeycloakAuthService`, typed token/JWT errors, `AuthenticatedUser` | sync provider thread offload, roles/scopes 추출, token error-to-HTTP mapping, provider policy mutation을 직접 작성한다. |
| Operations | `ServiceClientWrapper.runtime_defaults`와 service catalog | MinIO/Milvus/Ollama/Langfuse의 timeout·retry 설정 중 일부가 실제 SDK 호출 정책으로 연결되지 않아 소비자가 다시 적용해야 한다. |
| Messaging | lazy `NatsConnectionBuilder.connect()` | persistent connection의 `drain()`/`close()` 소유권을 application이 별도로 관리한다. |

현재 FastAPI 쪽에서 가장 큰 중복은 개별 factory가 아니라 `fastapi_core/readiness.py`와 `resources.py`가 각각 health·lifecycle registry를 보유하고, `lifecycle.py`가 서비스 runtime과 application resource의 종료를 조합하는 구조다. `ServiceRuntime`은 descriptor를 이미 검증하지만 consumer는 `configure_service_runtime()`에서 다시 check 존재 여부·이름 충돌·required flag를 검사한다.^[raw/articles/docmesh-py-core-api-reference-v0.6.0.md]

## Prioritized improvements

### P0 — framework-neutral health registry를 first-class 계약으로 승격

`RuntimeHealthDescriptor`를 단순한 runtime 내부 검증 자료가 아니라 외부 registry가 소비할 수 있는 `HealthCheckSpec`으로 확장한다. 제안하는 개념적 API는 다음과 같다. 이름은 예시이며 기존 `ServiceRuntime.check()`와 호환되는 additive API여야 한다.

```text
runtime.health_specs() -> tuple[HealthCheckSpec, ...]
HealthRegistry.from_runtime(runtime)
HealthRegistry.register(spec)
await HealthRegistry.check(names=None, policy=HealthcheckPolicy(...))
```

`HealthCheckSpec`에는 name, callable, required, per-check timeout, error redaction, result adapter를 포함하고, registry는 service check와 application-owned check를 동일하게 집계해야 한다. required 실패 때 모든 서비스 결과를 보존하고, optional 실패를 degraded로 구분하며, per-service/overall timeout의 error code를 안정적으로 제공해야 한다. 이 계약은 HTTP status를 직접 만들지 않고 `ok/degraded/error`에 해당하는 framework-neutral summary만 반환해야 한다.

이 기능이 있으면 fastapi-core는 `configure_service_runtime()`의 check 변환·중복 검증과 `readiness.py`의 nested result merge를 제거하고, health router는 summary를 HTTP 응답으로 렌더링하는 얇은 adapter만 남길 수 있다. `HealthCheckResult`에 `status`, `by_service()`, timeout metadata를 추가하는 것도 같은 방향이다. 현재 `async_check_all_services()`는 결과 집계는 제공하지만 arbitrary application check 등록과 redaction policy까지는 제공하지 않는다.^[raw/articles/docmesh-py-core-api-reference-v0.6.0.md]^[raw/articles/docmesh-py-core-examples-guide-v0.6.0.md]

**수용 기준**

- runtime health와 consumer resource health가 하나의 registry에서 동작한다.
- required 실패 시 성공한 optional check를 포함한 전체 결과가 유지된다.
- `parallel`, per-service timeout, overall timeout, retry, redaction이 한 계약으로 정의된다.
- FastAPI adapter는 `HealthCheckError`의 내부 구조를 재조합하지 않고 결과를 직렬화할 수 있다.

### P0 — generic managed-resource/lifecycle group 제공

FastAPI를 import하지 않는 `ManagedResource`/`ResourceGroup`을 Py Core에 추가한다. factory, healthcheck, close, required, timeout, redaction을 가진 resource를 순서대로 시작하고 역순으로 닫으며, factory 실패 시 이미 만든 resource를 rollback해야 한다. `ServiceRuntime`에 resource group을 합성하거나, `service_lifespan()`이 service runtime과 resource group을 함께 소유하는 additive overload가 적절하다.

현재 `fastapi_core/resources.py`는 288줄로 resource binding, dependency key, readiness 등록, rollback, reverse close, close failure aggregation을 모두 소유한다. `fastapi_core/lifecycle.py`도 injected runtime, custom lifespan, resource startup/shutdown, service close를 별도로 조합한다. framework-neutral group이 제공되면 FastAPI 쪽에는 `Request` 기반 `ResourceKey`와 dependency adapter만 남길 수 있다. 종료 실패는 resource와 service 양쪽을 모두 시도한 뒤 stage/name을 보존한 하나의 aggregate error로 반환해야 한다.^[raw/articles/docmesh-py-core-api-reference-v0.6.0.md]

**수용 기준**

- factory·startup check·custom application lifespan 실패가 deterministic rollback 순서를 가진다.
- resource와 service close를 모두 시도하고 모든 실패를 잃지 않는다.
- close는 멱등적이며, injected runtime도 같은 lifecycle contract를 사용한다.
- generic group은 FastAPI, Starlette, CLI에 import dependency를 만들지 않는다.

### P0 — 선언된 operation policy를 실제 client 호출에 연결

현재 config는 MinIO/Milvus/Ollama/Langfuse의 request timeout·connect timeout·max retries 일부를 파싱하지만, 설정 가이드가 명시하듯 일부 값은 `runtime_defaults`에만 보존되고 SDK constructor/retry에 자동 연결되지 않는다. `ServiceClientWrapper`에 defaults를 보관하는 것만으로는 소비자 source가 줄지 않는다.^[raw/articles/docmesh-py-core-configuration-guide-v0.6.0.md]

서비스별로 가능한 설정은 factory가 실제 SDK에 적용하고, SDK가 지원하지 않는 retry/timeout은 공통 `ServiceOperationPolicy` 또는 `invoke()` helper가 적용해야 한다. 소비자는 `runtime_defaults`를 꺼내 별도 retry loop를 작성하지 않고 wrapper/runtime의 공통 호출 계약을 사용해야 한다.

**수용 기준**

- configuration reference의 각 runtime wiring이 실제 호출 동작 또는 명시적인 unsupported diagnostic에 대응한다.
- retry 횟수, backoff, timeout, error classification이 서비스마다 임의 구현되지 않는다.
- 기존 direct factory와 `ServiceRuntime` 모두 같은 policy를 사용한다.

### P1 — prebuilt runtime과 startup policy를 같은 lifespan으로 관리

현재 `service_lifespan(plan=...)`은 자체 runtime을 만들 때는 편리하지만, FastAPI가 주입받은 prebuilt `ServiceRuntime`에는 consumer가 `check_with_policy()`와 close를 별도로 호출해야 한다. `service_lifespan(plan=..., runtime=runtime)` 또는 동등한 `manage_runtime(runtime, policy=...)`를 제공해 injected/assembled 경로의 ownership과 startup policy를 통합한다.

이렇게 하면 `fastapi_core/lifecycle.py`의 `runtime is None` 분기, `_check_runtime_on_startup()`, close 예외 로깅 일부가 사라지고 테스트용 runtime도 production runtime과 같은 contract를 사용한다. plan과 injected runtime의 selected/required service 불일치가 있으면 startup 전에 구조화 오류를 내야 한다.^[raw/articles/docmesh-py-core-examples-guide-v0.6.0.md]

### P1 — Keycloak domain convenience와 async 경계 제공

`KeycloakAuthService`의 현재 token/JWT API는 sync다. FastAPI consumer는 `/token`에서 `run_in_threadpool()`과 lambda를 직접 작성한다. `async_fetch_access_token()` 및 `async_extract_user_info()` 같은 framework-neutral async facade를 제공하면 event loop blocking을 소비자마다 반복하지 않아도 된다.

`AuthenticatedUser`에는 `all_roles`, `scopes`, `has_roles()`, `has_scopes()`, `has_permissions()` 같은 domain helper를 추가한다. 그러면 consumer의 `_get_roles()`, `_get_scopes()`, `_raise_for_missing()`가 사라지고 role 중복 제거·client role flattening·scope parsing 규칙이 한곳에서 유지된다. 반면 `HTTPException`, `Depends`, OAuth2 scheme는 Py Core에 넣지 않는다.

또한 `allowed_algorithms`는 생성 후 mutable public attribute로 두기보다 immutable policy로 보존한다. 현재 core constructor 기본값이 이미 `RS256`인데 fastapi-core가 `configure_keycloak_provider()`에서 다시 `['RS256']`로 덮어쓴다. 이 중복 mutation은 제거하거나 core에서 명시적인 auth policy constructor로 대체해야 한다.^[raw/articles/docmesh-py-core-api-reference-v0.6.0.md]

### P1 — 구조화 오류에 consumer policy metadata를 보강

`serialize_error()`는 이미 `error_type`, masked message, service, reason code, remediation, JSON-safe details를 제공한다. 다음 단계는 Keycloak token 오류와 runtime lookup/health 오류가 `retryable`, `failure_class`, `safe_message` 같은 안정적인 metadata를 제공하도록 하는 것이다. HTTP status 자체를 Py Core에 하드코딩하지 않고, FastAPI adapter가 이 metadata로 공통 mapping을 만들 수 있게 한다.

그러면 `routers/auth.py`의 예외 클래스별 status table과 `routers/health.py`의 결과 재조합이 작아지고, CLI·worker·다른 web framework도 동일한 오류 의미를 사용할 수 있다. 기존 `reason_code`와 `serialize_error()`를 대체하는 parallel error API는 만들지 않는다.^[raw/articles/docmesh-py-core-api-reference-v0.6.0.md]

### P2 — managed NATS connection과 plan-scoped 문서 생성

`NatsConnectionBuilder.connect()`가 반환한 persistent connection은 현재 caller가 `drain()`/`close()`해야 한다. `managed_connect()` async context manager 또는 runtime에 connection lease를 attach하는 API를 추가하면 messaging consumer의 shutdown 누락을 줄일 수 있다. builder 자체가 소유하지 않는 현재 lazy-check semantics는 유지하고, persistent lease를 명시적으로 선택하게 해야 한다.^[raw/articles/docmesh-py-core-examples-guide-v0.6.0.md]

`generate_environment_template()`와 `generate_configuration_reference()`에는 `RuntimePlan`을 받아 선택 서비스만 생성하는 변형도 유용하다. 현재 `.env.example`은 모든 key를 주석으로 나열하고 소비자가 uncomment 범위와 plan을 수동으로 맞춘다. 다만 `AppConfig`의 CORS·token URL·logging 같은 FastAPI 전용 설정을 Py Core로 옮기지는 않는다.^[raw/articles/docmesh-py-core-env-example-v0.6.0.md]

## Boundary decisions

- `RuntimePlan`, `Service`, `HealthcheckPolicy`, environment diagnosis의 canonical ownership은 계속 `docmesh-config`에 둔다. `docmesh-py-core`가 FastAPI `AppConfig`를 직접 해석하는 방식은 package boundary를 흐린다.
- `APIRouter`, `Depends`, OAuth2, HTTP status, RFC 7807 renderer, OpenAPI policy는 fastapi-core 책임이다. Py Core는 HTTP-neutral result/error contract만 제공한다.
- 설정 package 소비자 구현량을 줄이는 구체적인 개선은 [[docmesh-config-consumer-implementation-minimization]]에서 별도로 다룬다.
- 핵심 목표는 더 많은 per-service API를 추가하는 것이 아니라, runtime health·generic resource lifecycle·operation policy·auth domain semantics를 한 번만 구현하게 만드는 것이다. 이 방향은 [[docmesh-py-core]]의 factory/runtime 책임과 [[application-integration-patterns]]의 assembly-first 원칙을 유지한다.

## Recommended rollout

1. **다음 additive release:** `HealthCheckSpec`/generic registry, injected runtime lifespan, aggregate lifecycle error contract.
2. **그 다음 release:** operation policy 적용, Keycloak async/domain helpers, structured error metadata, managed NATS lease.
3. fastapi-core에서 새 계약을 병행 사용한 뒤 `ReadinessRegistry`·resource lifecycle·typed auth boilerplate를 deprecated하고 단계적으로 제거한다.
4. 각 단계에서 `uv run --frozen pytest -q`와 consumer contract test를 실행하고, 기존 `HealthCheckResult`·`serialize_error` payload 호환성을 유지한다.

## Verdict

소비자 구현 소스를 가장 많이 줄이는 P0는 **framework-neutral health registry**와 **generic managed-resource/lifecycle group**이다. 그 다음은 선언된 timeout/retry를 실제 operation에 연결하는 것과 injected runtime의 ownership 통합이다. Keycloak async/domain helper와 NATS lease는 개별 integration boilerplate를 줄이는 P1/P2 항목이다. FastAPI 전용 factory나 HTTP renderer를 Py Core에 넣는 것은 단기 줄 수는 줄여도 장기적으로 package boundary와 재사용성을 악화시키므로 권장하지 않는다.

이 결론은 [[service-health-check-aggregation]], [[operational-logging-and-retry-utilities]], [[service-configuration-contracts]], [[docmesh-py-core-vs-fastapi-core-usage-comparison]]과 함께 읽어야 한다.
