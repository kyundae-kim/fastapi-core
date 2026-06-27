# fastapi-core 설정 정의서

> 문서 목적: `fastapi-core`의 설정을 **현재 구현된 FastAPI 앱 조립 / dependency / readiness 관점**에서 설명한다.
> 기준 문서: `docs/prd.md`, `docs/srs.md`, `docs/api.md`
> 문서 상태: 구현 반영본(v0.3)

---

## 1. 문서 개요

이 문서는 계획 단계의 전체 플랫폼 설정 카탈로그가 아니라, **현재 저장소 구현이 실제로 읽고 사용하는 설정**을 우선 정리한다.
특히 `create_app(...)`, `AppConfig`, `load_default_settings()`, `app.state` 연계 지점을 중심으로 본다.

- 작성일: `2026-06-25`
- 작성자: `Hermes Agent`
- 버전: `v0.3`
- 상태: `implemented-surface`

핵심 관점:
- `create_app(...)`가 어떤 설정을 직접 소비하는가
- FastAPI dependency가 어떤 설정 객체를 참조하는가
- readiness가 어떤 방식으로 설정과 연결되는가
- 테스트 환경에서 어떤 최소 설정이 필요했는가

---

## 2. 현재 구현의 설정 계층

현재 구현은 설정을 두 층으로 나눈다.

1. **앱 조립 설정 (`AppConfig`)**
   - `fastapi_core.config.AppConfig`
   - FastAPI app 자체의 동작을 제어한다.
   - 예: `root_path`, CORS, readiness 병렬 플래그

2. **서비스/외부 의존성 설정 (`docmesh_py_core.Settings`)**
   - `docmesh_py_core.load_settings(...)` 결과
   - Keycloak / SQLite / MinIO / Milvus / Ollama / Langfuse / NATS 등 외부 시스템 설정을 포함한다.
   - 현재 `fastapi_core`는 이 객체를 주로 auth provider 생성과 테스트/앱 상태 보관에 사용한다.

즉, 현재 코드에서 FastAPI 앱은:
- `AppConfig`로 앱 조립 방식을 결정하고
- `Settings`로 외부 시스템 설정을 보관/전달한다.

---

## 3. AppConfig

정의 위치: `fastapi_core/config.py`

```python
class AppConfig(BaseModel):
    root_path: str = ""
    cors_origins: list[str] = ["*"]
    cors_credentials: bool = False
    readiness_parallel: bool = False
```

### 3.1 필드 의미

| 필드 | 적용 위치 | 현재 동작 |
| --- | --- | --- |
| `root_path` | `FastAPI(root_path=...)` | reverse proxy 하위 경로 배포 시 사용 |
| `cors_origins` | `CORSMiddleware` | 허용 origin 목록 |
| `cors_credentials` | `CORSMiddleware` | credential 허용 여부 |
| `readiness_parallel` | `app.state.readiness_parallel` | readiness check 병렬 실행 여부 |

### 3.2 로더

`load_app_config()`는 환경변수에서 `AppConfig`를 구성한다.

읽는 환경변수:
- `ROOT_PATH`
- `CORS_ORIGINS`
- `CORS_CREDENTIALS`
- `READINESS_PARALLEL`

### 3.3 파싱 규칙

- `CORS_ORIGINS`는 쉼표 구분 문자열로 읽는다.
- 비어 있으면 기본값 `[*]`를 사용한다.
- `CORS_CREDENTIALS`, `READINESS_PARALLEL`은 문자열이 `true`일 때만 `True`다.
- `load_app_config()`는 `lru_cache(maxsize=1)`로 캐시된다.

예시:

```env
ROOT_PATH=/api
CORS_ORIGINS=https://app.example.com,https://admin.example.com
CORS_CREDENTIALS=true
READINESS_PARALLEL=true
```

---

## 4. `create_app(...)`와 설정 연결

현재 구현의 `create_app(config=None, settings=None, lifespan=None, include_auth_router=True)`는 다음 순서로 설정을 사용한다.

1. `config`가 없으면 `load_app_config()` 사용
2. `settings`가 없으면 `load_default_settings()` 사용
3. `FastAPI(root_path=config.root_path, lifespan=lifespan)` 생성
4. `app.state.config = config`
5. `app.state.settings = settings`
6. `app.state.readiness_parallel = config.readiness_parallel`
7. CORS middleware 등록
8. health router 포함
9. 필요 시 auth router 포함

현재 구현에 **없는 것**:
- logging 초기화
- auth 전용 exception handler 등록
- 기본 readiness check 자동 주입

