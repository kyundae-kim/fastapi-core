# DocMesh runtime 경계 리팩터링 방안

## 1. 목표

`fastapi-core`를 `docmesh-py-core`의 대체 구현으로 키우지 않고, **DocMesh Py Core 기반 서비스를 FastAPI lifecycle·dependency·HTTP 운영 계약에 연결하는 얇은 조립 계층**으로 정리한다.

이번 방안은 v0.4.0 호환성 복구가 아니라, 이미 동작하는 v0.4.0 통합에서 남은 중복 정책과 늦은 검증 경계를 줄이는 후속 리팩터링이다.

핵심 원칙은 다음과 같다.

- 서비스 설정·client 생성·공통 healthcheck·close는 `docmesh-py-core`가 소유한다.
- FastAPI app factory, lifespan 순서, dependency, HTTP readiness 표현, managed resource는 `fastapi-core`가 소유한다.
- 일반 앱 경로는 `RuntimePlan` + `assemble_service_runtime()`를 유지한다.
- 서비스 없는 기본 앱은 upstream `RuntimePlan`이 빈 선택을 허용하지 않으므로 명시적 빈 `ServiceRuntime` 경로를 유지한다.
- 소비사 route가 private `app.state` 키나 `ServiceClientWrapper` 내부 구조를 알게 하지 않는다.
- 한 번에 runtime/readiness/resource를 재설계하지 않고, characterization test 이후 작은 단계로 변경한다.

## 2. 현재 기준선

조사 시점 기준:

- 의존성: `docmesh-py-core==0.4.0`
- 설치 패키지의 package-root 공개 API에 `RuntimePlan`, `assemble_service_runtime`, `ServiceRuntime`, `ServiceClientWrapper`, `diagnose_services`, health/cleanup 타입이 포함돼 있다.
- 전체 테스트: `159 passed, 1 skipped, 1 third-party warning`
- 작업 트리 기준 branch: `docmesh-py-core-v0.4.0`
- 기존 v0.4.0 호환성 계획의 1~5단계와 소비사 앱 조립 계획의 주요 소스 작업은 이미 구현돼 있다.

현재 잘 정렬된 부분:

1. `fastapi_core/runtime.py`가 `AppConfig`를 `RuntimePlan`으로 변환한다.
2. 기본 runtime은 lifespan startup에서 `assemble_service_runtime(plan=...)`로 조립된다.
3. 주입된 `ServiceRuntime`은 재조립하지 않고 동일 객체를 사용하고 닫는다.
4. `ServiceRuntime`이 DocMesh client/config/close의 유일한 소유자다.
5. `ReadinessRegistry`는 DocMesh runtime과 앱 고유 `ManagedResource`를 하나의 HTTP readiness 응답으로 합성한다.
6. 서비스 없는 `create_app()`은 외부 설정 없이 실제 lifespan에 진입한다.
7. 서비스별 dependency는 raw SDK client 또는 NATS builder 반환 계약을 유지한다.

따라서 `assemble_services()`로 되돌리거나, 별도 registry/container를 추가하거나, readiness 전체를 upstream 호출로 치환하는 큰 변경은 필요하지 않다.

## 3. 확인된 개선 지점

### 3.1 Keycloak readiness가 canonical wrapper 계약을 우회한다

`fastapi_core/runtime.py`는 Keycloak에 한해 `ServiceClientWrapper.check` 대신 wrapper의 `healthcheck` callable을 꺼내 별도 kwargs를 전달한다. 이 과정에서 `KEYCLOAK_TOKEN_USERNAME`, `KEYCLOAK_TOKEN_PASSWORD`를 다시 읽고, production 코드가 테스트 전용 이름인 `FASTAPI_CORE_TEST_SCOPE`까지 참조한다.

하지만 v0.4.0 `create_keycloak_client()`는 `KeycloakAuthService.fetch_access_token`을 wrapper healthcheck로 등록하고, `KeycloakConfig` 자체가 token username/password/scope를 환경변수에서 읽는다. 현재 코드는 다음 문제를 만든다.

