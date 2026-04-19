---
phase: "04-fastapi-htmx-web-layer"
plan: "01"
subsystem: web
tags: [fastapi, htmx, neo4j, jinja2, tdd]
dependency_graph:
  requires:
    - src/etl/run_etl.py (ETL main() signature)
    - src/workflow/run.py (Neo4j driver init pattern)
    - src/etl/constants.py (EXPECTED_NODE_COUNTS)
  provides:
    - src/web/app.py (FastAPI app with lifespan singleton)
    - src/web/dependencies.py (get_driver, verify_admin_key)
    - src/web/routes/api.py (GET /api/entities, POST /api/query)
    - src/web/routes/admin.py (POST /admin/refresh-data)
    - src/web/routes/pages.py (GET /)
    - tests/web/conftest.py (stub_driver, test_client, mock_admin_env)
  affects:
    - pyproject.toml (fastapi[standard]>=0.136.0, aiofiles>=24.1 added)
tech_stack:
  added:
    - fastapi[standard]==0.136.0 (includes uvicorn, jinja2, python-multipart)
    - aiofiles>=24.1
  patterns:
    - asynccontextmanager lifespan for Neo4j driver singleton
    - FastAPI dependency injection (Depends, Security)
    - Two-phase POST->SSE-GET pattern for query streaming
    - secrets.compare_digest() for timing-safe admin key comparison
    - Module-level ETL import to enable test patching
key_files:
  created:
    - src/web/__init__.py (1 line — package marker)
    - src/web/app.py (54 lines — FastAPI factory with lifespan)
    - src/web/dependencies.py (26 lines — get_driver, verify_admin_key)
    - src/web/routes/__init__.py (1 line — package marker)
    - src/web/routes/pages.py (15 lines — GET /)
    - src/web/routes/api.py (57 lines — GET /api/entities, POST /api/query)
    - src/web/routes/admin.py (29 lines — POST /admin/refresh-data)
    - src/web/templates/index.html (85 lines — roster tabs, query form)
    - src/web/templates/partials/progress.html (15 lines — SSE fragment)
    - src/web/templates/partials/result.html (35 lines — team result card)
    - src/web/static/app.js (90 lines — localStorage roster sync)
    - tests/web/__init__.py (0 lines — package marker)
    - tests/web/unit/__init__.py (0 lines — package marker)
    - tests/web/conftest.py (46 lines — shared fixtures)
    - tests/web/unit/test_app.py (27 lines — lifespan tests)
    - tests/web/unit/test_pages.py (16 lines — GET / tests)
    - tests/web/unit/test_api.py (59 lines — entities + query tests)
    - tests/web/unit/test_admin.py (44 lines — admin auth + ETL tests)
  modified:
    - pyproject.toml (added fastapi[standard]>=0.136.0, aiofiles>=24.1)
decisions:
  - "Module-level import of run_etl in admin.py enables patch('src.web.routes.admin.run_etl') in tests without patching the ETL module directly"
  - "stub_driver.close = AsyncMock() required because lifespan awaits driver.close() on shutdown — plain MagicMock.close() is not awaitable"
  - "Two-phase POST->SSE-GET pattern (D-09): POST /api/query stores job in app.state.jobs and returns sse-connect fragment; SSE GET reads job by ID"
  - "app.state.jobs dict initialized in lifespan for Plan 02 SSE job store; single uvicorn worker constraint documented"
  - "Pico CSS via CDN for minimal styling — no build toolchain needed"
metrics:
  duration: "~7 minutes"
  completed_date: "2026-04-19"
  tasks_completed: 2
  files_created: 18
  files_modified: 1
  tests_passing: 12
  lines_of_code: 548
---

# Phase 04 Plan 01: FastAPI App Skeleton Summary

**One-liner:** FastAPI web skeleton with Neo4j lifespan singleton, HTMX roster checklist, admin ETL endpoint, and 12 passing unit tests behind dependency injection.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | FastAPI app skeleton — lifespan, routes, templates, static | 0b243f5 | 11 files created, pyproject.toml modified |
| 2 | Wave 0 test stubs — all Phase 4 test files pass | 4d36ecb | 7 files (conftest + 4 unit test modules + admin.py fix) |

## Artifacts Created

