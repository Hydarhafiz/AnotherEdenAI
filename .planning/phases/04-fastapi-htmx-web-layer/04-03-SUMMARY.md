---
phase: "04-fastapi-htmx-web-layer"
plan: "03"
subsystem: web
tags: [htmx, sse, jinja2, ui-polish, partials]
dependency_graph:
  requires:
    - src/web/templates/partials/progress.html (Plan 01 stub — extended)
    - src/web/templates/partials/result.html (Plan 01 stub — extended with include delegation)
    - src/web/streaming.py (Plan 02 — pipeline_sse_generator producing node_status events)
  provides:
    - src/web/templates/partials/progress.html (sse-connect, sse-close, sse-swap, D-13 retry counter script)
    - src/web/templates/partials/error.html (error card for retry-cap-exhausted path)
    - src/web/templates/partials/empty.html (empty-state message when no teams found)
  affects:
    - src/web/templates/partials/result.html (now delegates to error.html and empty.html via Jinja2 include)
tech_stack:
  added: []
  patterns:
    - htmx:sseMessage event listener intercepts node_status JSON before HTMX swaps raw data
    - Jinja2 include with context for conditional partial delegation in result.html
    - sse-close="done" HTMX SSE extension attribute for auto-close on pipeline completion
key_files:
  created:
    - src/web/templates/partials/error.html (14 lines — error card partial)
    - src/web/templates/partials/empty.html (13 lines — empty-state partial)
  modified:
    - src/web/templates/partials/progress.html (stub replaced — 68 lines with inline JS script)
    - src/web/templates/partials/result.html (35->56 lines — Jinja2 include delegation added)
decisions:
  - "htmx:sseMessage intercept pattern: listen on document for htmx:sseMessage, check evt.detail.type === 'node_status', parse JSON, call evt.preventDefault() to suppress HTMX raw-data swap"
  - "error.html uses result.error directly (not a standalone error_message variable) — Jinja2 include with context passes result dict through automatically"
  - "result.html uses result.get('error') and result.get('frontline') for conditional branching — consistent with Plan 01 original contract"
metrics:
  duration: "~2 minutes"
  completed_date: "2026-04-21"
  tasks_completed: 1
  tasks_total: 2
  files_created: 2
  files_modified: 2
  tests_passing: 18
---

# Phase 04 Plan 03: UI Polish — Progress Retry Counter + Error/Empty Partials Summary

**One-liner:** HTMX progress partial updated with D-13 retry counter script (htmx:sseMessage intercept) and two new Jinja2 partials (error.html, empty.html) wired into result.html via conditional include delegation.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Progress partial with retry counter + error/empty partials | f6f7784 | 4 files (2 created, 2 modified) |

## Task 2 — PENDING (Browser Smoke Test)

Task 2 is a `checkpoint:human-verify` gate. Execution stopped after Task 1 per plan's `autonomous: false` directive. Browser smoke test must be performed by the user before this plan is marked complete.

## Artifacts Created

| File | Lines | Purpose |
|------|-------|---------|
| src/web/templates/partials/error.html | 14 | Error card for retry-cap-exhausted and pipeline failure paths |
| src/web/templates/partials/empty.html | 13 | Empty-state message when frontline is empty and no error |
| src/web/templates/partials/progress.html | 68 | SSE progress div with sse-connect, sse-close, sse-swap, D-13 inline JS |
| src/web/templates/partials/result.html | 56 | Result card — now delegates to error.html / empty.html via Jinja2 include |

## Test Results

```
pytest tests/web/unit/ -x -q
..................
18 passed in 0.07s
```

Jinja2 render check:
```
python -c "...template render assertions..."
All template render checks passed
```

All three render paths verified:
- Error path: `result.error` set -> "No recommendation found" in output
- Empty path: `result.frontline` empty, `result.error` None -> "No matching teams found" in output
- Happy path: characters in `result.frontline` -> character names rendered in grid

## Acceptance Criteria Status

- [x] `progress.html` contains `sse-connect="/api/stream/{{ job_id }}"`
- [x] `progress.html` contains `sse-close="done"`
- [x] `progress.html` contains `sse-swap="node_status"`
- [x] `progress.html` contains `"Validating... attempt"`
- [x] `error.html` exists and contains `No recommendation found`
- [x] `empty.html` exists and contains `No matching teams found`
- [x] Jinja2 template render check exits 0
- [x] `result.html` contains `result.get('error')` and includes error + empty partials

## Deviations from Plan

None — plan executed exactly as written. The three template files were implemented as specified in the plan action block.

## Browser Smoke Test (Task 2 — PENDING)

The following checks are pending human verification:

**Check A — Page load (WEB-01):** Page loads without HTTP error; zero JS console errors; Characters/Grastas tabs visible; character list populates.

**Check B — Roster checklist (WEB-02):** Search filters in real time; checked selections persist across page refresh via localStorage.

**Check C — Query submission (WEB-02):** Query text + roster submission shows "Running pipeline..." progress container.

**Check D — SSE streaming progress (WEB-03):** Node status updates appear in sequence (PLAN -> CYPHER -> VALIDATE -> ANALYZE -> FORMAT); page does not go blank.

**Check E — Retry counter (WEB-03, D-13):** If VALIDATE retries, "Validating... attempt N/3" appears in progress div.

**Check F — Result display (WEB-01, D-16, D-18):** Character cards grid renders; frontline 4-card row; reserve 2-card row; synergy explanation; no raw JSON.

**Check G — Admin endpoint (WEB-05):** `POST /admin/refresh-data` with valid X-Admin-Key returns 200; without key returns 403.

## Known Stubs

None. All stubs from Plans 01 and 02 are resolved. The browser smoke test (Task 2) is a manual verification gate, not a stub.

## Threat Flags

None. Threats T-04-11 through T-04-13 from the plan's threat model are addressed:
- T-04-11: Jinja2 HTML autoescaping is enabled by default for .html templates — `{{ result.error }}` and character names are HTML-escaped
- T-04-12: JSON.parse() on server-generated SSE data; no eval() or innerHTML assignment of parsed values; node names come from NODE_DESCRIPTIONS fixed map
- T-04-13: Accepted — ~900 DOM nodes for checklist within browser tolerance for single-user scope

## Self-Check: PASSED

Files exist:
- src/web/templates/partials/progress.html: FOUND
- src/web/templates/partials/error.html: FOUND
- src/web/templates/partials/empty.html: FOUND
- src/web/templates/partials/result.html: FOUND

Commits exist:
- f6f7784 (feat(04-03) progress/error/empty partials): FOUND

Tests: 18/18 web unit tests passing
Jinja2 render check: PASSED (all 3 paths)
