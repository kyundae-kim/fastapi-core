---
title: docmesh-config consumer implementation minimization
created: 2026-08-02
updated: 2026-08-02
type: query
tags: [query, comparison, config, contract, architecture, integration, implementation, refactor, decision]
sources:
  - raw/articles/docmesh-config-api-reference-v0.1.0.md
  - raw/articles/docmesh-config-configuration-v0.1.0.md
  - raw/articles/docmesh-config-examples-v0.1.0.md
  - raw/articles/docmesh-config-env-example-v0.1.0.md
  - raw/articles/docmesh-py-core-api-reference-v0.6.0.md
  - raw/articles/docmesh-py-core-configuration-guide-v0.6.0.md
  - fastapi_core/config.py
  - fastapi_core/docmesh_settings.py
  - fastapi_core/runtime.py
  - fastapi_core/factory.py
  - fastapi_core/testing.py
  - test_fastapi_core/test_config.py
  - test_fastapi_core/test_next_requirements.py
  - .venv/lib/python3.11/site-packages/docmesh_config/settings.py
  - .venv/lib/python3.11/site-packages/docmesh_config/config_loading.py
  - .venv/lib/python3.11/site-packages/docmesh_config/config_diagnostics.py
  - .venv/lib/python3.11/site-packages/docmesh_config/runtime_plan.py
  - .venv/lib/python3.11/site-packages/docmesh_config/plan_metadata.py
  - .venv/lib/python3.11/site-packages/docmesh_config/config_errors.py
confidence: medium
---

# docmesh-config consumer implementation minimization

## Question

`docmesh-config` 소비자가 환경변수 파싱·서비스 선택·plan 생성·preflight·설정 접근·문서 생성을 반복하지 않도록 하려면, 다음 버전에서 어떤 framework-neutral 계약을 우선 제공해야 하는가?

## Evidence baseline

- 현재 설치 버전은 `docmesh-config` v0.1.0이며 package root 공개 심볼은 36개다. 핵심 공개 API는 `load_service_configs()`, `load_available_service_configs()`, `diagnose_services()`, `validate_service_requirements()`, `RuntimePlan`, `build_runtime_plan_metadata()`, `ServiceConfigs`, `ConfigError`, `ConfigIssue`다.^[raw/articles/docmesh-config-api-reference-v0.1.0.md]
- 설정 모델은 의도적으로 process environment만 읽고 생성자 값은 거부한다. `DocmeshBaseSettings.__init__()`는 값이 전달되면 `TypeError`를 발생시키며, `has_environment_values()`·진단·loader도 전역 `os.environ`을 기준으로 동작한다.^[raw/articles/docmesh-config-api-reference-v0.1.0.md]
- fastapi-core는 `AppConfig`에서 `enabled_services`, `required_services`, `service_alternatives`, readiness/startup policy를 다시 파싱하고, `fastapi_core/runtime.py:build_runtime_plan()`에서 `Service.parse()`·required/optional selection·`HealthcheckPolicy`를 다시 조립한다. `docmesh_settings.py`는 선택 서비스 tuple을 키로 한 별도 `lru_cache`를 둔다.
- 검증 baseline은 `.venv/bin/pytest -q` → `218 passed, 1 skipped, 1 warning`이다. 이 query는 consumer 소스와 설치된 v0.1.0 live package를 직접 대조한 결과다.

## Alignment classification

| 분류 | 현재 상태 | 소비자 구현량 관점의 의미 |
| --- | --- | --- |
| implemented/aligned | typed service settings, selective loading, secret-safe dump, production security validation, `RuntimePlan` validation, structured diagnosis | 기본 설정 안전성은 이미 충분하므로 소비자가 별도 parser/secret masker를 만들 필요가 없다. |
| partially implemented | `RuntimePlanMetadata`는 diagnosis를 포함하지만 loaded `ServiceConfigs`와 하나의 snapshot으로 묶이지 않으며, catalog metadata는 주로 py-core에 있다. | preflight와 assembly 사이에서 동일 환경을 다시 읽고 plan/config 변환을 반복하게 된다. |
| missing | one-pass runtime configuration snapshot, generic `ServiceConfigs.get/require`, public field-level configuration catalog, explicit environment source | consumer가 service별 getter·환경 patch·문서/`.env` 추적표를 직접 유지한다. |
| divergent | fastapi-core는 `DOCMESH_HEALTHCHECK_ENABLED`와 plan 관련 환경변수를 자체 제공하지만 docmesh-config v0.1.0 문서는 `RuntimePlan.healthcheck`를 programmatic metadata로 정의하고 해당 환경변수를 canonical API로 약속하지 않는다. | package별 source of truth가 갈라져 consumer adapter와 테스트가 호환 규칙을 소유한다. |

