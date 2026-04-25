# Phase 5: Integration, Polish, and Portfolio Hardening - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-25
**Phase:** 05-integration-polish-and-portfolio-hardening
**Areas discussed:** Top-3 alternatives UX, Integration test DB strategy, Deployment target, Source attribution format

---

## Top-3 Alternatives UX

| Option | Description | Selected |
|--------|-------------|----------|
| Empty db_results | VALIDATE already detects zero rows — clean, unambiguous trigger | ✓ |
| Partial results below threshold | db_results returned data but couldn't fill 4 frontline slots | |
| Either empty or partial | ANALYZE decides which path | |

**User's choice:** Empty db_results

---

| Option | Description | Selected |
|--------|-------------|----------|
| 3 different team comps | 3 distinct team compositions, each with tradeoff label | ✓ |
| 3 best individual substitutions | 3 closest characters for the missing role | |
| 3 relaxed query variants | Progressively relaxed constraints | |

**User's choice:** 3 different team comps

---

| Option | Description | Selected |
|--------|-------------|----------|
| Collapsed accordion cards | 3 labelled sections, first expanded, same card layout inside | ✓ |
| Full card grid, stacked | 3 full card grids stacked vertically | |
| Text summary list | 3 bullet points — no character cards | |

**User's choice:** Collapsed accordion cards

---

| Option | Description | Selected |
|--------|-------------|----------|
| ANALYZE detects empty + generates 3 teams in one pass | No new Cypher queries — ANALYZE uses roster + plan_strategy context | ✓ |
| New retry loop with relaxed Cypher | Real graph data for each alternative, more latency and complexity | |

**User's choice:** ANALYZE detects empty + generates 3 teams in one pass

---

## Integration Test DB Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| AuraDB Free | Cloud Neo4j free tier, README walks through setup | ✓ |
| docker-compose + local Neo4j | Fully offline, Docker required | |
| Mock the driver | No Neo4j needed, less impressive for data engineering portfolio | |

**User's choice:** AuraDB Free

---

| Option | Description | Selected |
|--------|-------------|----------|
| pytest -m 'not integration' for unit-only | Uses existing pytest.mark.integration registration | ✓ |
| No split — all tests need Neo4j | Simpler instructions | |
| Two separate test suites | Cleaner separation | |

**User's choice:** pytest -m 'not integration' for unit-only

---

## Deployment Target

| Option | Description | Selected |
|--------|-------------|----------|
| AWS App Runner | Simpler pipeline, auto-HTTPS, appropriate for intermittent portfolio traffic | ✓ |
| ECS Fargate + ALB | More enterprise complexity, demonstrates stronger AWS/DevOps depth | |

**User's choice:** AWS App Runner

---

| Option | Description | Selected |
|--------|-------------|----------|
| AWS Secrets Manager | App Runner pulls via IAM role — production-grade secrets management | ✓ |
| App Runner env vars directly | Simpler, secrets visible in console | |
| SSM Parameter Store | Similar to Secrets Manager, simpler/cheaper | |

**User's choice:** AWS Secrets Manager

---

| Option | Description | Selected |
|--------|-------------|----------|
| python:3.12-slim, single-stage | Simple, small image; ETL triggered via endpoint not startup | ✓ |
| Multi-stage build | Smaller final image, more Dockerfile complexity | |
| python:3.12-slim + ETL on startup | Fresh data on deploy but slow startup blocks health checks | |

**User's choice:** python:3.12-slim, single-stage

---

## Source Attribution Format

| Option | Description | Selected |
|--------|-------------|----------|
| Embedded in synergy_explanation text | No schema change; FORMAT validates non-empty; citations inline | ✓ |
| Structured per-character attribution field | New 'attributions' list on CharacterSlot; richer data; schema change | |
| Separate synergy_sources list at TeamOutput level | Structured but not per-character | |

**User's choice:** Embedded in synergy_explanation text

---

| Option | Description | Selected |
|--------|-------------|----------|
| Prompt injection: mandate per-character citation | ANALYZE_SYSTEM_PROMPT updated with explicit format rule | ✓ |
| FORMAT validation: reject if no attribution markers | Brittle regex, no ANALYZE change | |
| Leave to Claude's discretion | Trust model to include attribution naturally | |

**User's choice:** Prompt injection: mandate per-character citation

---

## Claude's Discretion

- Specific accordion CSS/HTML structure
- Exact text labels for alternative team headings
- Latency measurement approach (log line format, location)
- README section structure and ordering

## Deferred Ideas

- Per-character structured attribution fields (`attributions: [{grasta, trait, effect}]`) — discussed, deferred in favor of embedded text
- ECS Fargate — discussed, App Runner chosen; ECS Fargate remains as a future upgrade
