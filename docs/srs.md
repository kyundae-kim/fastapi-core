# fastapi-core 소프트웨어 요구사항 정의서 (SRS)

> 문서 목적: `fastapi-core`를 **DocMesh Py Core 기반 서비스를 FastAPI 환경에서 동작시키기 위한 기능을 제공하는 FastAPI 컴포넌트**로 구현하기 위한 요구사항과 공개 인터페이스 계약으로 구체화한다.
> 기준 문서: `docs/prd.md`
> 문서 상태: 구현 계약 반영본

---

## 1. 문서 개요

- 문서명: `fastapi-core 소프트웨어 요구사항 정의서`
- 작성일: `2026-07-03`
- 작성자: `Hermes Agent`
- 상태: `aligned-to-source`

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
- runtime extension: `ManagedResource`, `ResourceKey[T]`, `ReadinessCheckSpec`, `register_readiness_check(...)`, `ErrorMapping`, `ErrorRenderer`, `register_error_mapper(...)`
- dependency: `get_config()`, `get_settings()`, `get_auth_provider()`, `get_resource(name)`, `get_service_client(service_name)`, `get_keycloak_auth_service()`, `get_postgres_engine()`, `get_sqlite_engine()`, `get_minio_client()`, `get_milvus_client()`, `get_ollama_client()`, `get_langfuse_client()`, `get_nats_connection_builder()`, `get_current_user()`, `require_roles(...)`, `require_scopes(...)`, `require_permissions(...)`
- schema: `TokenResponse`, `UserInfo`, `HealthResponse`, `ProblemDetail`
- endpoint: `/token`, `/user`, `/health/liveness`, `/health/readiness`

주의:
- 이 목록은 **패키지 루트 re-export 목록**이 아니라, SRS가 계약 대상으로 다루는 공개 FastAPI 표면을 뜻한다.
- package-root import 보장 범위는 구현 시점의 API 문서(`docs/api.md`)를 따른다.

### 3.3 공개 시그니처

아래 시그니처는 lifecycle/readiness와 오류 확장의 공개 계약이다. 실제 import 경로는 `docs/api.md`에 반영한다.

```python
@dataclass(frozen=True)
class ReadinessCheckSpec:
    name: str
    check: Callable[[], object | Awaitable[object]]
    required: bool = True
    timeout_seconds: float | None = None
    redact_errors: bool = True


@dataclass(frozen=True)
class ManagedResource(Generic[T]):
    name: str | ResourceKey[T]
    factory: Callable[[FastAPI], T | Awaitable[T]]
    healthcheck: Callable[[T], object | Awaitable[object]] | None = None
    close: Callable[[T], None | Awaitable[None]] | None = None
    required: bool = True
    readiness_timeout_seconds: float | None = None
    redact_errors: bool = True


def register_readiness_check(
    app: FastAPI,
    name: str,
    check: Callable[[], object | Awaitable[object]],
    *,
    required: bool = True,
    timeout_seconds: float | None = None,
    redact_errors: bool = True,
) -> None: ...


@dataclass(frozen=True)
class ResourceKey(Generic[T]):
    name: str

    def dependency(self, request: Request) -> T: ...


def get_resource(name: str) -> Callable[[Request], Any]: ...


@dataclass(frozen=True)
class ErrorMapping:
    status_code: int
    detail: str
    title: str | None = None
    type_uri: str = "about:blank"
    headers: dict[str, str] | None = None
    code: str | None = None
    extensions: dict[str, object] | None = None


ErrorRenderer = Callable[
    [Request, ErrorMapping],
    Response | Awaitable[Response],
]


def register_error_mapper(
    app: FastAPI,
    exception_type: type[Exception],
    mapper: Callable[[Request, Exception], ErrorMapping | Awaitable[ErrorMapping]],
) -> None: ...


def require_roles(*roles: str) -> Callable[..., UserInfo]: ...
def require_scopes(*scopes: str) -> Callable[..., UserInfo]: ...
def require_permissions(*permissions: str) -> Callable[..., UserInfo]: ...
```

`create_app(..., resources=(), error_renderer=None)`는 `ManagedResource` 목록을 공통 lifecycle/readiness registry에 연결하고 선택적 앱 단위 오류 renderer를 설치한다. 반환 객체는 plain `FastAPI` 계약을 유지하므로, 런타임에 동적으로 `app.register_readiness_check` 메서드를 추가하는 방식은 공개 계약으로 사용하지 않는다.

### 3.4 리팩토링 보호 계약

코드 크기 축소 리팩토링은 다음 공개 표면을 보호해야 한다.

