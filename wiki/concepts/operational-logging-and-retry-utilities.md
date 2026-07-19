---
title: Operational logging and retry utilities
created: 2026-06-29
updated: 2026-07-19
type: concept
tags: [api, observability, implementation, security]
sources: [raw/articles/docmesh-py-core-api-reference-2026.md, raw/articles/docmesh-py-core-api-reference-v0.2.0.md, raw/articles/docmesh-py-core-api-reference-v0.3.0.md, raw/articles/docmesh-py-core-api-reference-v0.4.0.md, raw/articles/docmesh-py-core-configuration-guide-2026.md, raw/articles/docmesh-py-core-configuration-guide-v0.3.0.md, raw/articles/docmesh-py-core-configuration-guide-v0.4.0.md, raw/articles/docmesh-py-core-examples-guide-2026.md, raw/articles/docmesh-py-core-examples-guide-v0.2.0.md, raw/articles/docmesh-py-core-examples-guide-v0.3.0.md, raw/articles/docmesh-py-core-examples-guide-v0.4.0.md]
confidence: medium
---

# Operational logging and retry utilities

`docmesh-py-core`는 서비스 연결 코드 주변의 운영 보일러플레이트를 줄이기 위해 `mask_sensitive_value`, `configure_logging`, `build_service_log_event`, `retry_call`, `close_service_clients`를 패키지 루트 공개 helper 표면으로 제공한다.^[raw/articles/docmesh-py-core-api-reference-v0.4.0.md]

## Utility surface

- `mask_sensitive_value(value)`: 비밀번호, 토큰, secret, DSN/URI의 민감값을 마스킹한다.
- `configure_logging(...)`: stderr/file handler를 구성하고 `DOCMESH_LOG_LEVEL` 또는 명시 `level` 값으로 로그 레벨을 결정한다.
- `build_service_log_event(...)`: 서비스명, operation, outcome, host, latency, retry_count, error를 포함하는 구조화 이벤트 dict를 만든다.
- `retry_call(operation, ..., retry_on, max_attempts, base_delay_seconds=0.5)`: 지수 백오프 기반으로 동기 함수를 재시도한다.
- `close_service_clients(clients)`: 여러 wrapper/client에 대해 `close()`를 순회 호출하고 `None` 값은 무시한다. 비동기/혼합 cleanup에는 실패를 모아 나머지 종료를 계속하는 `async_close_service_clients()`를 사용한다.^[raw/articles/docmesh-py-core-api-reference-v0.2.0.md]

v0.4.0 설정 가이드는 `DOCMESH_LOG_LEVEL`의 기본값을 `INFO`로 두고, `configure_logging(level=...)`를 주지 않으면 이 env를 읽도록 문서화한다. 또한 `DOCMESH_LOG_LEVEL`은 `CommonConfig` 필드가 아니라 로깅 함수가 직접 읽는 환경변수라고 구분한다.^[raw/articles/docmesh-py-core-configuration-guide-v0.4.0.md]

v0.4.0 예제는 `configure_logging()`과 `build_service_log_event()`를 함께 쓰며 token을 `***`로 마스킹하고, `retry_call()`에는 재시도 대상 예외를 명시한다. 함수 경계 logging과 `host` 값은 전체 입력을 자동 정제하지 않으므로 secret-safe 값만 전달해야 한다.^[raw/articles/docmesh-py-core-examples-guide-v0.4.0.md]

## Guardrails

- `configure_logging()`은 env 로그 레벨 값이 유효하지 않으면 `ValueError`를 발생시킨다.
- `retry_call()`은 `max_attempts < 1`이면 `ValueError`를 발생시킨다.
- 재시도 간격은 `base_delay_seconds * 2 ** (attempt - 1)` 지수 백오프다.
- `retry_call()`은 재시도 대상 예외만 다시 시도하고, 마지막 시도에서도 실패하면 원래 예외를 그대로 올린다.
- `ServiceClientWrapper`와 `build_service_log_event()`는 오류 문자열과 민감한 extra 필드를 마스킹하는 방향으로 맞물린다.^[raw/articles/docmesh-py-core-api-reference-2026.md]

## Operational implications

이 유틸리티 묶음은 fastapi-core가 서비스별 연결 코드마다 임의의 logging/retry/cleanup 패턴을 복제하기보다, 공통 포맷과 공통 마스킹 규칙을 재사용하도록 유도한다.

특히 헬스체크와 연결 오류를 기록할 때 `build_service_log_event`와 `mask_sensitive_value`를 함께 쓰면 운영 로그에 민감정보를 남기지 않으면서도 서비스명, 지연 시간, 재시도 횟수 같은 진단 신호를 일관되게 남길 수 있다. 여러 optional client를 함께 정리할 때는 `close_service_clients()`가 `None`을 무시하므로 선택 기능 토글과도 잘 맞는다.

## Related pages

- [[docmesh-py-core]]: 이 유틸리티들은 패키지 루트 공개 API의 일부다.
- [[service-health-check-aggregation]]: 헬스체크 오류 메시지는 마스킹 규칙과 구조화 이벤트 포맷의 직접적인 수혜를 받는다.
- [[service-configuration-contracts]]: 로그 레벨과 환경별 운영 규칙은 설정 계약과 맞물린다.
- [[application-integration-patterns]]: startup/shutdown 시 logging 초기화와 client 정리 패턴을 실제 앱 수명주기에 연결한다.
