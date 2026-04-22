---
phase: 04-fastapi-htmx-web-layer
verified: 2026-04-22T00:00:00Z
status: human_needed
score: 13/13 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Open http://localhost:8000 in a browser. Check A: page loads, Characters/Grastas tabs visible, character list populates within 2 seconds from /api/entities. No JS console errors in DevTools."
    expected: "Two tabs visible, checklist populates from Neo4j data, zero JS console errors"
    why_human: "Requires Neo4j running with loaded data; browser JS execution and network timing cannot be verified programmatically"
  - test: "Check B: check 3-4 character boxes, refresh page (F5), confirm same boxes are still checked."
    expected: "localStorage persistence — same selections survive page reload"
    why_human: "Requires real browser localStorage; cannot test with pytest or headless automation in this context"
  - test: "Check C+D: enter a query, click 'Find Best Team', confirm SSE progress updates appear in sequence (PLAN -> CYPHER -> VALIDATE -> ANALYZE -> FORMAT), page does not go blank."
    expected: "Progress status div updates in real time; no ERR_INCOMPLETE_CHUNKED_ENCODING"
    why_human: "Real LangGraph pipeline execution and live SSE stream require Neo4j + LLM provider; cannot mock end-to-end in unit test"
  - test: "Check E: submit a query that triggers a VALIDATE retry. Confirm 'Validating... attempt 2/3' appears in the progress area."
    expected: "Retry counter text 'Validating... attempt N/3' visible in browser"
    why_human: "Requires real pipeline with validation failure; unit tests confirm the JS logic but browser rendering of the text is human-only"
  - test: "Check F: result card renders as character grid with names, roles, and synergy explanation — no raw JSON visible."
    expected: "4-frontline + 2-reserve card grid; synergy paragraph; no raw JSON in result area"
    why_human: "Requires successful end-to-end pipeline run with real LLM and Neo4j"
  - test: "Check G (admin): curl -s -X POST http://localhost:8000/admin/refresh-data -H 'X-Admin-Key: <ADMIN_KEY>' — returns {status: ok}; curl without key returns 403."
    expected: "Authenticated request: 200 {status: ok}. Unauthenticated request: 403."
    why_human: "Admin key value is environment-specific; smoke test already documented as passed in 04-03-SUMMARY.md but should be confirmed against live server"
---

# Phase 4: FastAPI + HTMX Web Layer — Verification Report