- package root `fastapi_core`: `ErrorMapping`, `ErrorRenderer`, `ManagedResource`, `ReadinessCheckSpec`, `ResourceKey`, `create_app`, `register_error_mapper`, `register_readiness_check`
- `fastapi_core.dependencies`: 3.2에 열거한 config/auth/resource/service/authorization dependency
- `fastapi_core.schemas`: `HealthResponse`, `HealthServiceDetail`, `ProblemDetail`, `TokenResponse`, `UserInfo`
- endpoint: `POST /token`, `GET /user`, `GET /health/liveness`, `GET /health/readiness`
- `create_app(...)` 및 3.3 runtime extension 함수·dataclass의 parameter/field/default 계약

공개 표면의 추가·삭제·시그니처 변경은 단순 내부 리팩토링으로 처리하지 않는다. SRS와 API 문서, 공개 API 회귀 테스트를 같은 변경에서 명시적으로 갱신해야 한다.

readiness 확장은 `app.state.readiness_registry`를 단일 source of truth로 사용한다. 제거된 `app.state.readiness_checks`, `app.state.readiness_services`, `app.state.required_services` compatibility alias는 제공하지 않는다. 애플리케이션 코드는 `register_readiness_check(...)`, `ReadinessCheckSpec`, `ManagedResource`를 사용해야 한다.

---

## 4. 아키텍처 요구사항

### 4.1 App factory

- SR-001. 시스템은 `create_app(config=None, settings=None, lifespan=None, include_auth_router=True, resources=(), error_renderer=None) -> FastAPI`를 제공해야 한다.
- SR-002. `config is None`이면 기본 환경 설정 객체를 생성해야 한다.
- SR-003. `settings is None`이면 환경기반 서비스 설정을 로딩해야 한다.
- SR-004. 생성된 앱은 `root_path`를 설정할 수 있어야 한다.
- SR-005. 커스텀 lifespan을 주입할 수 있어야 한다.
- SR-006. 생성된 앱은 `app.state.config`, `app.state.settings`, `app.state.service_clients`, `app.state.root_logger`를 저장해야 한다.
- SR-006A. Keycloak 서비스가 활성화된 경우 생성된 앱은 `app.state.auth_provider`에 현재 auth provider를 저장하거나 재사용할 수 있어야 한다.
- SR-007. 시스템은 readiness 실행 옵션과 등록 정보를 앱 인스턴스별 registry에 유지해야 하며, 애플리케이션 코드에 내부 dict/set 조작을 요구하면 안 된다.
- SR-008. 시스템은 `app.state.service_clients`와 lifespan 경로를 통해 외부 의존성 정리와 readiness 구성을 연결할 수 있어야 한다.
- SR-009. `resources`는 `Sequence[ManagedResource[Any]]`를 받아야 하며, 애플리케이션 코드는 내부 resource/readiness state 컨테이너의 구조에 의존하지 않아야 한다.
- SR-009A. 앱은 `app.state.oauth2_scheme`에 자신의 `token_url`로 생성된 OAuth2 scheme을 보관하고 전역 scheme metadata를 변경하지 않아야 한다.
- SR-009B. 같은 프로세스에서 서로 다른 `token_url`을 사용하는 앱의 OpenAPI security schema는 서로 독립적이어야 한다.

### 4.2 Middleware / exception handling

