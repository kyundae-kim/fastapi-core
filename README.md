# fastapi-core

DocMesh 프로젝트의 FastAPI 기반 마이크로서비스가 공통으로 사용하는 Python SDK입니다.
`fastapi-core`는 단순 인프라 클라이언트 모음이 아니라, **공통 FastAPI 앱 표면**을 제공하는 데 초점을 둡니다.

현재 구현된 핵심 범위:
- package root export: `fastapi_core.create_app`
- auth router: `POST /token`, `GET /user`
- health router: `GET /health/liveness`, `GET /health/readiness`
- dependency: `get_config`, `get_settings`, `get_auth_provider`, `get_current_user`, `require_permissions`
- schema: `TokenResponse`, `UserInfo`, `HealthResponse`, `HealthServiceDetail`
- app state integration: `config`, `root_logger`, `settings`, `service_clients`, `auth_provider`(Keycloak 활성 시), `readiness_parallel`, `readiness_checks`, `readiness_services`, `required_services`

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

패키지 루트 공개 re-export는 현재 `create_app`만 보장합니다.

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
uv add "git+https://github.com/kyundae-kim/fastapi-core.git@v0.2.0"
```

앱 설정은 `.env` 파일을 자동으로 읽지 않고 프로세스 환경변수에서 읽습니다. `.env.example`은 설정 키의 예시이며, 컨테이너 환경·배포 플랫폼·실행 도구를 통해 필요한 값을 환경변수로 주입해야 합니다. 상세 계약은 `docs/config.md`를 참고하세요.

## Quick start

### 기본 앱 생성

```python
from fastapi_core import create_app

app = create_app()
```

### auth router 제외

```python
from fastapi_core import create_app

app = create_app(include_auth_router=False)
```

### 현재 사용자 주입

```python
from fastapi import APIRouter, Depends
from fastapi_core.dependencies.auth import get_current_user
from fastapi_core.schemas.user import UserInfo

router = APIRouter()

@router.get("/me", response_model=UserInfo)
async def me(user: UserInfo = Depends(get_current_user)) -> UserInfo:
    return user
```

더 많은 예제는 `docs/examples.md`를 참고하세요.

## 현재 구현 동작

### `create_app(...)`
- `config is None`이면 `load_app_config()`를 사용합니다.
- `settings is None`이면 lifespan startup에서 `assemble_service_runtime(...)`으로 설정 검증, 필수 서비스 검증, client 조립을 수행합니다.
- 명시적 `settings`를 전달하면 direct API 주입 경로를 유지하되 동일한 `ServiceRuntime` lifecycle로 감쌉니다.
- 앱 로깅을 먼저 초기화합니다.
- 기본 경로의 service client map은 lifespan startup에서 준비됩니다.
- `FastAPI(root_path=..., lifespan=...)`를 생성하고 내부 lifespan wrapper의 `finally`에서 `await service_runtime.close()`를 수행합니다.
- `app.state.config`, `app.state.root_logger`, `app.state.service_runtime`, `app.state.settings`, `app.state.service_clients`를 저장합니다. Keycloak client가 구성되면 `app.state.auth_provider`도 저장합니다.
- `app.state.readiness_parallel`, `app.state.readiness_checks`, `app.state.readiness_services`, `app.state.required_services`를 초기화합니다.
- per-service/overall readiness timeout을 state와 startup runtime check에 동일하게 적용합니다.
- `service_alternatives`가 있으면 각 그룹에서 최소 한 서비스가 구성됐는지 `one_of` 정책으로 검증합니다.
- `set_oauth2_token_url(config.token_url)`로 OpenAPI password flow token URL을 반영합니다.
- CORS middleware를 등록합니다.
- health router를 기본 포함하고, `include_auth_router=True`일 때 auth router를 포함합니다.

### 인증
- `/token`은 `OAuth2PasswordRequestForm`을 받습니다.
- 현재 구현은 `scope`, `username`, `password`를 provider의 `fetch_access_token(...)`에 직접 전달합니다.
- provider 예외는 유형에 따라 `401`, `500`, `503`, `502/500`으로 매핑되며, 실패 응답에는 `WWW-Authenticate: Bearer` 헤더가 포함됩니다.
- `/user`와 `get_current_user()`는 bearer token을 읽고 provider의 `extract_user_info(...)` 결과를 `UserInfo`로 변환합니다.
- 권한 검사는 `require_permissions(*roles)`로 수행합니다.

### 헬스체크
- `/health/liveness`는 `{"status": "ok", "details": null}`를 반환합니다.
- `/health/readiness`는 `app.state.readiness_checks`, `app.state.readiness_services`, `app.state.required_services`, `app.state.readiness_parallel`을 사용합니다.
- 기본 `create_app()` 경로에서는 `enabled_services`를 기준으로 service client 기반 readiness check를 자동 구성합니다.
- sync/async readiness check는 `async_check_all_services(...)`로 집계되며 필수 실패 시에도 전체 서비스 details를 보존합니다.
- per-service timeout은 해당 서비스 실패로 변환되고, overall timeout은 `503 + status="error"`로 반환됩니다.
- 필수 서비스 실패 시 `503`, 선택 서비스만 실패 시 `200 + degraded`, 모두 성공 시 `200 + ok`를 반환합니다.
- readiness 로그는 구조화된 이벤트로 남기며, 오류 문자열은 상위 `docmesh_py_core` 마스킹 정책 영향을 받습니다.

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
- `DOCMESH_LOG_LEVEL`
- `APP_LOG_PATH`
- `APP_LOG_JSON`
- `APP_LOG_FORCE`
- `DOCMESH_SERVICES`
- `READINESS_REQUIRED_SERVICES`

## 현재 제한 사항

현재 구현 기준으로 아직 문서상 주의가 필요한 항목:
- auth 전용 exception handler를 별도 등록하는 구조는 없습니다. 대신 route/dependency에서 HTTP 예외 정책을 직접 적용합니다.
- `get_current_user()`의 secure/insecure decode 분기나 introspection 모드는 `fastapi-core`가 직접 노출하지 않습니다.
- `get_nats_connection` 같은 메시징 전용 FastAPI dependency는 아직 없습니다.
- 외부 서비스 통합 테스트는 `pytest.mark.integration`으로 표시되지만 기본 `uv run pytest -q` 실행에서도 수집됩니다. 필요한 환경변수 또는 대상 서비스가 없으면 해당 테스트는 skip됩니다.

## 문서

- 제품 요구사항: `docs/prd.md`
- 소프트웨어 요구사항: `docs/srs.md`
- API Reference: `docs/api.md`
- 설정 정의: `docs/config.md`
- 메시징 정의: `docs/messaging.md`
- 테스트 정의: `docs/test.md`
- 예제: `docs/examples.md`
- 교차 정합성 체크리스트: `docs/consistency-checklist.md`

## Verification

현재 저장소 기준 검증 명령:

```bash
uv run pytest -q
```

최근 실행 결과:
- `57 passed, 2 third-party deprecation warnings`
