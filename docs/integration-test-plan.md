# fastapi-core 통합 테스트 설계안

> 문서 목적: 현재 `fastapi-core` 구현을 기준으로 **실제 외부 의존성 연동 통합 테스트**를 어떤 방식으로 추가할지 정의한다.
> 기준 소스: `fastapi_core/factory.py`, `fastapi_core/routers/auth.py`, `fastapi_core/routers/health.py`, `fastapi_core/dependencies/auth.py`, `docs/test.md`, `docs/api.md`, `docs/messaging.md`
> 문서 상태: 설계 초안(v0.1)

---

## 1. 목표

현재 테스트 스위트는 fake provider / 수동 readiness check 주입을 중심으로 FastAPI 앱 계층 계약을 빠르게 검증한다.
통합 테스트의 목표는 이 단위/계약 테스트를 대체하는 것이 아니라, 아래 두 가지를 **실제 외부 연동 경로**에서 추가 검증하는 것이다.

1. `create_app(...)`가 실제 서비스 설정을 바탕으로 외부 클라이언트를 조립한다.
2. auth / readiness / lifespan이 fake 객체가 아니라 실제 또는 준실제 서비스 경로에서 기대대로 동작한다.

즉, 통합 테스트는 다음 질문에 답해야 한다.

- 실제 Keycloak 설정이 있을 때 `/token`, `/user` 경로가 end-to-end로 성립하는가?
- 실제 NATS 설정이 있을 때 앱 startup/shutdown과 readiness 구성이 깨지지 않는가?
- 필수/선택 서비스 분류가 실제 서비스 상태와 함께 `ok/degraded/error`로 올바르게 반영되는가?

---

## 2. 현재 기준선

현재 저장소 상태에서 확인된 사실:

- 기본 회귀 테스트는 `test_fastapi_core/` 하위 7개 파일로 구성된다.
- `pytest` marker `integration`은 이미 `pyproject.toml`에 선언돼 있다.
- 아직 `test_lifespan.py`, `test_messaging_integration.py`, 실제 외부 서비스 전용 테스트 파일은 없다.
- 현재 health/auth 테스트는 대부분 `app.state.auth_provider`나 `app.state.readiness_checks`를 직접 주입하는 방식이다.

따라서 통합 테스트는 **기존 테스트를 확장**하되, 다음 원칙을 유지해야 한다.

- 기본 `uv run pytest -q`는 빠르게 유지
- 외부 의존성 테스트는 `-m integration`으로 분리
- 외부 서비스 미준비 시 실패보다 `skip`이 우선

---

## 3. 범위

### 3.1 포함 범위

1. **Keycloak 인증 통합**
   - 실제 Keycloak 서버 또는 준실제 테스트 인스턴스 사용
   - `/token` 발급 성공
   - `/user` 조회 성공
   - invalid token 401
   - 서비스 설정 오류/미가동 시 failure shape 확인

2. **NATS / lifespan 통합**
   - `enabled_services=["nats"]` 또는 `enabled_services=["keycloak", "nats"]` 상태에서 앱 생성
   - startup/shutdown 동안 NATS client builder/connection close 경로가 예외 없이 수행됨
   - 선택 서비스/필수 서비스 분류가 readiness 응답에 반영됨

3. **readiness 실연동 검증**
   - 실제 `service_clients`에서 생성된 `check()`가 `/health/readiness`에 연결됨
   - `required_services` 조합에 따라 `200/degraded` 또는 `503/error`가 달라짐

### 3.2 제외 범위

- 성능/부하 테스트
- 네트워크 장애 재시도 횟수 같은 세밀한 docmesh 내부 정책 검증
- MinIO/Milvus/Ollama/Langfuse 전체 서비스 matrix
- CI 인프라 구축 자체

---

## 4. 테스트 분리 전략

## 4.1 디렉터리 구조

권장 구조:

```text
test_fastapi_core/
  conftest.py
  integration/
    conftest.py
    test_keycloak_auth_flow.py
    test_readiness_with_live_services.py
    test_nats_lifespan.py
```

의도:

- 기존 빠른 회귀와 통합 테스트를 물리적으로 분리
- 공용 fixture는 `test_fastapi_core/conftest.py`에 유지
- 외부 서비스 전용 fixture/skip 로직은 `test_fastapi_core/integration/conftest.py`에 집중

