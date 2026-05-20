# fastapi-core

DocMesh 프로젝트의 FastAPI 기반 마이크로서비스가 공통으로 사용하는 Python SDK 패키지입니다.  
Keycloak 인증/인가, PostgreSQL 연동, MinIO 연동에 필요한 핵심 모듈을 제공합니다.

---

## 주요 기능

- **Keycloak 인증/인가** — OAuth2 Password Grant, JWT RS256 서명 검증, Realm Access 역할·스코프 파싱
- **PostgreSQL 연동** — SQLAlchemy ≥ 2.0 + psycopg v3 엔진 생성, 연결 확인 유틸리티
- **MinIO 연동** — 클라이언트 생성, 버킷 자동 생성, 연결 확인 유틸리티
- **설정 관리** — 환경 변수(`EnvConfig`) + YAML(`ServiceSettings`) 이중 레이어
- **FastAPI 앱 팩토리** — CORS·로깅·예외 핸들러·라우터를 한 번에 조립하는 `create_app()`
- **내장 라우터** — `/health/liveness`, `/health/readiness`, `/token`, `/user`

---

## 패키지 구조

```
fastapi_core/
├── core/               # 프레임워크 비의존 공통 인프라
│   ├── config.py       # EnvConfig, ServiceSettings, DatabaseConfig, MinIOConfig
│   ├── security.py     # KeycloakAuthProvider, extract_roles, extract_scopes
│   ├── logging.py      # setup_logging
│   ├── exceptions.py   # AuthError, auth_error_handler
│   ├── storage.py      # create_minio_client, ensure_bucket_exists
│   └── database.py     # create_db_engine, check_database_connection
├── dependencies/       # FastAPI Depends 모듈
│   ├── config.py       # get_config, get_settings
│   ├── database.py     # get_db_engine
│   ├── security.py     # get_current_user, require_permissions
│   └── storage.py      # get_minio_client
├── routers/            # 재사용 가능한 내장 라우터
│   ├── health.py       # GET /health/liveness, GET /health/readiness
│   └── auth.py         # POST /token, GET /user
├── schemas/            # Pydantic 스키마
│   ├── token.py        # TokenResponse
│   ├── user.py         # UserInfo
│   └── health.py       # HealthResponse
└── factory.py          # create_app()
```

---

## 설치

```bash
# uv (권장)
uv add git+https://github.com/your-org/fastapi-core.git

# pip
pip install git+https://github.com/your-org/fastapi-core.git
```

---

## 빠른 시작

```python
from fastapi_core import create_app

app = create_app()
```

커스텀 설정과 lifespan 지정:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi_core import create_app
from fastapi_core.core.config import EnvConfig, ServiceSettings

config = EnvConfig()
settings = ServiceSettings.from_yaml(config.config_path)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 시작 시 초기화 작업
    yield
    # 종료 시 정리 작업

app = create_app(config=config, settings=settings, lifespan=lifespan)
```

인증 의존성 사용:

```python
from fastapi import APIRouter, Depends
from fastapi_core import UserInfo
from fastapi_core.dependencies.security import get_current_user, require_permissions

router = APIRouter()

@router.get("/me")
def me(user: UserInfo = Depends(get_current_user)):
    return user

@router.get("/admin-only")
def admin(user: UserInfo = Depends(require_permissions("admin"))):
    return user
```

---

## 환경 변수

설정은 환경 변수와 YAML 파일 두 레이어로 분리됩니다. 자세한 내용은 [docs/config.md](docs/config.md)를 참고하세요.

| 변수명 | 기본값 | 설명 |
| --- | --- | --- |
| `ENV` | `dev` | 실행 환경 (`dev` \| `stage` \| `prod`) |
| `CONFIG_PATH` | `.devcontainer/config.yaml` | 서비스 설정 YAML 경로 |
| `LOGGING__LEVEL` | `DEBUG` | 로그 레벨 |
| `KEYCLOAK__HTTP_URL` | `http://keycloak:8080/` | Keycloak URL |
| `KEYCLOAK__REALM` | `restapi` | Keycloak Realm |
| `KEYCLOAK__CLIENT_ID` | `fastapi` | Client ID |
| `DB__HOST` | `postgres` | PostgreSQL 호스트 |
| `MINIO__ENDPOINT` | `minio:9000` | MinIO 엔드포인트 |

---

## 개발 환경 설정

```bash
# 의존성 설치
uv sync --all-groups

# 단위 테스트 실행 (외부 서비스 불필요)
uv run pytest -q

# 통합 테스트 실행 (devcontainer 환경)
uv run pytest -q -m integration
```

---

## 기술 스택

| 항목 | 버전 |
| --- | --- |
| Python | ≥ 3.10 |
| FastAPI | ≥ 0.111.0 |
| pydantic-settings | ≥ 2.0 |
| SQLAlchemy | ≥ 2.0 |
| psycopg | ≥ 3.3 (binary) |
| PyJWT | ≥ 2.12 (crypto) |
| minio-py | ≥ 7.2 |
| httpx | ≥ 0.27 |

---

## 문서

- [PRD](docs/prd.md) — 제품 요구사항 정의서
- [설정 가이드](docs/config.md) — 환경 변수 및 YAML 설정 전체 목록
- [테스트 가이드](docs/test.md) — 단위/통합 테스트 구조 및 실행 방법

