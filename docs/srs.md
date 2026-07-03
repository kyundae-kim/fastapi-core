# fastapi-core 소프트웨어 요구사항 정의서 (SRS)

> 문서 목적: `fastapi-core`를 **DocMesh Py Core 기반 서비스를 FastAPI 환경에서 동작시키기 위한 기능을 제공하는 FastAPI 컴포넌트**로 구현하기 위한 요구사항과 공개 인터페이스 계약으로 구체화한다.
> 기준 문서: `docs/prd.md`
> 문서 상태: 정렬본(v0.3)

---

## 1. 문서 개요

- 문서명: `fastapi-core 소프트웨어 요구사항 정의서`
- 작성일: `2026-06-25`
- 작성자: `Hermes Agent`
- 버전: `v0.3`
- 상태: `aligned-to-prd`

### 1.1 목적

본 문서는 `fastapi-core`를 **DocMesh Py Core 기반 서비스를 FastAPI 환경에서 구동시키기 위한 공통 FastAPI 컴포넌트**로 구현하기 위한 요구사항을 정의한다.
PRD가 capability 중심 문서라면, 이 문서는 그 capability를 실제 구현 가능한 함수, endpoint, dependency, schema, lifecycle 요구로 내려 적어 DocMesh Py Core 기반 기능이 FastAPI 서비스 표면으로 안정적으로 노출되도록 하는 역할을 가진다.

### 1.2 문서 역할 원칙

- PRD는 제품 목적, 사용자 가치, capability 범위를 정의한다.
- SRS는 구체 함수명, endpoint 경로, schema 이름, 동작 제약, 상태 코드 요구를 정의한다.
- API 문서는 현재 구현된 표면을 문서화한다.
- 구현이 SRS보다 앞서거나 뒤처질 수 있으므로, SRS는 목표 계약이고 API 문서는 현재 상태다.

### 1.3 범위

- DocMesh Py Core 기반 서비스용 `create_app(...)`
- auth / health router
- DocMesh 기능을 FastAPI request 처리에 연결하는 dependency 계층
- 서비스가 초기화한 외부 서비스 클라이언트 접근 경로
- FastAPI 응답 계약을 정의하는 response schema
- 설정 연동
- 외부 의존성과 FastAPI lifecycle 결합

---

## 2. 시스템 개요

`fastapi-core`는 DocMesh Py Core 기반 서비스를 FastAPI 애플리케이션으로 구동하기 위한 두 층의 조합으로 이해한다.

1. **DocMesh Py Core 및 서비스 기능층**
   - 설정, 인증 provider, 외부 서비스 연결, DocMesh 기반 기능 구성
2. **FastAPI 통합층**
   - app factory, router, dependency, schema, lifecycle, 오류 처리

이 문서는 두 번째 층을 중심으로 정의하되, 첫 번째 층의 기능이 FastAPI 표면에 어떻게 연결되어야 하는지도 함께 규정한다.

---

## 3. 공개 인터페이스 정책

### 3.1 정책

- `fastapi-core`의 공개 인터페이스는 app factory, router endpoint, dependency 함수, schema 모델로 구성된다.
- 정확한 symbol 이름과 endpoint 경로는 이 문서와 API 문서에서 관리한다.
- PRD에는 capability를 남기고, symbol 세부는 이 문서에서 관리한다.

### 3.2 문서화 대상 공개 표면

- app factory: `create_app(...)`
- dependency: `get_config()`, `get_settings()`, `get_auth_provider()`, `get_service_client(service_name)`, 서비스별 전용 `get_*_client()`, `get_current_user()`, `require_permissions(...)`
- schema: `TokenResponse`, `UserInfo`, `HealthResponse`
- endpoint: `/token`, `/user`, `/health/liveness`, `/health/readiness`

주의:
- 이 목록은 **패키지 루트 re-export 목록**이 아니라, SRS가 계약 대상으로 다루는 공개 FastAPI 표면을 뜻한다.
- package-root import 보장 범위는 구현 시점의 API 문서(`docs/api.md`)를 따른다.

---

## 4. 아키텍처 요구사항

### 4.1 App factory

- SR-001. 시스템은 `create_app(config=None, settings=None, lifespan=None, include_auth_router=True) -> FastAPI`를 제공해야 한다.
- SR-002. `config is None`이면 기본 환경 설정 객체를 생성해야 한다.
- SR-003. `settings is None`이면 환경기반 서비스 설정을 로딩해야 한다.
- SR-004. 생성된 앱은 `root_path`를 설정할 수 있어야 한다.
- SR-005. 커스텀 lifespan을 주입할 수 있어야 한다.
- SR-006. 생성된 앱은 `app.state.config`, `app.state.settings`, `app.state.service_clients`, `app.state.root_logger`를 저장할 수 있어야 한다.
- SR-007. readiness 제어용 상태(`app.state.readiness_parallel`, `app.state.readiness_checks`, `app.state.readiness_services`, `app.state.required_services`)를 저장할 수 있어야 한다.
- SR-008. 시스템은 `app.state.service_clients`와 lifespan 경로를 통해 외부 의존성 정리와 readiness 구성을 연결할 수 있어야 한다.