- upstream config와 FastAPI adapter가 같은 credential source를 중복 소유한다.
- 앱 생성 시점에 credential 값을 closure로 캡처한다.
- 테스트 전용 scope 환경변수가 production 경계에 노출된다.
- 다른 서비스는 `client.check`, Keycloak만 private한 예외 경로를 사용한다.

### 3.2 RuntimePlan 검증이 lifespan까지 늦춰진다

`AppConfig`는 required ⊆ enabled만 검증한다. unknown service, 중복 선택, 잘못된 `one_of` 그룹 같은 오류는 `build_runtime_plan()`이 호출되는 lifespan startup까지 지연될 수 있다.

설정에서 client를 만들 필요는 없지만, 순수한 runtime plan 생성·검증은 app factory 시점에 한 번 수행할 수 있다. 이로써 구성 오류를 `create_app()` 단계에서 빠르게 발견하고 startup에서 plan을 다시 만들지 않을 수 있다.

### 3.3 Runtime readiness 등록이 concrete client 구조에 과도하게 결합한다

`configure_service_runtime()`은 `runtime.clients`를 직접 순회하고 각 값의 `.check`를 꺼낸다. v0.4.0 `ServiceRuntime`은 이미 `checks`, `get`, `require`, `get_client`라는 공개 container 표면을 제공한다.

FastAPI 쪽에서 필요한 것은 다음 두 정보뿐이다.

- 서비스별 canonical check callable
- `runtime.required_services`의 required metadata

auth provider 추출처럼 raw concrete type이 실제로 필요한 경계만 `ServiceClientWrapper.unwrap()`을 사용하고, 일반 readiness 등록은 `runtime.checks`를 소비하는 편이 역할 분리가 명확하다.

### 3.4 빈 runtime 생성이 여러 위치에 중복된다

명시적 빈 `ServiceRuntime` 생성 로직이 production runtime 경로와 `fastapi_core.testing.create_empty_runtime()`에 각각 존재한다. upstream은 빈 `RuntimePlan`을 거부하므로 이 로직 자체는 필요하지만, 생성 규칙은 한 곳에서 소유해야 한다.

### 3.5 문서 인덱스와 실제 파일이 불일치한다

`AGENTS.md`와 `README.md`는 `docs/srs.md`, `docs/api.md`, `docs/config.md`, `docs/examples.md`, `docs/test.md`를 참조하지만 현재 파일이 없다. 기존 계획 문서는 구현 전 수치 또는 완료 상태를 포함해 최신 기준선과도 일부 어긋난다.

이는 source refactor를 막지는 않지만, 공개 계약 변경을 검토할 기준 문서가 없는 상태이므로 마지막 단계에서 반드시 동기화해야 한다.

## 4. 권장 실행 순서

## 단계 0. 현재 공개 계약 characterization 고정

대상:

- `test_fastapi_core/test_public_api.py`
- `test_fastapi_core/test_factory.py`
- `test_fastapi_core/test_dependencies.py`
- `test_fastapi_core/test_health_router.py`

먼저 추가하거나 명확히 할 테스트:

1. `create_app()`의 현재 signature와 package-root export를 고정한다.
2. 자동 조립 runtime과 주입 runtime 모두 동일 runtime 객체가 readiness에 등록되고 한 번만 닫히는지 확인한다.
3. 서비스 없는 기본 앱이 config/client 자동 탐색 없이 lifespan에 진입하는지 유지한다.
4. runtime required metadata가 `AppConfig.required_services`보다 우선하는 주입 경로를 고정한다.
5. 미활성 서비스 dependency는 `503`, 잘못된 concrete client는 `500`을 유지한다.
6. required failure는 `503 error`, optional failure는 `200 degraded`를 유지한다.

완료 조건:

- 이후 단계가 바꾸지 않아야 할 API·HTTP·lifecycle 계약이 테스트로 보호된다.
- `uv run pytest -q`가 통과한다.

## 단계 1. Keycloak readiness의 중복 credential 경로 제거

대상:

