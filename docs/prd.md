# fastapi-core 제품 요구사항 정의서 (PRD)

> 문서 목적: `fastapi-core`를 **FastAPI 애플리케이션 조립용 공통 코어**로 정의한다.
> 문서 상태: 초안(v0.2)

---

## 1. 문서 개요

- 문서명: `fastapi-core 제품 요구사항 정의서`
- 작성일: `2026-06-25`
- 작성자: `Hermes Agent 초안 / 사용자 검토 필요`
- 버전: `v0.2`
- 상태: `draft`

### 1.1 배경

`fastapi-core`는 단순한 인프라 SDK 문서 묶음이 아니라, **DocMesh 계열 FastAPI 서비스가 공통으로 사용하는 애플리케이션 코어**여야 한다. 실제 패키지 메타데이터와 배포 산출물 기준으로 이 프로젝트는 FastAPI 의존성을 가지며, `fastapi_core.factory:create_app`를 엔트리포인트로 사용하고, 공통 router / dependency / schema 계층을 포함한다.

즉 이 프로젝트의 핵심 가치는 단순히 Keycloak·DB·NATS 같은 외부 의존성에 연결하는 것이 아니라, 다음을 서비스마다 반복 구현하지 않도록 만드는 데 있다.

- FastAPI 앱 초기화
- 공통 CORS / 예외 핸들러 설정
- 인증 라우터와 헬스 라우터 등록
- 인증 dependency / current user 해석
- Pydantic 응답 스키마 표준화
- startup / shutdown 수명주기와 외부 의존성 연결의 결합

### 1.2 문제 정의

- 서비스마다 `FastAPI()` 초기화와 middleware / router 조립이 중복될 수 있다.
- 인증 라우터(`/token`, `/user`)와 health 라우터(`/health/liveness`, `/health/readiness`)의 동작이 서비스별로 달라질 수 있다.
- `Depends(...)` 기반 인증/설정 dependency가 서비스마다 달라지면 보안과 유지보수 품질이 흔들린다.
- 외부 인프라 연결 규칙은 공유하더라도, FastAPI 계층이 표준화되지 않으면 실제 서비스 개발 생산성은 충분히 올라가지 않는다.

---

## 2. 목표 / 비목표

### 2.1 목표

- FastAPI 서비스가 `create_app(...)` 중심의 공통 앱 조립 경로를 사용할 수 있어야 한다.
- 공통 auth / health router를 재사용 가능해야 한다.
- 공통 dependency(`get_config`, `get_settings`, `get_auth_provider`, `get_current_user`, `require_permissions`)를 제공해야 한다.
- 공통 응답 스키마(`TokenResponse`, `UserInfo`, `HealthResponse`)를 제공해야 한다.
- 설정/인증/메시징/스토리지 같은 인프라 기능이 FastAPI startup/shutdown 및 request lifecycle과 자연스럽게 통합되어야 한다.
- py-core 계층의 재사용과 별개로, FastAPI 서비스 작성자가 바로 사용할 수 있는 **웹 애플리케이션 표면**을 제공해야 한다.

### 2.2 비목표

- 개별 도메인 서비스의 비즈니스 endpoint 제공
- 서비스별 domain schema 전체 통합
- UI / 프론트엔드 제공
- 각 외부 시스템의 전체 관리자 기능 제공
- 모든 조직의 API 정책을 한 번에 일반화하는 것

---

## 3. 대상 사용자 및 이해관계자

### 3.1 대상 사용자

- 1차 사용자: FastAPI 마이크로서비스 개발자
- 2차 사용자: 플랫폼/백엔드 공통 모듈 유지보수자
- 3차 사용자: 운영/QA 담당자

### 3.2 이해관계자

- 백엔드 플랫폼 담당자
- 개별 FastAPI 서비스 개발팀
- 운영/보안 담당자

---

## 4. 제품 범위

### 4.1 포함 범위

- FastAPI 앱 팩토리 제공 (`create_app`)
- CORS middleware 설정
- 공통 auth router 제공
- 공통 health router 제공
- 공통 dependency 제공
- 공통 Pydantic schema 제공
- Keycloak 인증 연동
- 설정 로딩 및 검증
- 서비스별 인프라 연결 보조
- NATS 등 비동기 통합의 startup/lifespan 연계 기반 제공

### 4.2 제외 범위

- 서비스별 비즈니스 라우터 구현
- 서비스별 도메인 모델 정의
- 조직별 API 게이트웨이 정책 구현
- OpenAPI 문서 커스터마이징 전부 자동화

---

## 5. 대표 사용자 시나리오

### 5.1 공통 앱 조립
1. 개발자는 `create_app()`을 호출한다.
2. `fastapi-core`는 설정을 읽고 logging / middleware / exception handler를 등록한다.
3. health router가 기본 포함된다.
4. 옵션에 따라 auth router가 포함된다.
5. 개발자는 여기에 자신의 domain router만 추가한다.

### 5.2 인증 보호 endpoint 작성
1. 개발자는 endpoint에서 `Depends(get_current_user)` 또는 `Depends(require_permissions(...))`를 사용한다.
2. `fastapi-core`는 bearer token을 읽고 검증한다.
3. endpoint는 표준 `UserInfo` 구조를 사용한다.

