# fastapi-core 테스트 정의서

> 문서 목적: `fastapi-core`의 FastAPI 앱 계층을 어떤 수준으로 검증해야 하는지 정의한다.
> 기준 문서: `docs/prd.md`, `docs/srs.md`, `docs/api.md`, `docs/config.md`, `docs/messaging.md`
> 문서 상태: 초안(v0.1)

---

## 1. 문서 개요

이 문서는 `fastapi-core`를 단순 유틸리티 패키지가 아니라 **FastAPI 애플리케이션 코어**로 보고 테스트 범위를 정의한다.

- 작성일: `2026-06-25`
- 작성자: `Hermes Agent 초안 / 사용자 검토 필요`
- 버전: `v0.1`
- 상태: `draft`

핵심 검증 대상은 다음과 같다.

- `create_app(...)`
- auth router (`/token`, `/user`)
- health router (`/health/liveness`, `/health/readiness`)
- dependency (`get_config`, `get_settings`, `get_auth_provider`, `get_current_user`, `require_permissions`)
- schema (`TokenResponse`, `UserInfo`, `HealthResponse`)
- lifespan / startup / shutdown 연계
- 설정 오류 및 인증 오류 처리

---

## 2. 테스트 목표

- FastAPI 앱이 최소 boilerplate로 생성되는지 확인한다.
- 공통 router가 의도대로 포함/제외되는지 확인한다.
- dependency 계층이 request context에서 올바르게 동작하는지 확인한다.
- auth / health endpoint의 상태 코드와 response model이 일관적인지 확인한다.
- startup/shutdown에서 외부 자원 초기화/정리가 가능한지 확인한다.
- 설정/보안 오류가 조기에 드러나는지 확인한다.

---

## 3. 테스트 분류

## 3.1 단위 테스트

목적:
- schema, helper, dependency의 좁은 단위 동작 검증

대상 예:
- `TokenResponse` 기본값
- `UserInfo.roles`, `UserInfo.scopes` 기본값
- `HealthResponse.status` 검증
- `require_permissions(...)`의 role 검사 분기
- `get_current_user()`의 token 없음 경로

## 3.2 통합 테스트

목적:
- app factory + router + dependency가 함께 동작하는지 확인

대상 예:
- `create_app()` 결과 앱 인스턴스 검증
- `/health/liveness` 응답 검증
- `/token`, `/user` endpoint 검증
- dependency override를 통한 auth/provider 대체 검증

## 3.3 수명주기 테스트

목적:
- lifespan 기반 startup/shutdown 처리 검증

대상 예:
- custom lifespan 호출 여부
- startup에서 `app.state` 설정 여부
- shutdown에서 cleanup 수행 여부

## 3.4 외부 연동 테스트

목적:
- Keycloak, NATS 등 외부 의존성과의 실제 또는 준실제 연동 검증

대상 예:
- Keycloak 토큰 발급 성공/실패
- readiness의 외부 의존성 실패 처리
- NATS startup 연결 및 종료

> 외부 연동 테스트는 `integration` marker로 분리하는 것이 바람직하다.

---

## 4. 테스트 환경 원칙

- 테스트 러너는 `pytest`를 사용한다.
- 비동기 테스트는 `pytest-asyncio` 기반 async test function으로 작성한다.
- 외부 의존성이 없는 테스트는 로컬에서 바로 실행 가능해야 한다.
- 외부 서비스가 필요한 테스트는 명시적으로 분리해야 한다.
- secret/token/password는 테스트 fixture나 로그에 원문 노출하지 않는다.

`pyproject.toml` 기준 확인된 사항:
- `pytest-asyncio` dev dependency 사용
- `testpaths = ["test_fastapi_core"]`
- `integration` marker 사용
- `anyio_mode = "auto"`

---

## 5. App factory 테스트 요구사항

## 5.1 기본 앱 생성

검증 포인트:
- `create_app()`이 `FastAPI` 인스턴스를 반환한다.
- health router가 기본 포함된다.
- auth router가 기본 포함된다.

예상 테스트:
- `/health/liveness`가 200 반환
- `/token` route가 존재
- `/user` route가 존재

## 5.2 auth router 제외

검증 포인트:
- `create_app(include_auth_router=False)`일 때 auth endpoint가 노출되지 않는다.
- health router는 계속 사용 가능하다.

예상 테스트:
- `/token` → 404
- `/user` → 404
- `/health/liveness` → 200

## 5.3 root_path / lifespan 주입

검증 포인트:
- `root_path`가 앱 설정에 반영된다.
- custom lifespan이 호출된다.

---

## 6. Router 테스트 요구사항

## 6.1 Auth router

### `/token`
검증 항목:
- 정상 credential 입력 시 `TokenResponse` 구조 반환
- 실패 시 401 반환
- `WWW-Authenticate: Bearer` 헤더 포함

### `/user`
검증 항목:
- 인증 성공 시 `UserInfo` 반환
- token 없음 시 401 반환
- 권한 또는 token 오류 시 적절한 오류 반환

