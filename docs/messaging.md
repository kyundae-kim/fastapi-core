# fastapi-core 메시징 정의서

> 문서 목적: `fastapi-core`의 메시징 통합 범위와 NATS 기반 연결/운영 계약을 정의한다.
> 기준 문서: `docs/prd.md`, `docs/srs.md`, `docs/api.md`, `docs/config.md`
> 문서 상태: 초안(v0.1)

---

## 1. 문서 개요

- 문서명: `fastapi-core 메시징 정의서`
- 작성일: `2026-06-25`
- 작성자: `Hermes Agent 초안 / 사용자 검토 필요`
- 버전: `v0.1`
- 상태: `draft`

### 1.1 목적

이 문서는 `fastapi-core`가 제공하는 메시징 통합의 범위, 설정 계약, 공개 API 진입점, 연결 수명주기, 헬스체크, 오류 처리, 운영 원칙을 정의한다. 현재 범위의 메시징 통합은 **NATS**를 중심으로 한다.

### 1.2 범위

다음 항목을 포함한다.

- NATS 연결 설정 계약
- `ServiceFactoryRegistry`를 통한 NATS 연결 진입점
- `NatsConnectionBuilder` 사용 방식
- 메시징 헬스체크 정책
- 운영 보안 및 장애 대응 원칙
- 애플리케이션이 상위 레이어에서 정의해야 하는 책임 경계

### 1.3 비범위

다음은 본 문서의 직접 범위가 아니다.

- 각 서비스의 도메인 이벤트 스키마 설계
- 메시지 페이로드 버전 관리 정책 전체
- 소비자 비즈니스 로직 구현
- DLQ, exactly-once, saga orchestration 같은 고수준 분산 시스템 패턴의 세부 구현
- Kafka, RabbitMQ 등 NATS 이외 브로커 지원

---

## 2. 메시징 목표

`fastapi-core`의 메시징 통합은 다음 목표를 가진다.

- FastAPI 서비스가 공통 방식으로 메시징 연결을 초기화할 수 있어야 한다.
- 메시징 연결 설정을 환경변수 계약으로 일관되게 관리해야 한다.
- 인증 방식(user/password, token, creds file)을 표준화해야 한다.
- 서비스는 연결 상태를 헬스체크에서 진단할 수 있어야 한다.
- 민감정보가 로그나 진단 출력에 노출되지 않아야 한다.
- 도메인 이벤트 설계와 메시징 인프라 연결 책임을 분리해야 한다.

---

## 3. 아키텍처 상 위치

메시징 통합은 `fastapi-core` 내에서 다음 흐름으로 사용된다.

1. 애플리케이션이 `load_settings(env)`로 설정을 로드한다.
2. `Settings.nats` 또는 동등한 하위 설정 객체가 구성된다.
3. 애플리케이션이 `ServiceFactoryRegistry(settings)`를 생성한다.
4. `registry.create_client("nats")` 호출 시 `NatsConnectionBuilder`를 얻는다.
5. 실제 연결은 `await connect()` 또는 `await check()`에서 수행된다.
6. 애플리케이션은 상위 레이어에서 publisher/subscriber를 조립한다.

이 구조는 **연결 인프라**를 `fastapi-core`가 담당하고, **이벤트 의미와 소비 로직**은 각 서비스가 담당하도록 경계를 나눈다.

---

## 4. 공개 API 관점 정의

## 4.1 `ServiceFactoryRegistry(settings)`

메시징 통합은 registry 패턴을 통해 접근한다.

### 메시징 관련 요구사항
- `create_client("nats")`를 지원해야 한다.
- 지원하지 않는 서비스명은 `UnsupportedServiceError`로 처리해야 한다.
- 메시징 통합은 다른 서비스와 동일하게 설정 기반으로 생성되어야 한다.

## 4.2 `NatsConnectionBuilder`

NATS 연결용 비동기 builder다.

### 역할
- 설정을 기반으로 실제 NATS 클라이언트 연결을 준비한다.
- 즉시 연결된 클라이언트 대신 지연 연결(lazy connect가 아니라 explicit connect 시점 분리) 형태의 builder를 반환할 수 있다.
- async 애플리케이션 시작 수명주기와 자연스럽게 결합될 수 있어야 한다.

### 기대 인터페이스
- `await connect()` 또는 동등한 연결 메서드
- `await check()` 또는 동등한 연결 상태 확인 메서드
- `close()` 또는 동등한 종료 메서드가 필요할 수 있다

> 주의: 실제 메서드명과 시그니처는 구현 코드 기준으로 최종 확정되어야 한다.

---

## 5. NATS 설정 계약

## 5.1 기본 환경변수

