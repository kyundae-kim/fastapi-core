---
title: Lifecycle policy resolution
created: 2026-06-17
updated: 2026-06-17
type: concept
tags: [config, architecture, fastapi, convention, sdk]
sources: [raw/articles/fastapi-core-config-2026-06-17.md]
confidence: medium
---
# Lifecycle policy resolution

## Definition
이 개념은 `ServiceSettings.lifecycle` 과 `ServiceSettings.health` 값을 결합해 startup eager-init 정책을 계산하는 규칙을 설명한다. `docs/config.md` 는 `resolve_lifecycle_policy(settings)` 가 일부 서비스의 eager 여부를 health 설정에서 상속하고, 나머지는 명시값을 그대로 사용한다고 정리한다.

## Resolution rules
`eager_keycloak`, `eager_database`, `eager_minio`, `eager_langfuse` 가 `null` 이면 각각 `health.check_keycloak`, `health.check_database`, `health.check_minio`, `health.check_langfuse` 값을 따른다. 반면 `eager_milvus`, `eager_async_milvus`, `eager_ollama`, `eager_nats` 는 문서에 적힌 기본값 또는 명시값을 그대로 유지한다.

또한 관리 대상 서비스 가운데 하나라도 eager-init 대상이면 startup 단계에서 docmesh registry 를 선행 초기화한다. 단, `async_milvus_client` 는 예외적으로 registry가 아니라 `create_async_milvus_client(config.milvus)` 직접 경로를 사용한다. 이 점은 [[registry-backed-dependency-resolution]] 과 [[fastapi-app-state-singletons]] 에서 설명한 런타임 해석 규칙을 설정 수준으로 끌어올린 것이다.

## Why it matters
이 규칙 덕분에 운영자는 readiness 정책과 startup 비용 사이를 YAML만으로 조정할 수 있다. 또한 `use_docmesh_registry` 는 dependency 계층의 registry 사용 여부를 뒤집는 스위치가 아니라, startup 에서 registry bootstrap 을 더 명시적으로 강제하는 정책 플래그라는 점이 중요하다.

## Related Topics
- [[layered-configuration-model]] 은 이 lifecycle 정책이 어느 설정 레이어에 속하는지 설명한다.
- [[fastapi-app-factory-and-health-routes]] 는 계산된 정책이 `create_app()` 과 managed lifespan 아래서 어떻게 소비되는지 설명한다.
- [[registry-backed-dependency-resolution]] 은 lifecycle 정책이 어떤 dependency 해석 경로를 전제로 하는지 설명한다.
- [[fastapi-app-state-singletons]] 은 eager-init 결과가 어떤 state 키에 보관되는지 설명한다.
- [[function-style-fastapi-dependencies]] 는 외부 소비자가 보게 되는 dependency 표면이 여전히 함수형 API임을 설명한다.
