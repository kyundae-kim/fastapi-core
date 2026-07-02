# fastapi-core 테스트 정의서

> 문서 목적: `fastapi-core`의 **현재 구현된 FastAPI 앱 계층**을 어떤 수준으로 검증하는지 정리한다.
> 기준 문서: `docs/prd.md`, `docs/srs.md`, `docs/api.md`, `docs/config.md`
> 문서 상태: 구현 반영본(v0.5)

---

## 1. 문서 개요

이 문서는 계획 단계의 이상적인 테스트 목록이 아니라, 현재 저장소에 존재하는 테스트와 검증 범위를 기준으로 정리한다.
핵심 대상은 다음과 같다.

- `create_app(...)`
- auth router (`/token`, `/user`)
- health router (`/health/liveness`, `/health/readiness`)
- dependency (`get_current_user`, `require_permissions`, service_clients 기반 `get_auth_provider` 경로, `get_service_client(service_name)`, 서비스별 전용 `get_*` dependency)
- schema (`TokenResponse`, `UserInfo`, `HealthResponse`, `HealthServiceDetail`)
- config / settings loader
- custom lifespan 연계
- 구조화 로깅

- 작성일: `2026-06-29`
- 작성자: `Hermes Agent`
- 버전: `v0.5`
- 상태: `implemented-surface`

---

## 2. 현재 테스트 인벤토리

실제 테스트 파일:

```text
test_fastapi_core/
  conftest.py
  integration/
    conftest.py
    test_keycloak_auth_flow.py
    test_readiness_with_live_services.py
    test_nats_lifespan.py
  test_config.py
  test_factory.py
  test_auth_router.py
  test_health_router.py
  test_dependencies.py
  test_schemas.py
```

현재는 다음 파일이 **없다**:
- `test_lifespan.py`
- `test_messaging_integration.py`

즉, 문서는 없는 테스트를 이미 갖춘 것처럼 서술하면 안 되지만,
이제는 실제 외부 서비스 통합 전용 테스트 파일이 `test_fastapi_core/integration/` 아래에 존재한다.

---

## 3. 테스트 실행 기준

현재 저장소 검증 명령:

```bash
uv run pytest -q
uv run pytest -q -m integration
```

최근 실제 실행 결과:
- `uv run pytest -q` → `43 passed, 2 warnings`
- `uv run pytest -q -m integration` → `10 passed, 33 deselected, 2 warnings`

테스트 러너/환경 특성:
- `pytest` 사용
- 외부 서비스 통합 테스트는 `pytest.mark.integration`으로 분리
- FastAPI endpoint 검증은 `fastapi.testclient.TestClient` 사용
- 현재 테스트 파일들은 모두 동기 테스트 함수(`def`) 기반
- 비동기 테스트는 아직 없음
- import 안정화를 위해 `test_fastapi_core/conftest.py`에서 저장소 루트를 `sys.path`에 추가함

### 3.1 통합 테스트 실행/skip 정책

- 통합 테스트는 기본 회귀와 분리된 `test_fastapi_core/integration/`에 위치한다.
- Keycloak/NATS live 테스트는 환경변수 및 reachability가 충족될 때만 실행된다.
- 필수 환경변수 누락 또는 서비스 미도달이면 `skip`이 기본 정책이다.
- 서비스는 살아 있지만 앱 계약이 틀린 경우에는 `fail`로 처리한다.

Keycloak 통합 테스트 필수 env:
- `KEYCLOAK_URL`
- `KEYCLOAK_REALM`
- `KEYCLOAK_CLIENT_ID`
- `KEYCLOAK_CLIENT_SECRET`
- `KEYCLOAK_TOKEN_USERNAME`
- `KEYCLOAK_TOKEN_PASSWORD`

NATS 관련 기본 env:
- `NATS_SERVERS`
- 선택: `NATS_TOKEN`, `NATS_USER`, `NATS_PASSWORD`

---

## 4. 공통 테스트 fixture

정의 위치: `test_fastapi_core/conftest.py`

### 4.1 `build_test_settings()`

`load_docmesh_settings(...)`를 통해 테스트용 `ServiceConfigs`를 구성한다.

포함되는 최소 설정 범위:
- Keycloak
- SQLite
- MinIO
- Milvus
- Ollama
- Langfuse
- NATS

