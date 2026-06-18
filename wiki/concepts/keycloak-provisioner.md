---
title: KeycloakProvisioner
created: 2026-06-11
updated: 2026-06-11
type: concept
tags: [keycloak, auth, api, rbac, integration]
sources: [raw/articles/docmesh-py-core-api-2026-06-11.md]
confidence: medium
---
# KeycloakProvisioner

## Definition
`KeycloakProvisioner` 는 realm, client, role 상태를 원하는 선언과 맞추는 프로비저닝 도구다. 실제 Keycloak Admin API 호출은 외부 `admin_client` 구현에 위임하므로, SDK는 선언적 조정 로직과 결과 집계를 담당한다.

## Expected Admin Contract
문서에는 `ensure_realm`, `ensure_client`, `ensure_realm_role`, `ensure_client_role` 메서드를 가진 `KeycloakAdminClient` 프로토콜 계약이 제시된다. 이 때문에 호출자는 Keycloak 운영 표준에 맞는 admin adapter 를 별도로 제공해야 한다.

## Result Shape
`provision()` 결과는 `created`, `updated`, `unchanged`, `failed`, `planned`, `dry_run` 같은 필드를 포함한다. 즉 단순 성공/실패보다 선언 적용 결과를 세밀하게 관찰할 수 있다. 이 흐름은 [[keycloak-auth-integration]] 의 런타임 토큰 처리와는 다른 관리 평면(control plane) 성격을 가진다.

## Architectural Role
[[docmesh-py-core]] 가 인증을 단지 token fetch/JWT validation 으로만 제한하지 않고, Keycloak 리소스 상태 조정까지 API 표면에 포함한다는 점을 보여준다. 반면 [[service-factory-registry]] 중심의 데이터/인프라 client 조립 패턴과는 별도 축이다.

## Related Topics
- [[keycloak-auth-integration]] 는 런타임 인증 경로를 다룬다.
- [[docmesh-py-core]] 의 Keycloak 지원 범위를 확장해서 보여준다.
- [[load-settings-and-settings-model]] 의 설정 객체를 공유할 가능성이 높다.
