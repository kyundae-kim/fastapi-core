# 제품 요구사항 정의서 (PRD)

## 개요

`fastapi-core`은 Keycloak 기반 인증/인가, PostgreSQL 연동, MinIO 연동 구조를 갖춘 Python Package 프로젝트 템플릿입니다.  
`uv` 패키지 매니저 환경에서 동작합니다.

---

## 주요 기능

### Keycloak 기반 인증/인가

- OAuth2 Password Grant로 토큰 발급 및 검증
- JWT RS256 서명 검증 및 사용자 클레임 추출 (`sub`, `preferred_username`, `email`, `name`)
- Realm Access 기반 역할(Role) 및 스코프(Scope) 추출

### 환경별 설정 분리

- **환경 변수 레이어** (`EnvConfig`): 로깅 레벨, CORS, JWT 검증 정책, 실행 환경 타입, 설정 파일 경로, 외부 서비스 접속 정보
- **서비스 설정 레이어** (`ServiceSettings`, YAML): 
- `dev` / `stage` / `prod` 환경 분리 및 환경별 `.env` 파일 지원

### 문서화

- SDK 문서화 지원

### 로깅 및 예외 처리

- 로깅 레벨 동적 설정 (`WARNING` / `INFO` / `DEBUG`)

---

## 프로젝트 구조

```
fastapi_template/
├── main.py              # 앱 진입점 (uvicorn 엔트리)
├── factory.py           # FastAPI 앱 조립 (로깅·CORS·lifespan·라우트 등록)
├── core/                # 공통 인프라 계층 (프레임워크 비의존)
│   ├── config.py        # EnvConfig, ServiceSettings, 각종 설정 모델
│   ├── security.py      # KeycloakAuthProvider, JWT 디코드, Token/User 모델
│   ├── logging.py       # 로깅 레벨 초기화
│   ├── exceptions.py    # AuthError 및 전역 예외 핸들러
│   └── storage.py       # MinIO 클라이언트 생성 및 버킷 관리
├── dependencies/        # FastAPI Depends 모듈
│   ├── config.py        # get_config, get_settings
│   ├── database.py      # get_db_engine
│   ├── security.py      # get_current_user, require_permissions
│   └── storage.py       # get_minio_client
├── routes/              # HTTP 입출력 계층
│   ├── __init__.py      # 라우터 등록 함수 (register_routes)
│   ├── auth.py          # POST /token, GET /user, GET /example/*
│   ├── database.py      # GET /db/example/ping, GET /db/example/version
│   ├── health.py        # GET /health/liveness, GET /health/readiness
│   └── storage.py       # GET /storage/ping, GET /storage/buckets
├── schemas/             # Pydantic 요청/응답 스키마
│   ├── token.py         # TokenResponse
│   ├── user.py          # UserInfo
│   ├── health.py        # HealthResponse
│   ├── database.py      # DB 관련 스키마
│   └── storage.py       # MinIO 관련 스키마
└── services/            # 외부 서비스 연동 및 도메인 로직
    ├── security.py      # authenticate, refresh_token, decode_token, get_auth_provider
    └── database.py      # SQLAlchemy 기반 DB 쿼리
```

---

## SDK 

### 인증 (`routes/auth.py`)

| 메서드 | 경로 | 설명 | 인증 필요 |
| --- | --- | --- | --- |
| `POST` | `/token` | OAuth2 Password Grant로 액세스 토큰 발급 | 불필요 |
| `GET` | `/user` | JWT로 현재 사용자 정보 조회 | 필요 |
| `GET` | `/example/read` | `read` 역할 필요 예시 엔드포인트 | 필요 |
| `GET` | `/example/create` | `create` 역할 필요 예시 엔드포인트 | 필요 |
| `GET` | `/example/delete` | `delete` 역할 필요 예시 엔드포인트 | 필요 |

### 헬스체크 (`routes/health.py`)

| 메서드 | 경로 | 설명 |
| --- | --- | --- |
| `GET` | `/health/liveness` | 앱 프로세스 생존 여부 확인 |
| `GET` | `/health/readiness` | Keycloak 연결 가능 여부 확인 |

### PostgreSQL 예시 (`routes/database.py`)

| 메서드 | 경로 | 설명 |
| --- | --- | --- |
| `GET` | `/db/example/ping` | DB 연결 확인 (`SELECT 1`) |
| `GET` | `/db/example/version` | DB 버전 조회 (`SELECT version()`) |

### MinIO 예시 (`routes/storage.py`)

| 메서드 | 경로 | 설명 |
| --- | --- | --- |
| `GET` | `/storage/ping` | MinIO 연결 확인 및 기본 버킷 접근 여부 |
| `GET` | `/storage/buckets` | MinIO 버킷 목록 조회 |

---

## 기술 스택

| 항목 | 내용 |
| --- | --- |
| 런타임 | Python ≥ 3.10 |
| 패키지 매니저 | [uv](https://docs.astral.sh/uv/) |
| 웹 프레임워크 | FastAPI (with standard extras) |
| 인증 서버 | Keycloak (OAuth2 / OIDC) |
| JWT 처리 | PyJWT\[crypto\] (RS256) |
| DB 드라이버 | psycopg (v3, binary) |
| ORM | SQLAlchemy ≥ 2.0 |
| 오브젝트 스토리지 | MinIO (minio-py SDK) |
| 테스트 | pytest |
| 린터 | Ruff |