## Current duplication points

1. `config_loading.load_service_configs()`는 설정을 로드하고, `config_diagnostics.diagnose_services()`는 선택 서비스마다 다시 설정 모델을 로드한다. `build_runtime_plan_metadata()`도 다시 `diagnose_services()`를 호출한다. preflight 결과와 실제 assembly가 같은 immutable environment snapshot을 공유하지 않는다.^[raw/articles/docmesh-config-api-reference-v0.1.0.md]
2. `ServiceConfigs`는 내부 `_require()`를 가지고도 `require_keycloak()`부터 `require_nats()`까지 8개 명시 메서드를 반복한다. consumer는 여기에 다시 `getattr(configs, service)`와 optional/required 분기를 작성한다.
3. `RuntimePlan`은 문자열 정규화·중복·대안 그룹을 검증하지만, 문자열 service 목록을 `ServiceSelection`으로 만드는 편의 builder가 없다. fastapi-core가 `build_runtime_plan()`을 별도로 구현하는 직접적인 원인이다.
4. `EnvironmentDiagnosis`는 `ok`와 `to_dict()`를 제공하지만 consumer는 `if not diagnosis.ok: raise ValueError(...)`와 error rendering을 직접 작성한다. `ConfigError`로 올리는 표준 `require_ok()` 경계가 없다.
5. 설정 field의 env key·default·secret·conditional-required·production constraint가 Pydantic model과 문서에 흩어져 있다. `docmesh-py-core`의 `SERVICE_CATALOG`/generated reference가 일부 metadata를 제공하지만 config package의 canonical source와 분리되어 drift 가능성이 있다.^[raw/articles/docmesh-py-core-api-reference-v0.6.0.md]
6. global `os.environ`만 지원하므로 multi-app test나 isolated configuration에는 `test_environment()`와 `load_app_config.cache_clear()`/`load_docmesh_settings.cache_clear()`가 필요하다. 이것은 production 기능보다 테스트·embedding consumer의 boilerplate를 늘린다.

## Prioritized improvements

### P0 — one-pass `RuntimeConfiguration` snapshot

`docmesh-config`에 plan, loaded settings, diagnosis, metadata를 함께 보유하는 immutable snapshot을 추가한다. 개념적 API는 다음과 같다.

```text
configuration = load_runtime_configuration(
    plan=plan,
    selection_mode="auto",
    source=EnvironmentSource.process(),
)
configuration.configs
configuration.diagnosis
configuration.metadata
configuration.require_ok()
```

예시 타입은 `RuntimeConfiguration(plan, configs, diagnosis, metadata)`다. loader는 한 번 읽은 environment source로 설정을 구성하고, 동일한 결과를 diagnosis·requirements·security validation·metadata에 재사용해야 한다. `docmesh-py-core.assemble_service_runtime()`에는 이 snapshot 또는 `configs`를 선택적으로 전달할 수 있는 additive seam을 둔다. core가 config package를 다시 import하는 새 순환이 생기지 않도록 snapshot은 docmesh-config가 소유하고 core는 protocol/공개 타입만 소비한다.

이 API는 fastapi-core의 auth preflight와 runtime assembly 사이의 재진단, 별도 `load_docmesh_settings()` cache, `RuntimePlanMetadata`와 config bundle의 분리를 줄인다. 환경이 startup 중 변해도 diagnosis와 assembly가 서로 다른 값을 보는 문제도 없어진다.^[raw/articles/docmesh-config-api-reference-v0.1.0.md]^[raw/articles/docmesh-config-examples-v0.1.0.md]

**수용 기준**

- process environment default는 유지하고, 한 snapshot 안의 `configs`, `diagnosis`, `metadata`는 동일 source를 사용한다.
- required service, one-of, MinIO bucket, production security 오류가 하나의 secret-safe `ConfigError` 계약으로 반환된다.
- snapshot은 설정 원문을 repr/log에 노출하지 않으며 생성 후 변경할 수 없다.
- 기존 `load_service_configs()`와 `diagnose_services()`는 호환성을 위해 유지하고 snapshot API로 내부 구현을 수렴한다.

