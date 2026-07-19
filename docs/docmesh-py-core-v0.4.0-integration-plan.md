# docmesh-py-core v0.4.0 소스 반영 방안

> 실행 상태: 1~5단계 구현 완료. 이 문서의 실패 수치는 구현 전 baseline이며,
> 현재 전체 검증은 `146 passed, 1 skipped`이며 PostgreSQL 통합 환경변수 미설정
> 1건만 명시적으로 skip된다.

## 1. 목표

`fastapi-core`가 `docmesh-py-core` v0.4.0의 공개 계약을 사용하도록 호환성을 복구하고, FastAPI 앱의 기존 공개 API와 lifecycle/readiness 동작을 유지한다.

핵심 원칙은 다음과 같다.

- 일반 애플리케이션 bootstrap은 `RuntimePlan` + `assemble_service_runtime()`를 사용한다.
- `docmesh_py_core.__all__`에 포함된 package-root API만 소비한다.
- 서비스 설정은 Python 인자나 별도 env mapping이 아니라 프로세스 환경변수에서 읽는다.
- `ServiceRuntime`이 서비스 설정, client, healthcheck, close의 유일한 소유자라는 현재 경계를 유지한다.
- FastAPI 전용 설정은 `AppConfig`, 외부 서비스 설정은 `docmesh-py-core`가 소유한다.
- `fastapi-core`의 기존 package root export, endpoint, dependency 반환 계약은 이번 업데이트에서 변경하지 않는다.

## 2. 조사 결과

### 2.1 현재 상태

- `pyproject.toml`의 Git source revision은 작업 트리에서 이미 `v0.3.0`에서 `v0.4.0`으로 변경돼 있다.
- 실제 설치된 `docmesh-py-core` 버전도 `0.4.0`이다.
- `pyproject.toml`과 `uv.lock`에는 기존 미커밋 변경이 있으므로 구현 시 이를 사용자 변경으로 보존해야 한다. `uv.lock`은 직접 편집하거나 내용 기반으로 변경하지 않는다.
- 구현 전 전체 검증 `uv run pytest -q` 결과는 `24 failed, 32 passed, 72 errors`였다. 다수 오류는 아래 keyword-only API 불일치에서 연쇄 발생한 결과이며 서로 독립적인 96개 회귀로 해석하면 안 된다.

### 2.2 즉시 확인된 호환성 차이

| 영역 | 현재 호출 | v0.4.0 계약 | 영향 |
| --- | --- | --- | --- |
| 설정 로딩 | `load_service_configs(env, services=...)` | `load_service_configs(*, services=...)` | startup과 test fixture가 `TypeError`로 실패 |
| async 조립 | `assemble_service_runtime(env, plan=...)` | `assemble_service_runtime(*, plan=..., engine_options=None)` | 서비스가 활성화된 앱 startup 실패 |
| 설정 전달 | `build_docmesh_env_overlay()`로 `os.environ` 복사 | 모든 설정 모델과 loader가 프로세스 환경변수를 직접 읽음 | 중복 추상화이며 v0.4.0 계약과 불일치 |
| 조립 테스트 대역 | fake 함수가 positional `env`를 기대 | `plan` keyword-only | factory 테스트 계약이 구 API를 고정 |
| factory override 테스트 | `factory_overrides=...`를 assembly에 전달 | v0.4.0 공개 signature에 없음 | startup rollback 테스트를 public API 기반으로 재작성해야 함 |
| 로깅 decorator | `docmesh_py_core.function_logging` 직접 import | package root `__all__`에 없는 구현 모듈 | 14개 production import가 비공개 구현에 결합 |
| PostgreSQL 설정 | `POSTGRES_DSN` 보존을 테스트 | v0.4.0은 분리된 `POSTGRES_HOST/DB/USER/PASSWORD`만 지원 | legacy DSN 테스트·문서 제거 또는 앱 계층의 명시적 변환 정책 필요 |

### 2.3 유지할 현재 경계

- `fastapi_core.runtime.build_runtime_plan()`은 `AppConfig`의 enabled/required/one-of/readiness 정책을 upstream `RuntimePlan`으로 변환하는 adapter로 유지한다.
- `fastapi_core.lifecycle.build_lifespan()`은 runtime과 managed resource의 종료 순서 및 오류 우선순위를 계속 소유한다.
- `app.state.service_runtime`만 서비스 상태로 노출하고, 폐기된 `settings`/`service_clients` 상태는 재도입하지 않는다.
- 서비스별 FastAPI dependency는 기존 raw SDK client 또는 NATS builder 반환 계약을 유지한다.
- 서비스가 하나도 없는 FastAPI 앱은 `RuntimePlan`이 빈 선택을 허용하지 않으므로, 빈 `ServiceRuntime`을 명시적으로 만드는 별도 경로를 유지한다.