## 4.2 pytest 마커 정책

모든 통합 테스트에 다음 마커를 부여한다.

```python
pytestmark = pytest.mark.integration
```

실행 기준:

```bash
uv run pytest -q
uv run pytest -q -m integration
uv run pytest -q -m "not integration"
```

기본 회귀에서는 `not integration`만 돌리는 운영도 가능하다.

---

## 5. 환경/전제조건 설계

통합 테스트는 저장소 기본 fallback 값에 의존하면 안 된다.
명시적 테스트 환경변수가 있어야만 활성화한다.

### 5.1 Keycloak용 필수 환경변수

예상 필드:

- `KEYCLOAK_URL`
- `KEYCLOAK_REALM`
- `KEYCLOAK_CLIENT_ID`
- `KEYCLOAK_CLIENT_SECRET`
- `KEYCLOAK_TOKEN_USERNAME`
- `FASTAPI_CORE_TEST_PASSWORD`
- 선택: `FASTAPI_CORE_TEST_SCOPE`
- 선택: `FASTAPI_CORE_TEST_INVALID_TOKEN`

### 5.2 NATS용 필수 환경변수

예상 필드:

- `NATS_SERVERS`
- 선택: `NATS_TOKEN`
- 선택: `NATS_USER`
- 선택: `NATS_PASSWORD`
- 선택: `FASTAPI_CORE_TEST_NATS_REQUIRED` (`true/false`)

### 5.3 skip 정책

`integration/conftest.py`에서 다음 헬퍼를 둔다.

- 필수 env 누락 시 `pytest.skip(...)`
- 서비스 health probe 실패 시 `pytest.skip(...)`
- 연결 실패를 테스트 실패로 볼지, 환경 미준비로 볼지 기준을 명확히 분리

권장 기준:

- **env 누락**: skip
- **서비스에 TCP/HTTP로 전혀 도달 불가**: skip
- **서비스는 살아 있는데 앱 계약이 틀림**: fail

---

## 6. 권장 fixture 설계

### 6.1 `integration_app_config(...)`

역할:

- `AppConfig`를 통합 테스트용으로 명시 구성
- `enabled_services`, `required_services`, `token_url`, `readiness_parallel`을 시나리오별로 제어

예시 형태:

- Keycloak only: `enabled_services=["keycloak"]`
- Keycloak + NATS: `enabled_services=["keycloak", "nats"]`, `required_services=["keycloak"]`
- NATS required 시나리오: `required_services=["nats"]`

### 6.2 `integration_settings(...)`

역할:

- `load_docmesh_settings(tuple(config.enabled_services))`를 실제 환경변수 기준으로 호출
- 기본 테스트용 dummy env가 아니라 실제 통합 테스트 대상 설정을 사용

주의:

- `load_docmesh_settings()`는 `lru_cache(maxsize=1)`이므로 fixture 시작/종료에서 `cache_clear()`가 필요하다.
- `load_app_config()` 역시 캐시되므로 env 변경 기반 시나리오가 있으면 clear가 필요하다.

### 6.3 `live_app(...)`

역할:

- `create_app(config=config, settings=settings)`로 실제 app 생성
- `TestClient` 또는 async client와 함께 lifespan 포함 실행

### 6.4 `issued_access_token(...)`

역할:

- `/token` 또는 직접 provider 호출로 받은 실제 access token 재사용
- `/user`와 invalid/expired 변형 테스트의 기준 토큰으로 사용

---

## 7. 시나리오 설계

## 7.1 Keycloak 인증 통합

대상 파일: `test_fastapi_core/integration/test_keycloak_auth_flow.py`

### 시나리오 A. `/token` 성공

검증 내용:

- `POST /token`이 200을 반환한다.
- 응답에 `access_token`이 존재한다.
- `token_type`이 `bearer`다.
- `refresh_token`은 Keycloak 응답 형태에 맞게 존재하거나 `null`일 수 있다.

이 테스트가 필요한 이유:

- 현재는 fake provider만 검증하고 있어 `get_auth_provider()` → docmesh keycloak client → provider 호출 전체 경로는 비어 있다.

### 시나리오 B. `/user` 성공

검증 내용:

