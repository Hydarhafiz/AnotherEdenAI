---
phase: "04-fastapi-htmx-web-layer"
plan: "02"
subsystem: web
tags: [fastapi, htmx, sse, langgraph, jinja2, tdd]
dependency_graph:
  requires:
    - src/workflow/graph.py (build_graph — astream entry point)
    - src/workflow/nodes/format.py (final_output dict schema)
    - src/web/routes/api.py (POST /api/query, app.state.jobs job store — Plan 01)
    - src/web/templates/partials/result.html (Jinja2 result card — Plan 01)
  provides:
    - src/web/streaming.py (pipeline_sse_generator, NODE_LABELS)
    - src/web/routes/api.py (GET /api/stream/{job_id} — stream endpoint added)
    - tests/web/unit/test_streaming.py (6 SSE unit tests)
  affects:
    - src/web/templates/partials/progress.html (stub wired — sse-connect now has a real handler)
tech_stack:
  added: []
  patterns:
    - pipeline_sse_generator async generator — LangGraph astream() to SSE ServerSentEvent sequence
    - EventSourceResponse wrapping an async generator (fastapi.sse, fastapi>=0.136.0)
    - Module-level import of build_graph enables patch('src.web.streaming.build_graph') in tests
    - jobs.pop(job_id, None) single-use job store (T-04-07 DoS mitigation)
    - request.is_disconnected() disconnect detection before each yield (T-04-08)
key_files:
  created:
    - src/web/streaming.py (139 lines — pipeline_sse_generator, NODE_LABELS)
    - tests/web/unit/test_streaming.py (217 lines — 6 SSE unit tests)
  modified:
    - src/web/routes/api.py (57->85 lines — added GET /api/stream/{job_id} + imports)
decisions:
  - "build_graph import moved to module level in streaming.py (not inside function body) — enables patch('src.web.streaming.build_graph') without modifying workflow module"
  - "jobs.pop(job_id, None) makes each stream single-use — second GET on same job_id returns 404, preventing stream replay (T-04-07)"
  - "validate attempt = retry_count + 1 (Pitfall 7) — retry_count in LangGraph update is the post-increment value; adding 1 gives the user-facing attempt number"
  - "finally block always emits done event — even on exception or disconnect break, HTMX sse-close receives the signal to close the connection"
metrics:
  duration: "~4 minutes"
  completed_date: "2026-04-19"
  tasks_completed: 2
  files_created: 2
  files_modified: 1
  tests_passing: 18
  lines_of_code: 441
---

# Phase 04 Plan 02: SSE Streaming Pipeline Summary

**One-liner:** pipeline_sse_generator async generator bridges LangGraph astream() to FastAPI EventSourceResponse with node_status/result/done SSE protocol, 6 unit tests all passing.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | streaming.py — pipeline_sse_generator async generator | 7de32b0 | src/web/streaming.py created |
| 2 | Wire GET /api/stream/{job_id} + unit tests for SSE sequence | c5f3488 | src/web/routes/api.py modified, tests/web/unit/test_streaming.py created |

## Artifacts Created

| File | Lines | Purpose |
|------|-------|---------|
| src/web/streaming.py | 139 | pipeline_sse_generator, NODE_LABELS — LangGraph astream() to SSE bridge |
| tests/web/unit/test_streaming.py | 217 | 6 unit tests: happy path, label mapping, HTML result event, done-always-last, validate retry attempt, disconnect detection |
| src/web/routes/api.py | 85 (+28) | GET /api/stream/{job_id} endpoint using EventSourceResponse(pipeline_sse_generator(...)) |

## Test Results

```
pytest tests/web/unit/test_streaming.py -x -q
......
6 passed in 0.01s

pytest tests/web/unit/ -x -q
..................
18 passed in 0.07s
```

All 6 new streaming tests pass. Full 18-test web unit suite green.

TDD cycle followed:
- RED: streaming.py did not exist — `ModuleNotFoundError` on import confirmed
- GREEN Task 1 commit `7de32b0`: streaming.py created, import check passes
- GREEN Task 2 commit `c5f3488`: api.py stream endpoint + test_streaming.py, 6/6 pass

## LangGraph astream Chunk Format Observations

The plan's documented chunk format `{"type": "updates", "data": {node_name: state_update}}` was used directly from the research. Mock testing confirmed the generator correctly handles:

- Single node per chunk (standard case for sequential graph topology)
- `chunk.get("type") == "updates"` guard filters non-update events
- format node captures `final_output` from `state_update["final_output"]` key
- validate node reads `retry_count` from state_update (post-increment: 0 on first attempt, 1 after first retry)

## Patterns Established

**pipeline_sse_generator pattern** — Async generator taking `(query, roster, driver, templates, request)`. Called from route handler via `EventSourceResponse(pipeline_sse_generator(...))`. FastAPI streams the generator output directly to the HTTP response.

**SSE event protocol:**
- `node_status`: `{"event": "node_status", "node": <LABEL>, "attempt": <int>, "max": <int>}`
- `result`: Raw Jinja2-rendered HTML via `ServerSentEvent(raw_data=html, event="result")`
- `done`: `ServerSentEvent(data="", event="done")` — always emitted via `finally` block

**Test isolation pattern** — Direct async generator iteration (not TestClient/HTTP) avoids SSE streaming limitations in HTTPX. `patch("src.web.streaming.build_graph", return_value=mock_graph)` works because build_graph is a module-level name.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] build_graph local import prevented test patching**
- **Found during:** Task 2 — first test run raised `AttributeError: <module 'src.web.streaming'> does not have the attribute 'build_graph'`
- **Issue:** Plan's code example placed `from src.workflow.graph import build_graph` inside the function body. `patch("src.web.streaming.build_graph")` requires `build_graph` to be a module-level attribute.
- **Fix:** Moved `from src.workflow.graph import build_graph` to module-level imports in streaming.py, removed the local import from function body.
- **Files modified:** `src/web/streaming.py`
- **Commit:** c5f3488 (included in Task 2 commit alongside api.py and tests)

## Known Stubs

None. All stubs from Plan 01 are now resolved:
- `partials/progress.html` sse-connect URL now has a real handler (`GET /api/stream/{job_id}`)
- `partials/result.html` is rendered by pipeline_sse_generator's finally block
- `POST /api/query` SSE two-phase pattern is now fully wired end-to-end

## Threat Flags

None. All threats in the plan's threat model were mitigated as specified:
- T-04-07: `jobs.pop(job_id, None)` single-use stream — implemented in stream_job()
- T-04-08: `request.is_disconnected()` before each yield — implemented in pipeline_sse_generator
- T-04-09: Jinja2 autoescaping ON for HTML templates — confirmed by fastapi.templating default
- T-04-10: UUID4 job_id entropy (122 bits) — inherited from Plan 01 uuid4() job store

## Deferred Items

**Pre-existing test failure (out of scope):**
- `tests/workflow/test_llm.py::TestOpenRouter::test_get_llm_openrouter_default_role_uses_sonnet` — expects "sonnet" or "claude-3.5" model string but gets "moonshotai/kimi-k2.5". Pre-existing workflow test failure unrelated to web layer changes. Not introduced by this plan.

## Self-Check: PASSED

Files exist:
- src/web/streaming.py: FOUND
- src/web/routes/api.py: FOUND (extended)
- tests/web/unit/test_streaming.py: FOUND

Commits exist:
- 7de32b0 (feat: pipeline_sse_generator): FOUND
- c5f3488 (feat: stream endpoint + tests): FOUND

Tests: 18/18 web unit tests passing
