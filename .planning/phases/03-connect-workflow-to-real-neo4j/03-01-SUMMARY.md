---
phase: 03-connect-workflow-to-real-neo4j
plan: 01
subsystem: workflow
tags: [neo4j, async, langgraph, pytest, asyncmock, normalize, f2p]

# Dependency graph
requires:
  - phase: 02-langgraph-workflow-stub-data
    provides: validate_node (sync), graph.py with stub driver, test_validate.py
provides:
  - normalize_character_name() and normalize_roster() async helpers in src/workflow/normalize.py
  - F2P_CHARACTERS constant and augment_with_f2p() in src/workflow/f2p.py
  - async def validate_node that awaits driver.execute_query() with roster kwarg
  - async wrapper _validate() in graph.py for correct LangGraph ainvoke() behavior
  - Updated test infrastructure for async workflow (AsyncMock, ainvoke)
affects:
  - 03-02 (uses normalize.py and f2p.py for roster preprocessing)
  - 03-03 (end-to-end integration relies on async validate_node)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "AsyncMock for driver execute_query in all workflow unit tests"
    - "async def wrapper for LangGraph node when node is async coroutine"
    - "graph.ainvoke() required when any graph node is async"

key-files:
  created:
    - src/workflow/normalize.py
    - src/workflow/f2p.py
    - tests/workflow/test_normalize.py
    - tests/workflow/test_f2p.py
  modified:
    - src/workflow/nodes/validate.py
    - src/workflow/graph.py
    - tests/workflow/conftest.py
    - tests/workflow/test_graph.py
    - tests/workflow/test_state.py
    - tests/workflow/test_validate.py

key-decisions:
  - "async wrapper _validate() in graph.py — LangGraph lambda does NOT auto-resolve async coroutines; explicit async def is required"
  - "graph.ainvoke() replaces graph.invoke() in all graph tests — required once any node is async"
  - "stub_driver.execute_query is AsyncMock in conftest.py — Phase 2 sync mock insufficient for async validate_node"
  - "normalize_character_name returns shortest match (ORDER BY size ASC) — avoids returning alternate-style names when base name matches"
  - "augment_with_f2p deduplicates by checking membership before append — preserves roster order, no sorting"

patterns-established:
  - "TDD RED-GREEN: test files committed before implementation to mark async boundary clearly"
  - "Rule 1 - Bug: lambda s: validate_node(s, driver) returns unawaited coroutine — fixed with async def _validate(s)"
  - "Rule 1 - Bug: test_graph.py and test_state.py updated from sync invoke to async ainvoke"

requirements-completed: [QUERY-01, QUERY-02, QUERY-04]

# Metrics
duration: 7min
completed: 2026-03-16
---

# Phase 3 Plan 01: Normalize, F2P Helpers, and Async Validate Node Summary

**Async validate_node with AsyncDriver.execute_query(), normalize/f2p helper modules, and async test infrastructure for LangGraph ainvoke()**

## Performance

- **Duration:** ~7 min
- **Started:** 2026-03-16T06:54:56Z
- **Completed:** 2026-03-16T07:01:16Z
- **Tasks:** 2
- **Files modified:** 10

## Accomplishments
- Created `src/workflow/normalize.py` with async `normalize_character_name()` (case-insensitive contains match) and `normalize_roster()` (drops unresolved names)
- Created `src/workflow/f2p.py` with `F2P_CHARACTERS` (8 story-permanent characters) and `augment_with_f2p()` (deduplicating roster augmentation)
- Converted `validate_node` to `async def` that awaits `driver.execute_query()` with `roster=state.get("roster", [])` kwarg
- Fixed async wiring in `graph.py` — replaced sync lambda with `async def _validate()` so LangGraph ainvoke() awaits correctly
- Updated `test_validate.py` (22 async tests), `test_graph.py` (5 ainvoke tests), `test_state.py` (1 async test), `conftest.py` (AsyncMock stub_driver)

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: test_normalize.py + test_f2p.py (failing)** - `5d405e9` (test)
2. **Task 1 GREEN: normalize.py + f2p.py (implementation)** - `a1df86e` (feat)
3. **Task 2 RED: test_validate.py AsyncMock conversion (failing)** - `069a2a9` (test)
4. **Task 2 GREEN: async validate_node + graph.py + affected tests** - `1b1b5d2` (feat)

_Note: TDD tasks have multiple commits (test RED → feat GREEN)_