의미:
- 현재 구현에서 `ServiceConfigs` 생성이 성립하도록 필수 환경값 세트를 코드로 고정한 것
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
- Keycloak provider의 JWT 허용 알고리즘이 `RS256`으로 맞춰진다.
- `app.state.settings`가 저장된다.
- `app.state.config.token_url`이 기본값으로 반영된다.
- `app.state.service_clients`가 생성된다.
- `app.state.root_logger`가 생성된다.
- 기본 readiness state가 `keycloak` 기준으로 구성된다.
- async service check를 readiness 경로에서 동기 callable로 감싸 실행한다.
- Keycloak readiness는 healthcheck에 테스트 자격증명 env를 전달한다.
- custom `token_url`이 OpenAPI security scheme에 반영된다.
- `include_auth_router=False`일 때 `/token`, `/user`가 404다.
- custom lifespan startup/shutdown이 호출된다.
- 선택 서비스(`sqlite`)만 로딩하는 설정 경로가 동작한다.
- JSON 파일 로깅이 실제로 기록된다.

현재 검증하지 않는 항목:
- CORS middleware 세부 응답 헤더 동작
- `root_path` 기반 reverse proxy 실제 동작
- 여러 서비스 조합에서의 광범위한 service_clients matrix

## 5.2 auth router 테스트

정의 위치: `test_fastapi_core/test_auth_router.py`

현재 검증하는 항목:
- `/token`이 `TokenResponse` 구조를 반환한다.
- `/token` 응답의 `token_type`이 소문자 `bearer`로 정규화된다.
- `/token` 요청의 `scope`, `username`, `password`가 provider로 전달된다.
- `/token`이 인증 실패를 `401 Authentication failed`로 매핑한다.
- `/token`이 설정 오류를 `500 Authentication service misconfigured`로 매핑한다.
- `/token`이 일시 오류를 `503 Authentication service unavailable`로 매핑한다.
- 실패 응답에 `WWW-Authenticate: Bearer` 헤더가 포함된다.
- 실패 로그가 `token_issue_failed` 구조화 이벤트로 남고, secret이 마스킹된다.
- `/user`가 `UserInfo` 구조를 반환한다.
- fake auth provider를 `app.state.auth_provider`로 주입해 동작을 대체할 수 있다.
- `/user`는 bearer token 기반 사용자 변환 결과를 반환한다.

현재 검증하지 않는 항목:
- `/token`의 `KeycloakTokenError -> 502` 경로
- `/token`의 예상 밖 예외 `500` 경로
- 실제 Keycloak 연동

## 5.3 health router 테스트

정의 위치: `test_fastapi_core/test_health_router.py`

현재 검증하는 항목:
- readiness check가 모두 성공하면 `200 + status="ok"`
- 선택 서비스 실패 시 `200 + status="degraded"`
- 필수 서비스 실패 시 `503 + status="error"`
- 성공/실패 시 `details`에 서비스별 상태 구조가 들어간다.
- Keycloak live readiness가 실제 healthcheck 경로를 통해 `200`을 반환한다.
- NATS live readiness가 async check를 포함해 `ok/degraded/error` 계약을 지킨다.
- readiness 실패 로그가 `readiness_check_failed` 구조화 이벤트로 남는다.
- 오류 문자열에서 secret이 마스킹된다.

현재 검증하지 않는 항목:
- `/health/liveness` 단독 파일 수준 재검증(간접적으로 factory 테스트에서 검증)
- `READINESS_PARALLEL` 플래그의 병렬성 효과 자체
- timeout/네트워크 오류의 상세 분기
- 실제 외부 서비스 check 함수 연동

## 5.4 dependency 테스트

정의 위치: `test_fastapi_core/test_dependencies.py`

현재 검증하는 항목:
- `get_current_user()`의 token 없음 경로 → 401
- `WWW-Authenticate: Bearer` 헤더 검증
- `require_permissions("admin")`의 role 부족 경로 → 403
- service_clients 기반 auth provider 경로에서 `keycloak` client가 요청된다.
- service_clients에서 받은 provider가 token 해석에 사용된다.
- `get_service_client("sqlite")`가 wrapper 기반 service client를 반환한다.
- 전용 dependency 공개 심볼이 노출된다.
- `get_keycloak_auth_service() -> KeycloakAuthService` 타입 힌트가 검증된다.
- `get_sqlite_engine() -> sqlalchemy.engine.Engine` 타입 힌트가 검증된다.
- `get_nats_connection_builder() -> docmesh_py_core.NatsConnectionBuilder` 타입 힌트가 검증된다.
- `get_sqlite_engine`, `get_keycloak_auth_service`, `get_nats_connection_builder`가 concrete client/builder를 실제 FastAPI dependency로 주입한다.
- 비활성 서비스일 때 `get_service_client("sqlite")`가 503을 반환한다.
- 비활성 서비스일 때 `get_nats_connection_builder()`가 503을 반환한다.

현재 검증하지 않는 항목:
- `get_config()` 직접 테스트
- `get_settings()` 직접 테스트
- `app.state.auth_provider`가 이미 있을 때의 재사용 경로 직접 테스트
- invalid token 예외 매핑

