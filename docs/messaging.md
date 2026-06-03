# NATS 메시징 적용 가이드

## 목적

`fastapi-core` 기반 서비스 간 통신을 동기 HTTP 중심에서 비동기 이벤트 기반으로 확장하기 위해 NATS를 적용합니다.

- 서비스 간 결합도 감소
- 처리량 증가 시 수평 확장 용이
- 이벤트 중심 도메인 아키텍처 기반 마련

---

## 1) NATS 클라이언트 라이브러리 설치

패키지 의존성에 `nats-py`를 추가합니다.

```bash
# uv
uv add nats-py

# pip
pip install nats-py
```

`pyproject.toml` 예시:

```toml
dependencies = [
  # ...
  "nats-py>=2.9.0",
]
```

---

## 2) 환경설정

`EnvConfig`에 NATS 설정을 추가하여 환경 변수로 주입합니다.

권장 환경 변수:

| 변수명 | 타입 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `NATS__SERVERS` | `str` (콤마 구분) | `nats://nats:4222` | NATS 서버 목록 |
| `NATS__NAME` | `str` | `fastapi-core` | NATS 연결 이름 |
| `NATS__CONNECT_TIMEOUT` | `int` | `2` | 연결 타임아웃(초) |
| `NATS__MAX_RECONNECT_ATTEMPTS` | `int` | `60` | 재연결 최대 시도 횟수 |
| `NATS__RECONNECT_TIME_WAIT_MS` | `int` | `2000` | 재연결 간격(ms) |
| `NATS__QUEUE_GROUP` | `str` | `default-workers` | 기본 큐 그룹 |

`.env` 예시:

```dotenv
NATS__SERVERS=nats://nats:4222,nats://nats-2:4222
NATS__NAME=docmesh-fastapi-core
NATS__CONNECT_TIMEOUT=2
NATS__MAX_RECONNECT_ATTEMPTS=60
NATS__RECONNECT_TIME_WAIT_MS=2000
NATS__QUEUE_GROUP=docmesh-workers
```

---

## 3) Publish/Subscribe 샘플

### 3.1 연결/종료 (lifespan)

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
    yield
    await app.state.nats_client.drain()

app = create_app(config=config, lifespan=lifespan)
```

### 3.1.1 FastAPI dependency로 주입

`get_nats_client`는 `GetNatsClientDependency` class instance가 아니라 함수형 dependency입니다. 라우터에서는 `Depends(get_nats_client)`를 직접 사용합니다.

```python
import nats.aio.client
from fastapi import APIRouter, Depends

from fastapi_core.dependencies.messaging import get_nats_client

router = APIRouter()

@router.post("/events/{subject}")
async def publish_event(
    subject: str,
    nc: nats.aio.client.Client = Depends(get_nats_client),
):
    await nc.publish(subject, b"{}")
    return {"status": "published"}
```

### 3.2 이벤트 발행

```python
import json

async def publish_order_created(nc, order_id: str, user_id: str) -> None:
    subject = "orders.created"
    payload = {
        "event": "orders.created",
        "order_id": order_id,
        "user_id": user_id,
    }
    await nc.publish(subject, json.dumps(payload).encode("utf-8"))
```

### 3.3 이벤트 구독

```python
import json

async def subscribe_orders_created(nc):
    async def handler(msg):
        data = json.loads(msg.data.decode("utf-8"))
        # 후속 처리 (예: 알림 발송, 인덱싱, 집계)
        print("received:", msg.subject, data)

    await nc.subscribe("orders.created", queue="docmesh-workers", cb=handler)
```

---

## 4) 주요 도메인 서비스 적용 패턴

도메인 서비스는 트랜잭션 완료 후 이벤트를 발행하는 구조를 권장합니다.

```python
class OrderService:
    def __init__(self, order_repo, nats_client):
        self.order_repo = order_repo
        self.nats = nats_client

    async def create_order(self, dto):
        order = self.order_repo.create(dto)  # DB commit 이후

        await self.nats.publish(
            "orders.created",
            json.dumps(
                {
                    "event": "orders.created",
                    "order_id": order.id,
                    "customer_id": order.customer_id,
                }
            ).encode("utf-8"),
        )
        return order
```

권장 Subject 네이밍:

- `<domain>.<entity>.created`
- `<domain>.<entity>.updated`
- `<domain>.<entity>.deleted`

예:

- `billing.invoice.created`
- `users.profile.updated`
- `documents.file.deleted`

---

## 5) 테스트 전략

### 단위 테스트

- NATS 클라이언트를 `AsyncMock`으로 대체
- `publish` 호출 subject/payload 검증
- 예외(연결 실패, publish 실패) 경로 검증

### 통합 테스트

- 테스트 NATS 서버(또는 devcontainer 내 NATS) 연결
- 실제 pub/sub round-trip 검증
- queue group 기반 다중 소비자 분배 검증

예시:

```bash
# 전체 테스트
uv run pytest -q

# NATS 관련 테스트만 실행 (파일/마커 기준)
uv run pytest -q -k nats
```

---

## 6) 운영 고려사항

- 재연결 로깅 및 모니터링(연결 상태 이벤트 핸들러)
- 메시지 스키마 버전 필드(`schema_version`) 포함
- 멱등성 키(`event_id`) 기반 중복 처리 방지
- 점진적 도입: 핵심 도메인부터 이벤트 발행 후 구독자 확장