### 5.3 운영 readiness 확인
1. 운영자는 `/health/liveness`, `/health/readiness`를 호출한다.
2. 서비스는 기본 프로세스 상태와 외부 인증 의존성 준비 여부를 표준 응답으로 제공한다.

### 5.4 startup 연계 메시징/외부 연결
1. 서비스는 startup 단계에서 registry / builder를 이용해 외부 의존성을 준비한다.
2. FastAPI lifespan과 연결되어 정상 종료 시 자원을 정리한다.

---

## 6. 기능 요구사항

### 6.1 FastAPI 앱 팩토리

- FR-001. 시스템은 `create_app(...) -> FastAPI`를 제공해야 한다.
- FR-002. 시스템은 `config`, `settings`, `lifespan`, `include_auth_router`를 입력으로 받을 수 있어야 한다.
- FR-003. 시스템은 CORS middleware를 공통 설정으로 등록해야 한다.
- FR-004. 시스템은 공통 auth 예외 핸들러를 등록할 수 있어야 한다.
- FR-005. 시스템은 health router를 기본 포함해야 한다.
- FR-006. 시스템은 옵션에 따라 auth router를 포함/제외할 수 있어야 한다.

### 6.2 Router

- FR-010. 시스템은 `/token` endpoint를 제공해야 한다.
- FR-011. 시스템은 `/user` endpoint를 제공해야 한다.
- FR-012. 시스템은 `/health/liveness` endpoint를 제공해야 한다.
- FR-013. 시스템은 `/health/readiness` endpoint를 제공해야 한다.

### 6.3 Dependency

- FR-020. 시스템은 `get_config()` dependency를 제공해야 한다.
- FR-021. 시스템은 `get_settings()` dependency를 제공해야 한다.
- FR-022. 시스템은 `get_auth_provider()` dependency를 제공해야 한다.
- FR-023. 시스템은 `get_current_user()` dependency를 제공해야 한다.
- FR-024. 시스템은 `require_permissions(*roles)` dependency factory를 제공해야 한다.

### 6.4 Auth / Security

- FR-030. 시스템은 OAuth2 bearer token 기반 인증 흐름을 제공해야 한다.
- FR-031. 시스템은 token 미제공 시 401을 반환해야 한다.
- FR-032. 시스템은 권한 부족 시 403을 반환해야 한다.
- FR-033. 시스템은 JWT 검증 결과를 표준 사용자 구조로 변환해야 한다.

### 6.5 Schema

- FR-040. 시스템은 `TokenResponse`를 제공해야 한다.
- FR-041. 시스템은 `UserInfo`를 제공해야 한다.
- FR-042. 시스템은 `HealthResponse`를 제공해야 한다.

### 6.6 인프라 연계

- FR-050. 시스템은 외부 의존성 설정 계약을 제공해야 한다.
- FR-051. 시스템은 메시징/NATS 같은 비동기 연결을 FastAPI startup/shutdown 흐름과 연계할 수 있어야 한다.
- FR-052. 시스템은 readiness 판단에 필요한 외부 의존성 점검을 수행할 수 있어야 한다.

---

## 7. 수용 기준

- AC-001. 개발자는 `create_app()`만으로 기본 FastAPI 앱을 만들 수 있어야 한다.
- AC-002. 개발자는 별도 구현 없이 `/health/liveness`와 `/health/readiness`를 사용할 수 있어야 한다.
- AC-003. 개발자는 `Depends(get_current_user)`로 인증된 사용자 정보를 받을 수 있어야 한다.
- AC-004. 개발자는 `require_permissions(...)`로 권한 검사를 재사용할 수 있어야 한다.
- AC-005. auth router 사용 시 `/token`과 `/user` endpoint가 제공되어야 한다.
- AC-006. 공통 schema가 FastAPI response_model로 바로 사용 가능해야 한다.

---

## 8. 제약사항 / 리스크

- 현재 저장소에는 소스 트리 대신 배포 산출물(wheel)이 먼저 존재하므로 문서 정합성은 구현 소스 복원 후 재검증이 필요하다.
- 현재 FastAPI 계층은 Keycloak 중심 auth 및 health 흐름에 초점이 맞춰져 있으며, 일반화 수준은 아직 제한적일 수 있다.
- readiness가 현재 특정 외부 의존성(Keycloak) 중심이면 향후 확장 설계가 필요하다.

---

## 9. 참고 문서

- `README.md`
- `pyproject.toml`
- `docs/srs.md`
- `docs/api.md`
- `docs/config.md`
- `docs/messaging.md`

---

## 부록 A. 문서 상태 메모

이 문서는 `pyproject.toml`과 배포 산출물에 포함된 `fastapi_core.factory`, `routers`, `dependencies`, `schemas` 구조를 기준으로 FastAPI 중심으로 다시 정리했다. 이후 실제 소스 디렉터리가 반영되면 endpoint 계약과 lifespan 규칙을 코드 기준으로 재검증해야 한다.