**Phase Goal:** The working pipeline is exposed via HTTP with a streaming progress UI — users can submit roster and query through a browser and see pipeline node status update in real time
**Verified:** 2026-04-22
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | FastAPI app starts without error and app.state.driver is set by lifespan | VERIFIED | `app.py` lines 35-38: `app.state.driver = AsyncGraphDatabase.driver(...); app.state.jobs = {}; yield; await app.state.driver.close()`. Import check passes. test_lifespan_creates_driver passes. |
| 2 | GET / returns 200 with HTML containing the roster checklist and query form | VERIFIED | `routes/pages.py` returns `TemplateResponse("index.html")`. `index.html` contains Characters/Grastas tabs, query form with id="query-form", and two progress/result container divs. test_index_returns_html and test_index_contains_query_form both pass. |
| 3 | GET /api/entities returns JSON with 'characters' and 'grastas' lists | VERIFIED | `routes/api.py` get_entities() executes UNION ALL Cypher and returns `{"characters": [...], "grastas": [...]}`. test_get_entities_returns_characters_and_grastas and test_get_entities_empty_db both pass. |
| 4 | POST /api/query returns an HTML fragment with sse-connect URL containing a job_id | VERIFIED | post_query() stores job in app.state.jobs[uuid4] and returns TemplateResponse("partials/progress.html", {"job_id": job_id}). progress.html contains `sse-connect="/api/stream/{{ job_id }}"`. test_post_query_returns_sse_fragment and test_post_query_stores_job_in_state both pass. |
| 5 | GET /api/stream/{job_id} streams node_status SSE events for each LangGraph node | VERIFIED | `routes/api.py` stream_job() pops job from state.jobs, iterates pipeline_sse_generator(), yields ServerSentEvent objects directly. streaming.py iterates `graph.astream(stream_mode="updates")` and emits node_status events for each node. test_sse_events_sequence_happy_path confirms 5 node_status events emitted. |
| 6 | The final SSE event before 'done' carries rendered Jinja2 HTML of the result card | VERIFIED | streaming.py finally block: `template = templates.env.get_template("partials/result.html"); html = template.render(result=final_output); yield ServerSentEvent(raw_data=html, event="result")`. test_final_sse_event_is_html confirms result event emitted before done. Template render check passes for error/empty/happy paths. |
| 7 | If client disconnects mid-stream, the generator stops emitting events | VERIFIED | streaming.py line 84: `if await request.is_disconnected(): break`. test_disconnect_stops_generator confirms < 5 node_status events when client disconnects after 1 check, and done event still emitted. |
| 8 | VALIDATE retries appear as separate node_status events with incrementing attempt numbers | VERIFIED | streaming.py lines 95-97: `retry_count = state_update.get("retry_count", 0); attempt = retry_count + 1; max_attempts = 3`. test_validate_attempt_is_retry_count_plus_one confirms retry_count=1 produces attempt=2 in event data. progress.html JS renders "Validating... attempt N/3" when attempt > 1. |
| 9 | POST /admin/refresh-data with correct X-Admin-Key returns 200 JSON | VERIFIED | admin.py calls `verify_admin_key` dep (HTTPException 403 on mismatch) then `await run_etl(driver=driver)`. Returns `{"status": "ok", "message": "ETL complete — data refreshed"}`. test_refresh_data_valid_key passes. |
| 10 | POST /admin/refresh-data with wrong or missing X-Admin-Key returns 403 | VERIFIED | `verify_admin_key` in dependencies.py uses `secrets.compare_digest()` and raises HTTPException(403) on mismatch or missing key. test_refresh_data_invalid_key and test_refresh_data_missing_key both pass. |
| 11 | Neo4j driver initialized as app-level singleton with async connection pooling | VERIFIED | lifespan uses `AsyncGraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)` — identical pattern to src/workflow/run.py. Driver stored at app.state.driver, closed via `await driver.close()` on shutdown. |
| 12 | Progress div shows 'Validating... attempt 2/3' when VALIDATE retries | VERIFIED | progress.html inline JS: `if (node === "VALIDATE" && attempt > 1) { text = "Validating... attempt " + attempt + "/" + max; }`. Logic confirmed in test_validate_attempt_is_retry_count_plus_one (unit) and browser smoke test (Check E) per 04-03-SUMMARY.md. |
| 13 | Error partial renders "No recommendation found"; empty partial renders "No matching teams found" | VERIFIED | result.html uses `{% if result.get('error') %}{% include "partials/error.html" %}{% elif not result.get('frontline') %}{% include "partials/empty.html" %}`. Jinja2 render check passes for all three code paths. |

**Score:** 13/13 truths verified (automated)

### Required Artifacts

