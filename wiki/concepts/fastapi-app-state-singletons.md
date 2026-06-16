---
title: FastAPI app.state singletons
created: 2026-06-16
updated: 2026-06-16
type: concept
tags: [fastapi, architecture, integration, performance, convention]
sources: [raw/articles/fastapi-core-prd-2026-06-16.md]
confidence: medium
---
# FastAPI app.state singletons

## Definition
이 개념은 외부 서비스 접근 객체를 애플리케이션 시작 시 한 번만 생성해 `app.state` 에 저장하고, 이후 FastAPI dependency 가 이를 재사용하는 패턴을 설명한다. PRD는 auth provider, DB engine, MinIO, sync/async Milvus, Ollama, NATS 를 모두 이 방식으로 관리하도록 명시한다.

## State Contract
각 객체의 state 속성명은 SDK가 내부적으로 고정한다. 서비스 개발자는 속성명을 직접 다루지 않고 `set_*` 저장 함수와 `get_*` dependency 함수만 사용한다. 이 규칙은 `app.state` 계약을 라이브러리 내부로 숨기고, 사용자는 [[fastapi-core]] 가 제공하는 공개 API만 사용하게 만든다.

또한 PRD는 fallback 정책도 명시한다. 해당 state 값이 없으면 dependency 는 `EnvConfig` 를 읽어 객체를 생성하고, 생성한 객체를 다시 `app.state` 에 저장해 재사용한다. 이 정책은 lifespan 없이도 동작하게 해주지만, startup 중심 운영 모델과 어떻게 균형을 잡을지는 [[sdk-health-check-patterns]] 및 [[fastapi-app-factory-and-health-routes]] 와 함께 봐야 한다.

## Trade-offs
장점은 요청마다 클라이언트를 재생성하지 않아 성능과 일관성을 얻는다는 점이다. 반면 state 초기화 시점이 startup 인지 첫 요청인지에 따라 실패 노출 시점과 운영 경험이 달라질 수 있다. 따라서 이 패턴은 단순 캐싱이 아니라 lifecycle 정책의 일부로 봐야 한다.

## Related Topics
- [[fastapi-core]] 는 이 singleton/state 패턴을 제품의 기본 운영 규칙으로 둔다.
- [[layered-configuration-model]] 은 fallback 생성에 사용되는 설정 모델을 설명한다.
- [[fastapi-app-factory-and-health-routes]] 는 lifespan 과 health route 에서 이 객체들이 어떻게 쓰이는지 정리한다.
- [[service-factory-registry]] 는 더 중앙화된 서비스 조립 방향을 보여준다.
- [[fastapi-core-codebase-review-against-docmesh-py-core]] 는 request-time lazy init 과 startup lifecycle 사이의 긴장을 분석한다.
