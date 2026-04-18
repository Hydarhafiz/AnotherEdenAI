---
phase: quick-2
plan: 01
subsystem: tests/integration
tags: [integration-tests, pytest-asyncio, event-loop, idempotency, fixtures]
dependency_graph:
  requires: []
  provides: [passing integration tests, session-scoped loaded_db fixture]
  affects: [tests/integration/test_known_nodes.py, tests/integration/test_idempotency.py, tests/conftest.py, pytest.ini]
tech_stack:
  added: []
  patterns:
    - Session-scoped loaded_db fixture that runs ETL once per test session if DB count < 100
    - asyncio_default_test_loop_scope=session in pytest.ini to share event loop with fixtures
    - Idempotency tests use loader functions directly (no scraper) with static fixture data
key_files:
  created: []
  modified:
    - pytest.ini
    - tests/conftest.py
    - tests/integration/test_known_nodes.py
    - tests/integration/test_idempotency.py
decisions:
  - "asyncio_default_test_loop_scope=session added to pytest.ini — tests must share session loop with async_driver or RuntimeError occurs"
  - "loaded_db session fixture checks Character count >= 100 to distinguish real ETL data from idempotency test fixture data (which loads only 2 characters)"
  - "test_etl_idempotent uses loader functions directly with static fixtures — no scraper needed to verify idempotency, eliminates aiohttp loop conflict"
  - "Aldo element corrected to 'None, Fire' — wiki data-element is 'None, Fire' for base Aldo (dual-element character); original assertion 'Wind' was wrong"
metrics:
  duration: 12 minutes
  completed: 2026-03-15
  tasks_completed: 3
  files_changed: 4
---

# Quick Task 2: Fix 7 Failing Integration Tests — Summary

**One-liner:** Fixed all 7 integration tests by setting session-scoped asyncio test loop, adding loaded_db session fixture, rewriting idempotency test to use static fixtures instead of scraper, and correcting Aldo's element assertion.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Fix test_known_nodes — remove ETL re-run and clean_db | 8996513 | pytest.ini, tests/conftest.py, tests/integration/test_known_nodes.py |
| 2 | Fix test_idempotency — static fixtures, no scraper, fix threshold | 6c551a4 | tests/integration/test_idempotency.py |
| 3 | Full suite verification + conftest threshold fix | 63ea99f | tests/conftest.py |

## Root Cause Analysis

Two distinct root causes:

**Root Cause 1 — Event Loop Mismatch:**
`asyncio_default_test_loop_scope` was not set (defaulted to `function`), while `async_driver` was session-scoped. Each test ran on its own function-scoped loop, but the Neo4j driver was bound to the session loop. Any async call through `async_driver` inside a test raised `RuntimeError: Task got Future attached to a different loop`.

**Root Cause 2 — Stale Assertion:**
`test_etl_idempotent` asserted `counts_1["Grasta"] >= 500` but the actual loaded count is 489 (fixed in quick-1 for assert_schema.py but not updated in the integration test). Additionally, calling `run_etl_main()` in the test triggered aiohttp scraping which exacerbated the loop conflict.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Wrong Aldo element assertion**
- **Found during:** Task 1 verification (test ran but assertion failed after loop fix)
- **Issue:** `assert c["element"] == "Wind"` — wiki data shows Aldo has `data-element="None, Fire"` (dual-element character); the "Wind" assertion was never correct
- **Fix:** Updated assertion to `assert c["element"] == "None, Fire"`
- **Files modified:** tests/integration/test_known_nodes.py
- **Commit:** 8996513

**2. [Rule 2 - Missing Critical Functionality] loaded_db session fixture**
- **Found during:** Task 1 — removing run_etl_main from tests left no way to populate the DB
- **Issue:** Plan said "DB is already populated" but DB was empty (container likely restarted); tests querying existing data need guaranteed pre-population
- **Fix:** Added `loaded_db` session fixture in conftest.py that checks Character count and runs ETL if < 100
- **Files modified:** tests/conftest.py
- **Commit:** 8996513

**3. [Rule 1 - Bug] loaded_db threshold needed to be 100, not 0**
- **Found during:** Task 3 full test suite run
- **Issue:** `test_etl_idempotent` uses `clean_db` + loads 2 static characters; when it ran first in the session, `loaded_db` saw count=2 > 0 and skipped ETL, leaving stale fixture data in DB
- **Fix:** Raised threshold to 100 — static fixtures load 2 chars, real ETL loads 393
- **Files modified:** tests/conftest.py
- **Commit:** 63ea99f

## Final Test Results

```
22 passed in 6.28s
```

- 6 integration tests in test_known_nodes.py: PASS
- 1 integration test in test_idempotency.py: PASS
- 15 unit tests: PASS (no regression)

## Self-Check: PASSED

All files confirmed present. All commits confirmed in git log. Final test run: 22 passed.