- `/token`에서 받은 bearer token으로 `GET /user` 호출 시 200
- `sub`, `username`이 비어 있지 않음
- `roles`, `scopes`가 list 형태

이 테스트가 필요한 이유:

- 현재 `get_current_user()`는 fake `extract_user_info()`만 검증 중이다.
- 실제 JWT/claims 구조가 `_to_user_info()`와 맞물리는지 확인해야 한다.

### 시나리오 C. invalid token 401

검증 내용:

- 명백히 잘못된 bearer token으로 `GET /user` 호출 시 401
- `detail == "Invalid token"`
- `WWW-Authenticate == "Bearer"`

이 테스트가 필요한 이유:

- `docs/test.md`의 미완료 갭 항목을 직접 메운다.
- 실제 provider가 `TokenValidationError`를 일으키는 경로를 검증한다.

### 시나리오 D. auth router와 실제 설정 연결

검증 내용:

- `create_app()` 이후 `app.state.service_clients`에 `keycloak`이 존재
- `app.state.auth_provider`가 실제 keycloak client/provider에서 파생됨
- OpenAPI `tokenUrl`은 통합 테스트 설정값을 반영함

이 테스트가 필요한 이유:

- 조립 계층과 route 계층이 끊어지지 않았는지 확인한다.

---

## 7.2 readiness with live services

대상 파일: `test_fastapi_core/integration/test_readiness_with_live_services.py`

### 시나리오 A. Keycloak required only

구성:

- `enabled_services=["keycloak"]`
- `required_services=["keycloak"]`

검증 내용:

- `/health/readiness`가 200 또는 503 중 하나의 **계약 가능한 상태**를 반환한다.
- Keycloak reachable 환경에서는 `200 + status="ok"`
- 서비스는 살아 있으나 설정/권한이 잘못된 경우에는 `503 + status="error"`
- 응답 `details.keycloak.required is True`

주의:

- 이 테스트는 환경을 올바르게 준비한 CI/개발환경에서만 pass를 기대한다.
- 로컬 미준비 환경에서는 skip이 적절하다.

### 시나리오 B. Keycloak required + NATS optional

구성:

- `enabled_services=["keycloak", "nats"]`
- `required_services=["keycloak"]`

검증 내용:

- 두 서비스 모두 정상이면 `200 + ok`
- NATS만 비정상이면 `200 + degraded`
- Keycloak 비정상이면 `503 + error`
- `details.nats.required is False`

이 테스트가 필요한 이유:

- 현재 health 테스트는 수동 lambda로만 degraded/error를 만든다.
- 실제 service client `check()` 결과가 상태 분기와 연결되는지 봐야 한다.

### 시나리오 C. NATS required

구성:

- `enabled_services=["nats"]`
- `required_services=["nats"]`

검증 내용:

- NATS reachable 시 `200 + ok`
- NATS unreachable/인증 실패 시 `503 + error`

이 테스트가 필요한 이유:

- 선택 서비스와 필수 서비스 분류 로직을 실제 NATS 대상에서 검증한다.

---

## 7.3 NATS + lifespan 통합

대상 파일: `test_fastapi_core/integration/test_nats_lifespan.py`

### 시나리오 A. custom lifespan과 service client 정리 공존

구성:

- `enabled_services=["nats"]`
- custom `lifespan` fixture 사용

검증 내용:

- startup에서 custom lifespan 코드가 실행된다.
- `with TestClient(app): ...` 종료 후 shutdown 코드가 실행된다.
- 종료 과정에서 service client close 경로가 예외 없이 완료된다.

이 테스트가 필요한 이유:

- 현재는 fake custom lifespan의 호출 여부만 본다.
- 실제 외부 서비스가 있는 상태에서 `_build_lifespan(...)`의 정리 경로가 안전한지 확인해야 한다.

### 시나리오 B. app.state 확장 예시 검증

구성:

- custom lifespan에서 `app.state.nats_probe = ...` 같은 테스트용 state 설정

검증 내용:

- startup 중 state 설정 가능
- route 또는 테스트 본문에서 해당 state를 읽을 수 있음
- shutdown 후 정리 상태가 일관됨

이 테스트가 필요한 이유:

- `docs/messaging.md`가 설명하는 custom lifespan 확장 패턴을 실제 회귀로 고정할 수 있다.