## 3. 구현 단계

### 단계 1. v0.4.0 호출 호환성 복구

대상 파일:

- `fastapi_core/docmesh_settings.py`
- `fastapi_core/runtime.py`
- `test_fastapi_core/test_config.py`
- `test_fastapi_core/test_factory.py`
- `test_fastapi_core/integration/conftest.py`

변경 내용:

1. `load_docmesh_settings()`를 `load_service_configs(services=services)` 호출로 변경한다.
2. `assemble_runtime()`의 서비스 활성 경로를 `await assemble_service_runtime(plan=build_runtime_plan(config))`로 변경한다.
3. 서비스 미선택 경로는 `load_service_configs(services=set())`로 빈 `ServiceConfigs`를 만들고 `ServiceRuntime`을 명시적으로 생성한다.
4. `build_docmesh_env_overlay()`를 제거한다. v0.4.0 설정 loader가 프로세스 환경변수를 직접 읽으므로 env 사본을 전달하지 않는다.
5. fake loader/assembler의 signature와 assertion을 keyword-only 계약에 맞춘다.
6. `factory_overrides` 기반 rollback 테스트는 조립 함수를 monkeypatch하여 실패 client가 들어 있는 `ServiceRuntime`을 반환하게 바꾼다. 제거된 upstream 확장 인자를 테스트 목적으로 복원하지 않는다.
7. integration fixture의 direct factory 경로는 `load_docmesh_settings()`가 반환한 설정과 v0.4.0 `create_*_client(config)`를 그대로 사용하되, 가능하면 실제 앱 경로 검증은 `assemble_service_runtime(plan=...)`를 사용해 production bootstrap과 동일하게 만든다.

완료 조건:

- `test_fastapi_core/test_config.py`와 `test_fastapi_core/test_factory.py`에서 positional env 계약을 기대하는 테스트가 없다.
- 서비스 없는 앱과 SQLite runtime 조립 테스트가 통과한다.

### 단계 2. 비공개 upstream import 제거

대상 파일:

- 신규 `fastapi_core/function_logging.py` 또는 현재 앱 logging 모듈의 명확한 소유 위치
- `fastapi_core/**/*.py` 중 `docmesh_py_core.function_logging`을 import하는 14개 파일
- `test_fastapi_core/test_function_logging.py`
- `test_fastapi_core/test_public_api.py`

변경 내용:

1. `log_function_boundary`가 제품 요구사항이라면 동일한 관측 계약을 `fastapi-core` 내부 구현으로 소유한다. decorator가 sync/async 함수의 start/error/success 경계를 보존하는지 기존 동작을 characterization test로 먼저 고정한다.
2. 모든 production import를 로컬 decorator로 전환한다.
3. AST 테스트 이름과 assertion을 “py-core decorator 사용”이 아니라 “fastapi-core가 소유한 function-boundary decorator 사용”으로 수정한다.
4. `docmesh_py_core` import 감사 테스트를 추가한다.
   - upstream 심볼은 package root에서만 import한다.
   - import한 심볼은 `docmesh_py_core.__all__`에 포함돼야 한다.
   - `docmesh_py_core.config`, `factories`, `function_logging` 등 구현 모듈 직접 import를 금지한다.

대안:

- function-boundary logging 자체가 제품 요구사항이 아니라면 decorator와 AST 강제 테스트를 제거하는 것이 더 단순하다. 다만 현재 저장소가 모든 함수에 이를 강제하고 있으므로, 기본 방안은 로컬 소유로 이전하는 것이다.

완료 조건:

- production source에서 `docmesh_py_core.` 하위 모듈 import가 0개다.
- root public API import 감사 테스트가 통과한다.

### 단계 3. 설정 계약 정리

대상 파일:

- `fastapi_core/config.py`
- `test_fastapi_core/test_config.py`
- `.env.example`
- `README.md`
- 향후 생성할 `docs/config.md`

변경 내용:

