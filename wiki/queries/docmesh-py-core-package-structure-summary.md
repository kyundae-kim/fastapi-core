---
title: docmesh-py-core package structure summary
created: 2026-06-24
updated: 2026-06-24
type: query
tags: [query, sdk, architecture, api, config]
sources: [raw/articles/docmesh-py-core-sdk-2026-06-11.md, raw/articles/docmesh-py-core-api-2026-06-11.md, raw/articles/docmesh-py-core-config-2026-06-11.md]
confidence: medium
---
# docmesh-py-core package structure summary

## Structural View
`docmesh-py-core` 를 패키지 구조 관점에서 보면, 이 SDK는 하나의 거대한 범용 도구 상자라기보다 **설정 레이어**, **서비스 조립 레이어**, **공통 lifecycle 래퍼 레이어**, **헬스체크 집계 레이어**, **Keycloak 인증/프로비저닝 레이어**, **보안 유틸리티 레이어**로 나뉜다. 패키지 루트는 이 레이어들의 대표 엔트리포인트만 재수출하고, 일반 소비자는 하위 모듈보다 루트 import를 우선 쓰도록 설계되어 있다. ^[raw/articles/docmesh-py-core-api-2026-06-11.md]

## 1. Package Root: curated entrypoints
문서 기준 패키지 루트 `docmesh_py_core` 에서 바로 import 가능한 표면은 `load_settings`, `Settings`, `ServiceFactoryRegistry`, `ServiceClientWrapper`, `NatsConnectionBuilder`, `check_all_services`, `KeycloakAuthService`, `KeycloakProvisioner`, `mask_sensitive_value`, 그리고 인증/헬스체크 관련 예외·결과 타입들이다. 즉 루트는 "가장 자주 쓰는 공식 표면"을 모아둔 얇은 facade 역할을 한다. 이 점은 [[docmesh-py-core]] 가 단순 서비스 클라이언트 묶음이 아니라 운영 계약까지 포함한 SDK라는 해석과 맞닿아 있다. ^[raw/articles/docmesh-py-core-api-2026-06-11.md]

## 2. Configuration Layer
가장 아래의 진입 레이어는 [[load-settings-and-settings-model]] 이다. `load_settings(env)` 는 환경변수를 읽고 검증해 `Settings` 를 만들며, `Settings` 내부에는 `common`, `keycloak`, `postgres`, `sqlite`, `minio`, `milvus`, `ollama`, `langfuse`, `nats` 같은 서비스별 설정이 묶인다. 구조적으로 보면 이 레이어는 나머지 전부의 선행조건이며, 서비스별 timeout/retry/security 규칙도 여기서 결정된다. ^[raw/articles/docmesh-py-core-config-2026-06-11.md]

## 3. Service Assembly Layer
설정 다음의 중심 레이어는 [[service-factory-registry]] 다. `ServiceFactoryRegistry(settings)` 는 PostgreSQL, SQLite, MinIO, Milvus, Ollama, Langfuse, NATS, Keycloak 같은 외부 연동의 생성 책임을 한곳으로 모은다. 패키지 구조상 이 레이어는 소비 코드가 서비스별 SDK 초기화 세부사항을 직접 알지 않게 만드는 composition root에 해당한다. 또한 어떤 저장소를 실제로 쓸지는 [[environment-driven-service-selection]] 패턴처럼 설정 populated state에 따라 갈린다. ^[raw/articles/docmesh-py-core-sdk-2026-06-11.md]

## 4. Per-service Wrapper / Builder Layer
registry 아래의 반환 표면은 완전히 단일하지 않다. 대부분 서비스는 [[service-client-wrapper]] 로 감싸져 공통 `ping()`, `check()`, `close()` 계약을 제공한다. 반면 NATS는 연결 완료 client가 아니라 `NatsConnectionBuilder` 를 반환하며, 반드시 async 경계에서 `await connect()` 또는 `await check()` 로 사용해야 한다. 구조적으로 보면 `docmesh-py-core` 는 "공통 wrapper 기반 서비스들"과 "예외적인 async builder 서비스"를 함께 품는 혼합 구조다. ^[raw/articles/docmesh-py-core-api-2026-06-11.md]

## 5. Health Aggregation Layer
개별 서비스 `check()` 위에는 [[sdk-health-check-patterns]] 와 [[check-all-services]] 로 대표되는 운영 레이어가 놓인다. 패키지 구조상 이 레이어는 서비스 생성 이후 startup/readiness 판단을 공통화하는 역할을 하며, 여러 서비스의 health 함수를 받아 성공 여부·지연 시간·오류를 집계한다. 즉 `docmesh-py-core` 는 단순 생성기(factory)에서 멈추지 않고, 생성 이후 운영 상태 판정까지 패키지 표면에 포함한다. ^[raw/articles/docmesh-py-core-api-2026-06-11.md]

## 6. Authentication / Control-plane Layer
인증 쪽은 registry 중심의 일반 서비스 레이어와 별도 축을 이룬다. [[keycloak-auth-integration]] 은 런타임 토큰 발급과 JWT 검증을 담당하고, [[keycloak-provisioner]] 는 realm/client/role 상태를 선언적으로 맞추는 관리 평면 역할을 맡는다. 즉 구조적으로 Keycloak 관련 표면은 **runtime auth** 와 **admin provisioning** 이라는 두 하위 레이어로 갈라져 있으며, 둘 다 같은 `Settings` 를 공유하지만 책임은 다르다. ^[raw/articles/docmesh-py-core-api-2026-06-11.md]

## 7. Security Utility Layer
`mask_sensitive_value()` 는 독립적인 보안 유틸리티 레이어다. DSN, URL, token, secret, query string 같은 민감정보를 로그·예외·운영 화면에 내보내기 전 마스킹하도록 설계되어 있다. 이 함수는 다른 레이어처럼 서비스 조립을 담당하지는 않지만, 설정/헬스체크/인증 오류를 안전하게 표면화하기 위해 패키지 전반에 걸쳐 재사용되는 횡단 관심사(cross-cutting concern)다. ^[raw/articles/docmesh-py-core-config-2026-06-11.md]

## Practical Mental Model
실무적으로는 `docmesh-py-core` 를 아래처럼 이해하면 가장 깔끔하다.

1. **root API**: 루트에서 공식 엔트리포인트 import
2. **config**: `load_settings()` 와 `Settings`
3. **composition**: `ServiceFactoryRegistry`
4. **service surface**: `ServiceClientWrapper` 또는 `NatsConnectionBuilder`
5. **operations**: `check()` / `check_all_services()` / `close_all()`
6. **auth/control plane**: `KeycloakAuthService` / `KeycloakProvisioner`
7. **security utility**: `mask_sensitive_value()`

이 모델은 [[docmesh-py-core-package-summary]] 의 책임 요약을 더 구조화한 버전이며, 이후 [[fastapi-core]] 같은 상위 SDK가 어떤 층을 확장하거나 감싸는지 비교할 때 기준선으로 쓰기 좋다. ^[raw/articles/docmesh-py-core-sdk-2026-06-11.md]
