# fastapi-core

DocMesh 프로젝트의 FastAPI 기반 마이크로서비스가 공통으로 사용하는 Python SDK입니다.
`fastapi-core`는 단순 인프라 클라이언트 모음이 아니라, **공통 FastAPI 앱 표면**을 제공하는 데 초점을 둡니다.

현재 구현된 핵심 범위:
- `fastapi_core.factory:create_app`
- auth router: `POST /token`, `GET /user`
- health router: `GET /health/liveness`, `GET /health/readiness`
- dependency: `get_config`, `get_settings`, `get_auth_provider`, `get_current_user`, `require_permissions`
- schema: `TokenResponse`, `UserInfo`, `HealthResponse`

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

## Quick start

### 기본 앱 생성

```python
from fastapi_core.factory import create_app

app = create_app()
```

### auth router 제외

```python
from fastapi_core.factory import create_app

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

## 현재 구현 동작

### `create_app(...)`
- `FastAPI(root_path=..., lifespan=...)` 생성
- `app.state.config`, `app.state.settings` 저장
- CORS middleware 등록
- health router 기본 포함
- `include_auth_router=True`일 때 auth router 포함

### 인증
- `/token`은 `OAuth2PasswordRequestForm`을 받는다.
- 현재 구현은 provider의 `fetch_access_token(scope=...)`를 호출해 `TokenResponse`를 반환한다.
- `/user`와 `get_current_user()`는 bearer token을 읽고 provider의 `extract_user_info(...)` 결과를 `UserInfo`로 변환한다.
- 권한 검사는 `require_permissions(*roles)`로 수행한다.

### 헬스체크
- `/health/liveness`는 `{"status": "ok", "details": null}`를 반환한다.
- `/health/readiness`는 `app.state.readiness_checks`가 주입된 경우 `docmesh_py_core.check_all_services(...)`로 상태를 집계한다.
- 필수 서비스 집합은 `app.state.required_services`로 제어할 수 있다.
- readiness 병렬 실행 여부는 `app.state.readiness_parallel`을 사용한다.

## App config

`fastapi_core.config.AppConfig`:
- `root_path: str = ""`
- `cors_origins: list[str] = ["*"]`
- `cors_credentials: bool = False`
- `readiness_parallel: bool = False`

환경변수 예시는 저장소 루트의 `.env.example`를 참고하세요.

환경변수:
- `ROOT_PATH`
- `CORS_ORIGINS`
- `CORS_CREDENTIALS`
- `READINESS_PARALLEL`

## 현재 제한 사항

현재 구현은 문서 초안의 전체 목표를 모두 반영하지는 않습니다.

- `create_app()` 내부 logging 초기화는 아직 구현되지 않았습니다.
- auth 전용 예외 핸들러 등록은 아직 없습니다.
- `get_current_user()`의 secure/insecure decode 분기 설정은 아직 없습니다.
- `/health/readiness`는 기본적으로 Keycloak/NATS를 자동 점검하지 않고, `app.state.readiness_checks`가 주입된 경우에만 동작합니다.
- `/token`은 폼 필드를 받지만 현재 구현은 provider에 사용자명/비밀번호를 직접 전달하지 않습니다.

## Verification

현재 저장소 기준 검증 명령:

```bash
uv run pytest -q
```

최근 실행 결과:
- `12 passed`
