---
title: Layered configuration model
created: 2026-06-16
updated: 2026-06-17
type: concept
tags: [config, architecture, sdk, convention, fastapi]
sources: [raw/articles/fastapi-core-prd-2026-06-16.md, raw/articles/fastapi-core-config-2026-06-17.md]
confidence: medium
---
# Layered configuration model

## Definition
이 개념은 `fastapi-core` 가 설정을 두 레이어로 나누는 방식을 설명한다. PRD 기준으로 `EnvConfig` 는 외부 서비스 접속 정보와 실행 환경 값을 담당하고, `ServiceSettings` 는 lifecycle, health, CORS, JWT 정책처럼 애플리케이션 동작 방식을 담당한다.

## Core Structure
이 분리는 `__` 기반 중첩 환경변수 주입, `.env` 기반 기본 로드, 설정 파일 미존재 시 기본값 fallback, 그리고 환경별 동작 정책 제어와 결합된다. 즉 설정값이 어디서 오고 어떤 책임을 갖는지를 분리해, 인프라 접속 정보와 서비스 동작 정책이 같은 계층에 섞이지 않게 하는 모델이다.

새 PRD와 설정 가이드는 이 레이어가 단순 설정 보관을 넘어 managed lifespan 과 readiness 정책까지 제어하는 기준선임을 더 분명히 한다. 특히 `ServiceSettings.lifecycle` 과 `ServiceSettings.health` 가 startup eager-init 정책으로 연결된다는 점은 [[lifecycle-policy-resolution]] 로 따로 분리해 볼 만한 핵심 규칙이다. 그 결과 설정은 [[fastapi-app-factory-and-health-routes]] 의 앱 조립 흐름, [[fastapi-app-state-singletons]] 의 fallback 생성 정책, [[registry-backed-dependency-resolution]] 의 runtime 해석 전략을 함께 지탱하는 상위 계약이 된다.

## Why It Matters
설정 레이어를 분리하면 플랫폼 담당자는 외부 서비스 접속 정보와 환경변수를 관리하고, 애플리케이션 개발자는 서비스 동작 정책을 YAML 또는 설정 객체에서 제어할 수 있다. 이는 [[fastapi-core]] 가 목표로 하는 중복 제거와 운영 일관성의 전제다.

## Related Topics
- [[fastapi-core]] 는 이 설정 모델을 제품의 핵심 기반으로 둔다.
- [[configuration-principles]] 는 환경변수 중심 운영 원칙을 더 넓게 설명한다.
- [[database-configuration-patterns]] 는 이 레이어 위에서 데이터 저장소 설정 규칙이 어떻게 구체화되는지 보여준다.
- [[keycloak-configuration-rules]] 는 인증 영역에서의 세부 환경변수 계약을 설명한다.
- [[fastapi-app-factory-and-health-routes]] 는 설정이 앱 조립 흐름에 주입되는 위치를 다룬다.
- [[registry-backed-dependency-resolution]] 은 이 설정이 dependency fallback 과 registry 해석에 어떻게 쓰이는지 설명한다.
- [[lifecycle-policy-resolution]] 은 YAML 기반 lifecycle/health 값이 startup 정책으로 계산되는 방식을 설명한다.