- `fastapi_core/runtime.py`
- `test_fastapi_core/test_factory.py`
- 필요 시 `test_fastapi_core/integration/test_keycloak_auth_flow.py`

변경:

1. `build_keycloak_check_kwargs()`를 제거한다.
2. production 코드에서 `FASTAPI_CORE_TEST_SCOPE` 참조를 제거한다.
3. Keycloak readiness도 다른 서비스처럼 runtime이 제공하는 canonical check를 등록한다.
4. token username/password/scope fallback은 `KeycloakConfig`와 `KeycloakAuthService.fetch_access_token()`에 위임한다.
5. `configure_keycloak_provider()`의 RS256 정책은 이번 단계에서 무조건 제거하지 않는다. 이는 healthcheck 중복과 별개의 JWT 검증 정책이므로, 현재 보안 계약을 characterization test로 고정한 뒤 별도 설정화 여부를 결정한다.

테스트:

1. wrapper check가 한 번 호출되는지 확인한다.
2. FastAPI adapter가 process environment를 다시 읽거나 credential closure를 만들지 않는지 확인한다.
3. `KEYCLOAK_TOKEN_SCOPE` 등 upstream config 값이 실제 wrapper 경로에서 사용되는지 focused integration test로 검증한다.
4. readiness 오류에 username/password 원문이 노출되지 않는지 확인한다.

완료 조건:

- Keycloak을 포함한 모든 DocMesh 서비스 readiness가 runtime check 표면을 통해 등록된다.
- production source에서 `FASTAPI_CORE_TEST_SCOPE`가 사라진다.
- auth endpoint의 password grant 계약은 유지된다.

## 단계 2. RuntimePlan을 app 생성 시 한 번만 만들고 조기 검증

대상:

- `fastapi_core/config.py`
- `fastapi_core/factory.py`
- `fastapi_core/lifecycle.py`
- `fastapi_core/runtime.py`
- `test_fastapi_core/test_config.py`
- `test_fastapi_core/test_factory.py`

변경:

1. 서비스가 활성화된 경우 `create_app()`에서 순수 함수 `build_runtime_plan(app_config)`를 한 번 호출한다.
2. 생성된 plan을 내부 lifespan 조립 경로에 전달한다. startup에서 `AppConfig`를 다시 해석해 plan을 재생성하지 않는다.
3. 빈 서비스 선택은 plan을 만들지 않고 기존 빈 runtime 경로로 보낸다.
4. unknown service, duplicate service, 비어 있거나 잘못된 alternative group은 app 생성 시 명시적 validation error로 실패하게 한다.
5. `diagnose_services(plan=...)`는 여기서 자동 실행하지 않는다. diagnosis는 환경 preflight/관측 기능이며, app 생성 시 외부 서비스 설정을 요구하지 않는 기본 계약과 분리한다.

테스트:

1. unknown enabled/required service가 `TestClient` 진입 전 실패한다.
2. required ⊆ enabled 검증이 유지된다.
3. `one_of`가 선택 서비스와 모순되면 조기 실패한다.
4. valid plan이 assembly에 객체 동일성 기준으로 한 번 전달된다.
5. 주입 runtime 경로는 config plan을 근거로 runtime을 재조립하거나 선택 metadata를 덮어쓰지 않는다.
6. 빈 서비스 앱은 여전히 `RuntimePlan(services=())`를 만들지 않는다.

완료 조건:

- plan 관련 구성 오류가 client 생성 전 발견된다.
- 자동 조립 경로에 plan 해석 지점이 하나만 존재한다.
- 서비스 없는 기본 앱 계약은 유지된다.

## 단계 3. Runtime binding을 공개 container 표면 중심으로 단순화

대상:

- `fastapi_core/runtime.py`
- `fastapi_core/dependencies/services.py`
- `test_fastapi_core/test_factory.py`
- `test_fastapi_core/test_dependencies.py`

변경:

