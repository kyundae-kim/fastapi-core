---
source_url: https://github.com/kyundae-kim/docmesh-config/wiki/Examples-v0.1.0
ingested: 2026-08-01
sha256: f9499e7ebea86614eee32d3fa9190abd81d6fe1714ce96c15c49108d545772a5
---
# docmesh-config 사용 예제

| 항목 | 내용 |
| --- | --- |
| 기준 버전 | 0.1.0 |
| 최종 갱신일 | 2026-07-31 |
| 추적 요구사항 | [SRS NFR-8](./srs.md#5-비기능-요구사항) |
| API 레퍼런스 | [api.md](./api.md) |
| 설정 레퍼런스 | [config.md](./config.md) |
| 환경 템플릿 | [../.env.example](../.env.example) |

모든 설정 객체는 생성자 인자가 아니라 프로세스 환경변수에서 값을 읽는다. 예제는 외부 서비스에 연결하지 않는다.

## 1. SQLite 설정 로드

```python
import os

from docmesh_config import Service, load_service_configs

os.environ["SQLITE_PATH"] = ":memory:"

configs = load_service_configs(services={Service.SQLITE})
sqlite = configs.require_sqlite()

assert sqlite.path == ":memory:"
assert configs.postgres is None
```

`services`에 지정한 서비스는 설정이 완전해야 한다. 로드하지 않은 서비스를 `require_*()`로 요청하면 구조화된 `ConfigError`가 발생한다.

## 2. 환경에 존재하는 서비스만 로드

```python
import os

from docmesh_config import load_available_service_configs

os.environ["SQLITE_PATH"] = ":memory:"

configs = load_available_service_configs(
    services={"sqlite", "postgres", "minio"},
)

assert configs.sqlite is not None
assert configs.postgres is None
assert configs.minio is None
```

관련 환경변수가 일부만 존재하는 서비스는 조용히 무시하지 않고 validation 오류로 처리한다.

## 3. 서비스 상태 진단

```python
import os

from docmesh_config import RuntimePlan, Service, diagnose_services

os.environ["SQLITE_PATH"] = ":memory:"

plan = RuntimePlan(
    services=(
        Service.SQLITE.required(),
        Service.POSTGRES.optional(),
    ),
)
diagnosis = diagnose_services(plan=plan)

assert diagnosis.ok
assert diagnosis.services["sqlite"].state == "complete"
assert diagnosis.services["postgres"].state == "absent"
assert diagnosis.configured_services == frozenset({"sqlite"})
```

진단은 DNS, socket 또는 외부 API를 사용하지 않는다.

## 4. 대안 서비스와 strict 선택

```python
import os

from docmesh_config import RuntimePlan, Service, diagnose_services

os.environ["SQLITE_PATH"] = ":memory:"
os.environ["POSTGRES_HOST"] = "postgres.internal"
os.environ["POSTGRES_DB"] = "app"
os.environ["POSTGRES_USER"] = "app"
os.environ["POSTGRES_PASSWORD"] = "example-only"

plan = RuntimePlan(
    services=(Service.SQLITE, Service.POSTGRES),
    one_of=((Service.SQLITE, Service.POSTGRES),),
)
diagnosis = diagnose_services(plan=plan, selection_mode="strict")

assert not diagnosis.ok
assert "ambiguous_service_alternative" in {
    issue.error_type for issue in diagnosis.issues
}
```

`auto`와 `explicit`에서는 대안 그룹의 하나 이상이 구성되면 충족된다. `strict`에서는 정확히 하나만 구성되어야 한다.

## 5. Runtime plan 메타데이터 생성

```python
import os

from docmesh_config import (
    HealthcheckPolicy,
    RuntimePlan,
    Service,
    StartupFailureMode,
    build_runtime_plan_metadata,
)

os.environ["SQLITE_PATH"] = ":memory:"

plan = RuntimePlan(
    services=(Service.SQLITE.required(),),
    healthcheck=HealthcheckPolicy(
        on_startup=True,
        timeout_seconds=2,
        attempts=3,
        retry_delay_seconds=0.5,
        failure_mode=StartupFailureMode.REPORT,
    ),
)
metadata = build_runtime_plan_metadata(plan=plan)

assert metadata.requirements_satisfied
assert metadata.service_states == {"sqlite": "complete"}
assert metadata.to_dict()["healthcheck"]["failure_mode"] == "report"
```

`HealthcheckPolicy`는 실행 정책 메타데이터일 뿐 상태 확인을 직접 실행하지 않는다.

## 6. MinIO bucket 요구

```python
import os

from docmesh_config import RuntimePlan, Service, diagnose_services

os.environ["MINIO_ENDPOINT"] = "minio.internal:9000"
os.environ["MINIO_ACCESS_KEY"] = "example-access"
os.environ["MINIO_SECRET_KEY"] = "example-secret"
os.environ["MINIO_BUCKET"] = "documents"

plan = RuntimePlan(
    services=(Service.MINIO.required(),),
    minio_bucket_required=True,
)
diagnosis = diagnose_services(plan=plan)

assert diagnosis.ok
assert diagnosis.configured_services == frozenset({"minio"})
```

`minio_bucket_required=True`를 사용하려면 MinIO가 plan에 선택되어 있어야 한다.

## 7. 구조화된 설정 오류 처리

```python
import os

from docmesh_config import ConfigError, Service, load_service_configs

os.environ["POSTGRES_HOST"] = "postgres.internal"

try:
    load_service_configs(services={Service.POSTGRES})
except ConfigError as exc:
    missing_keys = set(exc.env_keys)
    assert "POSTGRES_DB" in missing_keys
    assert "POSTGRES_USER" in missing_keys
    assert "POSTGRES_PASSWORD" in missing_keys
    assert all(issue.remediation for issue in exc.issues)
else:
    raise AssertionError("partial PostgreSQL configuration must fail")
```

오류 객체에는 민감한 환경변수 원문이 아닌 canonical 환경변수 key와 조치 정보가 들어간다.

## 8. Production transport 정책

```python
import os

from docmesh_config import ConfigError, Service, load_service_configs

os.environ["DOCMESH_ENV"] = "production"
os.environ["OLLAMA_HOST"] = "https://ollama.internal"
os.environ["OLLAMA_VERIFY_SSL"] = "false"

try:
    load_service_configs(services={Service.OLLAMA})
except ConfigError as exc:
    assert exc.issues[0].error_type == "production_transport_security"
    assert exc.issues[0].env_key == "OLLAMA_VERIFY_SSL"
else:
    raise AssertionError("insecure production transport must fail")
```

production에서는 Keycloak SSL 검증, MinIO secure/cert check, Milvus secure, Ollama SSL 검증을 끌 수 없다.

## 9. Milvus endpoint와 secret-safe 출력

```python
import os

from docmesh_config import MilvusConfig

os.environ["MILVUS_ENDPOINT"] = "https://user:example-password@milvus.internal:19530"
os.environ["MILVUS_TOKEN"] = "example-token"

config = MilvusConfig()
dumped = config.model_dump()
serialized = config.model_dump_json()

assert config.endpoint == "https://user:example-password@milvus.internal:19530"
assert dumped["endpoint"] == "https://***:***@milvus.internal:19530"
assert dumped["token"] == "***"
assert "example-password" not in serialized
assert "example-token" not in serialized
```

Milvus의 현재 환경변수는 `MILVUS_ENDPOINT`다. `MILVUS_URI`는 지원하지 않는다.

## 10. 독립 값 마스킹

```python
from docmesh_config import mask_sensitive_value

masked = mask_sensitive_value(
    "https://user:password@example.com/path?token=abc&view=full"
)

assert masked == "https://***:***@example.com/path?token=%2A%2A%2A&view=full"
assert mask_sensitive_value("alice@example.com") == "alice@example.com"
```

malformed URL도 `username:password@` 형태면 fail-closed 방식으로 마스킹한다.

## 11. `.env.example` 사용

라이브러리가 `.env` 파일을 자동으로 읽지는 않는다. 애플리케이션 또는 배포 도구가 환경변수로 주입해야 한다. POSIX shell에서 개발용 템플릿을 명시적으로 로드하는 예:

```bash
cp .env.example .env
# 필요한 서비스 block의 주석을 해제하고 값을 수정한다.
set -a
. ./.env
set +a
python your_application.py
```

`.env`에는 실제 credential을 저장소에 커밋하지 않는다. production secret은 배포 환경의 Secret 관리 기능에서 프로세스 환경변수로 주입한다.