## Files Created/Modified
- `src/workflow/normalize.py` — async normalize_character_name and normalize_roster helpers
- `src/workflow/f2p.py` — F2P_CHARACTERS constant (8 chars) and augment_with_f2p()
- `src/workflow/nodes/validate.py` — converted to async def, awaits execute_query with roster kwarg
- `src/workflow/graph.py` — async def _validate() wrapper replaces sync lambda
- `tests/workflow/test_normalize.py` — 14 async unit tests with AsyncMock driver
- `tests/workflow/test_f2p.py` — 8 sync unit tests for F2P constant and augment helper
- `tests/workflow/test_validate.py` — all 22 tests converted to async def + AsyncMock driver
- `tests/workflow/conftest.py` — stub_driver.execute_query changed to AsyncMock
- `tests/workflow/test_graph.py` — all 5 graph invocation tests use ainvoke()
- `tests/workflow/test_state.py` — test_stub_nodes_return_only_owned_keys made async

## Decisions Made
- **async def _validate() in graph.py**: LangGraph does NOT auto-resolve a sync lambda returning a coroutine — even with ainvoke(). An explicit async wrapper is required for the graph to await validate_node correctly.
- **graph.ainvoke() across all graph tests**: Once any node in the graph is async, the whole graph must be invoked with ainvoke(). All 5 graph integration tests updated.
- **stub_driver.execute_query = AsyncMock**: The Phase 2 sync MagicMock for execute_query is incompatible with the async boundary — RuntimeWarning "coroutine never awaited" would appear if sync mock is used.
- **normalize returns shortest match**: ORDER BY size(c.name) ASC in the Cypher query ensures base names ("Aldo") are returned before alternate styles ("Aldo (Another Style)") when both match a partial input.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] sync lambda in graph.py returns unawaited coroutine**
- **Found during:** Task 2 (validate_node async conversion, full suite run)
- **Issue:** `lambda s: validate_node(s, driver)` returns a coroutine object; LangGraph's ainvoke() doesn't auto-await a sync lambda's return value — raises InvalidUpdateError
- **Fix:** Replaced lambda with `async def _validate(s): return await validate_node(s, driver)`
- **Files modified:** `src/workflow/graph.py`
- **Verification:** `pytest tests/ -m "not integration"` passes 121 tests
- **Committed in:** `1b1b5d2` (Task 2 feat commit)

**2. [Rule 1 - Bug] test_graph.py uses graph.invoke() — incompatible with async node**
- **Found during:** Task 2 (full suite run after validate_node async conversion)
- **Issue:** All 5 graph tests called `graph.invoke()` which doesn't run async nodes; stub_driver also had sync execute_query
- **Fix:** Converted all TestGraphHappyPath tests to `async def` + `await graph.ainvoke()`; updated conftest.py stub_driver to use AsyncMock
- **Files modified:** `tests/workflow/test_graph.py`, `tests/workflow/conftest.py`
- **Verification:** All 5 graph tests pass
- **Committed in:** `1b1b5d2` (Task 2 feat commit)

**3. [Rule 1 - Bug] test_state.py calls validate_node() without await**
- **Found during:** Task 2 (full suite run after graph test fix)
- **Issue:** `test_stub_nodes_return_only_owned_keys` called `validate_node()` in a sync context; returned coroutine instead of dict
- **Fix:** Made test async with `@pytest.mark.asyncio`, changed driver to AsyncMock, awaited validate_node call
- **Files modified:** `tests/workflow/test_state.py`
- **Verification:** Test passes with correct dict return value
- **Committed in:** `1b1b5d2` (Task 2 feat commit)

---

**Total deviations:** 3 auto-fixed (all Rule 1 - Bug: async boundary cascade from validate_node conversion)
**Impact on plan:** All fixes necessary for correctness — the async conversion of validate_node required propagating the async boundary through graph.py and all tests that invoke the graph or validate_node directly. No scope creep.

## Issues Encountered
- The plan comment "LangGraph resolves async coroutines natively in ainvoke — lambda unchanged" was incorrect. A sync lambda returning a coroutine is not the same as registering an async node. LangGraph requires the node callable itself to be async (or the coroutine to be awaited by the lambda).

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `normalize.py` and `f2p.py` are ready for use in Plan 02 (roster preprocessing before graph query)
- `validate_node` is async and wired correctly for real AsyncGraphDatabase driver
- All 121 unit tests (excluding integration) pass
- Plans 03-02 and 03-03 can depend on `normalize_character_name`, `normalize_roster`, `F2P_CHARACTERS`, `augment_with_f2p`

---
*Phase: 03-connect-workflow-to-real-neo4j*
*Completed: 2026-03-16*
