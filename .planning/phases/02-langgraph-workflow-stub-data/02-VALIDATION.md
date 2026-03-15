---
phase: 2
slug: langgraph-workflow-stub-data
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-15
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 + pytest-asyncio 1.3.0 |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `pytest tests/workflow/ -x --tb=short` |
| **Full suite command** | `pytest --tb=short` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/workflow/ -x --tb=short`
- **After every plan wave:** Run `pytest --tb=short`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 2-01-01 | 01 | 1 | AGENT-07 | unit | `pytest tests/workflow/test_state.py -x` | ❌ Wave 0 | ⬜ pending |
| 2-01-02 | 01 | 1 | AGENT-04, AGENT-05 | unit | `pytest tests/workflow/test_graph.py -x` | ❌ Wave 0 | ⬜ pending |
| 2-02-01 | 02 | 2 | AGENT-01 | unit | `pytest tests/workflow/test_plan.py -x` | ❌ Wave 0 | ⬜ pending |
| 2-02-02 | 02 | 2 | AGENT-02 | unit | `pytest tests/workflow/test_cypher.py -x` | ❌ Wave 0 | ⬜ pending |
| 2-03-01 | 03 | 3 | AGENT-03 | unit | `pytest tests/workflow/test_validate.py -x` | ❌ Wave 0 | ⬜ pending |
| 2-03-02 | 03 | 3 | AGENT-04, AGENT-05 | unit | `pytest tests/workflow/test_graph.py::test_single_retry tests/workflow/test_graph.py::test_retry_cap -x` | ❌ Wave 0 | ⬜ pending |
| 2-04-01 | 04 | 4 | AGENT-06 | unit | `pytest tests/workflow/test_analyze.py tests/workflow/test_format.py -x` | ❌ Wave 0 | ⬜ pending |
| 2-04-02 | 04 | 4 | AGENT-01–07 | unit | `pytest tests/workflow/ --tb=short` | ❌ Wave 0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/workflow/__init__.py` — package marker
- [ ] `tests/workflow/conftest.py` — `stub_driver`, `mock_llm` fixtures
- [ ] `tests/workflow/test_state.py` — covers AGENT-07 (reducer behavior, key ownership)
- [ ] `tests/workflow/test_graph.py` — covers AGENT-04, AGENT-05 (routing, retry cap)
- [ ] `tests/workflow/test_plan.py` — covers AGENT-01
- [ ] `tests/workflow/test_cypher.py` — covers AGENT-02
- [ ] `tests/workflow/test_validate.py` — covers AGENT-03
- [ ] `tests/workflow/test_analyze.py` — covers AGENT-06 (analyze side)
- [ ] `tests/workflow/test_format.py` — covers AGENT-06 (format side)
- [ ] `src/workflow/__init__.py` — package marker
- [ ] `src/workflow/nodes/__init__.py` — package marker
- [ ] Add `langchain-anthropic` to `pyproject.toml` dependencies

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
