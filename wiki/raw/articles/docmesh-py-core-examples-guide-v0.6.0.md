---
source_url: https://github.com/kyundae-kim/docmesh-py-core/wiki/Examples-v0.6.0
ingested: 2026-08-01
sha256: acde3de5bfcc85ba29960890ce9b01fcb73f6de83dc99252e7b2b5f0085473af
---
# docmesh-py-core 소비자 예제

이 문서는 복사 후 환경에 맞게 수정할 수 있는 통합 예제를 제공한다. 정확한 signature와 오류는 [공개 API 레퍼런스](./api.md), 모든 환경변수는 [설정 가이드](./config.md), 시작용 template은 [`.env.example`](../.env.example)을 참고한다.

## 0. 설치와 기본 원칙

```bash
uv add git+https://github.com/kyundae-kim/docmesh-py-core.git@v0.6.0
```

- 설정과 `RuntimePlan`은 `docmesh_config`에서 import한다.
- client와 lifecycle API는 `docmesh_py_core` package root에서 import한다.
- 서비스 설정은 constructor kwargs가 아니라 프로세스 환경변수에서 읽는다.
- 일반 애플리케이션은 `RuntimePlan` + `service_lifespan()`을 우선 사용한다.
- token, password, DSN, `connect_kwargs`를 출력하지 않는다.

## 1. 최소 SQLite 비동기 runtime

환경:

```dotenv
DOCMESH_ENV=development
SQLITE_PATH=:memory:
```

애플리케이션:

```python
import asyncio

from docmesh_config import RuntimePlan, Service
from docmesh_py_core import service_lifespan


async def main() -> None:
    plan = RuntimePlan(services=(Service.SQLITE.required(),))
    async with service_lifespan(plan=plan) as runtime:
        sqlite = runtime.require(Service.SQLITE)
        with sqlite.connect() as connection:
            value = connection.exec_driver_sql("SELECT 1").scalar_one()
        assert value == 1


if __name__ == "__main__":
    asyncio.run(main())
```

`service_lifespan()`이 SQLite engine을 종료한다. `runtime.require()`는 lifecycle wrapper를 반환하며 wrapper는 concrete SQLAlchemy API를 전달한다.

## 2. FastAPI lifespan과 readiness

FastAPI는 이 라이브러리의 dependency가 아니므로 소비 애플리케이션에서 별도로 설치한다. 필수 서비스 실패, optional 서비스 실패, 전체 timeout 모두 readiness endpoint에서 2xx를 반환하면 안 된다.

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from docmesh_config import HealthcheckPolicy, RuntimePlan, Service
from docmesh_py_core import HealthCheckError, serialize_error, service_lifespan

