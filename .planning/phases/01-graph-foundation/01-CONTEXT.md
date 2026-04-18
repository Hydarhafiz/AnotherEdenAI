# Phase 1: Graph Foundation - Context

**Gathered:** 2026-03-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the finalized, stable Neo4j graph schema and an idempotent ETL pipeline that scrapes anothereden.wiki and loads all Character, Grasta, and Ore data. No LLM prompts are written in this phase — SCHEMA.md must be a stable, versioned contract before Phase 2 begins.

</domain>

<decisions>
## Implementation Decisions

### Ore graph placement
- Ore nodes are **standalone entities** — no ENHANCES relationship in the graph
- The decision of which Ore to apply to which Grasta is a **dynamic player/AI decision**, handled by PLAN and ANALYZE agents at query time (Phase 2/3), not a static graph edge
- GRAPH-06 delivers Ore nodes with stats and source properties only
- **This supersedes the earlier schema direction** (REQUIREMENTS.md GRAPH-06 updated accordingly)

### Scraper architecture
- Reuse verified wiki selectors from `master_scraper.py` (CSS classes `character-row-entry`, `grasta-row-entry`, `equip-row-entry`, data attributes already confirmed working)
- Port to async architecture: `httpx` + `asyncio` replacing synchronous `requests`
- Async batch job preferred over sync — designed for future serverless AWS Lambda target
- Pydantic v2 models at ETL boundary for validation (per REQUIREMENTS DATA-02)

### Neo4j target environment
- Local Docker Neo4j (5.x Community) for all dev and test in Phase 1–4
- `docker-compose.yml` is a Phase 1 deliverable — any dev can spin up graph without manual setup
- AuraDB Free introduced only in Phase 5 (Integration and Portfolio Hardening) to prove cloud readiness

### ETL failure handling
- **Phase 1 development**: fail-fast (`ETL_MODE=strict`, default) — aggressively surfaces schema anomalies and unhandled wiki edge cases
- **Production runs**: skip-with-warnings (`ETL_MODE=lenient`) — single bad wiki row doesn't abort the batch
- Mode controlled via environment variable `ETL_MODE` (easy to override in Docker or Lambda)

### Claude's Discretion
- Rate limiting strategy for async httpx requests (concurrent connection pool size)
- Grasta `activating_trait` vs `personality_req` distinction — researcher to verify against wiki during Plan 01-01; schema can be extended if the game distinguishes equip vs activation trait

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `master_scraper.py`: verified wiki URL targets and CSS selectors for all entity types — port logic directly, replacing `requests` with `httpx`, adding async/await
- `separate_trait_grasta.py`: trait union logic (char personalities ∪ grasta requirements) — useful reference for Trait node construction during ETL load

### Established Patterns
- Wiki uses data attributes (`data-name`, `data-element`, `data-personality`, `data-share`, `data-tier`) for structured data on row elements — reliable for scraping, not dependent on text parsing
- Existing scraper silently swallows all exceptions (`except: continue`) — must be replaced with explicit Pydantic validation + fail-fast in strict mode

### Integration Points
- ETL outputs load directly into Neo4j via MERGE statements (idempotency requirement)
- `docker-compose.yml` Neo4j instance is the shared target for ETL and all Phase 2–4 dev/test
- `get_schema()` from Neo4jGraph (LangChain) must return stable output after ETL — Phase 2 GENERATE_CYPHER agent injects this into prompts

</code_context>

<specifics>
## Specific Ideas

- "Port master_scraper.py logic to async httpx + asyncio — the CSS selectors are already verified, don't throw that away"
- ETL_MODE=strict as development default: "aggressively trap schema anomalies during Phase 1, then go lenient for production"
- docker-compose.yml included as Phase 1 deliverable: "any dev can spin up the graph without manual setup"
- Future target: async batch job designed for AWS Lambda serverless deployment

</specifics>

<deferred>
## Deferred Ideas

- AWS Lambda deployment packaging — mentioned as future target but not part of Phase 1–4 scope
- Grasta activating_trait schema extension — researcher to verify during Plan 01-01 wiki audit; implement if wiki distinguishes equip vs activation trait

</deferred>

---

*Phase: 01-graph-foundation*
*Context gathered: 2026-03-14*
