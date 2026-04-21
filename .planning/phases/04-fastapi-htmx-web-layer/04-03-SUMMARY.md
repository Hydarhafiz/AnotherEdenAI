---
phase: "04-fastapi-htmx-web-layer"
plan: "03"
subsystem: web
tags: [htmx, sse, jinja2, ui-polish, partials, smoke-test]
dependency_graph:
  requires:
    - src/web/templates/partials/progress.html (Plan 01 stub — extended)
    - src/web/templates/partials/result.html (Plan 01 stub — extended with include delegation)
    - src/web/streaming.py (Plan 02 — pipeline_sse_generator producing node_status events)
  provides:
    - src/web/templates/partials/progress.html (sse-connect, sse-close, sse-swap, D-13 retry counter script)
    - src/web/templates/partials/error.html (error card for retry-cap-exhausted path)
    - src/web/templates/partials/empty.html (empty-state message when no teams found)
    - src/web/static/app.js (fetch()-based POST replacing json-enc; htmx.process() SSE reactivation)
    - src/web/streaming.py (stream_mode="updates" chunk parsing fixed)
    - src/web/routes/api.py (SSE events yielded directly from route)
  affects:
    - Phase 5 — integration test suite and portfolio hardening
tech_stack:
  added: []
  patterns:
    - htmx:sseMessage event listener intercepts node_status JSON before HTMX swaps raw data
    - Jinja2 include with context for conditional partial delegation in result.html
    - sse-close="done" HTMX SSE extension attribute for auto-close on pipeline completion
    - fetch() + JSON.stringify replaces hx-ext="json-enc" for roster array serialisation
    - htmx.process() called after hx-swap to reactivate SSE extension on swapped fragment
    - LangGraph stream_mode="updates" yields {node_name: state_update} dicts directly — not wrapped
key_files:
  created:
    - src/web/templates/partials/error.html (error card partial)
    - src/web/templates/partials/empty.html (empty-state partial)
  modified:
    - src/web/templates/partials/progress.html (stub replaced — sse-connect, sse-close, D-13 inline JS)
    - src/web/templates/partials/result.html (Jinja2 include delegation to error.html/empty.html)
    - src/web/static/app.js (replaced json-enc with fetch(); added htmx.process() call)
    - src/web/streaming.py (fixed stream_mode="updates" chunk parsing)
    - src/web/routes/api.py (yield SSE events directly from route, not wrapped in EventSourceResponse)
    - tests/web/unit/test_streaming.py (test mock updated to match LangGraph output format)
key_decisions:
  - "htmx:sseMessage intercept pattern: listen on document for htmx:sseMessage, check evt.detail.type === 'node_status', parse JSON, call evt.preventDefault() to suppress HTMX raw-data swap"
  - "error.html uses result.error directly — Jinja2 include with context passes result dict through automatically"
  - "result.html uses result.get('error') and result.get('frontline') for conditional branching — consistent with Plan 01 contract"
  - "fetch() + JSON.stringify replaces hx-ext='json-enc' — json-enc serialises hidden roster input value as string, sending nested JSON-string instead of array; fetch() serialises correctly"
  - "LangGraph stream_mode='updates' yields {node_name: state_dict} pairs directly — streaming.py must unpack as `for chunk in stream: for node_name, state in chunk.items()`"
  - "SSE events must be yielded directly from FastAPI route function (not wrapped in EventSourceResponse constructor) — sse-starlette expects generator to yield ServerSentEvent objects"
patterns_established:
  - "Pattern: SSE route yields ServerSentEvent objects directly from async generator path operation"
  - "Pattern: htmx.process(swappedElement) required after programmatic hx-swap to reactivate HTMX extensions on new DOM nodes"
requirements_completed:
  - WEB-01
  - WEB-02
  - WEB-03

metrics:
  duration: "~3 hours (including smoke test debug cycle)"
  completed_date: "2026-04-21"
  tasks_completed: 2
  tasks_total: 2
  files_created: 2
  files_modified: 6
  tests_passing: 18
---

# Phase 04 Plan 03: UI Polish + Browser Smoke Test Summary

**HTMX progress partial with D-13 retry counter, error/empty Jinja2 partials, and full end-to-end browser smoke test passing — three bugs found and fixed during smoke test (json-enc serialisation, LangGraph chunk parsing, SSE route yield pattern)**

## Performance

- **Duration:** ~3 hours (including smoke test debug cycle)
- **Started:** 2026-04-21
- **Completed:** 2026-04-21
- **Tasks:** 2/2
- **Files modified:** 8 (2 created, 6 modified)

## Accomplishments

- Progress partial extended with `sse-connect`/`sse-close`/`sse-swap` and inline JS for D-13 retry counter text ("Validating... attempt 2/3")
- Error and empty-state Jinja2 partials created and wired into result.html via conditional `{% include %}`
- Three bugs discovered and fixed during browser smoke test, bringing full end-to-end flow to working state
- Browser smoke test completed: all checks A through G passed — zero JS console errors, SSE streaming, result card rendered, admin endpoint auth enforced

