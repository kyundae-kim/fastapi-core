# 제품 요구사항 정의서 (PRD)

## 개요

`fastapi-core`는 DocMesh 프로젝트의 FastAPI 기반 마이크로서비스들이 공통으로 사용하는 Python SDK 패키지입니다.  
Keycloak 기반 인증/인가, PostgreSQL 연동, MinIO 연동에 필요한 핵심 모듈을 제공하며, `uv` 패키지 매니저 환경에서 동작합니다.

---

## 배경 및 목적

DocMesh 프로젝트는 다수의 FastAPI 기반 마이크로서비스로 구성됩니다. 각 서비스마다 Keycloak 토큰 검증, DB 연결, MinIO 연결 코드를 중복 구현하는 문제를 해결하기 위해 `fastapi-core` SDK를 분리합니다.

- **중복 제거**: 인증/DB/스토리지 연동 코드를 단일 패키지로 통합
- **일관성 보장**: 모든 서비스가 동일한 설정 구조·예외 처리·로깅 정책을 공유
- **빠른 서비스 개발**: 새 마이크로서비스는 `fastapi-core`를 의존성으로 추가하고 비즈니스 로직 구현에 집중

---

## 대상 사용자

| 사용자 | 설명 |
| --- | --- |
| DocMesh 서비스 개발자 | `fastapi-core`를 의존성으로 추가하여 FastAPI 서비스를 개발하는 내부 팀 |
| 인프라/DevOps 엔지니어 | Keycloak·PostgreSQL·MinIO 설정 및 환경 변수 관리 |

---

## 주요 기능 요구사항

### 1. Keycloak 기반 인증/인가

- OAuth2 Password Grant 방식으로 Keycloak에서 액세스 토큰 발급
- JWT RS256 서명 검증 및 클레임 추출 (`sub`, `preferred_username`, `email`, `name`)
- Realm Access 기반 역할(Role) 및 스코프(Scope) 파싱
- FastAPI `Depends` 기반 `get_current_user`, `require_permissions` 의존성 함수 제공
- 개발 환경용 서명 검증 생략 모드(`allow_insecure_jwt_decode`) 지원
- Keycloak 토큰 인트로스펙션(`use_introspection`) 선택적 지원

### 2. PostgreSQL 연동

- SQLAlchemy ≥ 2.0 + psycopg v3 기반 엔진 생성
- `DatabaseConfig`로 DSN 자동 조합 (또는 `DB__URL` 직접 지정)
- 연결 확인(`SELECT 1`) 및 DB 버전 조회 유틸리티 함수 제공
- `trust` / `password` 인증 방식 선택 지원
- FastAPI 의존성으로 재사용 가능한 DB 세션 제공 (`get_db_session`)
- 트랜잭션 헬퍼 제공 (`run_in_transaction` 또는 컨텍스트 매니저)
- 커넥션 풀 관련 설정(`pool_size`, `max_overflow`, `pool_timeout`, `pool_recycle`) 노출

### 3. MinIO 연동

- minio-py SDK 기반 클라이언트 생성 및 버킷 자동 생성(`ensure_bucket_exists`)
- 연결 확인 및 버킷 목록 조회 유틸리티 함수 제공
- TLS(`MINIO__SECURE`) 선택적 지원
- Presigned URL 생성 유틸리티 제공 (GET/PUT)

### 4. NATS 메시징

- `nats-py` 기반 비동기 클라이언트 연결/종료 지원
- Subject 기반 Publish/Subscribe 패턴 제공
- Queue Group 기반 소비자 수평 확장 지원
- 도메인 이벤트 발행 규칙 표준화 (`<domain>.<entity>.<action>`)
- FastAPI `app.state` 기반 NATS 클라이언트 싱글톤 관리 (`app.state.nats_client`)

### 5. 설정 관리

- **환경 변수 레이어** (`EnvConfig`): 외부 서비스 접속 정보, 실행 환경, 로깅 레벨 등 배포 환경에 따라 달라지는 값
- **서비스 설정 레이어** (`ServiceSettings`, YAML): CORS, JWT 검증 정책 등 애플리케이션 동작 값
- `dev` / `stage` / `prod` 환경 분리 및 환경별 `.env` 파일 지원
- `__` 구분자를 통한 중첩 모델 환경 변수 주입 (예: `KEYCLOAK__REALM`)

### 5. 로깅

- 로깅 레벨 동적 설정 (`WARNING` / `INFO` / `DEBUG`)

### 6. FastAPI 앱 조립 지원

- 로깅·CORS·lifespan·라우터 등록을 수행하는 `create_app` 팩토리 함수 제공
- 헬스체크 라우터(`/health/liveness`, `/health/readiness`) 내장 제공
- `/health/readiness`는 Keycloak뿐 아니라 PostgreSQL·MinIO 의존성까지 포함한 종합 준비 상태를 확인

### 8. FastAPI State 기반 싱글톤 관리

외부 서비스 접근 객체는 요청마다 새로 생성하지 않고 **애플리케이션 시작 시 단 한 번 생성**하여 `app.state`에 저장하는 싱글톤 패턴을 적용한다.

#### state 속성 위치 (하드코딩)

각 객체의 `app.state` 속성명은 `fastapi-core` SDK가 고정한다. 사용자(서비스 개발자)는 속성명을 직접 지정하거나 알 필요가 없으며, 아래에 명시된 **저장 함수**와 **의존성 함수**만 사용한다.