즉, 설정은 현재 코드에서 주로 **앱 조립**, **상태 저장**, **의존성 생성 기반값** 용도로 쓰인다.

---

## 5. `Settings` 기본 로더

정의 위치: `fastapi_core/config.py`

`load_default_settings()`는 현재 환경변수를 복사한 뒤, `docmesh_py_core.load_settings(...)`가 실패하지 않도록 여러 필수값에 개발용 기본값을 채운다.

대표 기본값:
- `KEYCLOAK_URL=http://keycloak.local`
- `KEYCLOAK_REALM=docmesh`
- `KEYCLOAK_CLIENT_ID=fastapi-core`
- `KEYCLOAK_CLIENT_SECRET=[development default]`
- `SQLITE_PATH=:memory:`
- `MINIO_ENDPOINT=minio.local:9000`
- `MINIO_ACCESS_KEY=minio`
- `MINIO_SECRET_KEY=[development default]`
- `MILVUS_URI=http://milvus.local:19530`
- `OLLAMA_HOST=http://ollama.local:11434`
- `LANGFUSE_HOST=http://langfuse.local:3000`
- `LANGFUSE_PUBLIC_KEY=[development default]`
- `LANGFUSE_SECRET_KEY=[development default]`
- `NATS_SERVERS=nats://nats.local:4222`
- `NATS_TOKEN=[development default]`

### 중요 해석

이 기본값들은 **운영 권장값이 아니라 개발/테스트용 fallback**이다.
운영 환경에서는 반드시 명시적 환경변수 또는 외부 secret 주입으로 대체해야 한다.

---

## 6. 인증 설정 (현재 구현 관점)

현재 auth 경로에 직접 연결되는 설정은 `docmesh_py_core.Settings` 내부의 Keycloak 관련 값들이다.

핵심 필수값:
- `KEYCLOAK_URL`
- `KEYCLOAK_REALM`
- `KEYCLOAK_CLIENT_ID`
- `KEYCLOAK_CLIENT_SECRET`

현재 구현 기준 영향 범위:
- `get_auth_provider()`가 `KeycloakAuthService(settings)` 생성에 사용
- `/token` endpoint의 provider 호출 기반값
- `/user` / `get_current_user()`의 token 해석 기반값

### 현재 문서화 시 주의할 점

문서 초안에 있던 다음 항목들은 **현재 fastapi_core 코드에서 직접 분기하지 않는다**:
- `KEYCLOAK_TOKEN_GRANT_TYPE`
- secure/insecure decode 분기
- introspection 모드 분기
- timeout/retry 정책의 FastAPI 계층 직접 반영

이 값들은 `docmesh_py_core` 내부에서는 의미가 있을 수 있지만, 현재 `fastapi_core` 공개 표면 문서에서는 **직접 구현된 동작으로 과장하면 안 된다**.

---

## 7. readiness / health 관련 설정

현재 readiness는 환경변수만으로 자동 구성되지 않는다.

실제 동작:
- `/health/liveness`는 설정 의존성이 거의 없다.
- `/health/readiness`는 아래 `app.state` 값을 읽는다.
  - `app.state.readiness_checks`
  - `app.state.required_services`
  - `app.state.readiness_parallel`

### 7.1 현재 설정 연결 방식

| 항목 | 공급 방식 | 설명 |
| --- | --- | --- |
| `readiness_checks` | 사용자/lifespan 주입 | 서비스명 → callable 매핑 |
| `required_services` | 사용자/lifespan 주입 | 실패 시 503을 유발하는 필수 서비스 집합 |
| `readiness_parallel` | `AppConfig` 또는 직접 state 설정 | 병렬 실행 여부 |

### 7.2 구현상 의미

- `READINESS_PARALLEL`은 실제로 사용된다.
- `KEYCLOAK_URL`, `NATS_SERVERS` 같은 값은 readiness가 자동으로 읽지 않는다.
- Keycloak/NATS readiness를 쓰려면 lifespan 또는 startup 코드에서 check를 등록해야 한다.

예시:

```python
app.state.readiness_checks = {
    "keycloak": lambda: None,
    "nats": lambda: None,
}
app.state.required_services = {"keycloak"}
```

---

## 8. CORS 설정

현재 CORS는 `create_app()`에서 항상 등록된다.

직접 연결되는 설정:
- `CORS_ORIGINS`
- `CORS_CREDENTIALS`

적용 코드:
- `allow_origins=app_config.cors_origins`
- `allow_credentials=app_config.cors_credentials`
- `allow_methods=["*"]`
- `allow_headers=["*"]`