1. `AppConfig`는 FastAPI 조립 정책만 유지한다. 서비스 connection 값은 추가하지 않는다.
2. `POSTGRES_DSN` 호환 테스트와 설명을 제거한다. v0.4.0은 `POSTGRES_HOST`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`를 요구한다.
3. 기존 배포에서 `POSTGRES_DSN`만 제공한다면 silent fallback 대신 명시적 migration error를 선택한다. 자동 변환 adapter는 secret URL parsing과 precedence 계약을 새로 소유해야 하므로 기본 방안에서 제외한다.
4. `.env.example`을 v0.4.0 변수 계약과 대조한다. 특히 다음을 반영한다.
   - `DOCMESH_SECURITY_MODE`, `DOCMESH_PRODUCTION_ALIASES`
   - Keycloak token/JWKS/provisioning 관련 변수
   - SQLite WAL/busy-timeout
   - MinIO/Milvus/Ollama/Langfuse runtime default 관련 변수
   - NATS 인증 방식 상호배타성
5. production TLS/placeholder 검증이 upstream에서 수행된다는 점과 `.env` 자동 로딩이 없다는 점을 문서화한다.

완료 조건:

- 설정 테스트가 프로세스 환경변수만 사용한다.
- source와 문서 어디에도 `POSTGRES_DSN` 지원을 현재 계약으로 표현하지 않는다.
- secret 원문을 assertion failure나 로그에 포함하지 않는다.

### 단계 4. RuntimePlan의 신규 정책 노출

대상 파일:

- `fastapi_core/config.py`
- `fastapi_core/runtime.py`
- `test_fastapi_core/test_config.py`
- `test_fastapi_core/test_factory.py`
- `README.md`
- 향후 생성할 `docs/config.md`, `docs/api.md`, `docs/examples.md`

변경 내용:

1. v0.4.0 `HealthcheckPolicy`의 다음 필드를 앱 설정에 명시적으로 노출할지 결정한다.
   - `failure_mode: fail | report`
   - `attempts: int >= 1`
   - `retry_delay_seconds: float >= 0`
2. 기본 방안은 기존 동작을 보존하도록 `fail`, `1`, `0`을 기본값으로 추가하는 것이다.
3. `build_runtime_plan()`에서 새 설정을 `StartupFailureMode`와 `HealthcheckPolicy`로 변환한다.
4. startup retry/report 동작을 async 테스트로 검증한다.
5. `diagnose_services(plan=...)`는 별도 preflight helper 또는 startup 전 진단 단계로 추가할 수 있다. 추가 시 `EnvironmentDiagnosis.to_dict()`의 secret-safe 결과만 로그에 사용하고, assembly가 수행하는 검증과 오류 의미를 중복·변형하지 않는다.

완료 조건:

- 기존 default startup 실패 동작은 동일하다.
- retry/report를 노출한다면 설정 parsing, plan mapping, lifecycle 결과 테스트가 모두 존재한다.

### 단계 5. Runtime/client 공개 계약 정렬

대상 파일:

- `fastapi_core/runtime.py`
- `fastapi_core/dependencies/services.py`
- 관련 dependency/factory/readiness 테스트

변경 내용:

1. `ServiceRuntime.clients`를 순회하는 내부 코드는 v0.4.0의 `ServiceHandle` concrete 구현(`ServiceClientWrapper`, `NatsConnectionBuilder`)만 기대하도록 타입과 오류를 정리한다.
2. wrapper의 raw client 접근은 가능하면 공개 `unwrap()`을 사용한다. NATS는 builder 자체를 반환한다.
3. Keycloak provider 연결은 `ServiceClientWrapper`를 명시적으로 확인한 뒤 unwrap하여 `KeycloakAuthService`인지 검증한다. 단순 `hasattr(client, "client")` 분기는 제거한다.
4. `runtime.get()`이 반환하는 `None`과 `runtime.require()`의 typed lookup 오류 중 FastAPI dependency에 더 적합한 경로를 선택하되, 현재 HTTP 계약인 미활성/미준비 `503`, 타입 불일치 `500`은 유지한다.
5. upstream `ServiceClientWrapperError`/`ServiceUnavailableError`가 request 경계까지 전파되는 경로가 있다면 RFC 7807 mapper에 연결할지 별도 테스트로 결정한다.

완료 조건:

- 서비스별 dependency의 기존 반환 타입과 HTTP status가 유지된다.
- Keycloak, SQLAlchemy, MinIO, Milvus, Ollama, Langfuse, NATS에 대한 타입/미활성 회귀 테스트가 통과한다.

### 단계 6. 문서 동기화

현재 저장소에는 `docs/prd.md`만 존재하지만 README는 `docs/api.md`, `docs/config.md`, `docs/examples.md`를 참조한다. 구현과 함께 누락 문서를 생성하거나 README 링크를 실제 문서 구조에 맞춰야 한다.

문서 책임은 다음처럼 분리한다.

- `docs/prd.md`: capability와 사용자/운영 결과만 유지하며 구체적인 upstream 함수 signature를 넣지 않는다.
- `docs/srs.md`: v0.4.0 runtime/config/lifecycle 요구사항과 acceptance criteria.
- `docs/api.md`: `create_app`, dependency, app state와 upstream adapter의 구체 계약.
- `docs/config.md`: `AppConfig`와 upstream 환경변수의 소유 경계, migration note.
- `docs/examples.md`: 서비스 없는 앱, RuntimePlan 기반 앱, runtime injection 예제.
- `docs/test.md`: unit/integration 분리, 필요한 외부 서비스와 skip 조건.

README의 “현재 구현 동작”은 실제 테스트 통과 후 갱신한다.

## 4. 테스트 전략

### 4.1 우선 실행

```bash
uv run pytest -q \
  test_fastapi_core/test_config.py \
  test_fastapi_core/test_factory.py \
  test_fastapi_core/test_dependencies.py \
  test_fastapi_core/test_health_router.py
