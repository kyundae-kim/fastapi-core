# Wiki Schema

## Domain
소프트웨어 개발 지식 베이스 — 프레임워크, 아키텍처 패턴, 설계 원칙, 도구, 언어, 라이브러리 등을 다룬다.
FastAPI, Python, DevOps, 시스템 설계, 분산 시스템, 클라우드 등 실용적 개발 지식 중심.

## Conventions
- 파일명: 소문자, 하이픈, 공백 없음 (예: `clean-architecture.md`)
- 모든 위키 페이지는 YAML frontmatter로 시작
- `[[wikilinks]]` 로 페이지 간 연결 (페이지당 최소 아웃바운드 링크 2개)
- 페이지 수정 시 `updated` 날짜 업데이트 필수
- 새 페이지는 `index.md` 의 올바른 섹션에 추가
- 모든 작업은 `log.md` 에 추가 (append-only)
- 3개 이상의 소스를 합성하는 페이지에는 단락 끝에 `^[raw/articles/source.md]` 출처 마커 사용

## Frontmatter
```yaml
---
title: 페이지 제목
created: YYYY-MM-DD
updated: YYYY-MM-DD
type: entity | concept | comparison | query | summary
tags: [태그 목록]
sources: [raw/articles/source-name.md]
confidence: high | medium | low
contested: true   # 해결되지 않은 모순이 있을 때
contradictions: [other-page-slug]
---
```

## Tag Taxonomy

### 언어/런타임
- `python` `javascript` `typescript` `go` `rust` `java` `kotlin`

### 프레임워크/라이브러리
- `fastapi` `django` `flask` `react` `nextjs` `express`
- `sqlalchemy` `pydantic` `celery` `redis`

### 아키텍처/패턴
- `architecture` `design-pattern` `microservices` `monolith`
- `clean-architecture` `ddd` `cqrs` `event-sourcing`
- `rest` `graphql` `grpc` `websocket`

### 인프라/DevOps
- `docker` `kubernetes` `ci-cd` `cloud` `aws` `gcp` `azure`
- `database` `postgresql` `mongodb` `elasticsearch`
- `monitoring` `observability` `logging`

### 개념/원칙
- `performance` `security` `scalability` `reliability`
- `testing` `tdd` `bdd` `solid` `dry` `kiss`
- `concurrency` `async` `distributed-systems`

### 메타
- `comparison` `timeline` `best-practice` `pitfall` `tutorial`
- `tool` `person` `company` `open-source`

## Page Thresholds
- **페이지 생성:** 2개 이상 소스에서 등장하거나 하나의 소스에서 핵심적 역할
- **기존 페이지에 추가:** 소스가 이미 다루는 항목을 언급할 때
- **페이지 생성 금지:** 단순 언급, 사소한 세부사항, 도메인 외 항목
- **페이지 분리:** ~200줄 초과 시 하위 토픽으로 분리 후 상호 링크
- **페이지 보관:** 내용이 완전히 대체됐을 때 `_archive/` 로 이동

## Entity Pages
한 페이지 = 하나의 주목할 만한 엔티티 (프레임워크, 라이브러리, 회사, 인물 등)
- 개요 / 무엇인지
- 핵심 사실과 날짜
- 다른 엔티티와의 관계 ([[wikilinks]])
- 소스 참조

## Concept Pages
한 페이지 = 하나의 개념 또는 주제 (패턴, 원칙, 기법 등)
- 정의/설명
- 현재 지식 상태
- 열린 질문 또는 논쟁
- 관련 개념 ([[wikilinks]])

## Comparison Pages
나란히 비교 분석. 포함 내용:
- 무엇을 비교하는지, 이유
- 비교 차원 (테이블 형식 권장)
- 결론 또는 종합
- 소스

## Update Policy
새 정보가 기존 내용과 충돌할 때:
1. 날짜 확인 — 최신 소스가 일반적으로 우선
2. 진짜 모순이면 두 입장 모두 날짜와 소스와 함께 기록
3. frontmatter에 모순 표시: `contradictions: [page-name]`
4. 린트 보고서에서 사용자 검토 요청
