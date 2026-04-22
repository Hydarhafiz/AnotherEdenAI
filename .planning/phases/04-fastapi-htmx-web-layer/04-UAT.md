---
status: resolved
phase: 04-fastapi-htmx-web-layer
source: [04-01-SUMMARY.md, 04-02-SUMMARY.md, 04-03-SUMMARY.md]
started: 2026-04-22T13:58:28Z
updated: 2026-04-22T19:00:00Z
gap_closure: 04.1-gap-closure
---

## Current Test

[testing complete]

## Tests

### 1. Cold Start Smoke Test
expected: Kill any running server. Start fresh with `uvicorn src.web.app:app --reload --port 8000`. Server boots without import errors or crash. Opening http://localhost:8000 returns HTTP 200 and the roster page is visible.
result: pass

### 2. Page Load + Roster Checklist Populates
expected: Page loads at http://localhost:8000 with zero JS console errors in DevTools. Characters and Grastas tabs are visible. The character checklist populates within 1-2 seconds (data served from GET /api/entities → Neo4j). No empty/broken UI state.
result: pass

### 3. Search Filters Character List in Real Time
expected: Typing in the search/filter box narrows the visible character list in real time without a page reload. Clearing the box restores the full list.
result: pass

### 4. localStorage Persistence Survives Reload
expected: Check 3-4 character boxes. Press F5 (hard reload). The same boxes are still checked after reload — selections are restored from localStorage automatically.
result: pass

### 5. Query Submission Shows Progress Container
expected: Enter a natural language query (e.g. "best fire team"), click "Find Best Team". The progress container appears on the page without a full page reload (HTMX partial swap). The container shows pipeline status beginning with "Planning...".
result: pass

### 6. SSE Streaming Progress — Full Pipeline Sequence
expected: After submitting a query, the status div updates in sequence: PLAN → CYPHER → VALIDATE → ANALYZE → FORMAT. The page does NOT go blank mid-stream. No ERR_INCOMPLETE_CHUNKED_ENCODING error in browser console or DevTools Network tab.
result: issue
reported: "minor pass: the status load design in frontend could make it better, instead of showing raw JSON like {\"event\": \"node_status\", \"node\": \"FORMAT\", \"attempt\": 1, \"max\": 1} — this applies for the whole workflow"
severity: minor

### 7. Retry Counter Text on VALIDATE Retry
expected: When VALIDATE retries (the pipeline re-runs Cypher generation after a validation failure), the progress div shows "Validating... attempt 2/3" (or attempt N/3 for the Nth retry). The attempt number increments correctly for each retry.
result: pass

### 8. Result Card Renders Correctly
expected: After pipeline completes, a result card appears showing: a 4-character frontline grid, a reserve row, role annotations alongside character names, and a synergy explanation paragraph. No raw JSON is visible anywhere on the page.
result: issue
reported: "Inconsistent team lineup size — yesterday got 6 characters (4 frontline + 2 sub), today got 3 characters (2 frontline + 1 sub). Unclear if LLM output issue (using nvidia/nemotron-3-super-120b-a12b:free via OpenRouter) or FORMAT node not enforcing 4+2 structure. Needs investigation."
severity: major

### 9. Error Partial — No Recommendation Found
expected: When the pipeline returns an error (retry cap exhausted, or LLM failure), the error partial renders with "No recommendation found" and shows the error detail. No raw JSON, no blank page.
result: skipped
reason: Hard to trigger on demand — requires retry cap exhaustion or LLM failure

### 10. Admin Endpoint Auth
expected: `curl -s -X POST http://localhost:8000/admin/refresh-data -H "X-Admin-Key: <ADMIN_KEY>"` returns HTTP 200 with `{"status": "ok", ...}`. The same request WITHOUT the header (or with a wrong key) returns HTTP 403. No auth bypass possible.
result: issue
reported: "ADMIN_KEY is not included in the .env file or documented anywhere — user had to discover it by reading source code. Once added (ADMIN_KEY=dev-admin-secret), authenticated request returned 200 {status: ok} and ETL completed successfully."
severity: minor

## Summary

total: 10
passed: 6
issues: 3
pending: 0
skipped: 1
blocked: 0
skipped: 0
blocked: 0

## Gaps

- truth: "SSE node_status events should display as human-readable status text (e.g. 'Planning...', 'Generating Cypher...') in the progress div — not raw JSON"
  status: resolved
  reason: "User reported: progress div shows raw JSON for all pipeline nodes instead of formatted text"
  severity: minor
  test: 6
  root_cause: "htmx-ext-sse@2.2.4 fires htmx:sseMessage AFTER the DOM swap is already committed. progress.html listens on htmx:sseMessage and calls evt.preventDefault(), but the swap has already written raw JSON into the DOM — preventDefault() is a no-op. The cancellable hook is htmx:sseBeforeMessage (checked before swap). Fix: change event name on line 41 of progress.html from htmx:sseMessage to htmx:sseBeforeMessage."
  artifacts:
    - src/web/templates/partials/progress.html:41
  missing: []

- truth: "Result card should consistently show 4-character frontline grid + 2-character reserve row on every successful pipeline run"
  status: resolved
  reason: "User reported: inconsistent lineup size — 6 characters (4+2) one run, 3 characters (2+1) another"
  severity: major
  test: 8
  root_cause: "analyze.py prompt uses 'typically 3-4 characters' (advisory). TeamOutput Pydantic model in format.py defines frontline/reserve as list[CharacterSlot] with no min_length/max_length constraints — undersized LLM output passes model_validate() silently. Fix: add Field(min_length=3, max_length=4) to frontline and Field(min_length=1, max_length=2) to reserve in TeamOutput. Also harden analyze.py prompt from 'typically' to 'MUST contain exactly N characters'."
  artifacts:
    - src/workflow/nodes/format.py (TeamOutput.frontline, TeamOutput.reserve — missing Field validators)
    - src/workflow/nodes/analyze.py:33 (advisory 'typically' wording)
  missing:
    - Field(min_length=3, max_length=4) on TeamOutput.frontline
    - Field(min_length=1, max_length=2) on TeamOutput.reserve

- truth: "ADMIN_KEY must be documented in .env.example and README so users know it is required before testing the admin endpoint"
  status: resolved
  reason: "ADMIN_KEY env var is not present in .env and is not documented — user had to read source code to discover it"
  severity: minor
  test: 10
  root_cause: "No .env.example file exists with ADMIN_KEY entry. README (if present) does not document required env vars for the admin endpoint. Fix: add ADMIN_KEY=<your-secret> to .env.example and document it in setup instructions."
  artifacts: []
  missing:
    - ADMIN_KEY entry in .env.example or equivalent setup docs