### 4.2 Middleware / exception handling

- SR-010. 시스템은 CORS middleware를 등록해야 한다.
- SR-011. CORS 설정은 앱 설정 객체에서 읽어야 한다.
- SR-012. 인증 관련 오류는 일관된 HTTP 예외 정책으로 반환되어야 한다.
- SR-013. 공통 auth 예외 핸들러 등록 여부는 구현 선택사항이지만, 외부 계약은 401/403 동작 일관성을 만족해야 한다.

### 4.3 Router registration

- SR-020. health router는 기본적으로 앱에 포함되어야 한다.
- SR-021. auth router는 `include_auth_router=True`일 때 포함되어야 한다.
- SR-022. router는 다른 서비스 router와 충돌하지 않도록 독립 prefix/tag 정책을 가져야 한다.

---

## 5. Router 요구사항

### 5.1 Auth router

- SR-030. `POST /token` endpoint를 제공해야 한다.
- SR-031. `/token`은 `OAuth2PasswordRequestForm` 입력을 사용해야 한다.
- SR-032. `/token` 성공 응답은 `TokenResponse`여야 한다.
- SR-033. 인증 실패 시 401과 `WWW-Authenticate: Bearer` 헤더를 반환해야 한다.
- SR-034. `GET /user` endpoint를 제공해야 한다.
- SR-035. `/user` 응답은 `UserInfo`여야 한다.
- SR-036. `/user`는 현재 사용자 dependency를 통해 인증 정보를 해석해야 한다.

### 5.2 Health router

- SR-040. `GET /health/liveness`는 프로세스 자체 생존 여부를 반환해야 한다.
- SR-041. `GET /health/readiness`는 외부 준비 상태를 확인해야 한다.
- SR-042. readiness 실패 시 503을 반환할 수 있어야 한다.
- SR-043. readiness 응답은 `HealthResponse`를 사용해야 한다.
- SR-044. readiness는 `app.state.readiness_checks`와 같은 주입식 확장 지점을 허용해야 한다.

---

## 6. Dependency 요구사항

### 6.1 Config / settings dependency

- SR-050. `get_config()`는 설정 객체를 반환해야 한다.
- SR-051. `get_settings()`는 서비스 설정 객체를 반환해야 한다.
- SR-052. dependency는 FastAPI `Depends(...)`로 바로 사용할 수 있어야 한다.
- SR-053. request context에 app state 설정이 있으면 우선 사용해야 한다.

### 6.2 Auth dependency

- SR-060. `get_auth_provider()`는 앱 상태, `service_clients`, 또는 설정 기반으로 auth provider를 획득해야 한다.
- SR-061. 앱 상태에 provider가 있으면 재사용해야 한다.
- SR-062. 앱 상태에 provider가 없고 `service_clients`에 Keycloak client가 있으면 이를 통해 기본 auth provider를 획득할 수 있어야 한다.
- SR-063. 앱 상태와 `service_clients`에 provider가 모두 없으면 설정 기반 기본 provider를 생성할 수 있어야 한다.

### 6.3 Service client access dependency

- SR-065. 시스템은 서비스가 초기화한 외부 서비스 클라이언트에 접근하기 위한 공통 dependency 또는 표준 접근 경로를 제공해야 한다.
- SR-066. 서비스 클라이언트 접근 경로는 `app.state.service_clients`에 저장된 클라이언트를 우선 재사용해야 한다.
- SR-067. 서비스 클라이언트 접근 경로는 request 처리 중 동일 앱 인스턴스에서 초기화된 클라이언트와 일관된 참조를 제공해야 한다.
- SR-068. 특정 서비스 클라이언트가 활성화되지 않았거나 구성되지 않은 경우, 구현은 명시적 오류 또는 문서화된 비활성 동작으로 처리해야 한다.

### 6.4 Current user dependency

- SR-070. `get_current_user()`는 bearer token을 읽어야 한다.
- SR-071. token이 없으면 401을 반환해야 한다.
- SR-072. token validation 실패를 401로 매핑해야 한다.
- SR-073. validation 결과를 `UserInfo`로 변환해야 한다.
- SR-074. secure decode / insecure decode / introspection 분기 지원 여부는 구현 단계에서 선택될 수 있으나, 외부 계약은 401/성공 변환 동작을 유지해야 한다.

