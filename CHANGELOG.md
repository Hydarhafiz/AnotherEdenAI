# Changelog

All notable changes to this project are documented here, grouped by development phase. Dates reflect actual commit dates.

---

## [Unreleased] Root Pillar Docs

### Added
- Root `architecture.md` documenting the current ETL, workflow, web, and schema boundaries for future milestone planning
- Root `milestone.md` establishing a living baseline for post-v1 roadmap planning

### Changed
- `README.md` now documents the five root project pillars used for planning and release synchronization

---

## [Phase 5] Integration, Polish, and Portfolio Hardening — 2026-04-25 to 2026-04-26

**Goal:** End-to-end system verified, all error paths hardened, suite passes on a cold clone.

### Added
- **Alternatives pipeline** — when no perfect 4-frontline/2-reserve team exists, the system now returns the top 3 closest alternatives with tradeoff explanations (`AlternativesOutput` Pydantic model, new `alternatives.html` template)
- **SSE latency logging** — every query response now records and logs `latency_ms` so the 15-second SLO can be monitored
- **Full integration test suite** — 5 scenario-driven tests covering happy path, name normalisation, alternatives fallback, retry cap exhaustion, and admin auth (`tests/integration/test_query_pipeline.py`)
- **`AlternativesOutput` Pydantic model** — structured output type for the alternatives branch; validated in FORMAT node
- **Alternatives template selection** — FORMAT node automatically selects `alternatives.html` when the alternatives path is taken

### Changed
- `WorkflowState` extended with `alternatives` field to carry alternatives output through the graph
- `analyze_node` prompt sharpened to explicitly produce alternatives when no exact match is found
- `route_after_validate` routing fixed to correctly branch into the alternatives path

### Fixed
- Retry counter display in alternatives path was not incrementing correctly — resolved by fixing `route_after_validate` conditional logic

---

## [Phase 4.1] UAT Gap Closure — 2026-04-22

**Goal:** Close 3 UAT gaps identified after Phase 4 user acceptance testing.

### Fixed
- **Gap 1 — SSE listener event name:** Changed HTMX SSE listener from `htmx:sseMessage` to `htmx:sseBeforeMessage`; results were rendering but not swapping into the result div
- **Gap 2a — TeamOutput length validators:** Added Pydantic `min_length=4` / `min_length=2` validators to `frontline` and `reserve` fields; malformed or non-JSON LLM team output now raises a typed error instead of passing silently
- **Gap 2b — ANALYZE prompt precision:** Sharpened the ANALYZE system prompt to explicitly enforce "exactly 4 frontline, exactly 2 reserve" counts, reducing malformed outputs from the LLM
- **Gap 3 — ADMIN_KEY documentation:** `ADMIN_KEY` env var added to `.env.example` and documented in README

### Tests
- Added failing tests for `TeamOutput` length validators and malformed-team / non-JSON error paths (RED → GREEN)
- Updated `_ANALYZE_RESPONSE` fixture to satisfy upcoming `min_length=3` validator

---

## [Phase 4] FastAPI + HTMX Web Layer — 2026-04-19 to 2026-04-21

**Goal:** Expose the working pipeline via HTTP with a real-time streaming progress UI.

### Added
- **FastAPI application** (`src/web/app.py`) with lifespan handler initialising the Neo4j async driver as an app-level singleton
- **`POST /api/query`** — accepts roster + natural language query, launches LangGraph pipeline as a background job, returns `job_id`
- **`GET /api/stream/{job_id}`** — SSE endpoint streaming pipeline node status events (`PLAN_DONE`, `CYPHER_DONE`, `VALIDATE_DONE`, `ANALYZE_DONE`, `RESULT`)
- **`POST /admin/refresh-data`** — triggers full ETL pipeline re-run; protected by `X-Admin-Key` header
- **`GET /`** — serves the main Jinja2 template with HTMX roster input form and query submission
- **`pipeline_sse_generator`** (`src/web/streaming.py`) — async generator bridging LangGraph `stream_mode="updates"` chunks to SSE events
- **Progress partial** (`templates/partials/progress.html`) — renders current node status with retry counter ("Validating... attempt 2/3")
- **Error and empty-result partials** — graceful degradation when retry cap is exhausted or no teams are found
- **Neo4j driver singleton** (`src/web/dependencies.py`) — shared across request lifespan via FastAPI dependency injection
- **Unit tests** for all routes, streaming bridge, app lifespan, and dependencies (26 tests passing)

