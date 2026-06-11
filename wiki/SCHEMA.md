# Wiki Schema

## Domain
FastAPI 기반의 재사용 가능한 SDK 프로젝트 지식베이스. 다양한 저장소(storage/repository), LLM 연동, 외부 서비스 커넥터, Keycloak 기반 인증/인가를 중심으로 아키텍처, 설계 결정, 구현 패턴, 비교 분석, 운영 지식을 정리한다.

## Conventions
- 파일명: 소문자, 하이픈 사용, 공백 없음 (예: `keycloak-token-flow.md`)
- 모든 위키 페이지는 YAML frontmatter로 시작한다.
- 페이지 간 연결은 `[[wikilinks]]` 를 사용한다. 모든 신규 페이지는 최소 2개의 outbound link를 포함한다.
- 페이지를 수정할 때마다 `updated` 날짜를 반드시 갱신한다.
- 새로운 위키 페이지는 반드시 `index.md` 의 올바른 섹션에 추가한다.
- 모든 작업은 `log.md` 에 append 한다.
- 3개 이상의 출처를 종합하는 문단에는 문단 끝에 `^[raw/articles/source-file.md]` 형태의 provenance marker를 추가한다.
- 원문(raw) 영역은 immutable 이다. 정정 사항은 위키 페이지에서만 다룬다.
- 하나의 페이지가 200줄을 넘으면 하위 주제로 분리한다.

## Frontmatter
```yaml
---
title: Page Title
created: YYYY-MM-DD
updated: YYYY-MM-DD
type: entity | concept | comparison | query | summary
tags: [from taxonomy below]
sources: [raw/articles/source-name.md]
confidence: high | medium | low
contested: true
contradictions: [other-page-slug]
---
```

- `confidence`, `contested`, `contradictions` 는 필요 시에만 사용한다.
- 단일 출처 기반이거나 빠르게 변하는 내용은 `confidence: medium` 또는 `low` 를 우선 고려한다.

## raw/ Frontmatter
```yaml
---
source_url: https://example.com/article
ingested: YYYY-MM-DD
sha256: <hex digest of the raw content below the frontmatter>
---
```

## Tag Taxonomy
아래 taxonomy 에 없는 태그는 먼저 이 문서에 추가한 뒤 사용한다.

- Core: sdk, fastapi, architecture, api, integration, auth
- Security: keycloak, oauth2, oidc, rbac, token, session
- AI/LLM: llm, prompt, embedding, reranking, inference, evaluation
- Data/Storage: repository, database, vector-db, cache, object-storage, queue
- Delivery/Ops: testing, observability, deployment, performance, config, migration
- Meta: comparison, query, decision, risk, roadmap, convention

## Page Thresholds
- 2개 이상의 출처에서 반복 등장하거나, 하나의 출처에서 중심 주제인 경우 새 페이지를 만든다.
- 이미 있는 주제면 새 페이지를 만들지 말고 기존 페이지를 확장한다.
- 스쳐 지나가는 언급, 범위 밖 세부사항, 구현과 무관한 주변 정보는 페이지를 만들지 않는다.
- 페이지가 과도하게 커지면 하위 주제로 분리하고 상호 링크를 건다.
- 완전히 대체된 내용은 `_archive/` 로 이동하고 인덱스에서 제거한다.

## Entity Pages
주요 엔티티(예: Keycloak, Milvus, OpenSearch, 특정 SDK 모듈, 외부 서비스)에 대해 작성한다.
포함 항목:
- 개요 / 무엇인지
- 핵심 역할과 책임
- 인터페이스 또는 연결 방식
- 관련 엔티티와의 관계 (`[[wikilinks]]`)
- 출처

## Concept Pages
핵심 개념(예: 인증 플로우, repository abstraction, LLM provider adapter, tenant isolation, retry policy)에 대해 작성한다.
포함 항목:
- 정의 / 설명
- 설계 패턴 또는 권장 방식
- 알려진 trade-off
- 열린 질문 / 미해결 이슈
- 관련 개념 (`[[wikilinks]]`)

## Comparison Pages
대안 비교(예: provider adapter 설계, vector store 선택, sync vs async client, auth 전략 비교)를 다룬다.
포함 항목:
- 비교 대상과 목적
- 비교 축 (표 권장)
- 결론 또는 추천
- 출처

## Update Policy
새로운 정보가 기존 내용과 충돌할 때:
1. 날짜를 확인하고 일반적으로 더 최신 출처를 우선한다.
2. 실제로 상충하면 두 입장을 모두 날짜와 함께 기록한다.
3. frontmatter 에 `contradictions:` 를 추가한다.
4. 필요 시 `contested: true` 로 표시하고 lint 결과에 포함한다.

## Recommended Initial Sections
초기에는 아래 주제를 우선 채운다.
- 인증/인가: Keycloak, token lifecycle, service-to-service auth
- LLM 연동: provider abstraction, prompt/runtime config, fallback/retry
- 저장소 연동: relational DB, vector DB, cache, object storage
- SDK 구조: package layout, client API, settings/config, error handling
- 운영: observability, testing strategy, migration/compatibility
