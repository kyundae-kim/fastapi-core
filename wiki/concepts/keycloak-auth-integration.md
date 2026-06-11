---
title: Keycloak auth integration
created: 2026-06-11
updated: 2026-06-11
type: concept
tags: [auth, keycloak, oauth2, oidc, token]
sources: [raw/articles/docmesh-py-core-sdk-2026-06-11.md]
confidence: medium
---
# Keycloak auth integration

## Definition
이 통합 주제는 `docmesh-py-core` 가 Keycloak 기반의 service-to-service access token 발급과 bearer JWT 검증을 공통화하는 방식을 다룬다. 문서의 예시에서는 `KeycloakAuthService(settings)` 를 직접 생성해 토큰 취득과 사용자 정보 추출을 수행한다.

## Main Use Cases
- service-to-service access token 발급
- bearer token 검증
- 사용자/역할 정보 추출

JWT 검증 예시에서는 `allowed_algorithms=["RS256"]` 를 지정해 검증 정책을 제한할 수 있다. 이 흐름은 [[docmesh-py-core]] 가 제공하는 인증 공통화 역할의 한 축이며, 서비스 연결 lifecycle 은 [[sdk-health-check-patterns]] 와 별개지만 운영상 함께 고려된다.

## Architectural Boundary
문서 기준으로 Keycloak 인증 서비스는 [[service-factory-registry]] 를 통한 일반 서비스 client 생성과는 별도 경로를 가진다. 즉 저장소/인프라 client 조립과 인증 로직은 같은 설정 집합을 공유하되, 애플리케이션 코드에서 서로 다른 통합 지점을 가질 수 있다.

## Related Topics
- [[docmesh-py-core]] 는 Keycloak 토큰 발급과 JWT 검증을 핵심 해결 문제로 포함한다.
- [[service-factory-registry]] 는 데이터/인프라 서비스 조립을 맡고, 인증은 별도 서비스 객체가 맡는 경계를 보여준다.
- [[environment-driven-service-selection]] 은 인증 외의 저장소 선택 패턴을 설명한다.

## Open Questions
- 사용자/역할 매핑 모델이 애플리케이션별로 어떻게 확장되는지 추가 문서 확인이 필요하다.
- Keycloak health/readiness 를 `check_all_services()` 집계에 포함하는 공식 패턴이 있는지는 후속 문서에서 확인해야 한다.
