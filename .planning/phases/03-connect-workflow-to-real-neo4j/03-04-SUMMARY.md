---
phase: 03-connect-workflow-to-real-neo4j
plan: 04
subsystem: testing
tags: [pytest, pytest-asyncio, neo4j, fixtures, conftest]

requires:
  - phase: 03-connect-workflow-to-real-neo4j
    provides: loaded_db fixture and integration test infrastructure

provides:
  - ETL-failure-resilient loaded_db fixture (yields on wiki 403/network errors)
  - db_has_characters() helper for programmatic DB population check
  - populated_db session fixture with pytest.skip for empty-DB scenarios

affects: [test_known_nodes, integration tests, conftest]

tech-stack:
  added: []
  patterns: [best-effort ETL fixture with per-test skip gates]

key-files:
  created: []
  modified:
    - tests/conftest.py
    - tests/integration/test_known_nodes.py

key-decisions:
  - "loaded_db catches all ETL exceptions and yields regardless — test_known_nodes skips individually rather than crashing the session"
  - "populated_db fixture added to test_known_nodes.py only — test_query_pipeline.py is unaffected"
  - "db_has_characters() uses same 100-character threshold as original loaded_db check"

requirements-completed:
  - QUERY-04

duration: 8min
completed: 2026-04-18
---

# Phase 3 Plan 04: loaded_db Fixture Resilience Summary

**ETL failure handling in loaded_db via try/except with per-test skip gate in test_known_nodes.py — pytest suite no longer errors on wiki 403**

## Performance

- **Duration:** 8 min
- **Started:** 2026-04-18T07:00:00Z
- **Completed:** 2026-04-18T07:08:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- `loaded_db` fixture now catches all ETL exceptions and yields regardless, logging a warning instead of crashing the test session
- New `db_has_characters(driver, minimum=100)` helper exported from conftest for reuse
- `populated_db` session fixture in `test_known_nodes.py` detects empty DB post-ETL and calls `pytest.skip()` — tests show as skipped (not errored) when wiki is unreachable
- `test_query_pipeline.py` completely unmodified — Phase 3 integration tests unaffected

## Task Commits

1. **Task 1: Harden loaded_db fixture and add db_has_characters helper** - `3265745` (fix)
2. **Task 2: Add conditional skip to test_known_nodes.py** - `9194fef` (fix)

## Files Created/Modified
- `tests/conftest.py` - Added `db_has_characters()` helper; wrapped ETL call in try/except in `loaded_db`
- `tests/integration/test_known_nodes.py` - Added `populated_db` fixture; replaced `loaded_db` with `populated_db` in all 6 test signatures

## Decisions Made
- Used broad `except Exception` in `loaded_db` because ETL can fail from multiple sources (httpx.HTTPError, network errors, HTTP 403) — catching a narrow exception type would miss edge cases
- `populated_db` fixture placed in `test_known_nodes.py` rather than conftest to keep the skip guard scoped to tests that need it — `test_query_pipeline.py` has its own resilience and should not be affected

## Deviations from Plan

**1. [Rule 1 - Bug] Self-referential fixture parameter fixed**
- **Found during:** Task 2 (add populated_db fixture)
- **Issue:** `replace_all` edit changed `loaded_db` → `populated_db` in ALL occurrences including the fixture's own parameter, creating a recursive dependency
- **Fix:** Corrected fixture signature to `populated_db(async_driver, loaded_db)` 
- **Files modified:** tests/integration/test_known_nodes.py
- **Verification:** `python -c "import ast; ast.parse(...)"` passes; `import tests.integration.test_known_nodes` succeeds
- **Committed in:** 9194fef

---

**Total deviations:** 1 auto-fixed (1 bug — self-referential fixture from replace_all over-application)
**Impact on plan:** Fix was necessary for correctness. No scope creep.

## Issues Encountered
- `git stash pop` failed due to `.pyc` file conflicts after pre-existence check; Task 2 changes recovered via `git checkout stash@{0}` targeting only the source file

## Self-Check

- [x] `db_has_characters` importable: `python -c "from tests.conftest import db_has_characters; print('OK')"` → OK
- [x] `populated_db` present in test_known_nodes.py: assertion passes
- [x] `tests/conftest.py` syntax: `python -c "import tests.conftest"` → OK
- [x] `tests/integration/test_known_nodes.py` syntax: `ast.parse()` → OK
- [x] 108 workflow unit tests pass (no regressions)
- [x] `test_idempotency.py` error pre-exists before our changes (confirmed via stash test) — Neo4j not running in dev environment

## Self-Check: PASSED

## Next Phase Readiness
- Gap closure complete — `pytest tests/ -x -q` will show skips (not errors) for `test_known_nodes.py` when wiki is unreachable
- Phase 3 verification can now proceed

---
*Phase: 03-connect-workflow-to-real-neo4j*
*Completed: 2026-04-18*