| `app.state` 속성 (내부 고정) | 타입 | 저장 함수 | 의존성 함수 |
| --- | --- | --- | --- |
| `app.state.auth_provider` | `KeycloakAuthProvider` | `set_auth_provider(app, provider)` 또는 `set_auth_provider(app, config=config)` | `get_auth_provider` |
| `app.state.db_engine` | SQLAlchemy `Engine` | `set_db_engine(app, engine)` 또는 `set_db_engine(app, config=config)` | `get_db_engine` |
| `app.state.minio_client` | `Minio` | `set_minio_client(app, client)` 또는 `set_minio_client(app, config=config)` | `get_minio_client` |
| `app.state.nats_client` | `nats.aio.client.Client` | `set_nats_client(app, client)` 또는 `set_nats_client(app, config=config)` *(추가 예정)* | `get_nats_client` *(추가 예정)* |

#### 저장 함수 (state setter)

- `set_auth_provider`, `set_db_engine`, `set_minio_client`, `set_nats_client` *(추가 예정)* 를 `dependencies` 모듈에서 제공
- 각 함수는 **두 가지 호출 형태**를 지원한다:
  - `set_auth_provider(app, provider)` — 외부에서 생성한 객체를 직접 전달
  - `set_auth_provider(app, config=config)` — `EnvConfig`를 전달하면 내부에서 객체를 생성하여 등록
  - `provider`와 `config` 중 하나는 반드시 지정해야 하며, 둘 다 생략하면 `ValueError`가 발생한다
- 각 함수는 내부적으로 고정된 `app.state` 속성명에 객체를 할당하며, 사용자가 속성명을 지정할 수 없다
- 서비스 개발자는 `lifespan` 컨텍스트 매니저 내에서 저장 함수를 호출하여 객체를 등록하고, `yield` 이후 `engine.dispose()` 등 리소스 정리를 수행한다

#### 의존성 함수 (state getter)

- `get_auth_provider`, `get_db_engine`, `get_minio_client`, `get_nats_client` *(추가 예정)* 는 `request.app.state`의 고정된 속성명에서 객체를 읽어 반환하는 `Depends` 함수다
- 서비스 개발자는 `Depends(get_db_engine)` 형태로만 사용하며 state 속성명을 알 필요가 없다

> **fallback 정책**: `app.state`에 해당 속성이 없으면 (`AttributeError`) `EnvConfig`를 읽어 생성하는 폴백을 두어 lifespan 없이도 동작하도록 한다. `auth_provider`와 `db_engine`은 생성 후 `app.state`에 저장하여 재사용한다.

---

## 패키지 구조

```
fastapi_core/
├── __init__.py
├── core/                # 프레임워크 비의존 공통 인프라
│   ├── config.py        # EnvConfig, ServiceSettings, 각종 설정 모델
│   ├── auth.py          # KeycloakAuthProvider, JWT 디코드, Token/User 모델
│   ├── logging.py       # 로깅 레벨 초기화
│   ├── exceptions.py    # AuthError 및 전역 예외 핸들러
│   ├── storage.py       # MinIO 클라이언트 생성 및 버킷 관리
│   └── messaging.py     # NATS 클라이언트 생성, pub/sub 헬퍼 *(추가 예정)*
├── dependencies/        # FastAPI Depends 모듈
│   ├── config.py        # get_config, get_settings
│   ├── database.py      # get_db_engine
│   ├── auth.py          # get_current_user, require_permissions, set_auth_provider, get_auth_provider
│   ├── storage.py       # get_minio_client
│   └── messaging.py     # set_nats_client, get_nats_client *(추가 예정)*
├── routers/             # 재사용 가능한 내장 라우터
│   ├── health.py        # GET /health/liveness, GET /health/readiness
│   └── auth.py          # POST /token, GET /user (선택적 마운트)
├── schemas/             # 공유 Pydantic 스키마
│   ├── token.py         # TokenResponse
│   ├── user.py          # UserInfo
│   └── health.py        # HealthResponse
└── factory.py           # create_app() — FastAPI 앱 조립 팩토리
```

---

## 공개 API (Public Interface)

각 심볼의 시그니처, 동작, 에러 처리, HTTP 엔드포인트 스펙은 **[docs/api.md](api.md)** 를 참조하세요.

---

## 비기능 요구사항

### 테스트

- 단위 테스트: 외부 서비스 없이 `unittest.mock` 기반으로 전체 공개 API 커버
- 통합 테스트: Keycloak·PostgreSQL·MinIO 실 인스턴스 연결 검증 (devcontainer 환경)
- 테스트 러너: pytest (`uv run pytest`)

### 품질

- 린터: Ruff (line-length 88)
- Python ≥ 3.11 호환성 유지
- 타입 힌트 전면 적용

### 패키지 배포

- `pyproject.toml` 기준 `uv` 로 빌드 및 설치
- 내부 PyPI 또는 Git URL(`pip install git+...`) 방식으로 서비스에서 의존성 추가

---

## 기술 스택

| 항목 | 내용 |
| --- | --- |
| 런타임 | Python ≥ 3.11 |
| 패키지 매니저 | [uv](https://docs.astral.sh/uv/) |
| 웹 프레임워크 | FastAPI |
| 인증 서버 | Keycloak (OAuth2 / OIDC) |
| JWT 처리 | PyJWT\[crypto\] (RS256) |
| DB 드라이버 | psycopg (v3, binary) |
| ORM | SQLAlchemy ≥ 2.0 |
| 오브젝트 스토리지 | MinIO (minio-py SDK) |
| 메시징 | NATS (nats-py SDK) *(신규)* |
| 테스트 | pytest |
| 린터 | Ruff |
