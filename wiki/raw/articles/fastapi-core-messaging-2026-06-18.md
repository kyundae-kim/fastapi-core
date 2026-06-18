---
source_url: file:///workspaces/fastapi-core/docs/messaging.md
ingested: 2026-06-18
sha256: 78687d6d45206b3b3c7631223faf7b5aac08b9722deab8407c0a35f3ed06846f
---
# NATS 메시징 가이드

## 개요

`fastapi-core`는 NATS 연동을 두 층으로 제공합니다.

1. **core helper**: `fastapi_core.core.messaging`
   - 순수 NATS 클라이언트 생성
   - subject 검증/조합
   - JSON publish / subscribe helper
2. **FastAPI dependency helper**: `fastapi_core.dependencies.messaging`
   - `app.state.nats_client` 캐시
   - docmesh registry 기반 lazy singleton 조회

---

## 설정

소스 설정 모델: `fastapi_core.core.config.NatsConfig`

| 변수명 | 타입 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `NATS__SERVERS` | `str` (콤마 구분) | `nats://nats:4222` | 서버 목록 원본 문자열 |
| `NATS__NAME` | `str` | `fastapi-core` | 연결 이름 |
| `NATS__CONNECT_TIMEOUT` | `int` | `2` | 연결 timeout(초) |
| `NATS__MAX_RECONNECT_ATTEMPTS` | `int` | `60` | 최대 재연결 횟수 |
| `NATS__RECONNECT_TIME_WAIT_MS` | `int` | `2000` | 재연결 대기 시간(ms) |
| `NATS__QUEUE_GROUP` | `str` | `default-workers` | 기본 queue group |

`NatsConfig.server_list`는 `NATS__SERVERS`를 분리한 계산 프로퍼티이며,
`create_nats_client()`는 이 값을 그대로 `nats.connect(servers=...)`에 전달합니다.

예시:

```dotenv
NATS__SERVERS=nats://nats:4222,nats://nats-2:4222
NATS__NAME=fastapi-core
NATS__CONNECT_TIMEOUT=2
NATS__MAX_RECONNECT_ATTEMPTS=60
NATS__RECONNECT_TIME_WAIT_MS=2000
NATS__QUEUE_GROUP=default-workers
```

---

## Core helper API

### 클라이언트 생성

```python
from fastapi_core.core.config import NatsConfig
from fastapi_core.core.messaging import create_nats_client

config = NatsConfig()
client = await create_nats_client(config)
```

동작:

- `servers=config.server_list`
- `name=config.name`
- `connect_timeout=config.connect_timeout`
- `max_reconnect_attempts=config.max_reconnect_attempts`
- `reconnect_time_wait=config.reconnect_time_wait_ms / 1000`

### Subject 규칙

이벤트 subject는 반드시 **3 segment** 형식이어야 합니다.

```text
<domain>.<entity>.<action>
```

각 segment는 다음만 허용됩니다.

- 소문자 영문자
- 숫자
- 하이픈(`-`)

예:

- `orders.order.created`
- `billing.invoice.updated`
- `documents.file.deleted`

잘못된 예:

- `orders.created`  # segment 2개
- `Orders.order.created`  # 대문자 포함
- `orders.order.created.v2`  # segment 4개

### Subject 조합/검증

```python
from fastapi_core.core.messaging import build_event_subject, validate_event_subject

subject = build_event_subject("orders", "order", "created")
assert subject == "orders.order.created"
assert validate_event_subject(subject) is True
```

`build_event_subject()`는 결과가 규칙에 맞지 않으면 `ValueError`를 발생시킵니다.

### 이벤트 발행

```python
from fastapi_core.core.messaging import build_event_subject, publish_event

subject = build_event_subject("orders", "order", "created")
await publish_event(
    client,
    subject,
    {
        "event_id": "order-created:123",
        "event": subject,
        "order_id": "123",
        "user_id": "u-1",
    },
)
```

동작:

