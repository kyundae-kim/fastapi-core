# Wiki Schema

## Domain
fastapi-core backend implementation wiki

This wiki covers the fastapi-core backend implementation: requirements, API behavior, configuration, messaging, testing strategy, architecture, implementation status, and operational knowledge.

## Conventions
- File names: lowercase, hyphens, no spaces (e.g., `request-routing.md`)
- Every wiki page starts with YAML frontmatter (see below)
- Use `[[wikilinks]]` to link between pages (minimum 2 outbound links per page)
- When updating a page, always bump the `updated` date
- Every new page must be added to `index.md` under the correct section
- Every action must be appended to `log.md`
- Provenance markers: on pages synthesizing 3+ sources, append `^[raw/articles/source-file.md]` at the end of paragraphs whose claims come from a specific source
- Prefer repo-local sources first (docs/, source files, tests/) before external commentary
- For repo-doc-vs-code comparisons, include direct verification evidence from file reads and executed tests/commands

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

`confidence`, `contested`, and `contradictions` are optional, but recommended for incomplete implementation audits, architecture debates, or single-source claims.

### raw/ Frontmatter

```yaml
---
source_url: https://example.com/article
ingested: YYYY-MM-DD
sha256: <hex digest of the raw content below the frontmatter>
---
```

The `sha256:` is computed over the body only (everything after the closing `---`).

## Tag Taxonomy
- Product / scope: product, requirement, roadmap, use-case, workflow
- Architecture: architecture, service, module, boundary, lifecycle, integration
- API / interfaces: api, endpoint, schema, contract, protocol, messaging
- Runtime / ops: config, deployment, environment, observability, performance, security
- Code / quality: implementation, refactor, test, migration, debt, bug
- Meta: comparison, query, decision, glossary, open-question

Rule: every tag on a page must appear in this taxonomy. Add new tags here before using them.

## Page Thresholds
- Create a page when an entity/concept appears in 2+ sources OR is central to one source
- Add to an existing page when a source mentions something already covered
- Don't create pages for passing mentions, minor details, or topics outside the fastapi-core domain
- Split a page when it exceeds ~200 lines
- Archive a page when its content is fully superseded — move to `_archive/`, remove from index

## Entity Pages
Use for notable repo entities such as services, subsystems, major modules, protocols, or external dependencies. Include:
- Overview / responsibility
- Key interfaces and files
- Relationships to other entities (`[[wikilinks]]`)
- Source references

## Concept Pages
Use for requirements themes, architectural patterns, workflows, and implementation topics. Include:
- Definition / explanation
- Current implementation state
- Open questions or gaps
- Related concepts (`[[wikilinks]]`)

## Comparison Pages
Use for spec-vs-code, design-vs-implementation, or option analyses. Include:
- What is being compared and why
- Dimensions of comparison (table preferred)
- Verdict / synthesis
- Source references and verification evidence

## Update Policy
When new information conflicts with existing content:
1. Check dates and code reality first — newer code or tests usually supersede older docs
2. If genuinely contradictory, note both positions with dates and sources
3. Mark the contradiction in frontmatter: `contradictions: [page-name]`
4. Flag it for user review in lint or comparison output
