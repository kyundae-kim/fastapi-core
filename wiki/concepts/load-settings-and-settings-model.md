---
title: load_settings and Settings model
created: 2026-06-11
updated: 2026-06-11
type: concept
tags: [config, sdk, api, convention, architecture]
sources: [raw/articles/docmesh-py-core-sdk-2026-06-11.md, raw/articles/docmesh-py-core-api-2026-06-11.md, raw/articles/docmesh-py-core-config-2026-06-11.md]
confidence: medium
---
# load_settings and Settings model

## Definition
`load_settings(env)` 는 환경변수 매핑에서 전체 설정을 읽고 검증한 뒤 `Settings` 객체를 반환하는 SDK의 표준 진입점이다. 문서는 일반적인 소비 프로젝트에서 `Settings()` 직접 생성보다 이 함수를 우선 권장한다.

## What It Produces
`Settings` 는 패키지의 최상위 설정 컨테이너이며 `common`, `keycloak`, `postgres`, `sqlite`, `minio`, `milvus`, `ollama`, `langfuse`, `nats` 같은 서비스별 설정을 묶어 제공한다. 이후 애플리케이션은 이 객체를 [[service-factory-registry]] 나 [[keycloak-auth-integration]] 에 전달해 런타임 통합을 구성한다.

## Validation Contract
`load_settings()` 는 단순 파싱이 아니라 필수값 누락, 형식 오류, 상호배타 규칙 위반, 운영 보안 규칙 위반을 검증하고 실패 시 `ConfigError` 를 발생시킨다. 설정 문서 기준으로 공백 문자열 무시, boolean 파싱, 숫자 범위 검증, 서비스별 timeout/retry 분리, 조건부 자격증명 규칙까지 포함하는 것이 기대된다. 따라서 [[environment-driven-service-selection]] 패턴이 환경에 의존하더라도, 잘못된 구성은 초기화 초기에 드러낼 수 있다.

## Why It Matters
이 함수는 설정 로드와 오류 메시지 정리를 일관된 한 지점으로 만들기 때문에, [[docmesh-py-core]] 의 표준 lifecycle 인 load → build → check → close 흐름을 안정적으로 시작하게 해준다. startup 검증 패턴은 [[sdk-health-check-patterns]] 와 결합될 때 가장 효과적이다.

## Related Topics
- [[docmesh-py-core]] 의 공식 초기화 시작점이다.
- [[configuration-principles]] 는 이 함수가 따라야 하는 환경변수 운영 철학을 제공한다.
- [[service-factory-registry]] 는 이 함수가 반환한 `Settings` 로 서비스 client를 조립한다.
- [[environment-driven-service-selection]] 은 이 설정 객체의 populated field를 기준으로 분기한다.
- [[nats-configuration-and-auth-modes]] 와 [[keycloak-configuration-rules]] 은 대표적인 조건부 검증 예시다.