- subject 유효성 검증
- payload를 compact JSON UTF-8 bytes로 인코딩
- `client.publish(subject, encoded_payload)` 호출

### 이벤트 구독

```python
from fastapi_core.core.messaging import subscribe_event, subscribe_queue_event

async def handler(subject: str, payload: dict[str, object]) -> None:
    print(subject, payload)

await subscribe_event(client, "orders.order.created", handler)
await subscribe_queue_event(client, "orders.order.created", "default-workers", handler)
```

동작:

- 수신 payload를 JSON decode
- `handler(subject, payload)` 호출
- handler가 async 함수면 await

---

## FastAPI 통합

### `set_nats_client`

```python
from fastapi import FastAPI
from fastapi_core.core.config import EnvConfig
from fastapi_core.dependencies.messaging import set_nats_client

config = EnvConfig()
app = FastAPI()

await set_nats_client(app, config=config)
```

현재 구현 기준:

- `client=`를 직접 넘기면 그대로 `app.state.nats_client`에 저장
- `config=`를 넘기면 `get_required_docmesh_service_async(app, "nats_client", config=config)` 결과를 저장
- 둘 다 없으면 `ValueError`

즉, FastAPI dependency 레이어는 `create_nats_client()`를 직접 호출하지 않고 **docmesh registry 기반 서비스 해석**을 사용합니다.

### `get_nats_client`

```python
import nats.aio.client
from fastapi import APIRouter, Depends
from fastapi_core.dependencies.messaging import get_nats_client

router = APIRouter()

@router.post("/events")
async def publish_sample(
    nc: nats.aio.client.Client = Depends(get_nats_client),
):
    await nc.publish("orders.order.created", b"{}")
    return {"status": "published"}
```

동작:

- `app.state.nats_client`가 있으면 재사용
- 없으면 docmesh registry로 생성하고 state에 저장
- 함수형 dependency이며 `GetNatsClientDependency` 같은 callable class는 없습니다

---

## lifespan 예시

### managed lifespan 사용 시

`create_app()` 기본값은 `create_managed_lifespan(config, settings)`를 사용합니다.
`settings.lifecycle.eager_nats = true`면 startup에서 NATS를 선행 초기화할 수 있습니다.

### 수동 lifespan 예시

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

from fastapi_core.core.config import EnvConfig
from fastapi_core.dependencies.messaging import set_nats_client
from fastapi_core.factory import create_app

config = EnvConfig()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await set_nats_client(app, config=config)
    try:
        yield
    finally:
        await app.state.nats_client.drain()

app = create_app(config=config, lifespan=lifespan)
```

---

## 도메인 이벤트 예시

```python
from fastapi_core.core.messaging import build_event_subject, publish_event

class OrderEvents:
    def __init__(self, nats_client):
        self.nats = nats_client

    async def order_created(self, order_id: str, customer_id: str) -> None:
        subject = build_event_subject("orders", "order", "created")
        await publish_event(
            self.nats,
            subject,
            {
                "event_id": f"order-created:{order_id}",
                "event": subject,
                "order_id": order_id,
                "customer_id": customer_id,
            },
        )
```

권장 사항:

- `event_id` 같은 멱등성 키를 포함
- payload에 `event` 또는 `schema_version` 필드를 포함
- subject는 helper로 생성해 규칙 위반을 방지

---

## 테스트 포인트

현재 저장소의 NATS 관련 테스트:

- `test_fastapi_core/core/test_messaging.py`
  - `create_nats_client`
  - `validate_event_subject`
  - `build_event_subject`
  - `publish_event`
  - `subscribe_event`
  - `subscribe_queue_event`
- `test_fastapi_core/dependencies/test_messaging.py`
  - `set_nats_client`
  - `get_nats_client`
  - 함수형 dependency 정책

실행 예:

```bash
uv run pytest -q test_fastapi_core/core/test_messaging.py test_fastapi_core/dependencies/test_messaging.py
```
