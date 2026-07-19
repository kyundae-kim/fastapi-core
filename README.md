# fastapi-core

`fastapi-core`는 **DocMesh Py Core 기반 서비스를 FastAPI로 실행하고 노출하기 위한 공통 컴포넌트**입니다.
앱 factory, 인증·인가, health endpoint, 서비스 client dependency, 오류 응답, 요청 추적, readiness와 자원 lifecycle을 하나의 FastAPI 애플리케이션 표면으로 제공합니다.

현재 구현된 핵심 범위:
- package root export: `create_app`, `ManagedResource`, `ResourceKey`, `ReadinessCheckSpec`, `register_readiness_check`, `ErrorMapping`, `ErrorRenderer`, `register_error_mapper`
- auth router: `POST /token`, `GET /user`
- health router: `GET /health/liveness`, `GET /health/readiness`
- dependency: 앱 설정/runtime, Keycloak·PostgreSQL·SQLite·MinIO·Milvus·Ollama·Langfuse·NATS client, managed resource, 현재 사용자와 권한 검사
- schema: `TokenResponse`, `UserInfo`, `HealthResponse`, `HealthServiceDetail`, `ProblemDetail`
- runtime extension: managed resource 생성·조회·readiness 등록·역순 종료
- HTTP contract: 앱별 OAuth2 scheme, `X-Correlation-ID`, RFC 7807 problem details, domain error mapper
- app state integration: `config`, `root_logger`, `service_runtime`, `readiness_registry`, `resource_registry`, `oauth2_scheme`, `error_renderer`, `auth_provider`(Keycloak 활성 시)

외부 연동은 `docmesh_py_core`를 통해 이어집니다.
- 인증/인가: Keycloak
- 데이터 저장소: PostgreSQL / SQLite
- 오브젝트 스토리지: MinIO
- 벡터 DB: Milvus
- 로컬 LLM: Ollama
- 관측/트레이싱: Langfuse
- 메시징: NATS

## Entry point

```toml
[tool.fastapi]
entrypoint = "fastapi_core.factory:create_app"
```

권장 최상위 API는 `fastapi_core.__all__`, FastAPI dependency와 schema는 각각 `fastapi_core.dependencies.__all__`, `fastapi_core.schemas.__all__`에서 확인할 수 있습니다.

## 설치

### 요구사항

