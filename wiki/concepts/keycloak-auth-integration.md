---
title: Keycloak auth integration
created: 2026-06-11
updated: 2026-06-11
type: concept
tags: [auth, keycloak, oauth2, oidc, token]
sources: [raw/articles/docmesh-py-core-sdk-2026-06-11.md, raw/articles/docmesh-py-core-api-2026-06-11.md, raw/articles/docmesh-py-core-config-2026-06-11.md]
confidence: medium
---
# Keycloak auth integration

## Definition
이 통합 주제는 `docmesh-py-core` 가 Keycloak 기반의 service-to-service access token 발급과 bearer JWT 검증을 공통화하는 방식을 다룬다. 문서의 예시에서는 `KeycloakAuthService(settings)` 를 직접 생성해 토큰 취득과 사용자 정보 추출을 수행한다.

## Main Use Cases
- service-to-service access token 발급
- bearer token 검증
- 사용자/역할 정보 추출
- admin client 기반 realm/client/role 프로비저닝과의 역할 분리

JWT 검증 예시에서는 `allowed_algorithms=["RS256"]` 를 지정해 검증 정책을 제한할 수 있다. API 문서 기준 `fetch_access_token()` 은 `AccessTokenResult` 를 반환하고, `extract_user_info()` 는 `AuthenticatedUser` 를 반환한다. 이 흐름은 [[docmesh-py-core]] 가 제공하는 인증 공통화 역할의 한 축이며, 서비스 연결 lifecycle 은 [[sdk-health-check-patterns]] 와 별개지만 운영상 함께 고려된다.

## Architectural Boundary
문서 기준으로 Keycloak 인증 서비스는 [[service-factory-registry]] 를 통한 일반 서비스 client 생성과는 별도 경로를 가진다. 즉 저장소/인프라 client 조립과 인증 로직은 같은 설정 집합을 공유하되, 애플리케이션 코드에서 서로 다른 통합 지점을 가질 수 있다.

설정 측면에서는 [[keycloak-configuration-rules]] 이 런타임 인증과 관리 평면 모두의 공통 기반이 되며, confidential client / password grant / audience / SSL 검증 같은 선택지가 이 경계를 실질적으로 결정한다.

또한 API 표면에는 런타임 인증 외에 [[keycloak-provisioner]] 도 존재한다. 전자는 토큰 발급/JWT 검증을 담당하고, 후자는 Keycloak 리소스 상태를 선언에 맞춰 조정하는 관리 평면 역할을 가진다.

## Related Topics
- [[docmesh-py-core]] 는 Keycloak 토큰 발급과 JWT 검증을 핵심 해결 문제로 포함한다.
- [[load-settings-and-settings-model]] 의 설정 객체를 공유한다.
- [[keycloak-configuration-rules]] 은 grant type, SSL, audience, admin credential 규칙을 정리한다.
- [[service-factory-registry]] 는 데이터/인프라 서비스 조립을 맡고, 인증은 별도 서비스 객체가 맡는 경계를 보여준다.
- [[keycloak-provisioner]] 는 관리 평면의 Keycloak 상태 조정을 다룬다.
- [[environment-driven-service-selection]] 은 인증 외의 저장소 선택 패턴을 설명한다.

## Open Questions
- 사용자/역할 매핑 모델이 애플리케이션별로 어떻게 확장되는지 추가 문서 확인이 필요하다.
- Keycloak health/readiness 를 `check_all_services()` 집계에 포함하는 공식 패턴이 있는지는 후속 문서에서 확인해야 한다.