## 5.5 config / settings 테스트

정의 위치: `test_fastapi_core/test_config.py`

현재 검증하는 항목:
- `load_app_config()`가 `ROOT_PATH`, `TOKEN_URL`, `CORS_ORIGINS`, `CORS_CREDENTIALS`, `READINESS_PARALLEL`을 읽는다.
- `DOCMESH_LOG_LEVEL`, `APP_LOG_PATH`, `APP_LOG_JSON`, `APP_LOG_FORCE`를 읽는다.
- `DOCMESH_SERVICES`, `READINESS_REQUIRED_SERVICES`를 읽는다.
- 기본 `AppConfig` 값이 현재 구현과 일치한다.
- `build_docmesh_env_overlay()`가 기본값을 채우되 기존 환경변수를 덮어쓰지 않는다.
- `load_docmesh_settings(("sqlite",))`가 선택 서비스만 로딩한다.

## 5.6 schema 테스트

정의 위치: `test_fastapi_core/test_schemas.py`

현재 검증하는 항목:
- `TokenResponse.token_type == "bearer"`
- `TokenResponse.refresh_token is None`
- `UserInfo.roles/scopes` 기본값이 빈 리스트
- `HealthResponse(status="ok")` 생성 가능
- `HealthResponse.details is None`

## 5.7 외부 연동 integration 테스트

정의 위치:
- `test_fastapi_core/integration/conftest.py`
- `test_fastapi_core/integration/test_keycloak_auth_flow.py`
- `test_fastapi_core/integration/test_readiness_with_live_services.py`
- `test_fastapi_core/integration/test_nats_lifespan.py`

현재 검증하는 항목:
- 실제 Keycloak 설정이 있을 때 `POST /token`이 live access token을 발급한다.
- 발급된 live bearer token으로 `GET /user`가 실제 사용자 정보를 반환한다.
- invalid bearer token이 `401`로 매핑된다.
- OpenAPI `tokenUrl`이 live auth 라우터 구성과 일치한다.
- Keycloak required readiness가 실제 healthcheck 경로로 `200 + status="ok"`를 반환한다.
- Keycloak + NATS 조합에서 readiness가 실제 service client check 결과를 반영한다.
- optional NATS가 비정상일 때 readiness가 `200 + status="degraded"`를 반환한다.
- NATS required 구성일 때 readiness가 `200/503` 계약을 지킨다.
- custom lifespan이 살아 있는 동안 live NATS app이 readiness 요청을 처리한다.

설계상 중요한 현재 동작:
- Keycloak readiness는 `KEYCLOAK_TOKEN_USERNAME` / `KEYCLOAK_TOKEN_PASSWORD`를 사용한 healthcheck로 검증된다.
- NATS async check는 readiness 경로에서 동기 wrapper로 실행된다.

---

## 6. 현재 테스트 설계 원칙

### 6.1 실제 구현 우선

문서 계획이 아니라 현재 구현된 계약을 검증한다.
예를 들어:
- readiness는 `app.state.readiness_checks`와 `readiness_services` 조합을 기준으로 검증한다.
- auth는 빠른 회귀에서는 fake provider 주입으로 계약을 고정하고, live integration에서는 실제 Keycloak 서버 경로를 검증한다.
- config는 실제 `AppConfig` 및 `docmesh_settings` 로더를 직접 통과시킨다.

### 6.2 좁고 빠른 회귀 우선

현재 테스트는 대부분 다음 계층의 계약 검증에 집중한다.
- response status
- response body shape
- route 포함/제외
- dependency failure branch
- 구성 값 파싱
- 로그/상태 side effect

### 6.3 실제 설정 모델 경로 사용

테스트는 단순 dict mock 대신 `load_docmesh_settings(...)` 또는 실제 로더를 통해 `ServiceConfigs`를 만든다.
따라서 설정 유효성 제약이 테스트에도 반영된다.

---

## 7. 현재 구현 기준의 테스트 갭

문서와 비교했을 때 아직 없는 검증:

1. `get_config()` / `get_settings()` 직접 테스트
2. `app.state.auth_provider` 선행 주입 재사용 경로의 직접 테스트
3. `/token`의 `502` 및 unexpected `500` 분기 테스트
4. CORS middleware 응답 헤더 테스트
5. `root_path` 반영 테스트
6. 비동기 테스트 함수 기반 검증
7. custom `app.state.nats` dependency 패턴 테스트
8. `READINESS_PARALLEL`의 실제 병렬성 효과 검증

이 항목들은 향후 추가 대상이지, 현재 완료된 테스트 범위는 아니다.

