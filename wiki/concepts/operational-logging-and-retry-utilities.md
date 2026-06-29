---
title: Operational logging and retry utilities
created: 2026-06-29
updated: 2026-06-29
type: concept
tags: [api, observability, implementation, security]
sources: [raw/articles/docmesh-py-core-api-reference-2026.md, raw/articles/docmesh-py-core-configuration-guide-2026.md, raw/articles/docmesh-py-core-examples-guide-2026.md]
confidence: medium
---

# Operational logging and retry utilities

`docmesh-py-core`는 서비스 연결 코드 주변의 운영 보일러플레이트를 줄이기 위해 `mask_sensitive_value`, `configure_logging`, `build_service_log_event`, `retry_call`을 공개 API로 제공한다.

## Utility surface

- `mask_sensitive_value(raw)`: 비밀번호, 토큰, secret, DSN/URI의 민감값을 마스킹한다.
- `configure_logging(...)`: stderr/file handler를 구성하고 `DOCMESH_LOG_LEVEL` 또는 명시 `level` 값으로 로그 레벨을 결정한다.
- `build_service_log_event(...)`: 서비스명, operation, outcome, host, latency, retry_count, error를 포함하는 구조화 이벤트 dict를 만든다.
- `retry_call(operation, ..., retry_on, max_attempts, base_delay_seconds=0.5)`: 지수 백오프 기반으로 동기 함수를 재시도한다.

설정 가이드는 `DOCMESH_LOG_LEVEL`의 기본값을 `INFO`로 두고, `configure_logging(level=...)`를 주지 않으면 이 env를 읽도록 문서화한다.

예제 문서는 `configure_logging(log_path="logs/app.log", force=True, env=environ)` 호출과 `DOCMESH_LOG_LEVEL=DEBUG|ERROR` 같은 실제 실행 패턴을 제시해, stderr와 파일 로그를 함께 쓰는 초기화 방식을 구체화한다.

## Operational implications

이 유틸리티 묶음은 fastapi-core가 서비스별 연결 코드마다 임의의 logging/retry 패턴을 복제하기보다, 공통 포맷과 공통 마스킹 규칙을 재사용하도록 유도한다.

특히 헬스체크와 연결 오류를 기록할 때 `build_service_log_event`와 `mask_sensitive_value`를 함께 쓰면 운영 로그에 민감정보를 남기지 않으면서도 서비스명, 지연 시간, 재시도 횟수 같은 진단 신호를 일관되게 남길 수 있다.

## Guardrails

- `configure_logging()`은 env 로그 레벨 값이 유효하지 않으면 `ValueError`를 발생시킨다.
- `retry_call()`은 `max_attempts < 1`이면 `ValueError`를 발생시킨다.
- 재시도 간격은 `base_delay_seconds * 2 ** (attempt - 1)` 지수 백오프다.
- `retry_call()` 예시는 영구 오류를 `retry_on`에 넣지 말고 일시적 오류만 재시도 대상으로 두는 운영 원칙을 강조한다.

## Related pages

- [[docmesh-py-core]]: 이 유틸리티들은 패키지 루트 공개 API의 일부다.
- [[service-health-check-aggregation]]: 헬스체크 오류 메시지는 마스킹 규칙과 구조화 이벤트 포맷의 직접적인 수혜를 받는다.
- [[service-configuration-contracts]]: 로그 레벨과 환경별 운영 규칙은 설정 계약과 맞물린다.