| 환경변수 | 필수 여부 | 타입 | 설명 |
| --- | --- | --- | --- |
| `NATS_SERVERS` | 필수 | string | 쉼표 구분 서버 목록 |
| `NATS_NAME` | 선택 | string | 연결 이름 |
| `NATS_CONNECT_TIMEOUT_SECONDS` | 선택 | int | 연결 timeout |
| `NATS_MAX_RECONNECT_ATTEMPTS` | 선택 | int | 최대 재연결 횟수 |

## 5.2 인증 환경변수

다음 세 방식 중 하나를 사용한다.

### 방식 A. user/password

| 환경변수 | 필수 여부 | 타입 | 설명 |
| --- | --- | --- | --- |
| `NATS_USER` | 조건부 | string | 사용자명 |
| `NATS_PASSWORD` | 조건부 | string | 비밀번호 |

### 방식 B. token

| 환경변수 | 필수 여부 | 타입 | 설명 |
| --- | --- | --- | --- |
| `NATS_TOKEN` | 조건부 | string | 토큰 기반 인증값 |

### 방식 C. creds file

| 환경변수 | 필수 여부 | 타입 | 설명 |
| --- | --- | --- | --- |
| `NATS_CREDS_FILE` | 조건부 | string | NATS creds file 경로 |

## 5.3 설정 규칙

- `NATS_SERVERS`는 최소 하나 이상의 서버 URL을 포함해야 한다.
- 여러 서버는 쉼표로 구분한다.
- 인증 방식은 위 세 가지 중 적어도 하나를 만족해야 한다.
- 모순된 인증 설정이 함께 주어진 경우 설정 오류로 처리할 수 있어야 한다.
- timeout 및 재연결 값은 양의 정수여야 한다.

### 예시

```env
NATS_SERVERS=nats://nats-a:4222,nats://nats-b:4222
NATS_TOKEN=[REDACTED]
NATS_NAME=fastapi-core
NATS_CONNECT_TIMEOUT_SECONDS=3
NATS_MAX_RECONNECT_ATTEMPTS=10
```

---

## 6. 연결 및 수명주기 요구사항

## 6.1 연결 생성

- 애플리케이션은 registry를 통해 NATS builder를 획득해야 한다.
- builder는 설정 유효성에 문제가 있으면 명확한 설정 오류를 발생시켜야 한다.
- 실제 네트워크 연결은 async 시점에서 수행되어야 한다.

## 6.2 애플리케이션 시작 시점

권장 흐름:

1. 설정 로드
2. registry 생성
3. `registry.create_client("nats")`
4. 애플리케이션 startup 단계에서 `await builder.connect()` 또는 `await builder.check()`
5. publisher/subscriber 조립

## 6.3 종료 시점

- 애플리케이션 shutdown 단계에서 NATS 연결을 정상 종료해야 한다.
- `registry.close_all()`이 NATS 종료까지 포함할지, builder/connection 객체에서 별도 close를 수행할지는 구현 시 확정 필요하다.
- 종료 실패가 발생하더라도 애플리케이션 종료 자체를 불필요하게 막아서는 안 된다.

---

## 7. 헬스체크 요구사항

## 7.1 개별 헬스체크

NATS 헬스체크는 다음과 같은 기본 동작을 가져야 한다.

- 연결 생성 가능 여부 확인
- 연결 후 `flush()` 또는 동등한 확인 수행
- 실패 시 마스킹된 오류 메시지 반환

## 7.2 집계 헬스체크 연동

- NATS는 `check_all_services(...)` 집계 대상에 포함될 수 있어야 한다.
- 서비스별 결과에는 성공 여부, 지연 시간, 오류 메시지가 포함되어야 한다.
- NATS가 필수 서비스인지 선택 서비스인지는 애플리케이션이 결정한다.

## 7.3 필수/선택 서비스 정책

- **필수 서비스**로 지정된 경우: 실패 시 `HealthCheckError` 또는 동등한 예외를 유발할 수 있어야 한다.
- **선택 서비스**로 지정된 경우: 실패 정보는 결과에 포함하되 핵심 애플리케이션 흐름은 유지 가능해야 한다.

---

## 8. 이벤트 설계 책임 경계

`fastapi-core`는 메시징 **인프라 연결**을 제공하지만, 다음 책임은 상위 서비스에 있다.

- subject / topic 이름 규칙 정의
- 이벤트 페이로드 스키마 정의
- 버전 관리 전략
- 소비자 재처리 정책
- DLQ 전략
- 메시지 순서 보장 수준 결정
- exactly-once / at-least-once / at-most-once 정책 선택

즉, `fastapi-core`는 “NATS에 안전하게 연결하고 상태를 점검하는 기반”을 제공하고, “어떤 이벤트를 어떻게 발행/구독할지”는 서비스 설계가 결정한다.

---

## 9. 오류 처리 기준

## 9.1 설정 오류

다음은 설정 오류로 처리되어야 한다.