### Fixed
- `stream_mode="updates"` chunk parsing in `streaming.py` — LangGraph update format was not being unwrapped correctly
- `POST /api/query` returning 422 — replaced `json-enc` HTMX extension with native `fetch()` for roster array serialisation
- HTMX roster array not serialising before POST — switched hook from `htmx:beforeRequest` to `htmx:configRequest`
- SSE events yielded through an extra generator wrapper — flattened to yield directly from the route, fixing streaming stall

---

## [Phase 3.1] Cloudflare Bypass — nodriver Scraper — 2026-04-19

**Goal:** Replace the `httpx`-based scraper with a headless browser that passes Cloudflare Turnstile.

### Added
- **nodriver async scraper** — `fetch_page()` in `src/etl/scraper.py` replaced with a nodriver (undetected headless Chrome) implementation; successfully retrieves HTML from all 7 wiki pages without 403/429 errors
- **`WEAPON_OVERRIDES` dict** in `parse_character()` — manual overrides for Anabel ES (`WeaponType=Spear`) and Mazrika (`WeaponType=Axe`) applied before any node is written to Neo4j
- **Smart polling** in `fetch_page` — waits for the target CSS selector before returning HTML, preventing partial-page race conditions
- **`nodriver>=0.48.1`** added to `pyproject.toml` dependencies
- **`scraper` pytest marker** added for integration tests that require a live browser

### Fixed
- Headless mode detection by Cloudflare — reverted to `headless=False` with `DISPLAY=:0` (WSL2 X server); headless fingerprint was immediately blocked
- `--no-sandbox` Chrome flags added for WSL2 startup compatibility
- `fetch_page` signature mismatch in integration test — `expected_selector` parameter now passed correctly
- Grasta page row threshold lowered from 100 to 50 — Characters page returns ~95 rows, not 100+

---

## [Phase 3] Connect Workflow to Real Neo4j — 2026-03-16 to 2026-04-19

**Goal:** Swap mocked Neo4j responses for real Cypher; validate roster filtering and Grasta traversal against live data.

### Added
- **`normalize_character_name()`** (`src/workflow/normalize.py`) — fuzzy-matches user-supplied names to canonical graph node names; prevents "character not found" errors from minor spelling variations
- **`augment_with_f2p()`** (`src/workflow/f2p.py`) — appends explicitly free-to-play units to any roster before query execution; all recommendations are constrained to owned + F2P characters
- **`run.py`** CLI entry point (`src/workflow/run.py`) — drives the full pipeline from the command line without the web layer
- **Integration tests** (`tests/integration/test_query_pipeline.py`) — 4 scenarios covering QUERY-01 through QUERY-04: roster-constrained results, name normalisation, known-good synergy pairs, and empty-roster edge case
- **`validate_node` converted to `async def`** — consistent with the async Neo4j driver; `test_validate.py` updated to use `AsyncMock`

### Fixed
- `loaded_db` fixture crashing when Neo4j is unpopulated — `db_has_characters()` helper added; fixture now skips gracefully with `pytest.skip` instead of raising
- ETL exception handling expanded to cover `db_has_characters` call within `loaded_db` (WR-01)
- `test_known_nodes.py` skips when database is empty rather than failing (gap closure 03-04)
- Known-character node assertions corrected — Aldo's element was mis-asserted in earlier fixture

---

## [Phase 2] LangGraph Workflow (Stub Data) — 2026-03-15

**Goal:** Complete PLAN → GENERATE_CYPHER → VALIDATE → ANALYZE → FORMAT pipeline built and tested against mocked Neo4j.