운영 권장:
- wildcard 대신 명시 origin 사용
- credential 허용 시 origin 범위를 엄격하게 제한

---

## 9. 외부 의존성 설정 범위

`load_default_settings()`는 다음 외부 시스템의 필수값을 채운다.

- SQLite
- MinIO
- Milvus
- Ollama
- Langfuse
- NATS

하지만 현재 `fastapi_core` 자체는 이들을 다음 정도로만 직접 다룬다.

| 시스템 | 현재 fastapi_core 직접 사용 여부 | 비고 |
| --- | --- | --- |
| SQLite | 간접 | `Settings` 생성 성공용 기본값 |
| MinIO | 간접 | 동일 |
| Milvus | 간접 | 동일 |
| Ollama | 간접 | 동일 |
| Langfuse | 간접 | 동일 |
| NATS | 간접 | `Settings` 보관, readiness/user-lifespan 확장 지점 |

즉, 현재 구현에서 이 값들은 **app factory가 즉시 클라이언트를 만들기 위한 설정**이 아니라, `Settings` 객체의 유효성 충족과 향후 확장 지점을 위한 값이다.

---

## 10. 테스트 환경에서 확인된 최소 설정

`test_fastapi_core/conftest.py`의 `build_test_settings()` 기준, 테스트용 `Settings`를 만들기 위해 다음 값들이 제공되었다.

- `KEYCLOAK_URL`
- `KEYCLOAK_REALM`
- `KEYCLOAK_CLIENT_ID`
- `KEYCLOAK_CLIENT_SECRET`
- `SQLITE_PATH`
- `MINIO_ENDPOINT`
- `MINIO_ACCESS_KEY`
- `MINIO_SECRET_KEY`
- `MILVUS_URI`
- `OLLAMA_HOST`
- `LANGFUSE_HOST`
- `LANGFUSE_PUBLIC_KEY`
- `LANGFUSE_SECRET_KEY`
- `NATS_SERVERS`
- `NATS_TOKEN`

문서상 의미:
- 현재 `docmesh_py_core.load_settings(...)`를 통과하려면 위 수준의 필수 세트가 필요했다.
- 따라서 `fastapi_core` 테스트/로컬 실행 예시도 이 사실을 반영해야 한다.

---

## 11. 운영/보안 원칙

- secret / token / password / 전체 URI는 문서 예시와 로그에서 원문 노출 금지
- 개발 fallback를 운영 기본값처럼 안내하지 말 것
- readiness 관찰 대상을 운영 정책으로 명시할 것
- `app.state` 주입 객체는 startup/lifespan과 정합성을 맞출 것

---

## 12. 현재 구현 기준 제한 사항

문서 초안과 달리, 아직 다음은 설정으로 연결되어 있지 않다.

- logging 설정 계층
- auth exception handler 설정
- `/token`의 username/password 직접 전달 정책
- readiness의 자동 Keycloak/NATS 등록
- secure/insecure JWT decode 분기 설정

이 항목들은 목표 문서에는 남아 있어도, 현재 구현 기준 설정 정의에서는 **미구현**으로 취급해야 한다.

---

## 13. 최소 예시

### 13.1 AppConfig 환경변수

```env
ROOT_PATH=/api
CORS_ORIGINS=https://app.example.com
CORS_CREDENTIALS=true
READINESS_PARALLEL=false
```

### 13.2 테스트/개발용 개념 예시

```env
KEYCLOAK_URL=http://keycloak.local
KEYCLOAK_REALM=docmesh
KEYCLOAK_CLIENT_ID=fastapi-core
KEYCLOAK_CLIENT_SECRET=[REDACTED]
SQLITE_PATH=:memory:
NATS_SERVERS=nats://nats.local:4222
NATS_TOKEN=[REDACTED]
```

---

## 14. 참고 문서

- `docs/prd.md`
- `docs/srs.md`
- `docs/api.md`
- `README.md`
- `fastapi_core/config.py`
- `fastapi_core/factory.py`
- `test_fastapi_core/conftest.py`

---

## 15. 문서 상태 메모

이 문서는 기존의 광범위한 플랫폼 설정 계획 문서를, **현재 저장소에서 실제 확인된 설정 소비 경로** 중심으로 축소/정렬한 것이다.
운영 수준의 상세 필드 카탈로그는 향후 `docmesh_py_core`와 실제 서비스 조립 코드가 확장된 뒤 다시 넓히는 것이 맞다.
