---
phase: 4
slug: fastapi-htmx-web-layer
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-19
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio 0.23+ |
| **Config file** | `pytest.ini` (already configured: `asyncio_mode=auto`, `asyncio_default_fixture_loop_scope=session`) |
| **Quick run command** | `pytest tests/web/ -x -q` |
| **Full suite command** | `pytest tests/ -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/web/unit/ -x -q`
- **After every plan wave:** Run `pytest tests/ -x -q --ignore=tests/integration`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 4-01-01 | 01 | 1 | WEB-04 | — | Driver singleton not recreated per request | unit | `pytest tests/web/unit/test_app.py::test_lifespan_creates_driver -x` | ❌ W0 | ⬜ pending |
| 4-01-02 | 01 | 1 | WEB-01 | — | GET / returns 200 HTML | unit | `pytest tests/web/unit/test_pages.py::test_index_returns_html -x` | ❌ W0 | ⬜ pending |
| 4-01-03 | 01 | 1 | WEB-02 | — | GET /api/entities returns chars + grastas JSON | unit | `pytest tests/web/unit/test_api.py::test_get_entities -x` | ❌ W0 | ⬜ pending |
| 4-01-04 | 01 | 1 | WEB-05 | — | X-Admin-Key header enforced (wrong key → 403) | unit | `pytest tests/web/unit/test_admin.py -x` | ❌ W0 | ⬜ pending |
| 4-02-01 | 02 | 1 | WEB-02 | — | POST /api/query returns HTML fragment with sse-connect URL | unit | `pytest tests/web/unit/test_api.py::test_post_query_returns_sse_fragment -x` | ❌ W0 | ⬜ pending |
| 4-02-02 | 02 | 1 | WEB-03 | — | SSE stream emits node_status events then result event | unit | `pytest tests/web/unit/test_streaming.py::test_sse_events_sequence -x` | ❌ W0 | ⬜ pending |
| 4-02-03 | 02 | 1 | WEB-03 | — | Final SSE event contains rendered Jinja2 HTML fragment | unit | `pytest tests/web/unit/test_streaming.py::test_final_sse_event_is_html -x` | ❌ W0 | ⬜ pending |
| 4-03-01 | 03 | 2 | WEB-01 | — | Browser smoke test: UI renders without JS errors | manual | Browser DevTools → Console → zero errors | N/A | ⬜ pending |
| 4-03-02 | 03 | 2 | WEB-03 | — | SSE retry counter visible in UI ("Validating... attempt 2/3") | manual | Submit query that triggers VALIDATE retry; confirm text in progress div | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/web/__init__.py` — package init
- [ ] `tests/web/unit/__init__.py` — unit subpackage init
- [ ] `tests/web/unit/test_app.py` — stubs for WEB-04 (lifespan driver singleton)
- [ ] `tests/web/unit/test_pages.py` — stubs for WEB-01 (GET / returns HTML)
- [ ] `tests/web/unit/test_api.py` — stubs for WEB-02 (entities + query endpoints)
- [ ] `tests/web/unit/test_streaming.py` — stubs for WEB-03 (SSE event sequence + HTML fragment)
- [ ] `tests/web/unit/test_admin.py` — stubs for WEB-05 (admin key auth: valid/invalid/missing)
- [ ] `tests/web/conftest.py` — shared fixtures (TestClient, mock driver, mock templates)

---

## SSE Test Architecture Note

Testing SSE streams requires iterating the async generator directly — `TestClient` does not stream SSE. Use direct generator test pattern:

```python
async def test_sse_events_sequence():
    async def mock_astream(*args, **kwargs):
        yield {"type": "updates", "data": {"plan": {"plan_strategy": "test"}}}
        yield {"type": "updates", "data": {"validate": {"db_results": [{}]}}}
        yield {"type": "updates", "data": {"format": {"final_output": {...}}}}

    with patch("src.web.streaming.build_graph", return_value=mock_graph):
        events = [e async for e in pipeline_sse_generator(...)]
    assert events[-2].event == "result"
    assert events[-1].event == "done"
```

For POST→SSE integration flow, use `httpx.AsyncClient` with `ASGITransport`.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Browser renders roster checklist with character + Grasta tabs | WEB-02 | Requires real browser rendering | Open `http://localhost:8000`, verify two tabs render, check/uncheck items, refresh page, confirm localStorage persistence |
| SSE progress updates visible during pipeline execution | WEB-03 | Requires end-to-end live run | Submit query with known roster; verify PLAN → CYPHER → VALIDATE → ANALYZE text appears in sequence in progress div |
| VALIDATE retry shows "attempt 2/3" in UI | WEB-03 | Requires retry-triggering query | Force a VALIDATE retry; confirm progress div shows retry text |
| Result card renders 4-frontline / 2-reserve grid | WEB-01 | Visual layout check | Submit valid query; verify 4 cards in top row, 2 in second row, synergy text below |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