1. 일반 readiness 등록은 `runtime.checks`와 `runtime.required_services`를 기준으로 한다.
2. service key 정규화는 `Service.parse()`를 한 경계에서만 수행한다.
3. auth provider 설치처럼 concrete client가 필요한 경우에만 `runtime.get(Service.KEYCLOAK)` 및 `ServiceClientWrapper.unwrap()`을 사용한다.
4. dependency는 generic handle 접근에는 `runtime.get()`, raw SDK client 접근에는 public `unwrap()` 또는 `runtime.get_client()` 중 현재 HTTP 오류 계약을 가장 명확히 보존하는 하나의 경로를 사용한다.
5. upstream lookup exception을 그대로 HTTP에 노출하지 않고 기존 `503/500` adapter를 유지한다.

주의:

- `ReadinessRegistry`를 제거하지 않는다. DocMesh runtime 외의 `ManagedResource` check, required/optional HTTP 상태, redaction, child detail namespace를 계속 소유해야 한다.
- 서비스별 typed dependency를 모두 generic dependency로 없애지 않는다. concrete 반환 타입은 소비사 편의와 정적 타입 계약이다.

완료 조건:

- runtime client 순회·check 추출 로직이 한 곳으로 축소된다.
- readiness는 upstream container API를 소비하되 HTTP 표현 정책은 기존과 동일하다.
- malformed injected runtime에 대한 실패가 명확하고 테스트돼 있다.

## 단계 4. 빈 runtime 생성 규칙 단일화

대상:

- `fastapi_core/runtime.py`
- `fastapi_core/testing.py`
- `fastapi_core/docmesh_settings.py`
- `test_fastapi_core/test_testing.py`
- `test_fastapi_core/test_config.py`

변경:

1. 빈 `ServiceConfigs` + 빈 `ServiceRuntime`을 만드는 내부 canonical helper를 한 곳에 둔다.
2. production의 service-free startup과 `fastapi_core.testing.create_empty_runtime()`이 같은 helper를 사용한다.
3. `load_docmesh_settings()`의 production 사용처가 실제로 없다면 즉시 삭제하지 말고 공개 사용 가능성을 먼저 확인한다.
4. 유지할 경우 “선택된 DocMesh 설정 loader”로 책임을 명확히 하고, test fixture 편의 함수와 production assembly 책임을 섞지 않는다.

완료 조건:

- 빈 runtime 필드 구성이 한 구현에만 존재한다.
- testing helper가 production과 다른 빈 runtime 계약을 만들 수 없다.
- 기존 import를 깨는 삭제는 별도 breaking-change 결정 없이 수행하지 않는다.

## 단계 5. 선택적 preflight API 설계

`diagnose_services(plan=...)`는 유용하지만 기본 startup에 무조건 넣지 않는다. 실제 소비사가 배포 전 진단을 요구할 때 다음 형태로 별도 검토한다.

후보:

- app factory 옵션이 아닌 별도 CLI/preflight helper
- 입력: 이미 생성된 `RuntimePlan`
- 출력: upstream `EnvironmentDiagnosis` 또는 secret-safe DTO
- 책임: complete/partial/invalid 및 production placeholder 진단
- 비책임: client 생성, startup 대체, HTTP readiness 대체

검증:

1. secret 값이 출력·로그에 포함되지 않는다.
2. service-free mode에서는 실행하지 않거나 명시적인 no-op 결과를 제공한다.
3. diagnosis 통과가 실제 연결 성공을 의미한다고 문서화하지 않는다.

소비사 요구가 확인되지 않으면 이 단계는 구현하지 않는다.

## 단계 6. 문서 동기화

대상:

- `docs/srs.md`
- `docs/api.md`
- `docs/config.md`
- `docs/examples.md`
- `docs/test.md`
- `README.md`
- `wiki/queries/docmesh-py-core-vs-fastapi-core-usage-comparison.md`
- 기존 완료된 계획 문서의 상태·테스트 수치

문서 책임:

