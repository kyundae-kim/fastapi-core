---
title: mask_sensitive_value
created: 2026-06-11
updated: 2026-06-11
type: concept
tags: [security, config, observability, api, convention]
sources: [raw/articles/docmesh-py-core-api-2026-06-11.md]
confidence: medium
---
# mask_sensitive_value

## Definition
`mask_sensitive_value(raw)` 는 DSN, URL, query string, 일반 문자열에 포함된 password, secret, token, api_key 계열 민감정보를 마스킹하는 보안 유틸리티다.

## Intended Usage
문서상 사용 시점은 로그 출력 전, 예외 메시지 노출 전, 운영 화면에 연결 정보나 오류를 보여주기 전이다. 따라서 이 함수는 개발 편의 기능이라기보다 운영 안전장치에 가깝다.

## Relationship to Health and Errors
[[check-all-services]] 의 `HealthCheckError.error` 가 마스킹된 오류 메시지를 제공한다는 설명은 이 유틸리티의 존재 이유와 맞닿아 있다. 설정 로드나 외부 서비스 연결 실패를 사용자에게 보여줄 때도 [[load-settings-and-settings-model]] 과 함께 민감정보 비노출 원칙을 유지하는 것이 중요하다.

## Why It Matters
다양한 외부 서비스와 Keycloak을 함께 다루는 [[docmesh-py-core]] 에서는 DSN, bearer token, client secret 같은 민감값이 자주 등장한다. 이 함수는 관측성과 보안 사이의 균형을 지키는 기본 도구다.

## Related Topics
- [[docmesh-py-core]] 의 공통 보안 유틸리티다.
- [[check-all-services]] 의 오류 노출 정책과 연결된다.
- [[keycloak-auth-integration]] 의 token 처리 맥락에서도 중요하다.
