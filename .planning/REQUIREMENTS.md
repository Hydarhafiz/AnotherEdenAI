# Requirements: Another Eden AI — GraphRAG Team Builder

**Defined:** 2026-03-14
**Core Value:** Mathematically optimal team recommendations constrained to the player's actual roster, zero hallucinated mechanics

## v1 Requirements

### Data Pipeline

- [ ] **DATA-01**: System scrapes character data (name, element, weapon, light_shadow, personalities) from anothereden.wiki
- [ ] **DATA-02**: System scrapes Grasta data for all categories (Attack, Life, Support, Special, VC) including tier, stats, personality_req, is_shareable
- [ ] **DATA-03**: System scrapes Ore data (name, category, stats, source)
- [ ] **DATA-04**: ETL pipeline is idempotent — re-running safely overwrites stale data without creating duplicates
- [ ] **DATA-05**: Schema version is tracked as a constant in ETL; post-load assertion confirms expected node types exist after each run

### Graph Schema

- [ ] **GRAPH-01**: Neo4j graph contains Character nodes with element, weapon, light_shadow, and name properties
- [ ] **GRAPH-02**: Character nodes are linked to Trait nodes via HAS_TRAIT relationships
- [ ] **GRAPH-03**: Neo4j graph contains Grasta nodes with is_shareable, personality_req, category, tier, and stats properties
- [ ] **GRAPH-04**: Grasta shareability is modeled with explicit is_shareable property; activating_trait distinguishes equip from activation
- [ ] **GRAPH-05**: Grasta nodes are linked to Trait nodes via REQUIRES_TRAIT relationships
- [ ] **GRAPH-06**: Neo4j graph contains Ore nodes with stats and source properties; Ore linked to Character via ENHANCES
- [ ] **GRAPH-07**: Graph schema is documented in SCHEMA.md as a versioned contract before any LLM prompts are written

### Agent Workflow

- [ ] **AGENT-01**: PLAN agent (Sonnet 4.6) receives user query + roster and decomposes into graph traversal sub-goals
- [ ] **AGENT-02**: GENERATE_CYPHER agent (Sonnet 4.6) produces Cypher with full schema injected via Neo4jGraph.get_schema() and few-shot examples
- [ ] **AGENT-03**: VALIDATE agent (Haiku 4.6) verifies Cypher syntax and confirms query returns non-empty results against game rules
- [ ] **AGENT-04**: VALIDATE agent routes failed queries back to GENERATE_CYPHER with full error context for correction
- [ ] **AGENT-05**: Retry loop is hard-capped at 3 attempts via conditional edge in WorkflowState; exceeding cap routes to graceful error
- [ ] **AGENT-06**: ANALYZE agent (Sonnet 4.6) synthesizes validated query results into final team recommendation
- [ ] **AGENT-07**: WorkflowState is a TypedDict validated by Pydantic v2; each node returns only the keys it modifies (no shared mutation)

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
| DATA-01 | Phase 1 | Pending |
| DATA-02 | Phase 1 | Pending |
| DATA-03 | Phase 1 | Pending |
| DATA-04 | Phase 1 | Pending |
| DATA-05 | Phase 1 | Pending |
| GRAPH-01 | Phase 1 | Pending |
| GRAPH-02 | Phase 1 | Pending |
| GRAPH-03 | Phase 1 | Pending |
| GRAPH-04 | Phase 1 | Pending |
| GRAPH-05 | Phase 1 | Pending |
| GRAPH-06 | Phase 1 | Pending |
| GRAPH-07 | Phase 1 | Pending |
| AGENT-01 | Phase 2 | Pending |
| AGENT-02 | Phase 2 | Pending |
| AGENT-03 | Phase 2 | Pending |
| AGENT-04 | Phase 2 | Pending |
| AGENT-05 | Phase 2 | Pending |
| AGENT-06 | Phase 2 | Pending |
| AGENT-07 | Phase 2 | Pending |
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

**Coverage:**
- v1 requirements: 32 total
- Mapped to phases: 32
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-14*
*Last updated: 2026-03-14 after initial definition*
