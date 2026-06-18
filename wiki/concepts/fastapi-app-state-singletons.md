---
title: FastAPI app.state singletons
created: 2026-06-16
updated: 2026-06-17
type: concept
tags: [fastapi, architecture, integration, performance, convention]
sources: [raw/articles/fastapi-core-prd-2026-06-16.md, raw/articles/fastapi-core-api-2026-06-17.md]
confidence: medium
---
# FastAPI app.state singletons

## Definition
이 개념은 외부 서비스 접근 객체를 애플리케이션 수명주기 안에서 재사용하도록 `app.state` 에 저장하는 패턴을 설명한다. 2026-06-17 PRD는 auth provider, DB engine, MinIO, sync/async Milvus, Ollama, NATS 뿐 아니라 Langfuse dependency 경로까지 포함해 state 캐시와 lifecycle 정리 규칙을 더 명시적으로 설명한다.

## State Contract
각 객체의 state 속성명은 SDK가 내부적으로 고정한다. 서비스 개발자는 속성명을 직접 다루지 않고 `set_*` 저장 함수와 `get_*` dependency 함수만 사용한다. API 명세 기준 주요 키는 `config`, `settings`, `auth_provider`, `db_engine`, `minio_client`, `milvus_client`, `async_milvus_client`, `ollama_client`, `langfuse_client`, `nats_client` 다. 이 규칙은 `app.state` 계약을 라이브러리 내부로 숨기고, 사용자는 [[fastapi-core]] 가 제공하는 공개 API만 사용하게 만든다.

또한 PRD는 fallback 정책과 lifecycle 정책을 함께 적는다. 해당 state 값이 없으면 dependency 는 필요한 설정을 읽어 객체를 생성하고, 생성한 객체를 다시 `app.state` 에 저장해 재사용한다. 동시에 startup 에서는 eager-init 정책을 통해 미리 자원을 준비하고, shutdown 에서는 `close` / `dispose` / `drain` / `flush` 정리를 수행한다. 이 점에서 이 패턴은 단순 캐시가 아니라 [[registry-backed-dependency-resolution]] 과 결합된 운영 계약이다.

## Trade-offs
장점은 요청마다 클라이언트를 재생성하지 않아 성능과 일관성을 얻는다는 점이다. 반면 startup 실패 조기 노출과 request-time fallback 유연성 사이의 긴장은 여전히 존재한다. 그래서 이 패턴은 캐싱 전략이라기보다 [[fastapi-app-factory-and-health-routes]] 와 함께 봐야 하는 lifecycle 정책의 일부다.

## Related Topics
- [[fastapi-core]] 는 이 singleton/state 패턴을 제품의 기본 운영 규칙으로 둔다.
- [[layered-configuration-model]] 은 fallback 생성과 lifecycle 정책에 사용되는 설정 모델을 설명한다.
- [[fastapi-app-factory-and-health-routes]] 는 lifespan 과 health route 에서 이 객체들이 어떻게 쓰이는지 정리한다.
- [[function-style-fastapi-dependencies]] 는 state 키를 직접 노출하지 않는 공식 dependency 표면을 설명한다.
- [[registry-backed-dependency-resolution]] 은 state 저장 전 서비스가 어떤 해석 경로를 타는지 설명한다.
- [[service-factory-registry]] 는 더 중앙화된 서비스 조립 방향을 보여준다.
- [[fastapi-core-codebase-review-against-docmesh-py-core]] 는 startup/lazy-init 사이의 긴장을 분석한다.
