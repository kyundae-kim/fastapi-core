---
title: Keycloak configuration rules
created: 2026-06-11
updated: 2026-06-17
type: concept
tags: [keycloak, auth, config, oidc, security]
sources: [raw/articles/docmesh-py-core-config-2026-06-11.md, raw/articles/fastapi-core-config-2026-06-17.md]
confidence: medium
---
# Keycloak configuration rules

## Definition
이 페이지는 `docmesh-py-core` 와 `fastapi-core` 가 Keycloak 인증, 토큰 발급, JWT 검증, 프로비저닝을 위해 요구하는 설정 계약을 정리한다. 런타임 인증 경로와 readiness/관리 평면 경로가 같은 Keycloak 설정 기반을 공유하지만, 사용되는 필드와 조건부 규칙은 제품마다 약간 다르다.

## Base Authentication Settings
`fastapi-core` 문서 기준 핵심 기본값은 `KEYCLOAK__HTTP_URL`, `KEYCLOAK__MANAGE_URL`, `KEYCLOAK__REALM`, `KEYCLOAK__CLIENT_ID` 이며, confidential client 인 경우 `KEYCLOAK__CLIENT_SECRET` 이 조건부로 필요하다. 여기에 `KEYCLOAK_USERNAME`, `KEYCLOAK_PASSWORD` 가 통합 테스트용 기본 자격정보로 문서화된다. readiness 경로가 관리 URL을 따로 쓰므로, 인증 URL과 health URL을 분리해 운영할 수 있다는 점이 중요하다.

## Token Grant Rules
기본 grant type 은 `client_credentials` 다. `KEYCLOAK_TOKEN_GRANT_TYPE=password` 를 사용할 경우 `KEYCLOAK_TOKEN_USERNAME`, `KEYCLOAK_TOKEN_PASSWORD` 가 필요하며, 문서는 이를 제한된 내부/레거시 용도로만 권장한다. 이 규칙은 [[keycloak-auth-integration]] 의 `fetch_access_token()` 사용 계약을 뒷받침한다.

## Provisioning Rules
`KEYCLOAK_PROVISIONING_ENABLED=true` 이면 Admin API 인증 정보가 필요하고, 인증 방식은 service account 또는 관리자 사용자명/비밀번호 중 하나만 선택해야 한다. 또한 프로비저닝 대상 realm/client 는 `KEYCLOAK_REALM`, `KEYCLOAK_CLIENT_ID` 를 재사용하며, 선언에서 제거된 리소스를 자동 삭제하지 않는다. 이는 [[keycloak-provisioner]] 의 관리 평면 철학을 반영한다.

## Security Notes
운영 환경에서는 TLS 검증을 유지하고, 관리자 자격정보는 최소 권한 원칙으로 관리해야 한다. 관리자 사용자명/비밀번호보다 service account 방식을 우선하는 것이 권장된다. 토큰, secret, 관리자 인증값은 [[mask-sensitive-value]] 정책과 함께 다뤄야 한다.

## Related Topics
- [[keycloak-auth-integration]] 는 런타임 토큰/JWT 경로를 다룬다.
- [[keycloak-provisioner]] 는 선언적 상태 조정을 다룬다.
- [[configuration-principles]] 는 공통 환경변수 운영 철학을 설명한다.
- [[lifecycle-policy-resolution]] 은 Keycloak readiness 설정이 eager-init 정책으로 상속될 수 있음을 설명한다.