- `NATS_SERVERS` 누락
- 인증 방식 미지정
- 잘못된 timeout/reconnect 값
- creds file 경로 누락 또는 비정상 형식
- 상호 충돌하는 인증 설정

예시:

- `ConfigError: NATS_SERVERS is required`
- `ConfigError: NATS authentication requires one of user/password, token, or creds file`
- `ConfigError: NATS_CONNECT_TIMEOUT_SECONDS must be a positive integer`

## 9.2 연결 오류

다음은 연결/운영 오류로 처리되어야 한다.

- 네트워크 도달 불가
- 인증 실패
- 브로커 응답 지연 또는 timeout
- 재연결 한도 초과

오류 메시지는 다음 원칙을 따라야 한다.

- 어떤 서버/설정 범주에서 문제가 났는지 식별 가능해야 한다.
- token, password, creds file 내용은 노출되면 안 된다.
- 운영 분석에 필요한 최소 맥락은 유지해야 한다.

---

## 10. 보안 및 운영 원칙

- `NATS_TOKEN`, `NATS_PASSWORD`, creds file 내용은 로그에 원문으로 남기지 않는다.
- `build_settings_snapshot(settings)`에는 민감값이 마스킹된 형태로만 포함되어야 한다.
- creds file 경로는 필요 시 노출 가능하더라도 파일 내용은 절대 출력하면 안 된다.
- 운영 환경에서는 권한이 최소화된 인증 수단을 사용한다.
- 연결 재시도 정책은 무한 루프 대신 제한된 시도 횟수와 명확한 관측 포인트를 가져야 한다.

---

## 11. 권장 사용 패턴

## 11.1 최소 연결 예시

```python
from os import environ
from fastapi_core import load_settings, ServiceFactoryRegistry

settings = load_settings(environ)
registry = ServiceFactoryRegistry(settings)
builder = registry.create_client("nats")

# async startup hook 안에서
# connection = await builder.connect()
```

## 11.2 헬스체크 연동 예시

```python
result = check_all_services(
    {
        "nats": builder.check,
    },
    required_services=set(),
    parallel=False,
)
```

## 11.3 설정 예시

### token 기반

```env
NATS_SERVERS=nats://nats:4222
NATS_TOKEN=[REDACTED]
NATS_NAME=fastapi-core
NATS_CONNECT_TIMEOUT_SECONDS=3
NATS_MAX_RECONNECT_ATTEMPTS=10
```

### creds file 기반

```env
NATS_SERVERS=nats://nats-a:4222,nats://nats-b:4222
NATS_CREDS_FILE=/run/secrets/nats.creds
NATS_NAME=fastapi-core-prod
NATS_CONNECT_TIMEOUT_SECONDS=3
NATS_MAX_RECONNECT_ATTEMPTS=20
```

---

## 12. 테스트 포인트

메시징 통합은 최소 다음 항목을 검증해야 한다.

### 12.1 설정 검증
- `NATS_SERVERS` 누락 시 오류
- 인증 방식 누락 시 오류
- invalid timeout/reconnect 값 오류
- 쉼표 구분 서버 목록 파싱

### 12.2 연결 동작
- 정상 연결 성공
- 인증 실패 처리
- timeout 처리
- 재연결 횟수 제한 적용

### 12.3 헬스체크
- `check()` 성공 시 healthy 결과 반환
- 브로커 미도달 시 unhealthy 결과 반환
- 집계 헬스체크 포함 시 결과 형식 일관성 유지

### 12.4 보안
- token/password/creds 내용 마스킹
- 설정 스냅샷에 민감정보 비노출

---

## 13. 오픈 이슈

- `NatsConnectionBuilder`의 실제 메서드 시그니처를 코드 기준으로 확정해야 한다.
- 연결 객체 close 책임이 builder, registry, 혹은 반환된 client 중 어디에 있는지 확정 필요
- publisher/subscriber helper를 `fastapi-core` 범위에 포함할지 여부 결정 필요
- NATS subject naming convention을 공통 문서로 둘지 서비스별 문서로 둘지 결정 필요
- DLQ / retry / ack 정책을 상위 서비스 문서에서 어떻게 표준화할지 결정 필요

---

## 14. 참고 문서

- `docs/prd.md`
- `docs/srs.md`
- `docs/api.md`
- `docs/config.md`
- `README.md`
- `wiki/concepts/service-configuration-contracts.md`

---

## 부록 A. 문서 상태 메모

이 초안은 현재 확인 가능한 PRD/SRS/API/config 문서와 ingest된 설정 계약 메모를 기준으로 작성되었다. 실제 구현 코드가 준비되면 NATS builder의 구체 메서드, 오류 클래스, 헬스체크 반환 스키마, 종료 수명주기 규칙을 코드 기준으로 다시 맞춰야 한다.
