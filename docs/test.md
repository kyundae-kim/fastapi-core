# fastapi-core 테스트 정의서

> 문서 목적: `fastapi-core`의 **현재 구현된 FastAPI 앱 계층**을 어떤 수준으로 검증하는지 정리한다.
> 기준 문서: `docs/prd.md`, `docs/srs.md`, `docs/api.md`, `docs/config.md`
> 문서 상태: 구현 반영본(v0.3)

---

## 1. 문서 개요

이 문서는 계획 단계의 이상적인 테스트 목록이 아니라, 현재 저장소에 존재하는 테스트와 검증 범위를 기준으로 정리한다.
핵심 대상은 다음과 같다.

- `create_app(...)`
- auth router (`/token`, `/user`)
- health router (`/health/liveness`, `/health/readiness`)
- dependency (`get_current_user`, `require_permissions`)
- schema (`TokenResponse`, `UserInfo`, `HealthResponse`)
- custom lifespan 연계

- 작성일: `2026-06-25`
- 작성자: `Hermes Agent`
- 버전: `v0.3`
- 상태: `implemented-surface`

---

## 2. 현재 테스트 인벤토리

실제 테스트 파일:

```text
test_fastapi_core/
  conftest.py
  test_factory.py
  test_auth_router.py
  test_health_router.py
  test_dependencies.py
  test_schemas.py
```

현재는 다음 파일이 **없다**:
- `test_lifespan.py`
- `test_config.py`
- `test_messaging_integration.py`

즉, 문서는 없는 테스트를 이미 갖춘 것처럼 서술하면 안 된다.

---

## 3. 테스트 실행 기준

현재 저장소 검증 명령:

```bash
uv run pytest -q
```

최근 실제 실행 결과:
- `12 passed`

테스트 러너/환경 특성:
- `pytest` 사용
- FastAPI endpoint 검증은 `fastapi.testclient.TestClient` 사용
- 현재 테스트 파일들은 모두 동기 테스트 함수(`def`) 기반
- 비동기 테스트는 아직 없음
- import 안정화를 위해 `test_fastapi_core/conftest.py`에서 저장소 루트를 `sys.path`에 추가함

---

## 4. 공통 테스트 fixture

정의 위치: `test_fastapi_core/conftest.py`

### 4.1 `build_test_settings()`

`docmesh_py_core.load_settings(...)`를 직접 호출해 테스트용 `Settings`를 구성한다.

포함되는 최소 설정 범위:
- Keycloak
- SQLite
- MinIO
- Milvus
- Ollama
- Langfuse
- NATS

의미:
- 현재 구현에서 `Settings` 생성이 성립하도록 필수 환경값 세트를 코드로 고정한 것
- 테스트는 mock이 아니라 **실제 설정 모델 생성 경로**를 통과한다.

### 4.2 `settings` fixture

각 테스트에서 `create_app(settings=settings)` 형태로 주입된다.

---

## 5. 실제 검증 범위

## 5.1 app factory 테스트

정의 위치: `test_fastapi_core/test_factory.py`

현재 검증하는 항목:
- `create_app()`이 liveness route를 포함한다.
- auth route(`/token`, `/user`)가 기본 포함된다.
- `app.state.settings`에 전달한 settings가 저장된다.
- `include_auth_router=False`일 때 `/token`, `/user`가 404다.
- custom lifespan startup/shutdown이 호출된다.

현재 검증하지 않는 항목:
- CORS middleware 세부 동작
- `root_path` 값 반영
- `app.state.config` 저장 여부
- `readiness_parallel` 상태 저장 여부

## 5.2 auth router 테스트

정의 위치: `test_fastapi_core/test_auth_router.py`

현재 검증하는 항목:
- `/token`이 `TokenResponse` 구조를 반환한다.
- `/user`가 `UserInfo` 구조를 반환한다.
- fake auth provider를 `app.state.auth_provider`로 주입해 동작을 대체할 수 있다.
- `/token` 요청의 `scope`가 provider로 전달된다.
- `/user`는 bearer token 기반 사용자 변환 결과를 반환한다.

현재 검증하지 않는 항목:
- provider 예외 시 `/token`의 401 경로
- `/user`에서 invalid token 예외 매핑
- 실제 Keycloak 연동

## 5.3 health router 테스트

정의 위치: `test_fastapi_core/test_health_router.py`

현재 검증하는 항목:
- readiness check가 성공하면 200
- 필수 readiness check가 실패하면 503
- 성공 시 `details`에 서비스별 상태 구조가 들어간다.
- 실패 시 `status == "error"`

현재 검증하지 않는 항목:
- `/health/liveness` 단독 파일 수준 재검증(간접적으로 factory 테스트에서 검증)
- `READINESS_PARALLEL` 플래그 전달 효과
- timeout/네트워크 오류의 세부 분기
- 선택 서비스(degraded) 정책

## 5.4 dependency 테스트

정의 위치: `test_fastapi_core/test_dependencies.py`

현재 검증하는 항목:
- `get_current_user()`의 token 없음 경로 → 401
- `WWW-Authenticate: Bearer` 헤더 검증
- `require_permissions("admin")`의 role 부족 경로 → 403

