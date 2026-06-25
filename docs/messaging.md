# fastapi-core 메시징 정의서

> 문서 목적: `fastapi-core`에서 메시징을 **FastAPI lifecycle과 어떻게 통합할지** 정의한다.
> 기준 문서: `docs/prd.md`, `docs/srs.md`, `docs/api.md`, `docs/config.md`
> 문서 상태: 초안(v0.2)

---

## 1. 문서 개요

이 문서는 NATS 자체의 일반론보다, `fastapi-core`가 FastAPI 앱 계층에서 메시징을 어떻게 다뤄야 하는지에 초점을 둔다.

핵심 질문은 다음과 같다.

- NATS 연결을 어디서 초기화할 것인가?
- request handler가 연결 객체를 어떻게 참조할 것인가?
- startup / shutdown과 어떤 관계를 가져야 하는가?
- health/readiness에 어떻게 반영할 것인가?

---

## 2. 메시징의 위치

`fastapi-core`에서 메시징은 독립 기능이 아니라 **FastAPI 앱 lifecycle에 연결되는 인프라 기능**이다.

권장 흐름:

1. `create_app(...)` 또는 외부 lifespan 정의
2. startup 단계에서 NATS builder/connect 수행
3. 필요 시 `app.state`에 연결 객체 저장
4. route / dependency / service layer가 이를 사용
5. shutdown 단계에서 연결 종료

즉, 메시징은 단순 builder API가 아니라 **앱 수명주기 자원**으로 다뤄야 한다.

---

## 3. FastAPI 통합 요구사항

### 3.1 Startup integration

- 메시징 연결은 request 처리 도중 즉석 생성보다 startup 단계 초기화를 우선해야 한다.
- `create_app(..., lifespan=...)`와 결합 가능해야 한다.
- 연결 실패 시 서비스 기동 차단 여부는 앱 정책으로 결정 가능해야 한다.

### 3.2 Shutdown integration

- 종료 시 열린 NATS 연결을 정상 close 해야 한다.
- 종료 실패가 있더라도 프로세스 종료를 과도하게 방해하지 않아야 한다.

### 3.3 App state integration

- 연결 객체 또는 builder를 `app.state`에 저장할 수 있어야 한다.
- dependency 계층에서 `request.app.state`를 통해 접근하는 패턴을 허용해야 한다.

---

## 4. Public surface

## 4.1 `ServiceFactoryRegistry(settings)`

- `create_client("nats")`를 지원해야 한다.
- FastAPI startup 코드에서 직접 호출 가능해야 한다.

## 4.2 `NatsConnectionBuilder`

메시징의 FastAPI 통합 진입점이다.

### 기대 역할
- 설정을 바탕으로 async 연결 준비
- `await connect()` 또는 동등한 메서드 제공
- `await check()` 또는 동등한 readiness 메서드 제공
- 종료 메서드 또는 종료 대상 객체 반환

---

## 5. Recommended FastAPI pattern

### 5.1 Lifespan 기반 패턴

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    # registry / builder / connect
    # app.state.nats = connection
    yield
    # close connection
```

이 패턴이 가장 권장된다. 이유는 다음과 같다.

- startup/shutdown 위치가 명확함
- 테스트에서 대체하기 쉬움
- health/readiness와 연계가 쉬움

### 5.2 Route handler 직접 연결 금지 원칙

route handler 내부에서 매 요청마다 NATS 연결을 새로 만드는 방식은 권장하지 않는다.

이유:
- 연결 비용 증가
- 장애 분석 어려움
- lifecycle 관리 분산

---

## 6. Health / readiness 연계

### 6.1 Readiness

FastAPI의 `/health/readiness`는 메시징이 필수 의존성일 경우 NATS 준비 상태를 반영할 수 있어야 한다.

예:
- startup 때 연결된 NATS 객체가 존재하는지
- `flush()` 또는 동등한 lightweight check 성공 여부

### 6.2 Optional dependency

NATS가 선택 의존성인 서비스라면 readiness 실패가 전체 서비스 실패를 의미하지 않을 수 있다. 이 경우:

- 응답에는 실패 정보를 남긴다.
- 서비스 기동 자체는 유지할 수 있다.

---

## 7. Dependency / handler integration

메시징 사용 방식은 보통 두 가지다.

### 방식 A. app.state 직접 참조
- startup에서 `app.state.nats` 저장
- route/service layer에서 참조

### 방식 B. dependency 래핑
- `get_nats_connection(request: Request)` 같은 dependency 제공
- endpoint는 `Depends(...)`로 주입

`fastapi-core`는 최소한 A를 허용하고, 필요 시 B를 후속 확장으로 둘 수 있다.

---

## 8. 설정 계약 요약

핵심 환경변수:

- `NATS_SERVERS`
- `NATS_NAME`
- `NATS_CONNECT_TIMEOUT_SECONDS`
- `NATS_MAX_RECONNECT_ATTEMPTS`
- `NATS_USER`
- `NATS_PASSWORD`
- `NATS_TOKEN`
- `NATS_CREDS_FILE`

핵심 규칙:

- 서버 목록은 쉼표 구분
- 인증 방식은 user/password, token, creds file 중 최소 하나
- timeout/reconnect는 양의 정수
- 민감정보는 로그에 노출 금지

세부 내용은 `docs/config.md`를 따른다.

---

## 9. 오류 처리 기준

### 설정 오류
- 서버 목록 누락
- 인증 방식 누락
- 잘못된 timeout/reconnect 값

### startup 오류
- 브로커 도달 불가
- 인증 실패
- 연결 timeout

### runtime 오류
- 연결 끊김
- 재연결 실패
- publish/flush 실패

FastAPI 계층에서의 원칙:
- startup 오류는 기동 실패 또는 degraded startup 정책으로 처리
- runtime 오류는 route/service 레벨에서 포착하되 민감정보는 마스킹

---

## 10. 테스트 포인트

- lifespan startup에서 연결 성공
- lifespan shutdown에서 정상 close
- 연결 실패 시 startup 정책 검증
- readiness에 메시징 상태 반영 여부 검증
- request handler가 state/dependency를 통해 연결 참조 가능한지 검증

---

## 11. 오픈 이슈

- `fastapi-core`가 `get_nats_connection` 같은 FastAPI dependency를 공식 제공할지 결정 필요
- readiness에 NATS를 기본 포함할지 서비스별 선택으로 둘지 결정 필요
- publisher/subscriber helper를 app layer 범위에 포함할지 결정 필요

---

## 12. 참고 문서

- `docs/prd.md`
- `docs/srs.md`
- `docs/api.md`
- `docs/config.md`
- `pyproject.toml`

---

## 부록 A. 문서 상태 메모

이 문서는 NATS 자체 설명보다 FastAPI startup/shutdown 및 app.state 연계에 초점을 두고 다시 작성했다. 실제 구현 코드가 추가되면 builder 메서드명과 dependency 제공 범위를 코드 기준으로 다시 맞춰야 한다.