- `docs/prd.md`: capability와 사용자/운영 결과만 유지한다.
- `docs/srs.md`: runtime, lifecycle, readiness, injection, validation 요구사항과 acceptance criteria를 정의한다.
- `docs/api.md`: `create_app`, dependency, extension descriptor, app-owned state의 구체 계약을 정의한다.
- `docs/config.md`: `AppConfig`와 upstream 환경변수의 소유 경계를 정의한다.
- `docs/examples.md`: service-free, environment assembly, runtime injection, managed resource 예제를 제공한다.
- `docs/test.md`: unit/integration 분리, 외부 서비스 조건, canonical 검증 명령을 정의한다.
- wiki 비교 문서는 v0.2.0 기준 서술을 v0.4.0 현재 구현 기준으로 갱신한다.

완료 조건:

- README와 AGENTS가 가리키는 문서가 실제로 존재한다.
- PRD에 구체 함수명·signature·endpoint 구현 세부사항을 추가하지 않는다.
- source, test, API/SRS 문서의 계약이 일치한다.

## 5. 권장 PR 분할

### PR 1 — Keycloak readiness canonicalization

- 단계 0 characterization
- 단계 1 credential 중복 경로 제거
- 전체 suite 검증

### PR 2 — RuntimePlan 조기 검증과 단일 전달

- 단계 2 plan 생성 위치 정리
- automatic/injected/service-free parity 테스트
- 전체 suite 검증

### PR 3 — Runtime binding 단순화

- 단계 3 public container API 사용
- 단계 4 empty runtime helper 단일화
- dependency/readiness 회귀 검증

### PR 4 — 문서와 선택적 preflight

- 단계 6 문서 생성·동기화
- 실제 소비사 요구가 확인된 경우에만 단계 5 추가

각 PR은 production source와 실행 가능한 회귀 테스트를 함께 포함하고, 마지막 명령은 항상 `uv run pytest -q`로 한다.

## 6. 검증 명령

Focused 검증:

```bash
uv run pytest -q \
  test_fastapi_core/test_factory.py \
  test_fastapi_core/test_config.py \
  test_fastapi_core/test_dependencies.py \
  test_fastapi_core/test_health_router.py
```

계약 검증:

```bash
uv run pytest -q \
  test_fastapi_core/test_public_api.py \
  test_fastapi_core/test_testing.py \
  test_fastapi_core/test_settings_compatibility.py
```

최종 검증:

```bash
uv run pytest -q
uv run python -c "from importlib.metadata import version; assert version('docmesh-py-core') == '0.4.0'"
```

live service가 준비된 환경의 별도 검증:

```bash
uv run pytest -q -m integration
```

## 7. 명시적 비목표

- `ServiceRuntime`을 자체 container로 대체하지 않는다.
- `assemble_service_runtime()` 대신 서비스별 `create_*_client()` dispatch를 FastAPI 내부에 복원하지 않는다.
- `ReadinessRegistry`를 제거해 managed resource 확장성을 잃지 않는다.
- `ServiceBundle`을 async FastAPI lifecycle의 주 경로로 도입하지 않는다.
- `settings=` compatibility seam이나 여러 동급 app factory를 추가하지 않는다.
- consumer가 private `app.state` 키를 직접 사용하도록 문서화하지 않는다.
- `diagnose_services()` 결과를 실제 연결 healthcheck로 오해하지 않는다.
- RS256 정책을 healthcheck 정리와 한 번에 변경하지 않는다.
- `uv.lock`을 직접 읽거나 편집하지 않는다.

## 8. 최종 완료 기준

- Keycloak readiness가 upstream config/wrapper 계약을 우회하지 않는다.
- RuntimePlan은 자동 조립 경로에서 한 번만 생성·검증된다.
- unknown/모순 서비스 선택이 client 생성 전에 실패한다.
- runtime readiness 등록은 `ServiceRuntime`의 공개 container 표면을 사용한다.
- 빈 runtime 생성 규칙이 단일화된다.
- automatic assembly, injected runtime, service-free mode의 lifecycle/readiness/close 계약이 모두 유지된다.
- 소비사 dependency의 `503/500` HTTP 계약과 concrete 반환 타입이 유지된다.
- 누락된 SRS/API/config/examples/test 문서가 실제 구현과 동기화된다.
- 최종 `uv run pytest -q`가 통과한다.