| Artifact | Provides | Status | Details |
|----------|----------|--------|---------|
| `src/web/app.py` | FastAPI factory, lifespan, route mounts | VERIFIED | 55 lines; async def lifespan, app.state.driver, app.state.jobs, all three routers included |
| `src/web/dependencies.py` | get_driver(), verify_admin_key() | VERIFIED | 27 lines; secrets.compare_digest, HTTPException(403), APIKeyHeader |
| `src/web/routes/pages.py` | GET / Jinja2 response | VERIFIED | Returns TemplateResponse("index.html") |
| `src/web/routes/api.py` | GET /api/entities, POST /api/query, GET /api/stream/{job_id} | VERIFIED | 89 lines; UNION ALL Cypher, job store, EventSourceResponse + yield pattern |
| `src/web/routes/admin.py` | POST /admin/refresh-data | VERIFIED | Module-level run_etl import, verify_admin_key dep, returns ok/error JSON |
| `src/web/streaming.py` | pipeline_sse_generator, NODE_LABELS | VERIFIED | 140 lines; stream_mode="updates", chunk.items() unpacking, disconnect check, finally emits done |
| `src/web/templates/index.html` | Full page with tabs, query form, containers | VERIFIED | Characters/Grastas tabs, query form id="query-form", progress-container, result-container |
| `src/web/templates/partials/progress.html` | SSE fragment with retry counter JS | VERIFIED | sse-connect/sse-close/sse-swap, inline htmx:sseMessage listener, D-13 "Validating... attempt N/3" |
| `src/web/templates/partials/result.html` | Conditional result/error/empty delegation | VERIFIED | Includes error.html and empty.html via Jinja2 include with context |
| `src/web/templates/partials/error.html` | Error card | VERIFIED | "No recommendation found", result.error details block |
| `src/web/templates/partials/empty.html` | Empty state | VERIFIED | "No matching teams found" with suggestions |
| `src/web/static/app.js` | localStorage sync, fetch() submit | VERIFIED | loadRoster/saveRoster, buildChecklistHTML, fetch POST /api/query with JSON.stringify, htmx.process() |
| `tests/web/conftest.py` | stub_driver, test_client, mock_admin_env | VERIFIED | stub_driver with AsyncMock execute_query and close; dependency_overrides pattern |
| `tests/web/unit/test_streaming.py` | 6 SSE unit tests | VERIFIED | All 6 pass: happy path, label mapping, result HTML, done-always-last, validate retry, disconnect |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| app.py lifespan | app.state.driver | AsyncGraphDatabase.driver() | WIRED | Lines 35-38 confirmed |
| app.py lifespan | app.state.jobs | dict literal | WIRED | Line 36 confirmed |
| GET /api/entities | Neo4j driver.execute_query | Depends(get_driver) | WIRED | Lines 29-38 in api.py; UNION ALL Cypher confirmed |
| POST /api/query | app.state.jobs[job_id] | uuid4 store | WIRED | Lines 50-58 in api.py; progress.html returned with job_id |
| GET /api/stream/{job_id} | pipeline_sse_generator | async for yield | WIRED | Lines 81-88 in api.py; yields events directly (not wrapped in constructor) |
| pipeline_sse_generator | graph.astream() | build_graph(driver=driver) | WIRED | Line 66, 82-89 in streaming.py; chunk.items() unpacking confirmed |
| pipeline_sse_generator format handler | templates.env.get_template("partials/result.html").render() | ServerSentEvent(raw_data=html, event="result") | WIRED | Lines 130-133 in streaming.py |
| POST /admin/refresh-data | verify_admin_key | Depends(verify_admin_key) | WIRED | admin.py line 13; HTTPException(403) path confirmed by 2 passing tests |
| POST /admin/refresh-data | run_etl(driver=driver) | module-level import | WIRED | admin.py lines 4, 26 |
| result.html error path | partials/error.html | Jinja2 include with context | WIRED | Jinja2 render check confirmed "No recommendation found" output |
| result.html empty path | partials/empty.html | Jinja2 include with context | WIRED | Jinja2 render check confirmed "No matching teams found" output |
| app.js form submit | POST /api/query | fetch() + JSON.stringify | WIRED | app.js lines 98-108; roster sent as real JSON array (json-enc bug fixed) |
| app.js | htmx.process(container) | after innerHTML swap | WIRED | app.js line 108; reactivates SSE extension on swapped progress fragment |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| GET /api/entities | records | driver.execute_query (UNION ALL Cypher) | Yes — Neo4j query, not static | FLOWING |
| pipeline_sse_generator | chunk | graph.astream(initial_state, stream_mode="updates") | Yes — real LangGraph execution | FLOWING |
| pipeline_sse_generator | final_output | state_update["final_output"] from format node | Yes — populated by LangGraph FORMAT node | FLOWING |
| result.html | result | final_output passed from pipeline_sse_generator templates.render() | Yes — LangGraph output, Jinja2 renders | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| App is importable | `python -c "from src.web.app import app; print('ok')"` | "app import ok" | PASS |
| streaming.py is importable with exports | `python -c "from src.web.streaming import pipeline_sse_generator, NODE_LABELS"` | exits 0 | PASS |
| All 18 unit tests pass | `pytest tests/web/unit/ -q` | 18 passed in 0.06s | PASS |
| Jinja2 templates render all three paths | render check (error/empty/happy) | "All template render checks PASSED" | PASS |
| Browser smoke test | All checks A-G | Documented as PASS in 04-03-SUMMARY.md | DOCUMENTED (human-confirmed) |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| WEB-01 | 04-01, 04-03 | User can access system via web browser (no installation) | SATISFIED | GET / returns 200 HTML with roster UI; browser smoke test Check A passed (per 04-03-SUMMARY.md) |
| WEB-02 | 04-01, 04-02, 04-03 | Web UI provides roster input form and natural language query submission | SATISFIED | index.html has character/grasta checklist, query form; POST /api/query endpoint confirmed; app.js sends fetch() with JSON roster array |
| WEB-03 | 04-02, 04-03 | Pipeline node completion status streamed to UI via SSE (PLAN->CYPHER->VALIDATE->ANALYZE) | SATISFIED | pipeline_sse_generator emits node_status events for all 5 nodes; sse-connect/sse-swap in progress.html; 6 SSE unit tests confirm event sequence |
| WEB-04 | 04-01 | Neo4j driver initialized as app-level singleton with async connection pooling | SATISFIED | AsyncGraphDatabase.driver() in lifespan, stored as app.state.driver, closed on shutdown; test_lifespan_creates_driver confirms |
| WEB-05 | 04-01 | Admin can trigger full data refresh via POST /admin/refresh-data | SATISFIED | Admin endpoint with X-Admin-Key auth (secrets.compare_digest), run_etl(driver=driver); browser smoke test Check G confirmed auth (per 04-03-SUMMARY.md) |

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| — | None found | — | No blocker or warning anti-patterns detected in key source files |

