# fastapi-core

DocMesh 프로젝트의 FastAPI 기반 마이크로서비스가 공통으로 사용하는 Python SDK입니다.
인증/인가(Keycloak), 데이터베이스(PostgreSQL), 오브젝트 스토리지(MinIO), 벡터 데이터베이스(Milvus), 로컬 LLM(Ollama), 설정/의존성/앱 조립을 표준화해 서비스 개발 시 중복 구현을 줄이는 것이 목적입니다.

## 무엇을 제공하나요?

- Keycloak 인증/인가
  - OAuth2 Password Grant 토큰 발급
  - JWT(RS256) 검증 및 사용자 정보 변환
  - 역할(role)/스코프(scope) 추출
- PostgreSQL 연동
  - SQLAlchemy + psycopg 기반 엔진 생성
  - 연결 확인, DB 버전 조회 유틸리티
  - DB 세션 의존성/트랜잭션 헬퍼
  - 커넥션 풀 파라미터 설정
- MinIO 연동
  - 클라이언트 생성
  - 버킷 존재 보장(없으면 생성)
  - 연결 확인 유틸리티
  - Presigned URL 생성 유틸리티
- Milvus 연동
  - Milvus 클라이언트 생성
  - 비동기 AsyncMilvusClient 생성
  - 컬렉션 목록 조회 / 연결 확인 유틸리티
  - 컬렉션 존재 보장 헬퍼
- Ollama 연동
  - Ollama 클라이언트 생성
  - 모델 목록 조회 / 연결 확인 유틸리티
  - 프롬프트 기반 텍스트 생성 헬퍼
- NATS 메시징
  - `nats-py` 기반 비동기 클라이언트 연결/종료
  - Subject 기반 Publish/Subscribe 헬퍼
  - Queue Group 기반 다중 소비자 스케일아웃
  - 도메인 이벤트 발행 패턴 (`*.created`, `*.updated`, `*.deleted`)
- 설정 관리
  - `EnvConfig`(환경 변수/.env)
  - `ServiceSettings`(YAML)
- FastAPI 조립
  - `create_app()` 팩토리
  - 로깅/CORS/예외 핸들러/헬스체크 라우터 기본 구성
  - readiness에 Keycloak·PostgreSQL·MinIO 종합 점검
- FastAPI state 기반 싱글톤 패턴
  - `app.state.auth_provider`, `app.state.db_engine`, `app.state.minio_client`, `app.state.milvus_client`, `app.state.ollama_client`, `app.state.nats_client` 사용
  - `set_*`/함수형 `get_*` dependency 제공
  - `Get*Dependency` class와 `get_* = Get*Dependency()` 전역 인스턴스는 사용하지 않음

## 설치

```bash
# uv
uv add git+https://github.com/your-org/fastapi-core.git

# pip
pip install git+https://github.com/your-org/fastapi-core.git
```

## 빠른 시작

가장 단순한 사용:

```python
from fastapi_core import create_app

app = create_app()
```

권장 패턴(lifespan에서 state 싱글톤 등록):

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

from fastapi_core.factory import create_app
from fastapi_core.core.config import EnvConfig
from fastapi_core.dependencies.auth import set_auth_provider
from fastapi_core.dependencies.database import set_db_engine
from fastapi_core.dependencies.storage import set_minio_client
from fastapi_core.dependencies.milvus import set_milvus_client
from fastapi_core.dependencies.ollama import set_ollama_client
from fastapi_core.dependencies.messaging import set_nats_client

config = EnvConfig()

@asynccontextmanager
async def lifespan(app: FastAPI):
    set_auth_provider(app, config=config)
    set_db_engine(app, config=config)
    set_minio_client(app, config=config)
    set_milvus_client(app, config=config)
    set_ollama_client(app, config=config)
    await set_nats_client(app, config=config)
    yield
    app.state.db_engine.dispose()
    app.state.milvus_client.close()
    await app.state.nats_client.drain()

app = create_app(config=config, lifespan=lifespan)
```

인증 의존성 사용 예:

```python
from fastapi import APIRouter, Depends
from fastapi_core.schemas.user import UserInfo
from fastapi_core.dependencies.auth import get_current_user, require_permissions

router = APIRouter()

@router.get("/me")
def me(user: UserInfo = Depends(get_current_user)):
    return user

@router.get("/admin")
def admin_only(user: UserInfo = Depends(require_permissions("admin"))):
    return user
```

## 내장 엔드포인트

- `GET /health/liveness`
- `GET /health/readiness`
- `POST /token` (옵션: `create_app(..., include_auth_router=True)`일 때)
- `GET /user` (옵션: `create_app(..., include_auth_router=True)`일 때)

## 설정 요약

설정은 2개 레이어로 분리됩니다.

1) 환경 변수 (`EnvConfig`)
- 외부 서비스 접속 정보, 실행 환경, 로깅 레벨
- 예: `ENV`, `CONFIG_PATH`, `LOGGING__LEVEL`, `KEYCLOAK__*`, `DB__*`, `MINIO__*`, `MILVUS__*`, `OLLAMA__*`, `NATS__*`

2) 서비스 설정 YAML (`ServiceSettings`)
- 앱 동작 정책
- 예: `cors.origins`, `cors.credentials`, `auth.verify_jwt`, `auth.allow_insecure_jwt_decode`, `auth.use_introspection`

자세한 키/기본값/예시는 `docs/config.md`를 참고하세요.

## 테스트

```bash
# 단위 테스트
uv run pytest -q

# 통합 테스트
uv run pytest -q -m integration
```

통합 테스트는 devcontainer 기반 실서비스(Keycloak/PostgreSQL/MinIO/Milvus/Ollama) 연결을 전제로 합니다.
NATS 적용 시 테스트 NATS 서버(로컬 또는 devcontainer) 연결을 추가로 구성하세요.

## 개발 정보

- Python: `>=3.11` (프로젝트 설정 기준)
- 테스트 루트: `test_fastapi_core/`
- 린트: Ruff (line-length 88)

## 문서

- `docs/prd.md` : 제품 요구사항(PRD)
- `docs/api.md` : 공개 API 시그니처/동작/에러 처리
- `docs/config.md` : 설정 가이드(환경 변수/YAML)
- `docs/test.md` : 테스트 가이드(단위/통합)
- `docs/messaging.md` : NATS 메시징 적용 가이드(설정, pub/sub, 도메인 적용, 테스트)
