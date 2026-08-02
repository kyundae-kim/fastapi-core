# fastapi-core 설정 기준

`fastapi-core`는 `.env` 파일을 자동으로 읽지 않는다. shell, container, deployment platform 또는 별도 dotenv loader가 환경변수를 process에 주입해야 한다.

## AppConfig 핵심 필드

| 필드 | 타입 | 기본값 |
|---|---|---|
| `root_path` | `str` | `""` |
| `token_url` | `str` | `"/token"` |
| `cors_origins` | `list[str]` | `["*"]` |
| `cors_credentials` | `bool` | `False` |
| `readiness_parallel` | `bool` | `False` |
| `readiness_timeout_seconds` | `float | None` | `None` |
| `readiness_overall_timeout_seconds` | `float | None` | `None` |
| `startup_healthcheck` | `bool` | `False` |
| `startup_failure_mode` | `StartupFailureMode` | `FAIL` |
| `startup_healthcheck_attempts` | `int` | `1` |
| `startup_healthcheck_retry_delay_seconds` | `float` | `0` |
| `enabled_services` | `list[str]` | `[]` |
| `required_services` | `list[str]` | `[]` |
| `service_alternatives` | `list[list[str]]` | `[]` |

## 주요 환경변수

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
- `DOCMESH_SERVICES`
- `READINESS_REQUIRED_SERVICES`

CSV 환경변수는 쉼표로 구분한다. 대체 서비스 그룹은 세미콜론으로 그룹을 구분하고 각 그룹 안에서 쉼표를 사용한다.

## 설정 검증

- `required_services`는 `enabled_services`의 부분집합이어야 한다.
- readiness timeout은 지정 시 양수여야 한다.
- startup healthcheck 시도 횟수는 1 이상이어야 한다.
- retry delay는 0 이상이어야 한다.
- 활성 서비스와 대체 서비스 group은 runtime 조립 전에 검증된다.

앱 조립과 runtime contract는 [`api.md`](api.md)와 [`srs.md`](srs.md)를 참조한다.