plan = RuntimePlan(
    services=(Service.POSTGRES.required(), Service.MINIO.optional()),
    healthcheck=HealthcheckPolicy(
        on_startup=True,
        parallel=True,
        timeout_seconds=5,
        overall_timeout_seconds=15,
    ),
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with service_lifespan(plan=plan) as runtime:
        app.state.services = runtime
        yield


app = FastAPI(lifespan=lifespan)


@app.get("/ready")
async def readiness() -> JSONResponse:
    try:
        result = await app.state.services.check(
            parallel=True,
            timeout_seconds=5,
            overall_timeout_seconds=15,
        )
    except HealthCheckError as exc:
        payload = exc.result.to_dict() if exc.result is not None else {
            "ok": False,
            "services": [exc.status.to_dict()],
        }
        return JSONResponse(payload, status_code=503)
    except Exception as exc:
        # overall timeout처럼 HealthCheckResult로 변환되지 않은 실패도 503이다.
        return JSONResponse(serialize_error(exc), status_code=503)
    return JSONResponse(result.to_dict(), status_code=200 if result.ok else 503)
```

서비스별 timeout은 실패 status가 되지만 전체 timeout은 `asyncio.TimeoutError`로 전파될 수 있다. 위 endpoint는 두 경로를 모두 503으로 매핑한다.

## 3. 동기 CLI·batch

NATS와 timeout startup policy가 없는 동기 통합에서만 `assemble_services()`를 사용한다.

```python
from docmesh_config import RuntimePlan, Service
from docmesh_py_core import assemble_services


def run_report() -> None:
    plan = RuntimePlan(services=(Service.POSTGRES.required(),))
    with assemble_services(plan=plan) as services:
        postgres = services.require(Service.POSTGRES)
        with postgres.connect() as connection:
            row_count = connection.exec_driver_sql(
                "SELECT COUNT(*) FROM documents"
            ).scalar_one()
        print(f"documents={row_count}")


if __name__ == "__main__":
    run_report()
```

## 4. Concrete client 타입 검증

```python
import asyncio

from sqlalchemy.engine import Engine
from docmesh_config import RuntimePlan, Service
from docmesh_py_core import service_lifespan


async def main() -> None:
    plan = RuntimePlan(services=(Service.POSTGRES.required(),))
    async with service_lifespan(plan=plan) as runtime:
        engine = runtime.require_client(Service.POSTGRES, Engine)
        with engine.connect() as connection:
            connection.exec_driver_sql("SELECT 1")


if __name__ == "__main__":
    asyncio.run(main())
```

타입이 다르면 `ServiceClientTypeError`가 발생한다. 선택/초기화 실패를 구분하려면 `get_client()`보다 `require()`/`require_client()`를 사용한다.

## 5. Direct factory: SQLite

단일 서비스 CLI나 SDK 세부 API가 필요한 경우 direct factory를 사용할 수 있다.

```python
from docmesh_config import SqliteConfig
from docmesh_py_core import create_sqlite_client


def main() -> None:
    config = SqliteConfig()
    sqlite = create_sqlite_client(config)
    try:
        sqlite.check()
        with sqlite.connect() as connection:
            connection.exec_driver_sql("SELECT 1")
    finally:
        sqlite.close()


if __name__ == "__main__":
    main()
```

`SqliteConfig()`는 `SQLITE_*` 환경변수를 직접 읽는다. `SqliteConfig(path=...)` 같은 kwargs 주입은 거부된다.

## 6. NATS lazy connection과 소유권

```python
import asyncio

from docmesh_config import NatsConfig
from docmesh_py_core import create_nats_client


async def main() -> None:
    builder = create_nats_client(NatsConfig())

    # 임시 연결을 열어 flush한 뒤 내부에서 닫는다.
    await builder.check()

    # connect()가 반환한 persistent connection은 호출자가 소유한다.
    connection = await builder.connect()
    try:
        await connection.publish("documents.created", b'{"id":"doc-1"}')
        await connection.flush()
    finally:
        await connection.drain()


if __name__ == "__main__":
    asyncio.run(main())
```

`builder.check()` 반환값은 이미 닫힌 임시 connection일 수 있으므로 재사용하지 않는다. `builder.close()`는 no-op이다. credential이 포함될 수 있는 `builder.connect_kwargs`를 로그에 남기지 않는다.

## 7. Runtime 상태 정책 재실행

```python
import asyncio

from docmesh_config import (
    HealthcheckPolicy,
    RuntimePlan,
    Service,
    StartupFailureMode,
)
from docmesh_py_core import service_lifespan


async def main() -> None:
    plan = RuntimePlan(services=(Service.SQLITE.required(),))
    async with service_lifespan(plan=plan) as runtime:
        result = await runtime.check_with_policy(
            HealthcheckPolicy(
                on_startup=False,
                parallel=True,
                attempts=3,
                retry_delay_seconds=0.5,
                failure_mode=StartupFailureMode.REPORT,
            )
        )
        if not result.ok:
            print("runtime is not ready")


if __name__ == "__main__":
    asyncio.run(main())
```

명시적 `check_with_policy()`는 `on_startup=False`여도 실행하며 runtime을 닫지 않는다.

## 8. Keycloak token 획득과 JWT 사용자 정보

```python
from docmesh_config import KeycloakConfig
from docmesh_py_core import KeycloakAuthService


def authenticate(username: str, password: str, bearer_token: str) -> str:
    auth = KeycloakAuthService(KeycloakConfig())
    token = auth.fetch_access_token(username=username, password=password)
    user = auth.extract_user_info(bearer_token)

    # access_token/refresh_token 원문은 출력하지 않는다.
    assert token.expires_in > 0
    return user.sub
```

기본 grant는 `password`이므로 call-time credential 또는 `KEYCLOAK_TOKEN_USERNAME`/`KEYCLOAK_TOKEN_PASSWORD`가 필요하다. `client_credentials`를 사용할 때는 `KEYCLOAK_CLIENT_SECRET`을 설정한다.

## 9. Keycloak provisioning

`admin_client`는 애플리케이션 adapter이며 네 가지 `ensure_*` 메서드를 구현해야 한다.

```python
from typing import Literal, Protocol

from docmesh_config import KeycloakConfig
from docmesh_py_core import KeycloakProvisioner, ProvisioningResult


ProvisioningState = Literal["created", "updated", "unchanged"]


class AdminClient(Protocol):
    def ensure_realm(self, config: KeycloakConfig) -> ProvisioningState: ...
    def ensure_client(self, config: KeycloakConfig) -> ProvisioningState: ...
    def ensure_realm_role(
        self, realm: str, role_name: str
    ) -> ProvisioningState: ...
    def ensure_client_role(
        self, realm: str, client_id: str, role_name: str
    ) -> ProvisioningState: ...


def provision(admin_client: AdminClient) -> ProvisioningResult:
    config = KeycloakConfig()
    if not config.provisioning_enabled:
        raise RuntimeError("Keycloak provisioning is disabled")

    result = KeycloakProvisioner(
        config,
        admin_client=admin_client,
    ).provision()
    if result.failed:
        failed_resources = [name for name, _error in result.failed]
        raise RuntimeError({"failed_resources": failed_resources})
    return result
```

`KeycloakProvisioner` 자체는 `provisioning_enabled`를 gate로 검사하지 않으므로 호출자가 확인한다. `KEYCLOAK_PROVISIONING_DRY_RUN=true`이면 원격 호출 없이 `planned`만 채운다. admin 인증은 service-account secret 또는 username/password 중 정확히 하나의 모드를 사용한다.

## 10. 로깅과 lifecycle observer

```python
import asyncio
import logging

from docmesh_config import RuntimePlan, Service
from docmesh_py_core import LifecycleEvent, configure_logging, service_lifespan


def observe(event: LifecycleEvent) -> None:
    logging.getLogger("app.lifecycle").info(
        "docmesh_lifecycle",
        extra={"lifecycle": event.to_dict()},
    )


async def main() -> None:
    configure_logging(log_path="logs/app.log")
    plan = RuntimePlan(services=(Service.SQLITE.required(),))
    async with service_lifespan(plan=plan, observer=observe):
        pass


if __name__ == "__main__":
    asyncio.run(main())
```

명시적 `level`이 `DOCMESH_LOG_LEVEL`보다 우선한다. observer에서 예외가 발생해도 lifecycle 결과는 바뀌지 않는다.

## 11. 오류를 API 응답으로 변환

```python
from docmesh_py_core import DocMeshError, serialize_error


def to_error_response(error: BaseException) -> tuple[dict[str, object], int]:
    payload = serialize_error(error)
    status = 503 if isinstance(error, DocMeshError) else 500
    return payload, status
```

`serialize_error()`는 구조화 상세를 JSON-safe하게 보존하고 알려진 민감값을 마스킹한다. 호출자가 직접 만든 generic exception 메시지에 secret을 넣지 않는 책임은 남아 있다.

## 12. 서비스 카탈로그와 설정 문서 생성

```python
from docmesh_config import Service
from docmesh_py_core import (
    SERVICE_CATALOG,
    generate_configuration_reference,
    generate_environment_template,
)


def inspect_catalog() -> None:
    sqlite = SERVICE_CATALOG[Service.SQLITE]
    required_keys = [item.key for item in sqlite.required_environment()]
    assert required_keys == ["SQLITE_PATH"]

    env_template = generate_environment_template()
    markdown_reference = generate_configuration_reference()
    assert "SQLITE_PATH=" in env_template
    assert "`SQLITE_PATH`" in markdown_reference
```

생성 결과는 deterministic하며 secret 원문을 포함하지 않는다. 소비자용 설명과 common/logging 변수는 [설정 가이드](./config.md)와 [`.env.example`](../.env.example)을 기준으로 한다.

## 13. Empty runtime

서비스 기능이 비활성화된 배포에서 별도 분기용 runtime으로 사용할 수 있다.

```python
import asyncio

from docmesh_py_core import create_empty_service_runtime


async def main() -> None:
    runtime = create_empty_service_runtime()
    try:
        result = await runtime.check()
        assert result.to_dict() == {"ok": True, "services": []}
    finally:
        await runtime.close()


if __name__ == "__main__":
    asyncio.run(main())
```