| File | Lines | Purpose |
|------|-------|---------|
| src/web/app.py | 54 | FastAPI factory, asynccontextmanager lifespan, app.state.driver + jobs |
| src/web/dependencies.py | 26 | get_driver() + verify_admin_key() with secrets.compare_digest |
| src/web/routes/pages.py | 15 | GET / -> Jinja2 index.html |
| src/web/routes/api.py | 57 | GET /api/entities (UNION ALL), POST /api/query (SSE two-phase) |
| src/web/routes/admin.py | 29 | POST /admin/refresh-data behind X-Admin-Key |
| src/web/templates/index.html | 85 | Characters/Grastas tabs, search, query form with hx-post |
| src/web/templates/partials/progress.html | 15 | SSE sse-connect fragment returned by POST /api/query |
| src/web/templates/partials/result.html | 35 | Team result card (used by Plan 02 streaming) |
| src/web/static/app.js | 90 | localStorage roster sync + client-side filter |
| tests/web/conftest.py | 46 | stub_driver, test_client, mock_admin_env fixtures |
| tests/web/unit/test_app.py | 27 | lifespan creates driver and jobs dict |
| tests/web/unit/test_pages.py | 16 | GET / returns 200 HTML |
| tests/web/unit/test_api.py | 59 | entities endpoint, query stores job + returns SSE fragment |
| tests/web/unit/test_admin.py | 44 | valid key->200, wrong key->403, missing->403, ETL error->error json |

## Test Results

```
pytest tests/web/unit/ -x -q
............
12 passed in 0.05s
```

All Wave 0 stubs pass. TDD RED/GREEN cycle followed:
- RED commit `cecbc4a`: 4 import-check stubs — all failed with ModuleNotFoundError
- GREEN commit `0b243f5`: Implementation — 4 RED stubs now pass
- GREEN commit `4d36ecb`: Full 12-test suite — all pass

## Patterns Established

**Lifespan pattern** — `asynccontextmanager` in `app.py` creates Neo4j driver singleton on startup, stores as `app.state.driver`, closes on shutdown. Identical to `src/workflow/run.py` driver init.

**Dependency injection pattern** — `get_driver(request: Request)` reads `request.app.state.driver`. Tests override via `app.dependency_overrides[get_driver] = lambda: stub_driver`.

**Admin auth pattern** — `APIKeyHeader(name="X-Admin-Key")` + `secrets.compare_digest()` + `HTTPException(403)` (T-04-01, T-04-06 mitigated per threat model).

**Two-phase POST→SSE pattern** — POST `/api/query` stores job in `app.state.jobs[uuid4]`, returns `partials/progress.html` with `sse-connect="/api/stream/{job_id}"`. Plan 02 implements the SSE GET endpoint.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] stub_driver.close must be AsyncMock**
- **Found during:** Task 2 — first test run
- **Issue:** Lifespan teardown calls `await app.state.driver.close()`. TestClient patches `AsyncGraphDatabase.driver` return value with `MagicMock()`, but `MagicMock.close()` is not a coroutine. Raised `TypeError: object MagicMock can't be used in 'await' expression`.
- **Fix:** Added `driver.close = AsyncMock()` to `stub_driver` fixture in `tests/web/conftest.py` and inline in `tests/web/unit/test_app.py`.
- **Files modified:** `tests/web/conftest.py`, `tests/web/unit/test_app.py`
- **Commit:** 4d36ecb

**2. [Rule 1 - Bug] run_etl moved to module-level import in admin.py**
- **Found during:** Task 2 — `test_admin.py::test_refresh_data_valid_key`
- **Issue:** Plan specified `patch("src.web.routes.admin.run_etl")` but the original `admin.py` did a local import inside the function body, so `run_etl` was not a module attribute — patch raised `AttributeError`.
- **Fix:** Moved `from src.etl.run_etl import main as run_etl` to module level in `admin.py`. This makes `run_etl` patchable at `src.web.routes.admin.run_etl` without modifying the ETL module.
- **Files modified:** `src/web/routes/admin.py`
- **Commit:** 4d36ecb

## Known Stubs

| File | Location | Description |
|------|----------|-------------|
| src/web/templates/partials/progress.html | full file | SSE fragment references `/api/stream/{job_id}` — streaming endpoint created in Plan 02 |
| src/web/templates/partials/result.html | full file | Result card template — wired in Plan 02 streaming response |
| src/web/routes/api.py | POST /api/query | Returns progress fragment but no actual SSE stream endpoint yet — Plan 02 adds GET /api/stream/{job_id} |

These stubs are intentional scaffolding. The roster checklist (GET /api/entities) and admin endpoint are fully functional. The query-to-result pipeline is completed in Plan 02.

## Threat Flags

None. All threats in the plan's threat model were mitigated as specified:
- T-04-01/T-04-06: `secrets.compare_digest()` in `verify_admin_key()` — implemented
- T-04-04: `QueryRequest(query: str, roster: list[str])` Pydantic validation at API boundary — implemented
- T-04-02: `app.state.jobs` in-memory dict with single uvicorn worker constraint — documented in app.py docstring

## Self-Check: PASSED

Files exist:
- src/web/app.py: FOUND
- src/web/dependencies.py: FOUND
- src/web/routes/api.py: FOUND
- src/web/routes/admin.py: FOUND
- src/web/templates/index.html: FOUND
- tests/web/conftest.py: FOUND

Commits exist:
- cecbc4a (RED stubs): FOUND
- 0b243f5 (feat skeleton): FOUND
- 4d36ecb (feat tests): FOUND

Tests: 12/12 passing
