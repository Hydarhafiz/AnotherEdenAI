# Requirements: Another Eden AI — GraphRAG Team Builder

**Defined:** 2026-03-14
**Core Value:** Mathematically optimal team recommendations constrained to the player's actual roster, zero hallucinated mechanics

## v1 Requirements

### Data Pipeline

- [x] **DATA-01**: System scrapes character data (name, element, weapon, light_shadow, personalities) from anothereden.wiki
- [x] **DATA-02**: System scrapes Grasta data for all categories (Attack, Life, Support, Special, VC) including tier, stats, personality_req, is_shareable
- [x] **DATA-03**: System scrapes Ore data (name, category, stats, source)
- [x] **DATA-04**: ETL pipeline is idempotent — re-running safely overwrites stale data without creating duplicates
- [x] **DATA-05**: Schema version is tracked as a constant in ETL; post-load assertion confirms expected node types exist after each run

### Graph Schema

- [x] **GRAPH-01**: Neo4j graph contains Character nodes with element, weapon, light_shadow, and name properties
- [x] **GRAPH-02**: Character nodes are linked to Trait nodes via HAS_TRAIT relationships
- [x] **GRAPH-03**: Neo4j graph contains Grasta nodes with is_shareable, personality_req, category, tier, and stats properties
- [x] **GRAPH-04**: Grasta shareability is modeled with explicit is_shareable property; activating_trait distinguishes equip from activation
- [x] **GRAPH-05**: Grasta nodes are linked to Trait nodes via REQUIRES_TRAIT relationships
- [x] **GRAPH-06**: Neo4j graph contains Ore nodes with stats and source properties; Ores are standalone nodes — no ENHANCES relationship (Ore application to Grasta is a dynamic player/AI decision handled by PLAN and ANALYZE agents, not a static graph edge)
- [x] **GRAPH-07**: Graph schema is documented in SCHEMA.md as a versioned contract before any LLM prompts are written

### Agent Workflow

- [ ] **AGENT-01**: PLAN agent (Sonnet 4.6) receives user query + roster and decomposes into graph traversal sub-goals
- [ ] **AGENT-02**: GENERATE_CYPHER agent (Sonnet 4.6) produces Cypher with full schema injected via Neo4jGraph.get_schema() and few-shot examples
- [ ] **AGENT-03**: VALIDATE agent (Haiku 4.6) verifies Cypher syntax and confirms query returns non-empty results against game rules
- [x] **AGENT-04**: VALIDATE agent routes failed queries back to GENERATE_CYPHER with full error context for correction
- [x] **AGENT-05**: Retry loop is hard-capped at 3 attempts via conditional edge in WorkflowState; exceeding cap routes to graceful error
- [ ] **AGENT-06**: ANALYZE agent (Sonnet 4.6) synthesizes validated query results into final team recommendation
- [x] **AGENT-07**: WorkflowState is a TypedDict validated by Pydantic v2; each node returns only the keys it modifies (no shared mutation)
- [x] **AGENT-08**: `src/workflow/llm.py` provides a `get_llm(role)` factory returning a `BaseChatModel`; `LLM_PROVIDER=ollama` in `.env` returns an Ollama-backed model for local testing; `LLM_PROVIDER=anthropic` (default) returns `ChatAnthropic` with the appropriate Sonnet or Haiku model for the given role

### Query Handling

- [ ] **QUERY-01**: User can input owned character roster (manually, as text list or CSV)
- [ ] **QUERY-02**: All recommendations are constrained to owned characters plus explicitly free-to-play units
- [ ] **QUERY-03**: User can submit natural language team-building queries (e.g., "highest damage blunt-zone synergy")
- [ ] **QUERY-04**: Character name input is normalized to canonical graph names before roster filtering

### Output

- [ ] **OUTPUT-01**: System returns team recommendations in 4-frontline/2-reserve format
- [ ] **OUTPUT-02**: Each recommendation includes personality + Grasta synergy explanation with source attribution (which Grasta + which trait)
- [ ] **OUTPUT-03**: Each character in the lineup includes a role annotation (e.g., "AF anchor", "off-element mule", "healer")
- [ ] **OUTPUT-04**: When no perfect match exists, system returns top 3 closest alternatives with explanation of tradeoffs
- [ ] **OUTPUT-05**: Validation progress is visible to user during pipeline execution ("Validating... attempt 2/3")

### Web Interface