### Added
- **`WorkflowState` TypedDict** (`src/workflow/state.py`) — Pydantic v2 validated; each node returns only the keys it owns; attempting to write a foreign key raises a validation error in tests
- **LangGraph `StateGraph`** (`src/workflow/graph.py`) — wires all five nodes with explicit conditional edges including the VALIDATE retry loop; retry counter is hard-capped at 3
- **`get_llm(role)` factory** (`src/workflow/llm.py`) — `LLM_PROVIDER=anthropic` returns `ChatAnthropic` with the role-appropriate model (Sonnet 4.6 for PLAN/CYPHER/ANALYZE, Haiku 4.5 for VALIDATE); `LLM_PROVIDER=ollama` returns `ChatOllama` for local dev; `LLM_PROVIDER=openrouter` and `LLM_PROVIDER=bedrock` also supported
- **PLAN node** (`src/workflow/nodes/plan.py`) — Sonnet 4.6; decomposes the user query into graph traversal sub-goals with roster context
- **GENERATE_CYPHER node** (`src/workflow/nodes/cypher.py`) — Sonnet 4.6; produces Cypher with full schema injected via `Neo4jGraph.get_schema()` and few-shot examples
- **VALIDATE node** (`src/workflow/nodes/validate.py`) — Haiku 4.5; two-step hybrid gate: LLM syntax check then live query execution; routes `pass → ANALYZE`, `fail-with-retries → GENERATE_CYPHER` (with full error context), `fail-at-cap → graceful error`
- **ANALYZE node** (`src/workflow/nodes/analyze.py`) — Sonnet 4.6; synthesises validated query results into a team recommendation with Grasta + personality source attribution and per-character role annotations
- **FORMAT node** (`src/workflow/nodes/format.py`) — structures ANALYZE output into a `TeamOutput` Pydantic model (4 frontline, 2 reserve)
- **`TeamOutput` Pydantic model** — validated structured output; `frontline` requires exactly 4 members, `reserve` requires exactly 2
- **Full unit test suite** — mocked LLM and Neo4j; covers happy path, single VALIDATE retry, retry cap exhaustion, and graceful error routing (no live LLM calls or Neo4j connections required)
- **OpenRouter and AWS Bedrock providers** added to `get_llm()` factory alongside Anthropic and Ollama

---

## [Phase 1] Graph Foundation — 2026-03-14 to 2026-03-15

**Goal:** Stable Neo4j schema and idempotent ETL pipeline complete before any LLM prompt is written.

### Added
- **`SCHEMA.md`** — versioned graph schema contract (`SCHEMA_VERSION: 1.0.0`); documents all node labels, properties, and relationship types; must be stable before GENERATE_CYPHER prompt is written
- **`assert_schema.py`** — post-ETL assertion script; exits 0 when expected node types (Character, Trait, Grasta, Ore) exist in the graph with correct counts
- **Pydantic v2 ETL models** (`src/etl/models.py`) — `CharacterRecord`, `GrastaRecord`, `OreRecord`; enforce schema contract at the ETL boundary
- **Async wiki scraper** (`src/etl/scraper.py`) — httpx-based (later replaced by nodriver in Phase 3.1); category-specific parsers for Characters, Grasta (Attack/Life/Support/Special/VC), and Ores
- **Idempotent Neo4j loader** (`src/etl/loader.py`) — MERGE-based; re-running against a populated database is safe and produces identical counts
- **ETL orchestrator** (`src/etl/run_etl.py`) — coordinates scrape → validate → load → assert pipeline
- **`docker-compose.yml`** — Neo4j 5 Community with APOC plugin; health check waits for Bolt to be ready
- **`pyproject.toml`** — project metadata, pinned dependencies, pytest config (`asyncio_mode = "auto"`)
- **`constants.py`** (`src/etl/constants.py`) — `EXPECTED_NODE_COUNTS` thresholds, wiki page URLs
- **Unit tests** — scraper parse tests with fixture HTML (RED → GREEN), ETL model validation tests, schema assertion tests
- **Integration tests** — idempotency test (two ETL runs produce identical counts), known-node property tests (Aldo's element, Grasta shareability)
- **APOC plugin** enabled in Docker Neo4j — required by `langchain_neo4j.Neo4jGraph.get_schema()`

### Fixed
- Grasta count assertion threshold calibrated — actual wiki count (~489) is below the initial 500 minimum; `constants.py` threshold corrected
- 7 failing integration tests after initial ETL wiring — `loaded_db` fixture rewritten with static loaders, `test_etl_idempotent` made scraper-free, `test_known_nodes` Aldo element assertion corrected

---

## [v0] Prototype — 2026-01-15 to 2026-01-19

**Initial proof-of-concept before the structured rebuild.**

### Added
- `master_scraper.py` — BeautifulSoup scraper producing `ae_characters.csv`, `ae_grasta_master.csv`, `ae_ores.csv`, and a Mermaid.js schema diagram
- `separate_trait_grasta.py` — trait deduplication; extracts unique traits from characters and Grastas into `ae_traits.csv`
- `optimize_character.py` — deterministic build optimizer; shareable Grasta matching by personality, weapon-based self-buff selection, meta Ore rotation

---

*Phase completion dates are derived from git history. Each phase was developed and committed atomically.*