- SR-010. 시스템은 CORS middleware를 등록해야 한다.
- SR-011. CORS 설정은 앱 설정 객체에서 읽어야 한다.
- SR-012. 인증 관련 오류는 일관된 HTTP 예외 정책으로 반환되어야 한다.
- SR-013. 기본 renderer에서 `HTTPException`, `RequestValidationError`, 미처리 `Exception`은 `ProblemDetail` 응답으로 변환해야 한다.
- SR-014. 모든 HTTP 요청은 `X-Correlation-ID`를 요청 상태와 응답 헤더에서 사용할 수 있어야 한다.
- SR-015. correlation ID는 `[A-Za-z0-9._:-]{1,128}`을 만족하는 입력만 신뢰하고 나머지는 32자리 hexadecimal UUID로 교체해야 한다.
- SR-016. 기본 문제 상세 renderer는 `application/problem+json` media type을 사용해야 한다.
- SR-017. HTTP 예외의 응답 header는 문제 상세 변환 후에도 보존해야 한다.
- SR-018. 외부 오류 detail은 `mask_sensitive_value(...)` 정책을 적용하고 미처리 예외 원문은 응답에 포함하지 않아야 한다.
- SR-019. `register_error_mapper(...)`는 서비스별 예외를 같은 문제 상세 응답으로 변환하는 sync/async mapper를 등록할 수 있어야 한다.
- SR-019A. `create_app(..., error_renderer=...)`는 HTTP, validation, domain, 미처리 오류의 최종 media type과 envelope를 앱 단위로 교체할 수 있어야 한다.
- SR-019B. custom renderer 호출 전 오류 detail 마스킹과 correlation ID 설정은 공통 계층에서 완료되어야 한다.
- SR-019C. `ErrorMapping`은 서비스 오류 code와 안전한 확장 metadata를 renderer에 전달할 수 있어야 한다.

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
- SR-044. readiness는 서비스 기본 check와 애플리케이션 사용자 정의 check를 동일한 registry에서 집계할 수 있어야 한다.
- SR-045. 사용자 정의 readiness 확장의 공개 계약은 `register_readiness_check(...)` 및 `ReadinessCheckSpec`이어야 하며, 제거된 legacy readiness state alias는 제공하지 않아야 한다.
- SR-046. 사용자 정의 readiness check는 sync/async callable을 모두 허용해야 한다.
- SR-047. check별 `required`, `timeout_seconds`, `redact_errors` 정책을 표현할 수 있어야 한다.
- SR-048. check별 timeout이 생략되면 `AppConfig.readiness_timeout_seconds`를 사용해야 한다.
- SR-049. 등록 이름이 중복되면 마지막 값으로 조용히 덮어쓰지 않고 명시적 설정 오류를 발생시켜야 한다.
- SR-049A. readiness check 반환값 `None`과 `True`는 성공, `False`는 실패로 판정해야 한다.
- SR-049B. readiness check가 `HealthCheckResult`를 반환하면 `ok`와 서비스별 결과를 판정에 반영해야 한다.
- SR-049C. 구조화 결과의 서비스 이름은 `<등록 이름>.<서비스 이름>`으로 namespace하여 응답에 보존해야 한다.

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

### 6.3A Managed resource access dependency

- SR-068A. `get_resource(name)`는 managed resource를 request 처리 계층에 주입하기 위한 dependency factory여야 한다.
- SR-068B. `get_resource(name)`는 동일 앱 lifecycle에서 생성된 객체와 동일한 참조를 반환해야 한다.
- SR-068C. 요청한 resource가 등록되지 않았거나 아직 사용할 수 없으면 문서화된 명시적 오류를 반환해야 한다.
- SR-068D. route 코드는 managed resource를 조회하기 위해 `app.state.<resource_name>` 또는 내부 registry dict를 직접 읽을 필요가 없어야 한다.
- SR-068E. `ResourceKey[T]`는 같은 typed key를 managed resource 등록과 route dependency에 재사용할 수 있어야 한다.

### 6.4 Current user dependency

- SR-070. `get_current_user()`는 bearer token을 읽어야 한다.
- SR-071. token이 없으면 401을 반환해야 한다.
- SR-072. token validation 실패를 401로 매핑해야 한다.
- SR-073. validation 결과를 `UserInfo`로 변환해야 한다.
- SR-074. secure decode / insecure decode / introspection 분기 지원 여부는 구현 단계에서 선택될 수 있으나, 외부 계약은 401/성공 변환 동작을 유지해야 한다.

### 6.5 Permission dependency

- SR-080. `require_roles(*roles)`, `require_scopes(*scopes)`, `require_permissions(*permissions)`는 dependency factory여야 한다.
- SR-081. `require_roles`는 `UserInfo.roles`, `require_scopes`는 `UserInfo.scopes`, `require_permissions`는 두 집합의 합집합을 검사해야 한다.
- SR-082. 필요한 값이 없으면 403을 반환하고 통과 시 현재 사용자 정보를 그대로 반환해야 한다.
- SR-083. `require_scopes`가 선언한 scope는 OpenAPI operation security requirement에 반영되어야 한다.

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

### 7.4 `ProblemDetail`

- SR-112. `type`, `title`, `status`, `detail`, `instance`, `correlation_id`를 포함해야 한다.
- SR-113. 기본 `type`은 `about:blank`여야 한다.
- SR-114. HTTP 표준 상태가 아닌 status code는 안정된 fallback title을 사용해야 한다.

---

## 8. Auth 처리 요구사항

- SR-120. auth router는 Keycloak provider 기반 토큰 발급 경로를 지원해야 한다.
- SR-121. dependency 계층은 bearer token 기반 current user 해석을 지원해야 한다.
- SR-122. 401과 403 오류 경계를 명확히 나눠야 한다.
- SR-123. 오류 메시지는 과도한 민감정보를 노출하면 안 된다.
- SR-124. OAuth2 password scheme은 앱별 객체로 생성되어 `app.state.oauth2_scheme`에 저장되어야 한다.
- SR-125. 전역 dependency key는 앱별 scheme으로 override할 수 있지만 전역 scheme model 자체를 변경하면 안 된다.