현재 검증하지 않는 항목:
- `get_config()` 직접 테스트
- `get_settings()` 직접 테스트
- `get_auth_provider()` 캐시/재사용 테스트
- invalid token 예외 매핑

## 5.5 schema 테스트

정의 위치: `test_fastapi_core/test_schemas.py`

현재 검증하는 항목:
- `TokenResponse.token_type == "bearer"`
- `TokenResponse.refresh_token is None`
- `UserInfo.roles/scopes` 기본값이 빈 리스트
- `HealthResponse(status="ok")` 생성 가능
- `HealthResponse.details is None`

---

## 6. 현재 테스트 설계 원칙

### 6.1 실제 구현 우선

문서 계획이 아니라 현재 구현된 계약을 검증한다.
예를 들어:
- readiness는 자동 Keycloak/NATS 등록이 아니라 `app.state.readiness_checks` 주입을 기준으로 검증한다.
- auth는 실제 Keycloak 서버 대신 fake provider 주입으로 계약을 고정한다.

### 6.2 좁고 빠른 회귀 우선

현재 테스트는 대부분 다음 계층의 계약 검증에 집중한다.
- response status
- response body shape
- route 포함/제외
- dependency failure branch
- lifespan 호출 여부

### 6.3 실제 설정 모델 경로 사용

테스트는 단순 dict mock 대신 `load_settings(...)`를 통해 `Settings`를 만든다.
따라서 설정 유효성 제약이 테스트에도 반영된다.

---

## 7. 현재 구현 기준의 테스트 갭

문서와 비교했을 때 아직 없는 검증:

1. `get_config()` / `get_settings()` 직접 테스트
2. `AppConfig` 로딩(`ROOT_PATH`, `CORS_ORIGINS`, `READINESS_PARALLEL`) 테스트
3. `/token` 실패 경로 테스트
4. invalid token → 401 매핑 테스트
5. `get_auth_provider()` 재사용/생성 분기 테스트
6. CORS middleware 동작 테스트
7. 실제 외부 연동(Keycloak/NATS) integration test
8. 비동기 테스트 함수 기반 검증
9. 메시징 startup/shutdown 연동 테스트
10. `root_path` 반영 테스트

이 항목들은 향후 추가 대상이지, 현재 완료된 테스트 범위는 아니다.

---

## 8. 권장 추가 테스트 우선순위

현재 구현을 기준으로 다음 순서를 권장한다.

### 우선순위 1
- `test_config.py` 추가
  - `load_app_config()` 환경변수 파싱
  - `cors_origins` 분리
  - `readiness_parallel` bool 파싱

### 우선순위 2
- dependency 직접 테스트 보강
  - `get_auth_provider()` state 재사용
  - invalid token 예외 매핑

### 우선순위 3
- router 실패 경로 보강
  - `/token` provider failure → 401
  - readiness optional/required 서비스 분기

### 우선순위 4
- 통합/외부 연동 테스트 분리
  - 실제 Keycloak 또는 준실제 stub
  - NATS startup/lifespan 연동

---

## 9. 작성 스타일 기준

현재 사용자 선호와 저장소 방향을 반영한 기준:
- 비동기 테스트가 필요할 때는 `pytest-asyncio`의 `async def` 테스트 함수 사용
- `asyncio.run(...)` 래퍼는 사용하지 않음
- FastAPI dependency 검증은 `Depends(...)` + `TestClient` 또는 async client로 수행
- 상태 코드와 응답 본문을 함께 검증
- 외부 의존성 테스트는 기본 회귀와 분리

---

## 10. 최소 체크리스트 (현재 완료 기준)

- [x] `create_app()`이 FastAPI 앱을 생성한다.
- [x] health route가 기본 포함된다.
- [x] auth route가 기본 포함된다.
- [x] `include_auth_router=False` 경로가 검증되었다.
- [x] custom lifespan startup/shutdown이 검증되었다.
- [x] `/token`이 `TokenResponse` 구조를 반환한다.
- [x] `/user`가 `UserInfo` 구조를 반환한다.
- [x] readiness 성공/실패가 검증되었다.
- [x] `get_current_user()`의 401 경로가 검증되었다.
- [x] `require_permissions(...)`의 403 경로가 검증되었다.
- [x] schema 기본값이 검증되었다.

미완료 체크:
- [ ] config 로더 직접 테스트
- [ ] invalid token 401 테스트
- [ ] `/token` 실패 경로 테스트
- [ ] 외부 연동 integration test
- [ ] 비동기 테스트 함수 기반 coverage

---

## 11. 참고 문서

- `docs/prd.md`
- `docs/srs.md`
- `docs/api.md`
- `docs/config.md`
- `README.md`
- `test_fastapi_core/conftest.py`
- `test_fastapi_core/test_factory.py`
- `test_fastapi_core/test_auth_router.py`
- `test_fastapi_core/test_health_router.py`
- `test_fastapi_core/test_dependencies.py`
- `test_fastapi_core/test_schemas.py`

---

## 12. 문서 상태 메모

이 문서는 기존의 넓은 테스트 계획 초안을, **현재 저장소에 실제 존재하는 테스트와 이미 검증된 계약** 중심으로 재정렬한 것이다.
향후 테스트가 추가되면 이 문서도 “계획”이 아니라 “실제 회귀 범위” 기준으로 계속 갱신하는 것이 맞다.