## 6.2 Health router

### `/health/liveness`
검증 항목:
- 항상 경량 200 응답
- `HealthResponse` 구조 사용

### `/health/readiness`
검증 항목:
- 외부 의존성 준비 시 200 가능
- 외부 의존성 미준비 시 503 가능
- timeout/네트워크 오류가 적절한 상태 코드로 매핑됨
- 최소 `status` 필드 존재 확인
- 선택 의존성 사용 시 `details` 같은 확장 필드와 degraded 정책 검증

---

## 7. Dependency 테스트 요구사항

## 7.1 `get_config()`

검증 항목:
- 설정 객체 반환
- 동일 실행 문맥에서 캐시 재사용 가능

## 7.2 `get_settings()`

검증 항목:
- config 기반 서비스 설정 반환
- 필요한 경우 dependency override 가능

## 7.3 `get_auth_provider()`

검증 항목:
- `app.state`에 provider가 있으면 재사용
- 없으면 설정 기반 기본 provider 생성

## 7.4 `get_current_user()`

검증 항목:
- token 없음 → 401
- secure decode 성공 → `UserInfo`
- decode 실패 → 401

## 7.5 `require_permissions(...)`

검증 항목:
- 요구 role 존재 시 통과
- 요구 role 부재 시 403

---

## 8. Schema 테스트 요구사항

## 8.1 `TokenResponse`

검증 항목:
- `access_token` 필수
- `refresh_token` optional
- `token_type` 기본값 `bearer`

## 8.2 `UserInfo`

검증 항목:
- `sub`, `username` 필드 직렬화
- `roles`, `scopes` 기본 리스트 초기화
- optional 필드가 없어도 모델 생성 가능

## 8.3 `HealthResponse`

검증 항목:
- `status` 필드 포함
- FastAPI response model로 사용 가능

---

## 9. Lifespan / startup / shutdown 테스트

## 9.1 Startup

검증 항목:
- custom lifespan startup 블록이 실행된다.
- startup에서 `app.state`에 provider/connection을 저장할 수 있다.

## 9.2 Shutdown

검증 항목:
- shutdown cleanup이 호출된다.
- 종료 예외가 필요 이상으로 전파되지 않는지 검토한다.

## 9.3 메시징 연계

검증 항목:
- NATS builder/connection을 startup에서 초기화 가능
- shutdown에서 close 가능
- readiness가 메시징 상태를 반영하도록 확장 가능한 구조인지 확인

---

## 10. 설정 및 오류 테스트

검증 대상 예:
- 필수 Keycloak 설정 누락
- 잘못된 token grant 조합
- 잘못된 timeout 값
- NATS 인증 방식 누락
- DSN/secret이 오류 메시지에 원문 노출되지 않는지 확인

오류 테스트 원칙:
- 어떤 설정이 잘못됐는지 식별 가능해야 함
- 민감정보 비노출
- 가능한 경우 수정 방향 유추 가능

---

## 11. 권장 테스트 구조

예시 디렉터리:

```text
test_fastapi_core/
  test_factory.py
  test_auth_router.py
  test_health_router.py
  test_dependencies.py
  test_schemas.py
  test_lifespan.py
  test_config.py
  test_messaging_integration.py
```

권장 fixture 예:
- `app`
- `client`
- `mock_auth_provider`
- `mock_settings`
- `mock_config`

---

## 12. 권장 작성 스타일

- 비동기 검증은 `async def` 테스트 함수로 작성
- `asyncio.run(...)` 래퍼 대신 `pytest-asyncio` 사용
- dependency override를 우선 활용
- 외부 서비스가 필요한 테스트는 marker 분리
- endpoint contract 검증 시 status code + response body를 함께 확인

---

## 13. 최소 검증 체크리스트

- [ ] `create_app()`이 FastAPI 앱을 반환한다.
- [ ] `/health/liveness`가 200과 `HealthResponse`를 반환한다.
- [ ] `/health/readiness`가 준비 상태를 반영한다.
- [ ] `/token`이 `TokenResponse`를 반환한다.
- [ ] `/user`가 `UserInfo`를 반환한다.
- [ ] `get_current_user()`의 401 경로가 검증되었다.
- [ ] `require_permissions(...)`의 403 경로가 검증되었다.
- [ ] `include_auth_router=False` 경로가 검증되었다.
- [ ] lifespan startup/shutdown이 검증되었다.
- [ ] 설정 오류 메시지에 민감정보가 포함되지 않는다.

---

## 14. 참고 문서

- `docs/prd.md`
- `docs/srs.md`
- `docs/api.md`
- `docs/config.md`
- `docs/messaging.md`
- `pyproject.toml`

---

## 부록 A. 문서 상태 메모

이 문서는 현재 확인된 FastAPI 공개 표면(`create_app`, router, dependency, schema, lifespan 연계)을 기준으로 작성했다. 실제 테스트 코드를 추가할 때는 wheel 또는 소스 트리 기준의 import path, fixture 전략, 외부 서비스 준비 절차를 함께 고정해야 한다.
