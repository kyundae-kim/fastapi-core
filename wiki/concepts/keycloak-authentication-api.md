---
title: Keycloak authentication API
created: 2026-06-25
updated: 2026-07-02
type: concept
tags: [service, api, security, integration, implementation]
sources: [raw/articles/docmesh-py-core-api-reference-2026.md, raw/articles/docmesh-py-core-configuration-guide-2026.md, raw/articles/docmesh-py-core-examples-guide-2026.md]
confidence: medium
---

# Keycloak authentication API

`KeycloakAuthService(config: KeycloakConfig, ...)`는 docmesh-py-core의 Keycloak 인증 고수준 진입점이다. 현재 API 레퍼런스는 이 타입이 `settings` aggregate가 아니라 `KeycloakConfig` 직접 입력을 받는다고 명시하며, access token 획득과 JWT 검증을 담당한다.^[raw/articles/docmesh-py-core-api-reference-2026.md]

## Discovery and base config

최신 설정 가이드는 `KeycloakDiscoveryConfig`와 `KeycloakConfig`를 구분한다.

- `KeycloakDiscoveryConfig`는 `KEYCLOAK_URL`, `KEYCLOAK_REALM`만 읽는다.
- `KeycloakConfig`는 discovery 설정을 확장하고 `KEYCLOAK_CLIENT_ID`를 추가로 요구한다.
- `KEYCLOAK_CLIENT_PUBLIC=false`가 기본값이므로, public client가 아니라면 `KEYCLOAK_CLIENT_SECRET`가 필요하다.
- 운영 환경에서는 `KEYCLOAK_VERIFY_SSL=false`를 허용하지 않는다.^[raw/articles/docmesh-py-core-configuration-guide-2026.md]

## Token acquisition

`fetch_access_token(*, scope=None, username=None, password=None) -> AccessTokenResult`는 기본적으로 `client_credentials` grant를 사용하고, 선택적으로 `scope`를 전달할 수 있으며, `config.token_grant_type == "password"`일 때는 설정 객체 필드와 무관하게 함수 인자 `username`, `password`를 반드시 전달해야 한다.^[raw/articles/docmesh-py-core-api-reference-2026.md]

대표 반환 필드는 `access_token`, `token_type`, `expires_in`, `refresh_token`, `scope`다.

대표 예외는 `KeycloakTokenConfigurationError`, `KeycloakTokenAuthenticationError`, `KeycloakTokenTemporaryError`, `KeycloakTokenError`다.

- HTTP `400/401/403`은 인증 오류로 분류된다.
- HTTP `408/429` 및 `5xx`는 일시적 오류로 분류되어 재시도 대상이 된다.
- `password` grant인데 `username` 또는 `password` 인자가 빠지면 `KeycloakTokenConfigurationError`가 발생한다.
- `KEYCLOAK_TOKEN_USERNAME`, `KEYCLOAK_TOKEN_PASSWORD`는 예시/테스트용 보조값일 뿐 자동 주입되지 않는다.
- 일시적 장애는 `config.max_retries + 1`번까지 재시도되고, 재시도 이벤트는 `build_service_log_event()` 포맷으로 로깅된다.^[raw/articles/docmesh-py-core-api-reference-2026.md]^[raw/articles/docmesh-py-core-configuration-guide-2026.md]

## User extraction and validation

`extract_user_info(token) -> AuthenticatedUser`는 raw JWT 또는 `Bearer <token>` 형식을 입력으로 받아 서명, 만료 시간, issuer, 선택적 audience, 허용 알고리즘을 검증한다.

반환 사용자 정보에는 `sub`, `preferred_username`, `email`, `given_name`, `family_name`, `name`, `realm_roles`, `client_roles`, `claims`가 포함된다. 검증 실패 시 `TokenValidationError`가 발생한다.

추가로 subject는 `sub` 우선, 없으면 `jti`를 대체 식별자로 사용하고, `realm_access.roles`와 `resource_access.*.roles`를 각각 `realm_roles`, `client_roles`로 분리한다. RS256 검증 시 JWKS는 `jwks_cache_ttl_seconds` 기준으로 캐시되고 필요 시 refresh한다.^[raw/articles/docmesh-py-core-api-reference-2026.md]

## Provisioning companion

`KeycloakProvisioner(config: KeycloakConfig, *, admin_client)`는 Realm/Client/Role을 선언형으로 생성·갱신하는 프로비저너이며, 멱등 실행과 dry-run을 지원하지만 선언에서 제거된 리소스를 자동 삭제하지는 않는다.^[raw/articles/docmesh-py-core-api-reference-2026.md]

`admin_client`는 `ensure_realm`, `ensure_client`, `ensure_realm_role`, `ensure_client_role` 계약을 만족해야 하며, 결과는 `created`, `updated`, `unchanged`, `failed`, `planned`, `dry_run` 필드를 가진다. 다만 `ProvisioningResult` 자체는 패키지 루트 `__all__`로 재-export되지는 않는다.^[raw/articles/docmesh-py-core-api-reference-2026.md]

설정 가이드는 `KEYCLOAK_PROVISIONING_ENABLED=true`일 때 admin 인증 방식이 정확히 하나여야 한다고 못 박는다.

- `KEYCLOAK_ADMIN_CLIENT_SECRET`
- `KEYCLOAK_ADMIN_USERNAME` + `KEYCLOAK_ADMIN_PASSWORD`

둘 다 주거나 둘 다 비우면 `KEYCLOAK provisioning requires a single admin auth mode` 오류가 발생한다.^[raw/articles/docmesh-py-core-configuration-guide-2026.md]

## Related pages

- [[docmesh-py-core]]: Keycloak 인증은 패키지 공개 API의 핵심 축이다.
- [[service-factory-registry]]: examples 기반 registry 소비와 별개로, 현재 API 레퍼런스는 direct `KeycloakConfig` + `KeycloakAuthService` 조합을 우선 설명한다.
- [[service-health-check-aggregation]]: 기본 Keycloak 헬스체크는 access token 획득으로 표현된다.
- [[service-configuration-contracts]]: Keycloak 관련 환경변수와 운영 보안 원칙의 상위 정리.

## Fastapi-core relevance

fastapi-core가 이 API를 채택하면 인증 검증 규칙, 역할 추출, 토큰 발급 오류 분류를 애플리케이션 전역에서 일관되게 공유할 수 있다.

예제 문서는 `client_credentials`와 `password` grant를 분리해 보여주고, RS256 토큰 검증 시 `allowed_algorithms=["RS256"]`를 명시하는 패턴을 제시한다. 즉 fastapi-core 통합에서는 사용자 credential을 설정 객체에 영구 보관하기보다 토큰 요청 시점 인자로 전달하고, JWT 검증은 Keycloak 배포 알고리즘에 맞춰 명시적으로 구성하는 것이 권장된다.
