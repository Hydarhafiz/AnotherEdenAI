---
phase: 03-connect-workflow-to-real-neo4j
plan: 02
subsystem: workflow
tags: [neo4j, async, langgraph, pytest, normalize, f2p, integration-tests, cli]

# Dependency graph
requires:
  - phase: 03-connect-workflow-to-real-neo4j
    plan: 01
    provides: normalize_roster(), augment_with_f2p(), async validate_node
provides:
  - async plan_node(state, driver) with roster normalization + F2P augmentation before LLM call
  - run.py CLI entry point: --roster CSV + --query string -> graph.ainvoke() -> prints final_output
  - tests/integration/test_query_pipeline.py: 7 tests covering QUERY-01 through QUERY-04
affects:
  - 03-03 (end-to-end pipeline depends on async plan_node with normalized roster)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "async def _plan(s) wrapper in graph.py — same pattern as _validate for LangGraph async node wiring"
    - "normalize_roster + augment_with_f2p patched in all graph/state tests to isolate validate driver calls"
    - "record.keys() for Neo4j Record key membership checks — Record.__contains__ checks values, not keys"

key-files:
  created:
    - src/workflow/run.py
    - tests/integration/test_query_pipeline.py
  modified:
    - src/workflow/nodes/plan.py
    - src/workflow/graph.py
    - tests/workflow/test_plan.py
    - tests/workflow/test_graph.py
    - tests/workflow/test_state.py

key-decisions:
  - "plan_node returns both plan_strategy AND roster — downstream nodes receive the normalized+F2P roster without a separate normalization step"
  - "graph.py uses async def _plan(s) wrapper — same proven pattern as _validate; plan_node is async so LangGraph must await it via explicit async wrapper"
  - "graph/state tests patch normalize_roster + augment_with_f2p — without this, those functions call stub_driver.execute_query consuming calls meant for validate assertions"
  - "record.keys() used for Neo4j Record key membership — Record.__contains__ iterates values, making 'key in record' always False for string keys"

patterns-established:
  - "Rule 1 - Bug: test_plan.py converted to async + mocked normalize_roster/augment_with_f2p — plan_node signature changed to async (state, driver)"
  - "Rule 1 - Bug: test_graph.py + test_state.py patched normalize_roster/augment_with_f2p — prevents stub_driver call count contamination from normalization queries"
  - "Rule 1 - Bug: record.keys() for Neo4j Record membership — Record.__contains__ checks values not keys, breaking 'key in record' assertions"

requirements-completed: [QUERY-01, QUERY-02, QUERY-03, QUERY-04]

# Metrics
duration: 14min
completed: 2026-03-16
---

# Phase 3 Plan 02: Async plan_node with Roster Normalization + Integration Test Suite Summary

**Async plan_node wiring normalize_roster/augment_with_f2p before LLM, CLI run.py, and 7 integration tests proving QUERY-01–04 against live Neo4j**

## Performance

- **Duration:** ~14 min
- **Started:** 2026-03-16T07:03:43Z
- **Completed:** 2026-03-16T07:17:23Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Converted `plan_node` to `async def plan_node(state, driver)` — calls `normalize_roster(driver, ...)` then `augment_with_f2p(...)` before building LLM prompt; returns both `plan_strategy` and normalized+augmented `roster`
- Created `src/workflow/run.py` CLI entry point: `--roster CSV --query string` → `graph.ainvoke()` → prints JSON `final_output`
- Updated `graph.py` to wire plan via `async def _plan(s)` wrapper (same pattern as `_validate`); plan node now receives real driver in production
- Created `tests/integration/test_query_pipeline.py` with 7 tests covering QUERY-01 (CSV parsing), QUERY-02 (roster filtering + F2P), QUERY-03 (Grasta synergy path), QUERY-04 (name normalization)
- All 137 tests pass: 123 unit + 7 integration + 7 existing integration

## Task Commits

Each task was committed atomically:

1. **Task 1: async plan_node, run.py CLI, graph.py + test updates** - `63e05de` (feat)
2. **Task 2: integration test suite QUERY-01 to QUERY-04** - `fed9eb5` (feat)

## Files Created/Modified
- `src/workflow/nodes/plan.py` — async def plan_node(state, driver); normalize_roster + augment_with_f2p before LLM; returns plan_strategy + roster
- `src/workflow/run.py` — CLI entry point with argparse, asyncio.run(main()), graph.ainvoke()
- `src/workflow/graph.py` — async def _plan(s) wrapper; plan node wired via closure with driver
- `tests/workflow/test_plan.py` — 8 async tests; normalize_roster + augment_with_f2p patched; stub_driver_plan fixture added
- `tests/workflow/test_graph.py` — all 5 graph tests patch normalize_roster + augment_with_f2p to prevent driver call contamination
- `tests/workflow/test_state.py` — plan_node call made async + awaited; expected keys updated to {plan_strategy, roster}
- `tests/integration/test_query_pipeline.py` — 7 integration tests: CSV parse, roster filter, F2P augment, Grasta synergy, 3 normalization tests