## Task Commits

Each task was committed atomically:

1. **Task 1: Progress partial with retry counter + error/empty partials** - `f6f7784` (feat)
2. **Smoke test fix: json-enc -> fetch() for POST /api/query** - `73fff6a` + `3471d55` (fix)
3. **Smoke test fix: stream_mode="updates" chunk parsing in streaming.py** - `e25b692` (fix)
4. **Smoke test fix: yield SSE events directly from route** - `18e43fe` (fix)

**Plan metadata:** (this commit — docs)

## Files Created/Modified

- `src/web/templates/partials/progress.html` - SSE progress div with sse-connect, sse-close, D-13 retry counter inline JS
- `src/web/templates/partials/error.html` - Error card partial (retry-cap-exhausted path)
- `src/web/templates/partials/empty.html` - Empty-state partial (no teams found)
- `src/web/templates/partials/result.html` - Conditional include delegation to error.html/empty.html
- `src/web/static/app.js` - Replaced hx-ext="json-enc" with fetch() + JSON.stringify; added htmx.process()
- `src/web/streaming.py` - Fixed stream_mode="updates" chunk parsing to unpack {node_name: state} pairs
- `src/web/routes/api.py` - Yield ServerSentEvent objects directly from route (not wrapped in EventSourceResponse)
- `tests/web/unit/test_streaming.py` - Mock updated to match actual LangGraph stream_mode="updates" format

## Browser Smoke Test Results

All checks passed after smoke test debug cycle. Three bugs were found and fixed before final approval.

| Check | Description | Result |
|-------|-------------|--------|
| A | Page loads, zero JS console errors, Characters/Grastas tabs visible, character list populates | PASS |
| B | Search filters in real time; checked selections persist across F5 via localStorage | PASS |
| C | Query submission shows "Running pipeline..." progress container | PASS |
| D | SSE streaming progress: PLAN -> CYPHER -> VALIDATE -> ANALYZE -> FORMAT in sequence; page does not go blank | PASS |
| E | Retry counter: "Validating... attempt N/3" text appears in progress div on VALIDATE retry | PASS |
| F | Result card: 4-frontline grid, reserve row, synergy explanation, no raw JSON visible | PASS |
| G | POST /admin/refresh-data with X-Admin-Key returns 200; without key returns 403 | PASS |

## Decisions Made

- `fetch()` + `JSON.stringify` replaces `hx-ext="json-enc"` — json-enc serialises the hidden `roster` input value as a JSON-string (double-encoded), sending `{"roster":"[\"Aldo\",...]"}` instead of `{"roster":["Aldo",...]}`. FastAPI's Pydantic validation then rejects with 422. Native fetch with `JSON.stringify` produces the correct schema.
- `htmx.process(progressDiv)` called after programmatic DOM swap — HTMX extensions (sse) are not applied to elements inserted via `innerHTML` assignment unless `htmx.process()` is called to reactivate them.
- LangGraph `stream_mode="updates"` contract: each yielded chunk is `{node_name: state_update_dict}` — the streaming loop must unpack as `for node_name, state in chunk.items()`. The previous code checked for a `"type"` key that does not exist in updates mode.
- FastAPI sse-starlette route pattern: `response_class=EventSourceResponse` with `yield ServerSentEvent(...)` inside the path operation. Wrapping the generator in `EventSourceResponse(generator)` causes silent encoding failures after 200 headers are sent.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] POST /api/query returning 422 — json-enc double-encodes roster array**
- **Found during:** Task 2 (browser smoke test, Check C)
- **Issue:** `hx-ext="json-enc"` reads the hidden `roster` input's string value directly and includes it as-is, producing `{"roster":"[\"Aldo\",...]"}` — a string, not an array. FastAPI Pydantic model rejects with 422 Unprocessable Entity.
- **Fix:** Replaced `hx-ext="json-enc"` in form with a custom fetch() submit handler in `app.js` that calls `JSON.parse(rosterInput.value)` to reconstruct the array and `JSON.stringify({query, roster})` for the POST body. Added `htmx.process(progressDiv)` to reactivate sse extension on swapped fragment.
- **Files modified:** `src/web/static/app.js`, `src/web/templates/index.html`
- **Verification:** POST /api/query accepted with 200; progress container appeared in browser
- **Committed in:** `73fff6a`, `3471d55`

**2. [Rule 1 - Bug] SSE stream silent no-op — LangGraph stream_mode="updates" chunk format mismatch**
- **Found during:** Task 2 (browser smoke test, Check D — SSE progress not updating)
- **Issue:** `streaming.py` checked `chunk.get("type") == "updates"` to unpack node state, but `stream_mode="updates"` yields `{node_name: state_dict}` dicts directly with no `"type"` wrapper key. The condition was always False, so the loop processed zero events, silently exhausting the stream with no SSE events emitted — causing `ERR_INCOMPLETE_CHUNKED_ENCODING` in the browser.
- **Fix:** Changed chunk iteration to `for node_name, state in chunk.items()` — the correct pattern for `stream_mode="updates"`. Updated `test_streaming.py` mock to match actual LangGraph output format.
- **Files modified:** `src/web/streaming.py`, `tests/web/unit/test_streaming.py`
- **Verification:** SSE events appeared in browser DevTools Network; progress text updated in sequence
- **Committed in:** `e25b692`