```

### 4.2 계약 회귀

```bash
uv run pytest -q \
  test_fastapi_core/test_public_api.py \
  test_fastapi_core/test_settings_compatibility.py \
  test_fastapi_core/test_function_logging.py
```

### 4.3 전체 unit suite

외부 서비스의 가용성과 무관한 기본 검증을 별도로 실행할 수 있도록 integration marker를 제외한다.

```bash
uv run pytest -q -m "not integration"
```

### 4.4 integration suite

필요한 환경변수와 서비스가 준비된 환경에서 실행한다.

```bash
uv run pytest -q -m integration
```

Keycloak, NATS, PostgreSQL, SQLite, MinIO, Milvus의 live 경로를 검증하고, Ollama/Langfuse가 현재 integration matrix에 없다면 추가 여부를 명시적으로 결정한다.

### 4.5 최종 검증

```bash
uv run pytest -q
uv run python -c "from importlib.metadata import version; assert version('docmesh-py-core') == '0.4.0'"
```

## 5. 권장 PR 분할

1. **PR 1 — v0.4.0 호환성 복구**
   - keyword-only loader/assembler 반영
   - env overlay 제거
   - fixture/fake/rollback 테스트 갱신
   - 기존 테스트 green 복구
2. **PR 2 — 공개 API 경계 정리**
   - 비공개 `function_logging` 의존 제거
   - root import 감사 테스트
   - wrapper/runtime typed access 정리
3. **PR 3 — 신규 정책과 문서**
   - retry/report 및 diagnosis 채택 여부 반영
   - 환경변수 migration과 누락 문서 작성
   - integration matrix 보강

PR 1에서는 기존 동작 복구 외의 기능 추가를 피한다. 신규 v0.4.0 기능은 green baseline 이후 별도 PR에서 도입해야 원인 분리와 rollback이 쉽다.

## 6. 위험과 대응

| 위험 | 대응 |
| --- | --- |
| 현재 pyproject/lock 변경을 덮어씀 | 기존 변경을 보존하고 `uv.lock`을 직접 편집하지 않음 |
| 모든 실패를 개별 회귀로 오판 | 먼저 keyword-only 호출 오류를 수정한 뒤 suite를 재실행해 잔여 실패를 재분류 |
| 제거된 `factory_overrides`를 앱 내부 API로 복원 | prebuilt runtime 또는 조립 함수 monkeypatch로 테스트 |
| upstream 내부 decorator에 계속 결합 | 로컬 소유 또는 기능 제거 후 root-only import 감사 테스트 추가 |
| `POSTGRES_DSN`을 조용히 무시 | migration error 또는 배포 설정 전환을 명시하고 silent fallback 금지 |
| `diagnose_services()`와 assembly 오류가 중복 | diagnosis는 preflight/관측 용도로만 사용하고 canonical 검증은 upstream assembly에 위임 |
| integration 테스트가 로컬 서비스 상태에 따라 흔들림 | unit와 integration 명령을 분리하고 명시적인 env/reachability skip 유지 |

## 7. 최종 완료 기준

- 설치된 `docmesh-py-core`가 v0.4.0이다.
- production source가 `docmesh_py_core.__all__` 공개 API만 import한다.
- loader/assembler 호출에 env positional argument가 없다.
- 서비스 없는 앱, 기본 runtime 조립, runtime injection, startup healthcheck, rollback, shutdown aggregation이 통과한다.
- dependency와 HTTP/public export 계약이 기존과 동일하다.
- `uv run pytest -q -m "not integration"`가 통과한다.
- 준비된 live 환경에서 `uv run pytest -q -m integration`이 통과하거나, 환경 미제공 서비스는 명시적 사유로 skip된다.
- README 및 실제 존재하는 docs가 v0.4.0 설정·runtime 계약과 일치한다.
