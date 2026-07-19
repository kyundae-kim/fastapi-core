---
title: Keycloak authentication API
created: 2026-06-25
updated: 2026-07-19
type: concept
tags: [service, api, security, integration, implementation]
sources: [raw/articles/docmesh-py-core-api-reference-2026.md, raw/articles/docmesh-py-core-api-reference-v0.2.0.md, raw/articles/docmesh-py-core-api-reference-v0.3.0.md, raw/articles/docmesh-py-core-api-reference-v0.4.0.md, raw/articles/docmesh-py-core-configuration-guide-2026.md, raw/articles/docmesh-py-core-configuration-guide-v0.2.0.md, raw/articles/docmesh-py-core-configuration-guide-v0.3.0.md, raw/articles/docmesh-py-core-configuration-guide-v0.4.0.md, raw/articles/docmesh-py-core-examples-guide-2026.md, raw/articles/docmesh-py-core-examples-guide-v0.3.0.md, raw/articles/docmesh-py-core-examples-guide-v0.4.0.md, fastapi_core/factory.py, fastapi_core/dependencies/auth.py, fastapi_core/routers/auth.py]
confidence: medium
---

# Keycloak authentication API

`KeycloakAuthService(config: KeycloakConfig, ...)`는 docmesh-py-core의 Keycloak 인증 고수준 진입점이다. 현재 API 레퍼런스는 이 타입이 `settings` aggregate가 아니라 `KeycloakConfig` 직접 입력을 받는다고 명시하며, access token 획득과 JWT 검증을 담당한다.^[raw/articles/docmesh-py-core-api-reference-2026.md]

## Discovery and base config

v0.4.0 설정 가이드는 `KeycloakDiscoveryConfig`와 `KeycloakConfig`를 구분하며, 두 타입 모두 프로세스 환경변수만 읽는다.

- `KeycloakDiscoveryConfig`는 `KEYCLOAK_URL`, `KEYCLOAK_REALM`만 읽는다.
- `KeycloakConfig`는 discovery 설정을 확장하고 `KEYCLOAK_CLIENT_ID`를 추가로 요구한다.
- `KEYCLOAK_CLIENT_PUBLIC=false`가 기본값이므로, public client가 아니라면 `KEYCLOAK_CLIENT_SECRET`가 필요하다.
- 운영 환경에서는 `KEYCLOAK_VERIFY_SSL=false`를 허용하지 않는다. `KEYCLOAK_PROVISIONING_ENABLED=true`일 때 admin service-account secret 또는 admin username/password 중 정확히 하나의 인증 방식을 구성해야 한다.^[raw/articles/docmesh-py-core-configuration-guide-v0.4.0.md]

## Token acquisition

`fetch_access_token(*, scope=None, username=None, password=None) -> AccessTokenResult`의 기본 grant type은 `password`이며, `client_credentials`도 명시적으로 선택할 수 있다. 함수 인자를 우선 사용하되, 생략된 username/password는 환경 설정 자격증명에서 가져온다.^[raw/articles/docmesh-py-core-api-reference-v0.4.0.md]

대표 반환 필드는 `access_token`, `token_type`, `expires_in`, `refresh_token`, `scope`다.

대표 예외는 `KeycloakTokenConfigurationError`, `KeycloakTokenAuthenticationError`, `KeycloakTokenTemporaryError`, `KeycloakTokenError`다.

- HTTP `400/401/403`은 인증 오류로 분류된다.
- HTTP `408/429` 및 `5xx`는 일시적 오류로 분류되어 재시도 대상이 된다.
- `password` grant에서 함수 인자가 빠진 경우 config의 `token_username`, `token_password`를 fallback으로 사용한다.
- 기본 password grant로 Keycloak client healthcheck를 실행할 때도 `KEYCLOAK_TOKEN_USERNAME`과 `KEYCLOAK_TOKEN_PASSWORD`가 모두 필요하다. 이 누락은 config loading 이후 healthcheck 단계에서 드러난다.^[raw/articles/docmesh-py-core-configuration-guide-v0.3.0.md]
- 함수 인자와 config 양쪽을 합쳐도 credential이 완전하지 않으면 `KeycloakTokenConfigurationError`가 발생한다.^[raw/articles/docmesh-py-core-configuration-guide-v0.2.0.md]
- 일시적 장애는 `config.max_retries + 1`번까지 재시도되고, 재시도 이벤트는 `build_service_log_event()` 포맷으로 로깅된다.^[raw/articles/docmesh-py-core-api-reference-2026.md]^[raw/articles/docmesh-py-core-configuration-guide-2026.md]

## User extraction and validation

`extract_user_info(token) -> AuthenticatedUser`는 raw JWT 또는 `Bearer <token>` 형식을 입력으로 받아 서명, 만료 시간, issuer, 선택적 audience, 허용 알고리즘을 검증한다.

반환 사용자 정보에는 `sub`, `preferred_username`, `email`, `given_name`, `family_name`, `name`, `realm_roles`, `client_roles`, `claims`가 포함된다. 검증 실패 시 `TokenValidationError`가 발생한다.

추가로 subject는 `sub` 우선, 없으면 `jti`를 대체 식별자로 사용하고, `realm_access.roles`와 `resource_access.*.roles`를 각각 `realm_roles`, `client_roles`로 분리한다. RS256 검증 시 JWKS는 `jwks_cache_ttl_seconds` 기준으로 캐시되고 필요 시 refresh한다.^[raw/articles/docmesh-py-core-api-reference-2026.md]

## Provisioning companion

`KeycloakProvisioner(config: KeycloakConfig, *, admin_client)`는 Realm/Client/Role을 선언형으로 생성·갱신하는 프로비저너이며, 멱등 실행과 dry-run을 지원하지만 선언에서 제거된 리소스를 자동 삭제하지는 않는다.^[raw/articles/docmesh-py-core-api-reference-2026.md]

`admin_client`는 `ensure_realm`, `ensure_client`, `ensure_realm_role`, `ensure_client_role` 계약을 만족해야 하며, 결과는 `created`, `updated`, `unchanged`, `failed`, `planned`, `dry_run` 필드를 가진다. v0.3.0에서는 `ProvisioningResult`도 패키지 루트 공개 import 목록에 포함된다.^[raw/articles/docmesh-py-core-api-reference-v0.3.0.md]

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

fastapi-core는 현재 이 API를 채택해 Keycloak client/provider를 구성한다. `/token`은 `fetch_access_token()`으로 토큰을 발급하고 예외 유형을 HTTP 오류로 매핑하며, `/user`와 `get_current_user()`는 bearer token을 검증해 역할과 scope를 `UserInfo`로 변환한다.

v0.4.0 예제는 `KeycloakConfig()` 환경 설정으로 `KeycloakAuthService`를 만들고, password grant 호출 인자는 환경 credential보다 우선함을 보인다. RS256은 explicit verification key 대신 JWKS endpoint와 cache/rotation 경로를 사용한다.^[raw/articles/docmesh-py-core-examples-guide-v0.4.0.md]
