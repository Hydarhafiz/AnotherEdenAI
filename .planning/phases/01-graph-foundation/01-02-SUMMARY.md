---
phase: 01-graph-foundation
plan: 02
subsystem: database
tags: [pydantic, httpx, beautifulsoup4, neo4j, etl, async, scraper]

# Dependency graph
requires:
  - phase: 01-graph-foundation
    plan: 01
    provides: constants.py (WIKI_URLS, GRASTA_CATEGORIES, STRICT, ETL_MODE, NEO4J_URI/AUTH), Docker Neo4j, SCHEMA.md, test scaffold stubs

provides:
  - src/etl/models.py — Pydantic v2 CharacterRow, GrastaRow, OreRow + parse_* functions with ETL_MODE toggle
  - src/etl/scraper.py — async httpx wiki scraper with Semaphore(5), parse_characters/parse_grastas/parse_vc_grastas/parse_ores
  - src/etl/loader.py — idempotent UNWIND+MERGE loader; ensure_constraints; no ENHANCES edges
  - src/etl/run_etl.py — async ETL entry point that prints SCHEMA_VERSION/ETL_MODE and runs full pipeline
  - 15 passing unit tests (no network calls, fixture HTML)

affects:
  - 01-03 (graph validation — runs assert_schema.py against loaded graph)
  - Phase 2 (Cypher generation — consumes CharacterRow/GrastaRow/OreRow model shape)
  - Phase 3 (PLAN agent — Ore standalone decision means agent must handle Ore application dynamically)

# Tech tracking
tech-stack:
  added:
    - pydantic>=2.8 (field_validator, model_validate)
    - httpx>=0.27 (AsyncClient, Semaphore-limited concurrency)
    - beautifulsoup4>=4.12 (HTML parsing with html.parser)
    - neo4j>=5.0 (AsyncGraphDatabase.driver, async session)
  patterns:
    - TDD RED-GREEN cycle — failing tests committed before implementation
    - UNWIND+MERGE idempotency pattern for all Neo4j node loads
    - ETL_MODE toggle: strict raises ValidationError, lenient returns None + WARN
    - VC grasta name from col[1] not data-name (verified against live wiki)
    - Stats always from col[3] not col[2] (anti-pattern from master_scraper.py fixed)
    - Single AsyncClient shared across all 7 fetch_page calls (not per-loop)

key-files:
  created:
    - src/etl/models.py
    - src/etl/scraper.py
    - src/etl/loader.py
    - src/etl/run_etl.py
    - tests/unit/test_models.py (stubs replaced with working tests)
    - tests/unit/test_scraper.py (stubs replaced with fixture-HTML tests)
  modified: []

key-decisions:
  - "VC grastas: parse_grasta() forces personality_req=None regardless of raw input — model and parser both enforce this"
  - "Stats column is col[3] not col[2] — col[2] is personality_req; anti-pattern from master_scraper.py avoided"
  - "Ore nodes are standalone (no ENHANCES edges) — Ore application is dynamic player/AI decision in Phase 2/3"
  - "Tier read from data-tier attribute at parse time — never hard-coded (VC wiki shows tier=3, not 4)"
  - "Single httpx.AsyncClient shared for all 7 page fetches via asyncio.gather"

patterns-established:
  - "Pydantic v2 parse_* wrappers: try model_validate, raise if STRICT else log.warning + return None"
  - "UNWIND+MERGE for all Neo4j loads — never CREATE without constraint backing"
  - "IF NOT EXISTS on all constraint creation — safe for repeated ETL runs"
  - "REQUIRES_TRAIT gated in Cypher WHERE clause: category <> 'VC' AND personality_req IS NOT NULL"
  - "Fixture HTML in test file as module-level strings — no file I/O, no network calls"

requirements-completed: [DATA-01, DATA-02, DATA-03, DATA-04, GRAPH-01, GRAPH-02, GRAPH-03, GRAPH-04, GRAPH-05, GRAPH-06]

# Metrics
duration: 21min
completed: 2026-03-14
---

# Phase 1 Plan 02: ETL Pipeline Summary