### P0 — 문자열 service selection builder 제공

`RuntimePlan.from_service_names()` 또는 `RuntimePlanBuilder`를 추가해 consumer가 반복하는 `Service.parse()`, required/optional 분기, `one_of` 변환을 canonical API로 이동한다.

```text
plan = RuntimePlan.from_service_names(
    enabled=("keycloak", "sqlite"),
    required=("keycloak",),
    one_of=(("postgres", "sqlite"),),
    healthcheck=policy,
)
```

이 builder는 FastAPI를 몰라야 하며, 현재 `RuntimePlan`의 immutable validation을 그대로 사용해야 한다. 환경변수 자체를 자동으로 읽는 API를 기본값으로 만들기보다는 명시적인 입력을 받는 builder를 우선한다. 환경 기반 plan이 제품 요구사항이면 별도의 `RuntimeSelectionConfig`를 두어 service settings와 plan selection을 구분한다.

이 개선으로 `fastapi_core/runtime.py:build_runtime_plan()`은 thin adapter가 되며, `AppConfig`가 가진 FastAPI 전용 설정과 DocMesh plan 설정의 경계도 명확해진다.^[raw/articles/docmesh-config-api-reference-v0.1.0.md]

### P0 — `ServiceConfigs`에 generic access contract 추가

기존 typed `require_sqlite()` 등은 호환용으로 유지하되 다음 generic API를 공개한다.

```text
configs.get(Service.SQLITE) -> SqliteConfig | None
configs.require(Service.SQLITE) -> DocmeshBaseSettings
configs.loaded_services -> frozenset[Service]
configs.items() -> iterable[(Service, DocmeshBaseSettings)]
```

`Service.parse()`를 내부에서 적용하고, 미로드 서비스에는 현재 `service_not_loaded` issue와 동일한 `ConfigError`를 반환한다. 가능한 경우 `@overload`로 known service의 반환 타입을 보조하지만, FastAPI나 특정 SDK 타입을 config package에 넣지 않는다. 이 계약은 consumer의 `getattr`, 8개 wrapper, loaded/absent 분기를 한곳으로 모은다.^[raw/articles/docmesh-config-api-reference-v0.1.0.md]

### P0 — config-owned field catalog와 plan-scoped 문서 생성

`SERVICE_CONFIG_TYPES`만 제공하는 현재 registry를 `EnvironmentRequirement` metadata까지 포함하는 immutable `CONFIG_CATALOG`로 확장한다. 각 requirement는 canonical env key, type, default, secret 여부, required 조건, production constraint, compatibility/deprecation 정보를 표현한다.

```text
CONFIG_CATALOG[Service.MINIO].environment_variables()
generate_environment_template(plan=plan)
generate_configuration_reference(plan=plan)
```

설정 package가 98개 canonical environment variable의 source of truth가 되고, py-core의 `SERVICE_CATALOG`는 factory/runtime metadata를 이 catalog에 연결한다. consumer `.env.example`, configuration reference, deployment validation은 catalog에서 생성하거나 검증할 수 있어 수동 추적표가 줄어든다. generated output은 secret 원문과 executable object를 포함하지 않아야 한다.^[raw/articles/docmesh-config-configuration-v0.1.0.md]^[raw/articles/docmesh-config-env-example-v0.1.0.md]^[raw/articles/docmesh-py-core-api-reference-v0.6.0.md]

### P1 — explicit `EnvironmentSource` 지원

process environment-only 기본 동작은 유지하면서, loader와 diagnosis에 명시적인 source를 주입할 수 있게 한다.

```text
source = EnvironmentSource.from_mapping(test_values)
load_service_configs(services={Service.SQLITE}, source=source)
diagnose_services(plan=plan, source=source)
```

settings constructor에 임의 kwargs를 허용하는 방식은 피하고, 읽기 전용 mapping을 감싼 `EnvironmentSource`/`EnvironmentSnapshot`을 별도 타입으로 둔다. source는 복사·정규화되며 secret-safe serialization을 제공해야 한다. 이 방식은 `os.environ` mutation, 전역 cache clear, nested `test_environment()` 없이 단위 테스트와 여러 app instance를 격리한다.

### P1 — diagnosis의 표준 실패 경계

`EnvironmentDiagnosis.require_ok()` 또는 `raise_for_issues()`를 제공해 다음 패턴을 없앤다.

```text
if not diagnosis.ok:
    raise ValueError(f"...{diagnosis.to_dict()}")
```