- [ ] **WEB-01**: User can access the system via web browser (no installation required)
- [ ] **WEB-02**: Web UI provides roster input form and natural language query submission
- [ ] **WEB-03**: Pipeline node completion status is streamed to UI via SSE (PLAN → CYPHER → VALIDATE → ANALYZE)
- [ ] **WEB-04**: Neo4j driver is initialized as an app-level singleton with async connection pooling
- [ ] **WEB-05**: Admin can trigger a full data refresh via POST /admin/refresh-data endpoint

### Deployment

- [ ] **DEPLOY-01**: GitHub Actions CI/CD pipeline builds a Docker image of the FastAPI + HTMX app and pushes to AWS on merge to main
- [ ] **DEPLOY-02**: App is deployed to AWS App Runner or ECS Fargate with environment variables sourced from AWS Secrets Manager or Parameter Store
- [ ] **DEPLOY-03**: Deployment is production-ready — health checks pass, service auto-restarts on failure, and a public URL is accessible after deploy

---

## v2 Requirements

### Deep Optimization

- **OPT-01**: System calculates exact Grasta stat distribution across team for maximum DPS
- **OPT-02**: System models Badge stat allocation alongside Grasta for combined optimization
- **OPT-03**: System accounts for Another Force (AF) zone mechanics in synergy recommendations

### Farming Optimization

- **FARM-01**: System recommends optimal Another Dungeon (AD) for Red/Green key spending given upgrade goal
- **FARM-02**: System calculates expected drops per key for each dungeon
- **FARM-03**: System tracks daily key budget and recommends priority order

---

## v3 Requirements

### Boss Strategies

- **BOSS-01**: System generates turn-by-turn skill rotation for specified superboss
- **BOSS-02**: System identifies HP stopper thresholds and required burst damage windows
- **BOSS-03**: System cross-references team recommendation with boss mechanics (RAG over wiki guides)

---

## Out of Scope

| Feature | Reason |
|---------|--------|
| Account OCR / screen reading | High complexity, legal grey area, defer entirely |
| Real-time game state sync | No game API; would require client modification |
| PvP meta analysis | Another Eden is strictly PvE |
| Social features (build sharing) | Distraction from core AI pipeline for portfolio focus |
| Mobile app | Web-first; mobile would require React Native or similar |
| Opus 4.6 model usage | Explicitly excluded for latency and cost efficiency |

---

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DATA-01 | Phase 1 | Complete |
| DATA-02 | Phase 1 | Complete |
| DATA-03 | Phase 1 | Complete |
| DATA-04 | Phase 1 | Complete |
| DATA-05 | Phase 1 | Complete (01-01) |
| GRAPH-01 | Phase 1 | Complete |
| GRAPH-02 | Phase 1 | Complete |
| GRAPH-03 | Phase 1 | Complete |
| GRAPH-04 | Phase 1 | Complete |
| GRAPH-05 | Phase 1 | Complete |
| GRAPH-06 | Phase 1 | Complete |
| GRAPH-07 | Phase 1 | Complete (01-01) |
| AGENT-01 | Phase 2 | Pending |
| AGENT-02 | Phase 2 | Pending |
| AGENT-03 | Phase 2 | Pending |
| AGENT-04 | Phase 2 | Complete |
| AGENT-05 | Phase 2 | Complete |
| AGENT-06 | Phase 2 | Pending |
| AGENT-07 | Phase 2 | Complete |
| AGENT-08 | Phase 2 | Complete |
| QUERY-01 | Phase 3 | Pending |
| QUERY-02 | Phase 3 | Pending |
| QUERY-03 | Phase 3 | Pending |
| QUERY-04 | Phase 3 | Pending |
| WEB-01 | Phase 4 | Pending |
| WEB-02 | Phase 4 | Pending |
| WEB-03 | Phase 4 | Pending |
| WEB-04 | Phase 4 | Pending |
| WEB-05 | Phase 4 | Pending |
| OUTPUT-01 | Phase 5 | Pending |
| OUTPUT-02 | Phase 5 | Pending |
| OUTPUT-03 | Phase 5 | Pending |
| OUTPUT-04 | Phase 5 | Pending |
| OUTPUT-05 | Phase 5 | Pending |
| DEPLOY-01 | Phase 5 | Pending |
| DEPLOY-02 | Phase 5 | Pending |
| DEPLOY-03 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 36 total
- Mapped to phases: 36
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-14*
*Last updated: 2026-03-14 after initial definition*