**Pydantic v2 models + async httpx scraper + idempotent Neo4j MERGE loader delivering the complete wiki-to-graph ETL pipeline for Character, Grasta, and Ore data**

## Performance

- **Duration:** 21 min
- **Started:** 2026-03-14T15:17:53Z
- **Completed:** 2026-03-14T15:21:14Z
- **Tasks:** 2 (each TDD: RED commit + GREEN commit)
- **Files modified:** 6

## Accomplishments

- Pydantic v2 ETL models with strict/lenient mode toggle and VC personality_req enforcement
- Async httpx scraper using Semaphore(5) and single AsyncClient; all 3 correct column mappings verified
- Idempotent Neo4j UNWIND+MERGE loader; REQUIRES_TRAIT gated correctly; no ENHANCES edges per GRAPH-06
- ETL orchestrator run_etl.py as executable entry point printing SCHEMA_VERSION/ETL_MODE on start
- 15 unit tests pass (fixture HTML, no network calls); all 4 modules importable without error

## Task Commits

Each task was committed atomically (TDD pattern):

1. **Task 1 RED (models tests):** `d4b3629` (test: failing ETL model tests)
2. **Task 1 RED (scraper tests):** `35d7732` (test: failing scraper parse tests with fixture HTML)
3. **Task 1+2 GREEN (models + scraper):** `2ac7606` (feat: Pydantic ETL models and async wiki scraper)
4. **Task 2 GREEN (loader + run_etl):** `b6783f3` (feat: idempotent Neo4j loader and ETL orchestrator)

_Note: TDD tasks have multiple commits (RED test → GREEN implementation)_

## Files Created/Modified

- `/home/shogunix/AnotherEdenAI/src/etl/models.py` — CharacterRow, GrastaRow, OreRow + parse_* with ETL_MODE toggle
- `/home/shogunix/AnotherEdenAI/src/etl/scraper.py` — Async scraper: fetch_page, parse_characters, parse_grastas, parse_vc_grastas, parse_ores, scrape_all
- `/home/shogunix/AnotherEdenAI/src/etl/loader.py` — ensure_constraints, load_characters, load_grastas, load_ores, load_relationships
- `/home/shogunix/AnotherEdenAI/src/etl/run_etl.py` — async main() ETL entry point
- `/home/shogunix/AnotherEdenAI/tests/unit/test_models.py` — 10 passing model validation tests
- `/home/shogunix/AnotherEdenAI/tests/unit/test_scraper.py` — 5 passing scraper parse tests

## Decisions Made

- VC grasta name comes from `cols[1].get_text(strip=True)` not `data-name` (which includes character name suffix like "Proof of Courage Aldo")
- Stats always from `cols[3]` not `cols[2]` — `cols[2]` is personality_req; this was a confirmed bug in the pre-existing master_scraper.py
- Ore nodes are standalone (no ENHANCES relationship) per GRAPH-06 user decision — Ore application is a dynamic Phase 2/3 agent decision
- Tier read from `data-tier` attribute — never hard-coded; wiki shows VC tier=3, not 4 as previously assumed

## Deviations from Plan

None - plan executed exactly as written. All column mappings, VC rules, and Ore standalone requirement were clearly specified in the plan's `<interfaces>` block from 01-RESEARCH.md.

## Issues Encountered

- `pydantic` and `httpx` were not pre-installed; installed via pip with `--break-system-packages` (WSL2 environment, no venv active). Project dependencies now available for test runs.

## User Setup Required

None - no external service configuration required for unit tests. Running `run_etl.py` against live Neo4j requires the Docker compose stack from Plan 01-01 to be running.

## Next Phase Readiness

- All ETL modules importable; unit tests pass
- Plan 01-03 (graph validation) can now run `assert_schema.py` against the fully loaded graph
- To populate the graph: start Docker Neo4j (`docker compose up -d`) then `python src/etl/run_etl.py`
- Blocker: requires live wiki access and Docker Neo4j for integration run; unit tests are self-contained

---
*Phase: 01-graph-foundation*
*Completed: 2026-03-14*