### 6.5 Permission dependency

- SR-080. `require_permissions(*roles)`는 dependency factory여야 한다.
- SR-081. 필요한 role이 없으면 403을 반환해야 한다.
- SR-082. 통과 시 현재 사용자 정보를 그대로 반환할 수 있어야 한다.

---

## 7. Schema 요구사항

### 7.1 `TokenResponse`

- SR-090. `access_token: str`를 포함해야 한다.
- SR-091. `refresh_token: str | None`를 포함할 수 있어야 한다.
- SR-092. `token_type` 기본값은 `bearer`여야 한다.

### 7.2 `UserInfo`

- SR-100. `sub`, `username`을 포함해야 한다.
- SR-101. `email`, `name`은 optional일 수 있어야 한다.
- SR-102. `roles`, `scopes`는 list 기본값을 가져야 한다.

### 7.3 `HealthResponse`

- SR-110. 최소 `status: str` 필드를 포함해야 한다.
- SR-111. 필요 시 `details` 확장 필드를 포함할 수 있어야 한다.

---

## 8. Auth 처리 요구사항

- SR-120. auth router는 Keycloak provider 기반 토큰 발급 경로를 지원해야 한다.
- SR-121. dependency 계층은 bearer token 기반 current user 해석을 지원해야 한다.
- SR-122. 401과 403 오류 경계를 명확히 나눠야 한다.
- SR-123. 오류 메시지는 과도한 민감정보를 노출하면 안 된다.

---

## 9. Health / readiness 요구사항

- SR-130. liveness는 경량이어야 한다.
- SR-131. readiness는 외부 의존성 준비 여부를 확인할 수 있어야 하며, 특정 인증 서비스에만 고정되지 않아야 한다.
- SR-132. readiness는 주입식 check 집계 구조를 지원해야 한다.
- SR-133. 필수 서비스 실패 시 readiness 오류를 HTTP 503으로 매핑 가능해야 한다.
- SR-134. readiness의 필수 서비스 집합을 분리해 표현할 수 있어야 한다.
- SR-135. 선택 서비스 실패만 있을 경우 부분 저하(`degraded`) 상태를 표현할 수 있어야 한다.
- SR-136. readiness는 서비스별 메타데이터(`required`, `enabled`)를 함께 해석할 수 있어야 한다.

---

## 10. Lifespan / startup 요구사항

- SR-140. app factory는 lifespan 주입을 허용해야 한다.
- SR-141. 메시징/NATS 같은 비동기 연결은 startup 단계에서 초기화되거나 공통 `service_clients`/lifespan 흐름에 연결될 수 있어야 한다.
- SR-142. 연결 자원은 shutdown 단계에서 정리할 수 있어야 한다.
- SR-143. FastAPI lifecycle과 외부 의존성 lifecycle이 문서상 명확히 연결되어야 한다.
- SR-144. 전용 메시징 FastAPI dependency가 없더라도 custom lifespan과 `app.state` 확장 지점을 통해 통합 가능해야 한다.

---

## 11. 비기능 요구사항

- NFR-001. FastAPI 서비스가 최소한의 boilerplate로 앱을 조립할 수 있어야 한다.
- NFR-002. dependency는 테스트 대체가 쉬워야 한다.
- NFR-003. 공통 response model은 OpenAPI에 안정적으로 노출 가능해야 한다.
- NFR-004. 인증/설정 오류는 디버깅 가능한 메시지를 제공해야 한다.
- NFR-005. 민감정보는 로그와 오류 detail에 직접 노출되면 안 된다.

---

## 12. 테스트 요구사항

- `POST /token`, `GET /user` 응답 검증
- `GET /health/liveness`, `GET /health/readiness` 응답 검증
- `get_current_user()`의 401 경로 검증
- `require_permissions()`의 403 경로 검증
- `create_app(include_auth_router=False)` 동작 검증
- lifespan 주입 시 startup/shutdown 연결 검증

---

## 13. 구현 상태 메모

이 문서는 목표 계약을 정의한다. 현재 구현 상태는 `docs/api.md`가 authoritative한 현황 문서다.
현재 구현과 비교하면 다음은 SRS 목표 대비 부분 구현 또는 미구현일 수 있다.

- auth 전용 exception handler 등록 방식
- secure/insecure decode / introspection 세부 분기
- 메시징 전용 FastAPI dependency (`get_nats_connection` 등)

---

## 14. 참고 문서

- `docs/prd.md`

---

## 부록 A. 문서 상태 메모

이 문서는 PRD에서 의도적으로 낮춘 capability를 다시 구체 symbol/경로/타입 계약으로 내린 SRS다. 실제 코드와의 차이는 API 문서에서 별도로 관리하며, SRS는 목표 인터페이스 계약을 유지한다.
