---
title: Layered configuration model
created: 2026-06-16
updated: 2026-06-16
type: concept
tags: [config, architecture, sdk, convention, fastapi]
sources: [raw/articles/fastapi-core-prd-2026-06-16.md]
confidence: medium
---
# Layered configuration model

## Definition
이 개념은 `fastapi-core` 가 설정을 두 레이어로 나누는 방식을 설명한다. PRD 기준으로 `EnvConfig` 는 외부 서비스 접속 정보, 실행 환경, 로깅 레벨 같은 배포 환경별 값을 담당하고, `ServiceSettings` 는 CORS 정책이나 JWT 검증 정책처럼 애플리케이션 동작 방식을 담당한다.

## Core Structure
이 분리는 환경별 `.env` 파일 지원, `dev`/`stage`/`prod` 분리, 그리고 `KEYCLOAK__REALM` 같은 `__` 기반 중첩 환경변수 주입과 결합된다. 즉 설정값이 어디서 오고 어떤 책임을 갖는지를 분리해, 인프라 접속 정보와 서비스 동작 정책이 같은 계층에 섞이지 않게 하는 모델이다.

이 패턴은 기존 [[configuration-principles]] 와 겹치지만, 여기서는 특히 `fastapi-core` 제품 요구사항 관점에서 환경 정보와 서비스 정책을 별도의 모델로 분리한다는 점이 중요하다. 이는 [[fastapi-app-factory-and-health-routes]] 에서 앱 조립 시 설정을 주입하는 방식과도 연결된다.

## Why It Matters
설정 레이어를 분리하면 인프라/DevOps 역할과 서비스 개발자 역할이 덜 충돌한다. 인프라 담당자는 외부 서비스 접속 정보와 환경변수를 관리하고, 애플리케이션 개발자는 서비스 동작 정책을 YAML 또는 설정 객체에서 제어할 수 있다. 이는 [[fastapi-core]] 가 목표로 하는 중복 제거와 일관성 보장에 필요한 전제다.

## Related Topics
- [[fastapi-core]] 는 이 설정 모델을 제품의 핵심 기반으로 둔다.
- [[configuration-principles]] 는 환경변수 중심 운영 원칙을 더 넓게 설명한다.
- [[database-configuration-patterns]] 는 이 레이어 위에서 데이터 저장소 설정 규칙이 어떻게 구체화되는지 보여준다.
- [[keycloak-configuration-rules]] 는 인증 영역에서의 세부 환경변수 계약을 설명한다.
- [[fastapi-app-factory-and-health-routes]] 는 설정이 앱 조립 흐름에 주입되는 위치를 다룬다.
