# 코드 크기 축소 중심 리팩토링 방안

## 1. 목적

현재 동작과 핵심 공개 API를 가능한 한 유지하면서 `fastapi-core`의 구현 및 테스트 코드를 줄인다. 단순히 코드를 다른 파일로 이동하거나 과도한 helper를 추가해 파일별 줄 수만 줄이는 방식은 제외한다.

## 2. 현재 기준선

`pygount` 기준 Python code LOC:

| 구분 | 파일 수 | Code LOC |
|---|---:|---:|
| `fastapi_core/` | 18 | 1,127 |
| `test_fastapi_core/` | 14 | 1,617 |
| 합계 | 32 | 2,744 |

프로덕션 코드 상위 모듈:

| 모듈 | Code LOC | 관찰 |
|---|---:|---|
| `fastapi_core/factory.py` | 246 | 서비스 조립, readiness 연결, lifecycle, 앱 초기화가 집중됨 |
| `fastapi_core/extensions.py` | 198 | typed readiness와 managed resource lifecycle을 관리함 |
| `fastapi_core/routers/health.py` | 100 | typed registry 결과를 HTTP 응답으로 변환함 |
| `fastapi_core/http.py` | 128 | HTTP 오류 정규화와 correlation ID 처리 |
| `fastapi_core/config.py` | 114 | 환경변수 alias/파싱/검증 |

테스트 코드 상위 모듈:

| 모듈 | Code LOC |
|---|---:|
| `test_fastapi_core/test_factory.py` | 342 |
| `test_fastapi_core/test_dependencies.py` | 174 |
| `test_fastapi_core/test_extensions.py` | 168 |
| `test_fastapi_core/test_config.py` | 131 |
| `test_fastapi_core/test_health_router.py` | 120 |

현재 기준 동작은 `uv run pytest -q` 실행에서 `101 passed`다.

## 3. 남은 핵심 판단

가장 큰 남은 축소 지점은 `docmesh_py_core`와 `fastapi_core`가 각각 보유한 서비스 클라이언트 조립 분기다.

테스트에서는 동일한 앱 생성, provider 실패, readiness 상태 조립을 테스트마다 반복하는 부분을 검토하되, 이미 공통 fixture로 추상화한 계약을 다시 일반화하지 않는다.

## 4. 권장 리팩토링

### P3. 서비스 runtime 조립을 `docmesh_py_core`에 위임

**근거**
- `fastapi_core/factory.py:80-106`의 `_build_service_clients()`는 서비스 이름별 create 함수 분기를 직접 보유한다.
- 설치된 `docmesh_py_core`의 `assemble_services()`도 동일한 서비스별 create 분기를 보유한다.
- 기본 경로는 이미 `fastapi_core/factory.py:224-236`에서 `assemble_service_runtime(...)`에 위임한다.
- 중복은 명시적 `settings` 주입 경로(`factory.py:157-172`)를 지원하기 위해 남아 있다.

**권장 방안**
- `docmesh_py_core`에 설정 객체를 입력받는 공개 조립 API를 먼저 추가한다. 예: `assemble_service_runtime_from_configs(configs, *, services, required, one_of, ...)`.
- `fastapi_core`는 기본 환경변수 경로와 명시적 settings 경로 모두 upstream 조립 API만 호출한다.
- upstream API가 준비되면 다음을 삭제한다.
  - 서비스별 `create_*_client` import
  - `_build_service_clients()`
  - `_build_injected_service_runtime()`의 직접 validation/runtime 생성

**예상 절감**
- 이 저장소 프로덕션: 약 35~50 LOC
- 테스트: 약 20~35 LOC

**위험**
- 현재 설치된 `docmesh_py_core` 공개 API에는 설정 객체 기반 runtime 조립 함수가 없다.
- upstream 변경 없이 로컬 registry/dict로 if/elif만 치환하면 줄 수 감소는 작고, 특수 처리(Keycloak, Langfuse, NATS)가 숨겨져 오히려 읽기 어려워질 수 있다.
- 따라서 upstream 지원 전에는 현재 분기를 유지하는 편이 낫다.

**검증**
- 환경 기반 조립과 settings 주입 조립에서 동일한 `selected_services`, `required_services`, client 타입, startup check, rollback, shutdown 결과를 검증한다.

---

### P5. 작은 축소는 동작 경계를 유지하는 범위에서만 수행

#### 유지 권장

- `fastapi_core/dependencies/services.py`의 typed getter들은 반복처럼 보이지만 IDE/type checker와 문서화된 공개 API를 제공한다. 동적 함수 생성으로 줄이지 않는다.
- `ManagedResource`의 sync/async 호출 및 역순 종료 로직은 오류·rollback 의미가 다르므로 무리하게 하나의 generic invoke helper로 합치지 않는다.
- `create_app()`의 state 초기화를 dataclass/builder로 옮기는 것은 총 LOC를 줄이지 못하고 간접 호출만 늘릴 가능성이 높다.
- 한 줄 comprehension, 중첩 lambda, 동적 registry로 물리적 줄 수만 줄이지 않는다.

#### 선택적 후보

- `dependencies/auth.py:15-37`의 role 중복 제거는 순서 보존 helper로 5~8 LOC 줄일 수 있으나 현재 코드가 더 명시적이므로 우선순위가 낮다.
- `dependencies/services.py:73-105`의 wrapped client getter 공통화는 공개 return type을 유지하면서 8~12 LOC 줄일 수 있을 때만 적용한다.
- JSON logging formatter를 `docmesh_py_core`의 공통 기능으로 올릴 수 있다면 `factory.py:48-77` 일부를 위임할 수 있으나, 한 저장소에서 다른 저장소로 코드를 이동하는 것만으로는 전체 시스템 크기 축소가 아니다.

## 5. 권장 실행 순서

1. **P3 upstream runtime API 추가**: `docmesh_py_core` 변경과 릴리스를 먼저 완료한다.
2. `fastapi_core`에서 로컬 service factory 분기를 제거한다.
3. **P5 작은 축소**를 적용하되, 각 변경이 실제 순감소인지 diff로 확인한다.

## 6. 목표치

현재 기준선에서 현실적인 다음 목표:

| 구분 | 현재 | 목표 | 예상 감소 |
|---|---:|---:|---:|
| 프로덕션 Code LOC | 1,127 | 1,077~1,092 | 35~50 (3.1~4.4%) |
| 테스트 Code LOC | 1,617 | 1,582~1,597 | 20~35 (1.2~2.2%) |
| 합계 | 2,744 | 2,659~2,689 | 55~85 (2.0~3.1%) |

## 7. 완료 조건

- `uv run pytest -q` 전체 통과
- 공개 import/API 및 OpenAPI endpoint 계약 유지
- readiness 상태/HTTP status/error redaction/lifecycle rollback 회귀 없음
- `pygount` 기준 Code LOC가 단계별로 순감소
- 새 helper/fixture의 LOC를 포함한 **저장소 전체 순감소** 확인
- upstream 위임 시 `docmesh_py_core` 최소 지원 버전 또는 git revision 갱신