메서드는 기존 `ConfigError(issues=diagnosis.issues)`를 발생시키고 `service`, `reason_code`, `env_keys`, remediation을 보존해야 한다. HTTP status나 FastAPI exception은 추가하지 않는다. `warnings`와 `issues`의 우선순위도 명시해 consumer가 `ok`를 임의로 재정의하지 않게 한다.^[raw/articles/docmesh-config-api-reference-v0.1.0.md]

### P1 — plan-aware validation으로 요구사항 API 통합

현재 `validate_service_requirements(configs, required=..., one_of=...)`, `require_minio_bucket()`, `diagnose_services(plan=...)`가 동일한 요구사항을 서로 다른 입력 형태로 받는다. `validate_runtime_configuration(configs, plan=plan)` 또는 snapshot 내부 `require_ok()`가 required/one-of/bucket/security validation을 한 번에 수행하도록 한다.

`RuntimePlan`을 canonical 입력으로 사용하면 consumer가 `required`, `one_of`, `minio_bucket_required`를 별도로 변환하거나 같은 조건을 두 번 선언하지 않아도 된다. 기존 함수는 deprecated adapter로 남기고, `RuntimePlan`과 `ServiceConfigs`가 서로 다른 source of truth가 되지 않게 한다.^[raw/articles/docmesh-config-api-reference-v0.1.0.md]^[raw/articles/docmesh-config-examples-v0.1.0.md]

### P2 — immutable configuration and explicit cache scope

`ServiceConfigs`와 settings snapshot의 mutation 가능성을 줄이고, cache가 필요하면 process-global `lru_cache` 대신 source/plan fingerprint를 포함한 명시적 cache scope를 제공한다. 기본 loader는 cache하지 않고, application이 snapshot lifetime을 소유하는 편이 안전하다. 이는 현재 `load_docmesh_settings.cache_clear()`와 test helper에 의존하는 consumer 코드를 단순화한다.

## Boundary decisions

- `docmesh-config`는 environment source, typed settings, plan selection, diagnosis, config metadata를 소유한다.
- `docmesh-py-core`는 config snapshot을 받아 client factory/runtime/health를 소유한다. SDK kwargs나 FastAPI 객체를 config package에 넣지 않는다.
- CORS, token URL, OAuth2, logging transport, APIRouter는 fastapi-core 책임이다. 다만 `DOCMESH_SERVICES`, required services, startup health policy처럼 DocMesh plan에 속한 값은 consumer별 재정의 대신 docmesh-config의 canonical builder/source를 사용해야 한다.
- `.env` 자동 로딩을 추가하지 않는다. process environment default와 explicit source injection을 분리한다.

## Recommended rollout

1. **다음 additive release:** `RuntimePlan.from_service_names()`, `ServiceConfigs.get/require/loaded_services`, `EnvironmentDiagnosis.require_ok()`.
2. **다음 단계:** `EnvironmentSource`와 one-pass `RuntimeConfiguration` snapshot을 추가하고 py-core assembly가 선택적으로 소비하도록 한다.
3. **그 다음 단계:** config-owned `CONFIG_CATALOG`와 plan-scoped template/reference generation을 도입하고 py-core catalog와 중복 metadata를 연결한다.
4. fastapi-core의 `build_runtime_plan()`, `load_docmesh_settings()` cache, auth preflight 중복, `test_environment()` 의존을 단계적으로 deprecated한다.

## Verdict

소비자 구현 소스를 가장 크게 줄이는 docmesh-config 개선은 **one-pass runtime configuration snapshot**, **문자열 service selection builder**, **generic ServiceConfigs access**, **config-owned environment catalog**이다. 이 네 가지가 있으면 consumer는 환경변수 이름·plan validation·서비스별 getter·preflight 결과·`.env` 문서의 source of truth를 직접 유지하지 않아도 된다.

다만 설정 package의 process-environment 기본 원칙과 FastAPI 경계를 깨지 않는 것이 중요하다. `docmesh-config`에 FastAPI adapter를 넣기보다 명시적 environment source와 immutable snapshot을 제공하는 편이 [[docmesh-config]], [[service-configuration-contracts]], [[application-integration-patterns]]의 현재 경계를 보존하면서 구현량을 줄인다. Py Core 측 lifecycle 개선과의 연결은 [[docmesh-py-core-consumer-implementation-minimization]]을 함께 참고한다.
