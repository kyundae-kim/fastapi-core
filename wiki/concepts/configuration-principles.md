---
title: Configuration principles
created: 2026-06-11
updated: 2026-06-11
type: concept
tags: [config, sdk, security, convention, deployment]
sources: [raw/articles/docmesh-py-core-config-2026-06-11.md]
confidence: medium
---
# Configuration principles

## Definition
`docmesh-py-core` 의 설정 모델은 모든 외부 서비스 연결 정보를 환경변수에서 읽고, 애플리케이션 시작 시 1회 로드·검증하는 원칙에 기반한다. URL, 계정, 비밀번호, token, secret key를 코드에 하드코딩하지 않는 것이 기본 전제다.

## Core Rules
공백 문자열은 값이 없는 것으로 간주하고, boolean 값은 대소문자와 관계없이 `true` / `false` 로 해석한다. 숫자형 값은 허용 범위를 검증하며, 공통 timeout/retry/pool 설정을 두지 않고 서비스별 환경변수로 분리한다. 이 원칙은 [[load-settings-and-settings-model]] 의 검증 계약을 구체화한다.

## Environment Strategy
로컬/개발/스테이징/운영의 차이는 코드 분기가 아니라 환경변수 값으로 표현한다. 운영에서는 TLS 및 인증서 검증을 기본값으로 유지하고, SSL 검증 비활성화는 개발/테스트에서만 허용하는 방향을 권장한다. integration 테스트 역시 운영 설정과 분리된 별도 `.env.integration` 또는 CI secret 세트를 써야 한다.

## Security Posture
민감정보는 Secret Manager, CI secret, 배포 플랫폼 secret 주입 기능으로 관리해야 하며, 출력이 필요한 경우에는 [[mask-sensitive-value]] 정책을 따라 마스킹해야 한다. 이 원칙은 DSN, token, secret, 파일 경로 같은 여러 서비스 설정 전반에 공통으로 적용된다.

## Related Topics
- [[load-settings-and-settings-model]] 는 이 원칙을 실제 설정 객체 생성으로 연결한다.
- [[environment-driven-service-selection]] 은 설정이 채워졌는지 여부를 런타임 분기 기준으로 사용한다.
- [[mask-sensitive-value]] 는 설정과 오류 메시지의 보안 노출을 줄이는 도구다.