**3. [Rule 1 - Bug] ERR_INCOMPLETE_CHUNKED_ENCODING — SSE events wrapped in EventSourceResponse instead of yielded directly**
- **Found during:** Task 2 (browser smoke test, Check D — SSE stream closed immediately after 200)
- **Issue:** The SSE route wrapped the pipeline generator in `EventSourceResponse(pipeline_sse_generator(...))`, treating it as a `StreamingResponse`. sse-starlette expects the path operation itself to be the async generator — it wraps the route's return values. When a generator is passed as the constructor argument, sse-starlette tries to `.encode()` the `ServerSentEvent` dataclass objects as bytes, crashes silently, and closes the connection after headers.
- **Fix:** Changed the route to `response_class=EventSourceResponse` and `yield` `ServerSentEvent` objects inline (or from the pipeline generator directly), so sse-starlette handles encoding.
- **Files modified:** `src/web/routes/api.py`
- **Verification:** `ERR_INCOMPLETE_CHUNKED_ENCODING` resolved; full SSE event sequence visible in Network tab
- **Committed in:** `18e43fe`

---

**Total deviations:** 3 auto-fixed (all Rule 1 — bugs blocking smoke test checks C and D)
**Impact on plan:** All three fixes were necessary for the pipeline to function end-to-end. No scope creep. Bugs were latent from Plans 01/02 — surface area only became visible during real browser execution.

## Issues Encountered

- `d28452e` was an initial 422 fix attempt (adding a `htmx:configRequest` event listener) that was superseded by the correct fix (`73fff6a` — replacing json-enc with fetch()). The initial attempt was committed before the root cause was understood.

## Notes for Phase 5

- **Multi-worker concern:** The current SSE implementation holds an open connection per query for the pipeline duration (~10-30 seconds). Single-worker uvicorn is fine for portfolio demo; Phase 5 deployment should confirm the worker model (gunicorn/uvicorn workers) and whether long-lived SSE connections need Redis pub/sub or a job queue.
- **ETL nodriver async concern:** `POST /admin/refresh-data` runs nodriver (headless browser) inside the FastAPI async event loop. nodriver uses its own asyncio loop management which can conflict. Not observed in smoke test (admin endpoint tested via curl, not ETL trigger), but Phase 5 integration tests should test the full ETL trigger path.
- **htmx.process() fragility:** If the progress fragment HTML structure changes (e.g., different container element), the `htmx.process(progressDiv)` call in `app.js` must target the correct element. The ID `progress-container` is load-bearing — document in CONTEXT.md for Phase 5.
- **LangGraph streaming contract:** `stream_mode="updates"` is confirmed as the correct mode for node-level status events. If the graph structure changes in Phase 5 (new nodes, parallel edges), update the `NODE_DESCRIPTIONS` map in `progress.html` accordingly.

## Known Stubs

None. All Phase 4 success criteria are met. No stub data or placeholder content flows to the UI.

## Threat Flags

None. Threats T-04-11 through T-04-13 from the plan's threat model are addressed:
- T-04-11: Jinja2 HTML autoescaping is enabled by default for .html templates — `{{ result.error }}` and character names are HTML-escaped. Confirmed visually during smoke test (no raw HTML injection visible).
- T-04-12: JSON.parse() on server-generated SSE data; no eval() or innerHTML assignment of parsed values; node names resolved through NODE_DESCRIPTIONS fixed map before DOM write.
- T-04-13: Accepted — ~900 DOM nodes for checklist within browser tolerance for single-user scope. Confirmed acceptable during smoke test (page load under 2 seconds).

## Self-Check: PASSED

Files exist:
- `src/web/templates/partials/progress.html`: FOUND
- `src/web/templates/partials/error.html`: FOUND
- `src/web/templates/partials/empty.html`: FOUND
- `src/web/templates/partials/result.html`: FOUND
- `src/web/static/app.js`: FOUND
- `src/web/streaming.py`: FOUND
- `src/web/routes/api.py`: FOUND

Commits exist:
- f6f7784 (feat(04-03) progress/error/empty partials): FOUND
- 73fff6a (fix(04-03) json-enc -> fetch()): FOUND
- e25b692 (fix(04-03) stream_mode updates chunk parsing): FOUND
- 18e43fe (fix(04-03) yield SSE events directly from route): FOUND

Tests: 18/18 web unit tests passing
Browser smoke test: all checks A-G passed

---
*Phase: 04-fastapi-htmx-web-layer*
*Completed: 2026-04-21*
