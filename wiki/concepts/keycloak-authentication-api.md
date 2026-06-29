---
title: Keycloak authentication API
created: 2026-06-25
updated: 2026-06-29
type: concept
tags: [service, api, security, integration, implementation]
sources: [raw/articles/docmesh-py-core-api-reference-2026.md, raw/articles/docmesh-py-core-configuration-guide-2026.md, raw/articles/docmesh-py-core-examples-guide-2026.md]
confidence: medium
---

# Keycloak authentication API

`KeycloakAuthService(settings, *, http_client=None, verification_key=None, allowed_algorithms=None, logger=None, event_logger=None, timer=time.perf_counter, sleep=time.sleep, current_time=time.time)`는 docmesh-py-core의 Keycloak 인증 고수준 진입점이다. 문서상 access token 획득, JWT 검증, 사용자 정보 및 역할 추출을 담당한다.

기본 허용 알고리즘은 `HS256`이며, 일반적인 Keycloak의 RS256 토큰 검증을 하려면 `allowed_algorithms=['RS256']`와 JWKS 기반 검증 구성이 필요하다.

## Token acquisition

`fetch_access_token(scope=None, username=None, password=None) -> AccessTokenResult`는 기본적으로 `client_credentials` grant를 사용하고, 선택적으로 `scope`를 전달할 수 있으며, 명시적 설정이 있으면 `password` grant도 사용할 수 있다.

대표 반환 필드는 `access_token`, `token_type`, `expires_in`, `refresh_token`, `scope`다.

대표 예외는 `KeycloakTokenConfigurationError`, `KeycloakTokenAuthenticationError`, `KeycloakTokenTemporaryError`, `KeycloakTokenError`다.

- HTTP `400/401/403`은 인증 오류로 분류된다.
- HTTP `408/429` 및 `5xx`는 일시적 오류로 분류되어 재시도 대상이 된다.
- `password` grant인데 `username` 또는 `password` 인자가 빠지면 `KeycloakTokenConfigurationError`가 발생한다.

## User extraction and validation

`extract_user_info(token) -> AuthenticatedUser`는 raw JWT 또는 `Bearer <token>` 형식을 입력으로 받아 서명, 만료 시간, issuer, 선택적 audience, 허용 알고리즘을 검증한다.

반환 사용자 정보에는 `sub`, `preferred_username`, `email`, `given_name`, `family_name`, `name`, `realm_roles`, `client_roles`, `claims`가 포함된다. 검증 실패 시 `TokenValidationError`가 발생한다.

추가로 subject는 `sub` 우선, 없으면 `jti`를 대체 식별자로 사용하고, `realm_access.roles`와 `resource_access.*.roles`를 각각 `realm_roles`, `client_roles`로 분리한다. RS256 검증 시 JWKS는 `KEYCLOAK_JWKS_CACHE_TTL_SECONDS` 기준으로 캐시된다.

## Provisioning companion

`KeycloakProvisioner(settings, *, admin_client)`는 Realm/Client/Role을 선언형으로 생성·갱신하는 프로비저너이며, 멱등 실행과 dry-run을 지원하지만 선언에서 제거된 리소스를 자동 삭제하지는 않는다.

`admin_client`는 `ensure_realm`, `ensure_client`, `ensure_realm_role`, `ensure_client_role` 계약을 만족해야 하며, `provision()` 결과는 `created`, `updated`, `unchanged`, `failed`, `planned`, `dry_run` 필드를 가진다.

## Configuration contract

설정 가이드는 Keycloak 구성을 세 영역으로 나눈다.

- 기본 인증/JWT 검증: `KEYCLOAK_URL`, `KEYCLOAK_REALM`, `KEYCLOAK_CLIENT_ID`가 필수 축이며, `KEYCLOAK_VERIFY_SSL`, `KEYCLOAK_AUDIENCE`, timeout/retry, JWKS cache TTL을 별도로 둔다.
- 토큰 획득: 기본 grant는 `client_credentials`이고, `password` grant를 쓰려면 실제 함수 호출 시 `username`/`password` 인자가 추가로 필요하다. 설정 문서는 해당 env를 테스트용 선택값으로만 다룬다.
- 프로비저닝: `KEYCLOAK_PROVISIONING_ENABLED=true`이면 Admin API 인증정보가 필요하고, service account 방식이 권장된다.

운영 가이드는 `password` grant를 운영 기본값으로 두지 않는 것을 권장하며, 애플리케이션 설정 객체에 username/password를 고정하지 말고 호출 시점 인자로 전달할 것을 권장한다. 프로비저닝 역시 최소 권한 계정으로 수행해야 하며, service account 방식과 username/password 방식은 정확히 하나만 선택해야 한다.

## Related pages

- [[docmesh-py-core]]: Keycloak 인증은 패키지 공개 API의 핵심 축이다.
- [[service-factory-registry]]: registry의 `keycloak` 경로와 함께 사용될 수 있다.
- [[service-health-check-aggregation]]: 기본 Keycloak 헬스체크는 access token 획득으로 표현된다.
- [[service-configuration-contracts]]: Keycloak 관련 환경변수와 운영 보안 원칙의 상위 정리.

## Fastapi-core relevance

fastapi-core가 이 API를 채택하면 인증 검증 규칙, 역할 추출, 토큰 발급 오류 분류를 애플리케이션 전역에서 일관되게 공유할 수 있다.

예제 문서는 `client_credentials`와 `password` grant를 분리해 보여주고, RS256 토큰 검증 시 `allowed_algorithms=["RS256"]`를 명시하는 패턴을 제시한다. 즉 fastapi-core 통합에서는 사용자 credential을 설정 객체에 영구 보관하기보다 토큰 요청 시점 인자로 전달하고, JWT 검증은 Keycloak 배포 알고리즘에 맞춰 명시적으로 구성하는 것이 권장된다.
