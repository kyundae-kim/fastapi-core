---
title: ServiceFactoryRegistry
created: 2026-06-25
updated: 2026-07-02
type: concept
tags: [service, module, integration, api, implementation]
sources: [raw/articles/docmesh-py-core-api-reference-2026.md, raw/articles/docmesh-py-core-examples-guide-2026.md]
confidence: low
contested: true
---

# ServiceFactoryRegistry

`ServiceFactoryRegistry(settings)`는 docmesh-py-core의 older examples 문서에서 외부 서비스 클라이언트 생성을 위한 중앙 진입점으로 제시됐던 패턴이다. 당시 examples는 `create_client(service_name)`, `close_all()`, 앱 수명주기 동안 registry 재사용을 전제로 설명했다.^[raw/articles/docmesh-py-core-examples-guide-2026.md]

하지만 2026-07-02에 다시 ingest한 최신 API 레퍼런스의 루트 공개 import 목록에는 `ServiceFactoryRegistry`가 더 이상 나타나지 않고, 대신 `load_service_configs()`, 서비스별 config class, `create_*_client()`, `close_service_clients()` 중심 표면이 문서화된다. 최신 examples 역시 더 이상 registry 예시를 앞세우지 않고 direct factory 조립만 보여준다.^[raw/articles/docmesh-py-core-api-reference-2026.md]^[raw/articles/docmesh-py-core-examples-guide-2026.md]

## Historical role

older examples 기준 registry 패턴의 장점은 다음과 같다.

- 동일 서비스에 대해 이미 생성한 클라이언트를 재사용한다.
- startup 시 1회 생성해 `app.state.registry`에 보관하고 shutdown 시 `close_all()`로 정리할 수 있다.
- wrapper 기반 `check()` / `close()` 인터페이스를 서비스 이름 기반으로 묶어 호출부 분기를 줄인다.

## Current status

최신 public 문서 기준 canonical path는 direct factory 조립이다.

- `CommonConfig()` 또는 `load_service_configs()`로 설정을 준비한다.
- 필요한 서비스만 `create_*_client()`로 생성한다.
- 종료 시 `close_service_clients()` 또는 개별 `close()`를 호출한다.
- `nats`는 `NatsConnectionBuilder`를 통해 연결을 지연 생성한다.^[raw/articles/docmesh-py-core-api-reference-2026.md]^[raw/articles/docmesh-py-core-examples-guide-2026.md]

따라서 이 위키에서 `ServiceFactoryRegistry`는 "현재 canonical public API"라기보다, older docs와 일부 소비 코드에서 중요한 historical integration pattern으로 보는 편이 맞다.

## How to read this page

- 최신 SDK 표면 자체를 이해하려면 [[service-configuration-contracts]]와 [[application-integration-patterns]]를 먼저 읽는다.
- 기존 fastapi-core 같은 소비자가 registry 패턴을 어떻게 채택했는지 보려면 [[docmesh-py-core-vs-fastapi-core-usage-comparison]]을 함께 본다.
- 헬스체크 집계 측면에서는 registry 유무와 관계없이 [[service-health-check-aggregation]]가 최종 check callable 계약을 설명한다.

## Related pages

- [[docmesh-py-core]]: 패키지 전체 capability와 최신 공개 표면 변화의 상위 정리.
- [[application-integration-patterns]]: current direct factory 수명주기와 older registry 패턴의 차이를 함께 정리한다.
- [[service-configuration-contracts]]: direct config/API 조합이 현재 public entrypoint로 문서화된 배경.
- [[service-health-check-aggregation]]: registry가 있든 없든 서비스 check 결과 집계는 같은 health API를 사용한다.
