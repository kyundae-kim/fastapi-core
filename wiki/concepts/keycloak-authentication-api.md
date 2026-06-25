---
title: Keycloak authentication API
created: 2026-06-25
updated: 2026-06-25
type: concept
tags: [service, api, security, integration, implementation]
sources: [raw/articles/docmesh-py-core-api-reference-2026.md, raw/articles/docmesh-py-core-configuration-guide-2026.md]
confidence: medium
---

# Keycloak authentication API

`KeycloakAuthService(settings, allowed_algorithms=None)`는 docmesh-py-core의 Keycloak 인증 고수준 진입점이다. 문서상 access token 획득, JWT 검증, 사용자 정보 및 역할 추출을 담당한다.

## Token acquisition

`fetch_access_token(scope=None) -> AccessTokenResult`는 기본적으로 `client_credentials` grant를 사용하고, 선택적으로 `scope`를 전달할 수 있으며, 명시적 설정이 있으면 `password` grant도 사용할 수 있다.

대표 반환 필드는 `access_token`, `token_type`, `expires_in`, `refresh_token`, `scope`다.

대표 예외는 `KeycloakTokenConfigurationError`, `KeycloakTokenAuthenticationError`, `KeycloakTokenTemporaryError`, `KeycloakTokenError`다.

## User extraction and validation

`extract_user_info(token) -> AuthenticatedUser`는 raw JWT 또는 `Bearer <token>` 형식을 입력으로 받아 서명, 만료 시간, issuer, 선택적 audience, 허용 알고리즘을 검증한다.

반환 사용자 정보에는 `sub`, `preferred_username`, `email`, `name`, `realm_roles`, `client_roles`, `claims`가 포함된다. 검증 실패 시 `TokenValidationError`가 발생한다.

## Provisioning companion

`KeycloakProvisioner`는 Realm/Client/Role을 선언형으로 생성·갱신하는 프로비저너이며, 멱등 실행과 dry-run을 지원하지만 선언에서 제거된 리소스를 자동 삭제하지는 않는다.

## Configuration contract

설정 가이드는 Keycloak 구성을 세 영역으로 나눈다.

- 기본 인증/JWT 검증: `KEYCLOAK_URL`, `KEYCLOAK_REALM`, `KEYCLOAK_CLIENT_ID`가 필수 축이며, `KEYCLOAK_VERIFY_SSL`, `KEYCLOAK_AUDIENCE`, timeout/retry, JWKS cache TTL을 별도로 둔다.
- 토큰 획득: 기본 grant는 `client_credentials`이고, `password` grant를 쓰려면 사용자명/비밀번호가 추가로 필요하다.
- 프로비저닝: `KEYCLOAK_PROVISIONING_ENABLED=true`이면 Admin API 인증정보가 필요하고, service account 방식이 권장된다.

운영 가이드는 `password` grant를 운영 기본값으로 두지 않는 것을 권장하며, 프로비저닝 역시 최소 권한 계정으로 수행할 것을 요구한다.

## Related pages

- [[docmesh-py-core]]: Keycloak 인증은 패키지 공개 API의 핵심 축이다.
- [[service-factory-registry]]: registry의 `keycloak` 경로와 함께 사용될 수 있다.
- [[service-health-check-aggregation]]: 기본 Keycloak 헬스체크는 access token 획득으로 표현된다.
- [[service-configuration-contracts]]: Keycloak 관련 환경변수와 운영 보안 원칙의 상위 정리.

## Fastapi-core relevance

fastapi-core가 이 API를 채택하면 인증 검증 규칙, 역할 추출, 토큰 발급 오류 분류를 애플리케이션 전역에서 일관되게 공유할 수 있다.
