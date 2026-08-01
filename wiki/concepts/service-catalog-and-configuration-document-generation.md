---
title: Service catalog and configuration document generation
created: 2026-08-01
updated: 2026-08-01
type: concept
tags: [api, config, contract, module, implementation, workflow, security]
sources: [raw/articles/docmesh-py-core-api-reference-v0.6.0.md, raw/articles/docmesh-py-core-configuration-guide-v0.6.0.md, raw/articles/docmesh-py-core-examples-guide-v0.6.0.md, raw/articles/docmesh-py-core-env-example-v0.6.0.md]
confidence: medium
---

# Service catalog and configuration document generation

`docmesh-py-core` v0.6.0은 설정 모델과 client factory의 대응을 실행 시점에 추측하지 않도록 `SERVICE_CATALOG`라는 immutable `Service -> ServiceDescriptor` mapping을 공개한다. 각 descriptor는 config type, factory, sync runtime 지원 여부, 순서, 환경변수 metadata를 함께 표현한다.^[raw/articles/docmesh-py-core-api-reference-v0.6.0.md]

## Catalog metadata

`ServiceDescriptor.environment_variables()`는 `EnvironmentRequirement` tuple을 반환하고, `required_environment()`는 required 또는 conditional-required 항목을 분리한다. `EnvironmentRequirement`는 key, secret 여부, required 조건, default, production constraint를 표현하지만 실제 환경변수 값이나 secret 원문을 읽거나 보존하지 않는다.^[raw/articles/docmesh-py-core-api-reference-v0.6.0.md]

이 catalog는 [[docmesh-config]]의 설정 타입·서비스 선택 계약과 [[docmesh-py-core]]의 factory/runtime 표면 사이를 연결하는 문서화용 metadata다. catalog 자체는 client를 만들거나 외부 서비스에 연결하지 않는다.^[raw/articles/docmesh-py-core-api-reference-v0.6.0.md]^[raw/articles/docmesh-py-core-configuration-guide-v0.6.0.md]

## Generation APIs

- `generate_environment_template() -> str`: catalog 순서의 deterministic `KEY=value` 템플릿을 생성한다.
- `generate_configuration_reference() -> str`: required, secret, default, production constraint를 Markdown 표로 생성한다.

예제는 생성 결과가 deterministic하고 secret 원문을 포함하지 않는지 확인한다. 저장소의 소비자용 `.env.example`은 catalog 생성 결과에 common/logging 안내와 사용법을 더한 별도 template이므로 두 산출물을 동일한 파일로 취급하지 않는다.^[raw/articles/docmesh-py-core-api-reference-v0.6.0.md]^[raw/articles/docmesh-py-core-examples-guide-v0.6.0.md]^[raw/articles/docmesh-py-core-env-example-v0.6.0.md]

## Operational use

새 서비스나 환경변수 계약을 추가할 때는 config model, catalog descriptor, factory wiring, generated reference, consumer `.env.example` 사이의 추적성을 함께 확인해야 한다. `config.md`의 설정 → API 추적표와 catalog generation 예제가 이 경계를 구체화한다.^[raw/articles/docmesh-py-core-configuration-guide-v0.6.0.md]^[raw/articles/docmesh-py-core-examples-guide-v0.6.0.md]

이 패턴은 설정·문서·factory matrix가 서로 다른 source of truth로 drift하는 위험을 줄이지만, generated metadata가 실제 SDK 동작이나 deployment secret 주입을 대체하지는 않는다.^[raw/articles/docmesh-py-core-api-reference-v0.6.0.md]^[raw/articles/docmesh-py-core-env-example-v0.6.0.md]

## Related pages

- [[docmesh-config]]: canonical 설정 모델, 환경변수, 진단
- [[docmesh-py-core]]: catalog를 소비하는 client factory와 runtime
- [[service-configuration-contracts]]: 서비스별 설정과 production 제약
- [[application-integration-patterns]]: catalog/preflight 이후 assembly lifecycle