- Python `>=3.11`
- [uv](https://docs.astral.sh/uv/)

### 저장소에서 개발 환경 구성

저장소 루트에서 아래 명령을 실행합니다. `uv`가 런타임 의존성과 `dev` dependency group을 함께 설치하고, 로컬 패키지를 editable 방식으로 사용할 수 있게 구성합니다.

```bash
uv sync --all-groups
```

설치 확인:

```bash
uv run python -c "from fastapi_core import create_app; print(create_app)"
```

### 다른 uv 프로젝트에서 로컬 의존성으로 사용

소비하는 서비스 프로젝트에서 로컬 checkout 경로를 editable dependency로 추가할 수 있습니다.

```bash
uv add --editable ../fastapi-core
```

### GitHub에서 uv로 설치

GitHub 저장소를 직접 dependency로 추가하려면 소비하는 프로젝트에서 다음 명령을 실행합니다.

```bash
uv add "fastapi-core @ git+https://github.com/kyundae-kim/fastapi-core.git"
```

재현 가능한 배포에서는 기본 브랜치 대신 tag 또는 commit을 고정합니다.

```bash
uv add "git+https://github.com/kyundae-kim/fastapi-core.git@v0.4.0"
```

앱 설정은 `.env` 파일을 자동으로 읽지 않고 프로세스 환경변수에서 읽습니다. `.env.example`은 설정 키의 예시이며, 컨테이너 환경·배포 플랫폼·실행 도구를 통해 필요한 값을 환경변수로 주입해야 합니다. 상세 계약은 `docs/config.md`를 참고하세요.

## Quick start

### 서비스 없는 최소 앱

```python
from fastapi_core import create_app
from fastapi_core.config import AppConfig

app = create_app(
    config=AppConfig(enabled_services=[], required_services=[]),
    include_auth_router=False,
)
```

실행:

```bash
uv run fastapi dev main.py
curl -i http://127.0.0.1:8000/health/liveness
curl -i http://127.0.0.1:8000/health/readiness
```

기본 설정은 Keycloak을 활성·필수 서비스로 사용합니다. 기본 `create_app()`을 실행하려면 `.env.example`과 `docs/config.md`를 참고해 Keycloak 환경변수를 프로세스에 주입해야 합니다. 인증 router만 제외하려면 다음과 같이 구성합니다.

```python
app = create_app(include_auth_router=False)
```

### 현재 사용자 주입

```python
from fastapi import APIRouter, Depends
from docmesh_py_core import AuthenticatedUser
from fastapi_core.dependencies.auth import get_current_user

router = APIRouter()

@router.get("/me")
async def me(
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, str]:
    return {"sub": user.sub, "username": user.preferred_username or user.sub}
```

더 많은 예제는 `docs/examples.md`를 참고하세요.

## 현재 구현 동작

### `create_app(...)`
- `config is None`이면 `load_app_config()`를 사용합니다.
- `runtime is None`이면 lifespan startup에서 환경 기반 `ServiceRuntime`을 조립합니다.
- 명시적 `runtime`을 전달하면 완성된 `ServiceRuntime`을 재조립하지 않고 동일한 lifecycle과 app state에 연결합니다.
- startup healthcheck의 failure mode, 재시도 횟수와 재시도 간격은 자동 조립 runtime과 명시적으로 주입한 runtime에 동일하게 적용됩니다.
- 앱 로깅을 먼저 초기화합니다.
- `FastAPI(root_path=..., lifespan=...)`를 생성하고 framework lifespan이 runtime과 managed resource의 정리를 소유합니다.
- `app.state.config`, `app.state.root_logger`, `app.state.service_runtime`, `app.state.readiness_registry`, `app.state.resource_registry`를 저장합니다. Keycloak client가 구성되면 `app.state.auth_provider`도 저장합니다.
- 앱별 readiness/resource registry를 초기화합니다. readiness 확장은 typed registry API만 사용합니다.
- `resources=[ManagedResource(...)]`로 서비스 고유 자원을 startup/readiness/shutdown 흐름에 연결합니다.
- per-service/overall readiness timeout을 `AppConfig`와 startup runtime check에 동일하게 적용합니다.
- `service_alternatives`가 있으면 각 그룹에서 최소 한 서비스가 구성됐는지 `one_of` 정책으로 검증합니다.
- 앱별 OAuth2 password flow에 `config.token_url`을 반영합니다.
- CORS, correlation ID middleware와 problem detail handler를 등록합니다.
- health router를 기본 포함하고, `include_auth_router=True`일 때 auth router를 포함합니다.

### 인증
- `/token`은 `OAuth2PasswordRequestForm`을 받습니다.
- 현재 구현은 `scope`, `username`, `password`를 provider의 `fetch_access_token(...)`에 직접 전달합니다.
- provider 예외는 유형에 따라 `401`, `500`, `503`, `502/500`으로 매핑되며, 실패 응답에는 `WWW-Authenticate: Bearer` 헤더가 포함됩니다.
- `get_current_user()`는 bearer token을 읽고 provider의 `AuthenticatedUser`를 정보 손실 없이 그대로 반환합니다. `/user` endpoint에서만 공개 응답 DTO인 `UserInfo`로 변환합니다.
- role은 `AuthenticatedUser.realm_roles/client_roles`, scope는 `claims["scope"]`를 기준으로 검사합니다. `require_roles(...)`, `require_scopes(...)`, `require_permissions(...)`도 같은 `AuthenticatedUser`를 반환합니다.
- 각 앱은 자신의 OAuth2 scheme과 token URL을 유지하므로 multi-app OpenAPI 구성이 서로 영향을 주지 않습니다.

### 헬스체크
- `/health/liveness`는 `{"status": "ok", "details": null}`를 반환합니다.
- `/health/readiness`는 `app.state.readiness_registry`와 `app.state.config`를 사용합니다.
- 기본 `create_app()` 경로에서는 조립된 runtime client의 readiness check를 자동 등록합니다.
- sync/async readiness check를 함께 실행할 수 있으며 필수 실패 시에도 전체 서비스 details를 보존합니다.
- per-service timeout은 해당 서비스 실패로 변환되고, overall timeout은 `503 + status="error"`로 반환됩니다.
- 필수 서비스 실패 시 `503`, 선택 서비스만 실패 시 `200 + degraded`, 모두 성공 시 `200 + ok`를 반환합니다.
- readiness 로그는 구조화된 이벤트로 남기며, 오류 문자열은 상위 `docmesh_py_core` 마스킹 정책 영향을 받습니다.
- 사용자 정의 check는 `register_readiness_check(...)`로 등록하며 check별 required/timeout/error redaction을 적용할 수 있습니다.

## App config

`fastapi_core.config.AppConfig` 주요 필드:
- `root_path: str = ""`
- `token_url: str = "/token"`
- `cors_origins: list[str] = ["*"]`
- `cors_credentials: bool = False`
- `readiness_parallel: bool = False`
- `readiness_timeout_seconds: float | None = None`
- `readiness_overall_timeout_seconds: float | None = None`
- `service_alternatives: list[list[str]] = []`
- `startup_healthcheck: bool = False`
- `startup_failure_mode: StartupFailureMode = StartupFailureMode.FAIL`
- `startup_healthcheck_attempts: int = 1`
- `startup_healthcheck_retry_delay_seconds: float = 0`
- `log_level: str | None = "WARNING"`
- `log_path: str | None = None`
- `log_json: bool = True`
- `log_force: bool = False`
- `enabled_services: list[str] = ["keycloak"]`
- `required_services: list[str] = ["keycloak"]`

주요 환경변수:
- `ROOT_PATH`
- `TOKEN_URL`
- `CORS_ORIGINS`
- `CORS_CREDENTIALS`
- `READINESS_PARALLEL`
- `READINESS_TIMEOUT_SECONDS`
- `READINESS_OVERALL_TIMEOUT_SECONDS`
- `DOCMESH_SERVICE_ALTERNATIVES`
- `DOCMESH_HEALTHCHECK_ENABLED`
- `DOCMESH_STARTUP_FAILURE_MODE`
- `DOCMESH_STARTUP_HEALTHCHECK_ATTEMPTS`
- `DOCMESH_STARTUP_HEALTHCHECK_RETRY_DELAY_SECONDS`
- `DOCMESH_LOG_LEVEL`
- `APP_LOG_PATH`
- `APP_LOG_JSON`
- `APP_LOG_FORCE`
- `DOCMESH_SERVICES`
- `READINESS_REQUIRED_SERVICES`

## 서비스 client dependency

`fastapi_core.dependencies`는 `ServiceRuntime`을 유일한 서비스 상태 소유자로 사용합니다.

- 공통 접근: `get_service_runtime`, `get_settings`, `get_service_client(name)`
- typed 접근: `get_keycloak_auth_service`, `get_postgres_engine`, `get_sqlite_engine`, `get_minio_client`, `get_milvus_client`, `get_ollama_client`, `get_langfuse_client`, `get_nats_connection_builder`
- 서비스 미활성 또는 runtime 미준비: `503 Service Unavailable`
- 예상 wrapper/client 타입 불일치: `500 Internal Server Error`

폐기된 `app.state.settings`나 `app.state.service_clients`에 직접 의존하지 않습니다. 서비스별 사용 예제는 `docs/examples.md`를 참고하세요.

## 운영 시 주의사항

- HTTP, validation, auth/permission, 미처리 오류는 correlation ID가 포함된 `ProblemDetail` 응답으로 정규화됩니다. 서비스별 domain 오류는 `register_error_mapper(...)`로 같은 형식에 연결합니다.
- `TOKEN_URL`은 OpenAPI OAuth2 scheme의 token URL만 변경하며 내장 `POST /token` route path는 변경하지 않습니다.
- `.env.example`은 자동으로 로드되지 않습니다. shell, 컨테이너, 배포 플랫폼 또는 별도 dotenv loader로 값을 프로세스 환경에 주입해야 합니다.
- 외부 서비스 통합 테스트에는 `pytest.mark.integration`이 지정됩니다. 필요한 환경변수나 대상 서비스가 없으면 skip됩니다.

## 문서

- 제품 요구사항: `docs/prd.md`
- API Reference: `docs/api.md`
- 설정 정의: `docs/config.md`
- 예제: `docs/examples.md`

## 개발 및 검증

현재 저장소 기준 검증 명령:

```bash
uv run pytest -q
```