## Decisions Made
- **plan_node returns roster alongside plan_strategy**: Downstream nodes (generate_cypher, analyze) benefit from having the normalized roster in state without re-normalizing. Single normalization at PLAN stage is cleaner than normalizing at each node.
- **async def _plan(s) wrapper in graph.py**: LangGraph does not auto-resolve async node callables from sync lambdas. The plan node must be wrapped exactly like validate_node was in Plan 01.
- **normalize_roster/augment_with_f2p patched in graph tests**: Without patching, the stub_driver.execute_query accumulates calls from normalize_roster (one per roster entry), breaking test assertions that count validate_node's exact call count.
- **record.keys() for Neo4j Record membership**: The `in` operator on a Neo4j Record object checks values (like a list), not keys. `"character" in record` returns False even when the key exists. Must use `"character" in record.keys()`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] test_plan.py: plan_node signature change broke all 6 existing tests**
- **Found during:** Task 1 (after converting plan_node to async def accepting driver)
- **Issue:** All 6 tests called `plan_node(sample_state)` synchronously without driver; expected only `["plan_strategy"]` but plan_node now returns `["plan_strategy", "roster"]`
- **Fix:** Rewrote test_plan.py with 8 async tests; added stub_driver_plan fixture; patched normalize_roster (AsyncMock) and augment_with_f2p; updated expected keys
- **Files modified:** `tests/workflow/test_plan.py`
- **Verification:** `pytest tests/ -m "not integration"` passes 123 tests
- **Committed in:** `63e05de` (Task 1 commit)

**2. [Rule 1 - Bug] test_graph.py: all 5 graph tests had uncontrolled stub_driver calls from normalize_roster**
- **Found during:** Task 1 (full unit suite run after plan_node conversion)
- **Issue:** normalize_roster calls driver.execute_query once per roster entry (["Aldo","Ciel"] = 2 calls); tests using `side_effect` lists had their validate calls consumed by normalize_roster
- **Fix:** Added `patch("src.workflow.nodes.plan.normalize_roster", new_callable=AsyncMock, ...)` and `patch("src.workflow.nodes.plan.augment_with_f2p", ...)` to all 5 TestGraphHappyPath tests
- **Files modified:** `tests/workflow/test_graph.py`
- **Verification:** All 5 graph tests pass; retry_count and call_count assertions correct
- **Committed in:** `63e05de` (Task 1 commit)

**3. [Rule 1 - Bug] test_state.py: plan_node called sync without await or driver**
- **Found during:** Task 1 (full unit suite run)
- **Issue:** test_stub_nodes_return_only_owned_keys called `plan_node(sample_state)` without await; also expected `{"plan_strategy"}` but plan_node now returns `{"plan_strategy", "roster"}`
- **Fix:** Made plan call async with `await plan_node(sample_state, mock_driver)`; added normalize_roster/augment_with_f2p patches; updated expected keys set
- **Files modified:** `tests/workflow/test_state.py`
- **Verification:** Test passes
- **Committed in:** `63e05de` (Task 1 commit)

**4. [Rule 1 - Bug] test_query_pipeline.py: `"character" in record` always False on Neo4j Record**
- **Found during:** Task 2 (integration test run)
- **Issue:** Neo4j Record.__contains__ checks values not keys — `"character" in record` returns False even when key exists; test failure showed data was present but assertion failed
- **Fix:** Changed to `"character" in record.keys()` for all three key membership assertions
- **Files modified:** `tests/integration/test_query_pipeline.py`
- **Verification:** `pytest tests/integration/test_query_pipeline.py -m integration` passes 6/6
- **Committed in:** `fed9eb5` (Task 2 commit)

---

**Total deviations:** 4 auto-fixed (all Rule 1 - Bug: signature change cascade + Neo4j Record API behavior)
**Impact on plan:** All fixes necessary for correctness. Tasks 1-3 were a direct cascade from converting plan_node to async(state, driver). Task 4 was a Neo4j API behavior discovery. No scope creep.

## Issues Encountered
- Docker Desktop WSL integration was not active when integration tests first ran (Neo4j unreachable). Resolved by restarting Docker Desktop via PowerShell — the docker-desktop WSL proxy initialized after restart. Neo4j container started successfully and tests passed.

## User Setup Required
None - no external service configuration required beyond Docker Desktop running.

## Next Phase Readiness
- `plan_node` is async and wired correctly with normalize_roster + augment_with_f2p
- `run.py` CLI provides a complete end-to-end invocation path
- All QUERY-01 through QUERY-04 requirements confirmed via live Neo4j integration tests
- Phase 3 Plan 03 can depend on the complete async pipeline (plan → generate_cypher → validate → analyze → format) being end-to-end tested

## Self-Check: PASSED

- src/workflow/nodes/plan.py: FOUND
- src/workflow/run.py: FOUND
- tests/integration/test_query_pipeline.py: FOUND
- .planning/phases/03-connect-workflow-to-real-neo4j/03-02-SUMMARY.md: FOUND
- Commit 63e05de: FOUND
- Commit fed9eb5: FOUND

---
*Phase: 03-connect-workflow-to-real-neo4j*
*Completed: 2026-03-16*