---

## 8. 구현 순서 제안

### 단계 1. 통합 테스트 골격 추가

파일:

- `test_fastapi_core/integration/conftest.py`
- `test_fastapi_core/integration/test_keycloak_auth_flow.py`

작업:

- integration marker 적용
- env 검증/skip 헬퍼 추가
- Keycloak happy-path + invalid token 401 먼저 구현

이유:

- 현재 테스트 갭 중 가치가 가장 높은 항목을 가장 작은 범위로 닫는다.

### 단계 2. live readiness 추가

파일:

- `test_fastapi_core/integration/test_readiness_with_live_services.py`

작업:

- keycloak only
- keycloak + nats optional
- nats required

이유:

- app assembly와 health router 연결을 실제 service client 기준으로 검증할 수 있다.

### 단계 3. NATS/lifespan 통합 추가

파일:

- `test_fastapi_core/integration/test_nats_lifespan.py`

작업:

- custom lifespan + real NATS client coexistence
- startup/shutdown close 경로 검증

이유:

- 현재 문서에만 있는 메시징 lifecycle 설명을 실제 테스트로 고정한다.

---

## 9. 테스트 스타일 가이드

이 저장소와 사용자 선호를 반영한 권장 사항:

- 비동기 검증이 필요하면 `pytest-asyncio` 기반 `async def` 테스트 사용
- `asyncio.run(...)` 래퍼 금지
- HTTP endpoint 호출은 기본적으로 `TestClient`로 충분하지만,
  NATS 연결 상태 확인이나 비동기 startup 보조 검증이 필요하면 async fixture를 병행
- 외부 서비스용 timeout은 짧고 명시적으로 유지
- token, password, secret 값은 assertion/log 출력에 그대로 남기지 않음

권장 분리:

- auth endpoint 중심: `TestClient`
- async connection/lifecycle 세부 검증: `pytest.mark.asyncio`

---

## 10. 검증 명령

기본 명령:

```bash
uv run pytest -q -m integration
```

선택 실행 예시:

```bash
uv run pytest -q test_fastapi_core/integration/test_keycloak_auth_flow.py -m integration
uv run pytest -q test_fastapi_core/integration/test_readiness_with_live_services.py -m integration
uv run pytest -q test_fastapi_core/integration/test_nats_lifespan.py -m integration
```

CI 분리 예시:

```bash
uv run pytest -q -m "not integration"
uv run pytest -q -m integration
```

---

## 11. 리스크와 주의사항

1. **환경 의존성**
   - 외부 서비스가 없으면 실패가 아니라 skip가 되어야 한다.

2. **캐시 오염**
   - `load_app_config()` / `load_docmesh_settings()`의 `lru_cache` 때문에 시나리오 간 환경 변경이 섞일 수 있다.

3. **테스트 계정 안정성**
   - Keycloak 테스트 계정/클라이언트 설정이 바뀌면 auth 테스트가 불안정해질 수 있다.

4. **NATS의 실제 close 검증 난이도**
   - 현재 공개 표면상 close가 명시적 반환값을 주지 않으므로, 1차 검증은 “예외 없이 shutdown 완료” 중심이 현실적이다.

5. **문서/코드 용어 차이**
   - 일부 문서에는 registry 표현이 남아 있지만 현재 구현은 `app.state.service_clients`와 그 `check()` 경로가 핵심이다.
   - 설계 및 구현은 실제 코드 기준 용어를 우선해야 한다.

---

## 12. 최종 권장안

가장 먼저 추가할 통합 테스트 묶음은 다음이다.

1. `test_keycloak_auth_flow.py`
   - `/token` 성공
   - `/user` 성공
   - invalid token 401

2. `test_readiness_with_live_services.py`
   - keycloak required
   - keycloak required + nats optional

3. `test_nats_lifespan.py`
   - custom lifespan startup/shutdown
   - 외부 서비스 연결이 있는 상태에서 close 경로 무예외 종료

이 순서가 좋은 이유는:

- `docs/test.md`의 미완료 항목을 직접 메우고
- auth/health/lifecycle의 실제 연동 경로를 모두 커버하며
- 기본 회귀 테스트의 속도를 해치지 않기 때문이다.