No TODO/FIXME comments, no return null/return []/return {} stub patterns, no hardcoded empty values flowing to rendering, no console.log-only implementations found in the web layer source files.

**Notable deviation (intentional, not a stub):** `index.html` does not contain `hx-post="/api/query"`. This attribute was removed during Plan 03 as a bug fix: `hx-ext="json-enc"` was double-encoding the roster array, causing 422 errors. The form now uses a vanilla `fetch()` submit handler in `app.js` that correctly serializes `JSON.stringify({query, roster})`. The form submit is fully wired (app.js lines 89-113) and the POST /api/query endpoint works correctly (confirmed by 2 passing tests and browser smoke test).

### Human Verification Required

The automated checks (18 unit tests, import checks, Jinja2 render checks) all pass. The browser smoke test was completed by a human during Plan 03 and all checks A-G passed (documented in 04-03-SUMMARY.md). However, because the smoke test was performed during development and is not reproducible programmatically, the following items require human re-confirmation against a live server to formally close the phase.

#### 1. Page load and roster checklist population

**Test:** Start `uvicorn src.web.app:app --reload --port 8000`, open `http://localhost:8000` in a browser.
**Expected:** Page loads without HTTP error; zero JS console errors in DevTools; Characters and Grastas tabs visible; character list populates within 1-2 seconds from `/api/entities`.
**Why human:** Requires Neo4j running with loaded data; real browser JS execution; network timing.

#### 2. localStorage persistence

**Test:** Check 3-4 character boxes, press F5, confirm same boxes are still checked.
**Expected:** Same selections restored from localStorage after page reload.
**Why human:** Requires real browser localStorage; cannot test with pytest.

#### 3. End-to-end SSE streaming

**Test:** Enter a query (e.g., "best fire team"), click "Find Best Team", watch progress.
**Expected:** Progress container appears, status div updates in sequence (PLAN... CYPHER... VALIDATE... ANALYZE... FORMAT...), page does not go blank, result card appears with character grid.
**Why human:** Requires live LangGraph + Neo4j + LLM provider; unit tests cover generator logic but not live execution.

#### 4. Retry counter text

**Test:** Submit a query that triggers VALIDATE retry; or observe DevTools Network tab for validate SSE events.
**Expected:** "Validating... attempt 2/3" (or N/3) appears in the progress div.
**Why human:** Requires real pipeline execution with validation failure.

#### 5. Admin endpoint

**Test:** `curl -s -X POST http://localhost:8000/admin/refresh-data -H "X-Admin-Key: ${ADMIN_KEY}" | python3 -m json.tool` and `curl -s -X POST http://localhost:8000/admin/refresh-data | python3 -m json.tool`
**Expected:** Authenticated: `{"status": "ok", "message": "ETL complete..."}`. Unauthenticated: HTTP 403.
**Why human:** ADMIN_KEY value is environment-specific; ETL involves nodriver browser automation.

### Gaps Summary

No gaps found. All 13 observable truths verified. All 5 phase requirements (WEB-01 through WEB-05) have implementation evidence. All key artifact links are wired. No stub or placeholder patterns detected.

The phase status is `human_needed` because the browser smoke test (the final validation gate for a UI-heavy phase) is not reproducible programmatically. The smoke test was already performed and documented as passing in 04-03-SUMMARY.md (all checks A-G), but formal phase closure requires the human verification items above to be confirmed against a live server.

---

_Verified: 2026-04-22_
_Verifier: Claude (gsd-verifier)_
