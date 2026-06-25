# fastapi-core 소프트웨어 요구사항 정의서 (SRS)

> 문서 목적: `fastapi-core`의 FastAPI 계층을 구현 가능한 요구사항으로 구체화한다.
> 기준 문서: `docs/prd.md`
> 문서 상태: 초안(v0.2)

---

## 1. 문서 개요

- 문서명: `fastapi-core 소프트웨어 요구사항 정의서`
- 작성일: `2026-06-25`
- 작성자: `Hermes Agent 초안 / 사용자 검토 필요`
- 버전: `v0.2`
- 상태: `draft`

### 1.1 목적

본 문서는 `fastapi-core`를 **FastAPI 애플리케이션 조립 라이브러리**로 구현하기 위한 요구사항을 정의한다. 특히 app factory, router, dependency, schema, startup/lifespan, auth 처리, health 처리에 초점을 둔다.

### 1.2 범위

- `create_app(...)`
- auth / health router
- dependency 계층
- response schema
- 설정 연동
- 외부 의존성과 FastAPI lifecycle 결합

---

## 2. 시스템 개요

`fastapi-core`는 두 층으로 이해한다.

1. **인프라 재사용층**: 설정, 인증 provider, 외부 서비스 연결
2. **FastAPI 통합층**: app factory, router, dependency, schema, exception handler

이 문서는 두 번째 층을 중심으로 정의한다.

---

## 3. 아키텍처 요구사항

### 3.1 App factory

- SR-001. 시스템은 `create_app(config=None, settings=None, lifespan=None, include_auth_router=True) -> FastAPI`를 제공해야 한다.
- SR-002. `config is None`이면 기본 환경 설정 객체를 생성해야 한다.
- SR-003. `settings is None`이면 설정 파일 또는 환경기반 서비스 설정을 로딩해야 한다.
- SR-004. 생성된 앱은 `root_path`를 설정할 수 있어야 한다.
- SR-005. 커스텀 lifespan을 주입할 수 있어야 한다.

### 3.2 Middleware / exception handling

- SR-010. 시스템은 CORS middleware를 등록해야 한다.
- SR-011. CORS 설정은 서비스 설정 객체에서 읽어야 한다.
- SR-012. auth 관련 커스텀 예외 핸들러를 등록할 수 있어야 한다.

### 3.3 Router registration

- SR-020. health router는 기본적으로 앱에 포함되어야 한다.
- SR-021. auth router는 `include_auth_router=True`일 때 포함되어야 한다.
- SR-022. router는 다른 서비스 router와 충돌하지 않도록 독립 prefix/tag 정책을 가져야 한다.

---

## 4. Router 요구사항

### 4.1 Auth router

- SR-030. `/token` POST endpoint를 제공해야 한다.
- SR-031. `/token`은 `OAuth2PasswordRequestForm` 입력을 사용해야 한다.
- SR-032. `/token` 성공 응답은 `TokenResponse`여야 한다.
- SR-033. 인증 실패 시 401과 `WWW-Authenticate: Bearer` 헤더를 반환해야 한다.
- SR-034. `/user` GET endpoint를 제공해야 한다.
- SR-035. `/user` 응답은 `UserInfo`여야 한다.

### 4.2 Health router

- SR-040. `/health/liveness`는 프로세스 자체 생존 여부를 반환해야 한다.
- SR-041. `/health/readiness`는 외부 준비 상태를 확인해야 한다.
- SR-042. readiness 실패 시 503을 반환할 수 있어야 한다.
- SR-043. readiness 응답은 `HealthResponse`를 사용해야 한다.

---

## 5. Dependency 요구사항

### 5.1 Config / settings dependency

- SR-050. `get_config()`는 캐시 가능한 설정 객체를 반환해야 한다.
- SR-051. `get_settings()`는 서비스 설정 객체를 반환해야 한다.
- SR-052. dependency는 FastAPI `Depends(...)`로 바로 사용할 수 있어야 한다.

### 5.2 Auth dependency