---

## 8. 권장 추가 테스트 우선순위

현재 구현을 기준으로 다음 순서를 권장한다.

### 우선순위 1
- dependency 직접 테스트 보강
  - `get_config()` / `get_settings()`
  - `app.state.auth_provider` 재사용 경로

### 우선순위 2
- router 실패 경로 보강
  - `/token`의 `KeycloakTokenError -> 502`
  - `/token`의 unexpected 예외 `500`

### 우선순위 3
- app factory / middleware 보강
  - CORS 응답 헤더
  - `root_path` 반영
  - `READINESS_PARALLEL` 전달 효과

### 우선순위 4
- 비동기/운영성 관점 보강
  - `pytest-asyncio` 기반 async 테스트
  - 실제 `READINESS_PARALLEL` 효과 검증

---

## 9. 작성 스타일 기준

현재 사용자 선호와 저장소 방향을 반영한 기준:
- 비동기 테스트가 필요할 때는 `pytest-asyncio`의 `async def` 테스트 함수 사용
- `asyncio.run(...)` 래퍼는 사용하지 않음
- FastAPI dependency 검증은 `Depends(...)` + `TestClient` 또는 async client로 수행
- 상태 코드와 응답 본문을 함께 검증
- 로그/민감정보 마스킹 검증은 회귀 가치가 높으므로 유지
- 외부 의존성 테스트는 기본 회귀와 분리

---

## 10. 최소 체크리스트 (현재 완료 기준)

- [x] `create_app()`이 FastAPI 앱을 생성한다.
- [x] health route가 기본 포함된다.
- [x] auth route가 기본 포함된다.
- [x] `include_auth_router=False` 경로가 검증되었다.
- [x] custom lifespan startup/shutdown이 검증되었다.
- [x] OpenAPI `tokenUrl` 반영이 검증되었다.
- [x] 기본 readiness state 구성이 검증되었다.
- [x] 선택 서비스 로딩이 검증되었다.
- [x] JSON 로깅이 검증되었다.
- [x] `/token`이 `TokenResponse` 구조를 반환한다.
- [x] `/token` 실패 경로 일부가 검증되었다.
- [x] `/user`가 `UserInfo` 구조를 반환한다.
- [x] readiness `ok/degraded/error`가 검증되었다.
- [x] 실제 Keycloak/NATS integration test가 분리되어 추가되었다.
- [x] invalid token 401 테스트가 있다.
- [x] `get_current_user()`의 401 경로가 검증되었다.
- [x] `require_permissions(...)`의 403 경로가 검증되었다.
- [x] config 로더 직접 테스트가 있다.
- [x] schema 기본값이 검증되었다.

미완료 체크:
- [ ] `/token`의 502/unexpected 500 테스트
- [ ] CORS 응답 헤더 테스트
- [ ] `root_path` 반영 테스트
- [ ] 비동기 테스트 함수 기반 coverage

---

## 11. 참고 문서

- `docs/prd.md`
- `docs/srs.md`
- `docs/api.md`
- `docs/config.md`
- `docs/examples.md`
- `docs/consistency-checklist.md`
- `README.md`
- `test_fastapi_core/conftest.py`
- `test_fastapi_core/test_config.py`
- `test_fastapi_core/test_factory.py`
- `test_fastapi_core/test_auth_router.py`
- `test_fastapi_core/test_health_router.py`
- `test_fastapi_core/test_dependencies.py`
- `test_fastapi_core/test_schemas.py`
- `test_fastapi_core/integration/conftest.py`
- `test_fastapi_core/integration/test_keycloak_auth_flow.py`
- `test_fastapi_core/integration/test_readiness_with_live_services.py`
- `test_fastapi_core/integration/test_nats_lifespan.py`

---

## 12. 문서 상태 메모

이 문서는 기존의 넓은 테스트 계획 초안을, **현재 저장소에 실제 존재하는 테스트와 이미 검증된 계약** 중심으로 재정렬한 것이다.
특히 Keycloak/NATS live integration 테스트 추가, Keycloak readiness credential 기반 검증, RS256 bearer token 검증, async NATS readiness wrapper, 전체 `43 passed, 2 warnings` / integration `10 passed, 33 deselected, 2 warnings` 결과를 반영해 최신 코드와 맞췄다.
이제 dependency 테스트는 공통 lookup용 `get_service_client(service_name)`뿐 아니라 타입이 구체화된 전용 dependency(`get_keycloak_auth_service`, `get_postgres_engine`, `get_sqlite_engine`, `get_minio_client`, `get_milvus_client`, `get_ollama_client`, `get_langfuse_client`, `get_nats_connection_builder`) 공개 계약도 포함한다.