---

## 9. Health / readiness 요구사항

- SR-130. liveness는 경량이어야 한다.
- SR-131. readiness는 외부 의존성 준비 여부를 확인할 수 있어야 하며, 특정 인증 서비스에만 고정되지 않아야 한다.
- SR-132. readiness는 주입식 check 집계 구조를 지원해야 한다.
- SR-133. 필수 서비스 실패 시 readiness 오류를 HTTP 503으로 매핑 가능해야 한다.
- SR-134. readiness의 필수 서비스 집합을 분리해 표현할 수 있어야 한다.
- SR-135. 선택 서비스 실패만 있을 경우 부분 저하(`degraded`) 상태를 표현할 수 있어야 한다.
- SR-136. readiness는 서비스별 메타데이터(`required`, `enabled`)를 함께 해석할 수 있어야 한다.
- SR-137. readiness는 sync/async check를 native async 집계 경로에서 실행하고, 필수 서비스 실패 시에도 전체 서비스 결과를 보존해야 한다.
- SR-138. 등록된 check에서 발생한 예외는 readiness 응답 상태로 정규화되어야 하며 endpoint 밖으로 원문 예외가 누출되면 안 된다.
- SR-139. `redact_errors=True`인 check의 외부 응답에는 민감한 원문 오류를 노출하지 않아야 하며, 구조화 로그에도 공통 마스킹 정책을 적용해야 한다.
- SR-139A. 선택 check만 실패하면 `200 + degraded`, 필수 check가 실패하면 `503 + error`라는 기존 정책을 사용자 정의 check에도 동일하게 적용해야 한다.
- SR-139B. 구조화 check 결과의 하위 서비스는 부모 check의 required/redaction 정책을 상속해야 한다.

---

## 10. Lifespan / startup 요구사항

- SR-140. app factory는 lifespan 주입을 허용해야 한다.
- SR-141. 메시징/NATS 같은 비동기 연결은 startup 단계에서 초기화되거나 공통 `service_clients`/lifespan 흐름에 연결될 수 있어야 한다.
- SR-142. sync/async 연결 자원은 shutdown 단계에서 await 가능한 공통 정리 경로로 정리되어야 한다.
- SR-143. FastAPI lifecycle과 외부 의존성 lifecycle이 문서상 명확히 연결되어야 한다.
- SR-144. 전용 메시징 FastAPI dependency가 없더라도 custom lifespan과 `app.state` 확장 지점을 통해 통합 가능해야 한다.
- SR-145. custom lifespan shutdown이 실패하더라도 공통 service client 정리는 `finally` 경로에서 실행되어야 한다.
- SR-146. 기본 앱 경로는 `assemble_service_runtime(...)`으로 설정 탐색, required 검증, client 조립을 수행하고 runtime을 `app.state.service_runtime`에 노출해야 한다.
- SR-147. `DOCMESH_HEALTHCHECK_ENABLED`는 명시적 startup healthcheck 정책으로 연결되어야 하며 기본값은 비활성화여야 한다.
- SR-148. 서비스 설정 mapping 로딩은 프로세스 `os.environ`을 변경하지 않아야 한다.
- SR-149. 서비스별 및 전체 healthcheck timeout은 startup check와 readiness endpoint에 동일하게 적용되어야 한다.
- SR-150. overall readiness timeout은 HTTP 503 오류 응답으로 정규화되어야 한다.
- SR-151. 서비스 대안 그룹은 assembly `one_of` 정책으로 검증되어야 한다.
- SR-152. startup healthcheck 실패 시 조립된 서비스 client는 custom lifespan 진입 전에 rollback되어야 한다.
- SR-153. service runtime 종료 실패는 민감정보 없는 구조화 이벤트로 기록하고 `ServiceCloseError`로 전파해야 한다.

### 10.1 Managed resource lifecycle