- SR-060. `get_auth_provider()`는 앱 상태 또는 설정 기반으로 auth provider를 획득해야 한다.
- SR-061. 앱 상태에 provider가 있으면 재사용해야 한다.
- SR-062. 앱 상태에 없으면 설정 기반 기본 provider를 생성해야 한다.

### 5.3 Current user dependency

- SR-070. `get_current_user()`는 bearer token을 읽어야 한다.
- SR-071. token이 없으면 401을 반환해야 한다.
- SR-072. 설정에 따라 secure decode / insecure decode 분기를 지원할 수 있어야 한다.
- SR-073. decode 결과를 `UserInfo`로 변환해야 한다.

### 5.4 Permission dependency

- SR-080. `require_permissions(*roles)`는 dependency factory여야 한다.
- SR-081. 필요한 role이 없으면 403을 반환해야 한다.

---

## 6. Schema 요구사항

### 6.1 `TokenResponse`

- SR-090. `access_token: str`를 포함해야 한다.
- SR-091. `refresh_token: str | None`를 포함할 수 있어야 한다.
- SR-092. `token_type` 기본값은 `bearer`여야 한다.

### 6.2 `UserInfo`

- SR-100. `sub`, `username`을 포함해야 한다.
- SR-101. `email`, `name`은 optional일 수 있어야 한다.
- SR-102. `roles`, `scopes`는 list 기본값을 가져야 한다.

### 6.3 `HealthResponse`

- SR-110. 최소 `status: str` 필드를 포함해야 한다.

---

## 7. Auth 처리 요구사항

- SR-120. auth router는 Keycloak provider 기반으로 토큰 발급을 수행해야 한다.
- SR-121. dependency 계층은 bearer token 기반 current user 해석을 지원해야 한다.
- SR-122. 401과 403 오류 경계를 명확히 나눠야 한다.
- SR-123. 오류 메시지는 과도한 민감정보를 노출하면 안 된다.

---

## 8. Health / readiness 요구사항

- SR-130. liveness는 경량이어야 한다.
- SR-131. readiness는 외부 인증/핵심 의존성 준비 여부를 확인할 수 있어야 한다.
- SR-132. readiness는 network timeout을 명시적으로 가져야 한다.
- SR-133. readiness 오류는 HTTP 503으로 매핑 가능해야 한다.

---

## 9. Lifespan / startup 요구사항

- SR-140. app factory는 lifespan 주입을 허용해야 한다.
- SR-141. 메시징/NATS 같은 비동기 연결은 startup 단계에서 초기화될 수 있어야 한다.
- SR-142. 연결 자원은 shutdown 단계에서 정리할 수 있어야 한다.
- SR-143. FastAPI lifecycle과 외부 의존성 lifecycle이 문서상 명확히 연결되어야 한다.

---

## 10. 비기능 요구사항

- NFR-001. FastAPI 서비스가 최소한의 boilerplate로 앱을 조립할 수 있어야 한다.
- NFR-002. dependency는 테스트 대체가 쉬워야 한다.
- NFR-003. 공통 response model은 OpenAPI에 안정적으로 노출 가능해야 한다.
- NFR-004. 인증/설정 오류는 디버깅 가능한 메시지를 제공해야 한다.
- NFR-005. 민감정보는 로그와 오류 detail에 직접 노출되면 안 된다.

---

## 11. 테스트 요구사항

- auth router `/token`, `/user` 응답 검증
- health router `/health/liveness`, `/health/readiness` 응답 검증
- `get_current_user()`의 401 경로 검증
- `require_permissions()`의 403 경로 검증
- `create_app(include_auth_router=False)` 동작 검증
- lifespan 주입 시 startup/shutdown 연결 검증

---

## 12. 참고 문서

- `docs/prd.md`
- `docs/api.md`
- `docs/config.md`
- `docs/messaging.md`
- `pyproject.toml`

---

## 부록 A. 문서 상태 메모

이 문서는 배포 산출물에서 확인된 `factory.py`, `routers/`, `dependencies/`, `schemas/` 구조를 기준으로 FastAPI 관점으로 재정리했다. 실제 소스 트리가 복원되면 타입명과 예외명, lifecycle 규칙을 코드 기준으로 다시 정렬해야 한다.