- SR-154. `ManagedResource[T]`는 최소 `str | ResourceKey[T]` 이름, `factory`, 선택적 `healthcheck`, 선택적 `close`, `required`, 선택적 readiness timeout과 오류 마스킹 정책을 표현해야 한다.
- SR-155. `factory`는 `FastAPI`를 입력으로 받아 `T` 또는 `Awaitable[T]`를 반환할 수 있어야 한다.
- SR-156. 명시적 `close`는 생성된 resource를 입력으로 받아 sync/async 정리를 모두 지원해야 한다.
- SR-157. 명시적 `close`가 없으면 구현은 `aclose()` 후 `close()` 순서로 지원 프로토콜을 탐색하고, 어느 것도 없으면 정리가 필요 없는 resource로 취급해야 한다.
- SR-158. managed resource는 선언 순서로 생성하고 생성의 역순으로 종료해야 한다.
- SR-159. resource factory 또는 startup healthcheck가 실패하면 실패 전에 생성된 managed resource를 역순으로 rollback해야 한다.
- SR-160. managed resource startup은 공통 service runtime 준비 후, 사용자 custom lifespan 진입 전에 완료되어야 한다.
- SR-161. 사용자 custom lifespan shutdown은 managed resource shutdown보다 먼저 실행되어야 한다.
- SR-162. healthcheck가 지정된 managed resource는 생성 성공 후 public readiness registry에 자동 등록되어야 한다.
- SR-162A. `AppConfig.startup_healthcheck=True`이면 required managed resource의 healthcheck도 custom lifespan 진입 전에 실행해야 한다.
- SR-163. 동일한 resource 이름, 빈 이름 또는 framework 예약 이름은 startup 전에 명시적 설정 오류로 거부해야 한다.

### 10.2 설정 검증

- SR-164. `AppConfig.required_services`는 `AppConfig.enabled_services`의 부분집합이어야 한다.
- SR-165. SR-164 위반은 readiness check에서 조용히 누락하지 않고 앱 생성 또는 startup 전에 명시적 설정 오류로 처리해야 한다.
- SR-166. `CORS_ORIGINS`, `DOCMESH_SERVICES`, `READINESS_REQUIRED_SERVICES`가 환경에 존재하지 않으면 각 필드의 문서화된 기본값을 적용해야 한다.
- SR-167. 위 목록형 환경변수가 명시적으로 빈 문자열이면 빈 목록으로 해석해야 하며 기본값을 복원하면 안 된다.
- SR-168. 코드에서 잘못된 타입을 직접 전달한 경우에는 환경변수 빈 문자열 정규화와 구분하여 Pydantic validation error를 유지해야 한다.

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
- async service client close가 await되는지 검증
- custom lifespan shutdown 실패 시에도 공통 client가 정리되는지 검증
- 필수 readiness 실패 응답에 전체 서비스 결과가 보존되는지 검증
- public readiness 등록 API가 sync/async check와 required/optional 상태 정책을 적용하는지 검증
- check별 timeout fallback과 오류 마스킹을 검증
- managed resource의 선언 순서 startup, 역순 shutdown, 부분 startup 실패 rollback을 검증
- managed resource healthcheck 자동 등록과 `get_resource(name)` 동일 참조 반환을 검증
- duplicate/reserved resource 및 readiness 이름이 명시적 오류를 발생시키는지 검증
- required service가 enabled service에 없으면 앱 생성 또는 startup이 실패하는지 검증
- 목록형 환경변수의 미설정 기본값과 명시적 빈 목록 의미를 각각 검증
- 서로 다른 `token_url`의 두 앱에서 OpenAPI security schema가 격리되는지 검증
- role, scope, 통합 permission dependency의 성공/403 및 scope OpenAPI 선언을 검증
- 유효/무효 correlation ID의 request state와 response header 전파를 검증
- HTTP, validation, 미처리 예외의 `ProblemDetail` 변환과 민감정보 마스킹을 검증
- custom sync/async error mapper가 표준 문제 상세 응답을 생성하는지 검증
- `False` 및 실패 `HealthCheckResult` 반환이 required readiness 실패로 판정되는지 검증
- 구조화 readiness 서비스 상태가 namespace와 부모 required/redaction 정책을 보존하는지 검증
- custom sync/async error renderer가 domain/validation 오류 envelope를 교체하면서 detail 마스킹과 correlation ID를 유지하는지 검증
- `ResourceKey[T]` 하나를 등록과 typed dependency에 함께 사용하는 경로를 검증

---

## 13. 구현 상태 메모

이 문서는 목표 계약을 정의한다. 현재 구현 상태는 `docs/api.md`가 authoritative한 현황 문서다.
현재 구현과 비교하면 다음은 SRS 목표 대비 부분 구현 또는 미구현일 수 있다.

- secure/insecure decode / introspection 세부 분기
- 메시징 전용 FastAPI dependency (`get_nats_connection` 등)


---

## 14. 참고 문서

- `docs/prd.md`

---

## 부록 A. 문서 상태 메모

이 문서는 PRD에서 의도적으로 낮춘 capability를 다시 구체 symbol/경로/타입 계약으로 내린 SRS다. 실제 코드와의 차이는 API 문서에서 별도로 관리하며, SRS는 목표 인터페이스 계약을 유지한다.
