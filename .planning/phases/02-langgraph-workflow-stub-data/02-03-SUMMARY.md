---
phase: 02-langgraph-workflow-stub-data
plan: "03"
subsystem: workflow/validate
tags: [validate, hybrid-gate, semantic-gate, haiku, retry, tdd]
dependency_graph:
  requires: ["02-02"]
  provides: ["02-04"]
  affects: ["src/workflow/nodes/validate.py", "tests/workflow/test_validate.py", "tests/workflow/test_graph.py", "tests/workflow/test_state.py"]
tech_stack:
  added: []
  patterns:
    - "Two-step hybrid validation gate: deterministic driver execution + Haiku 4.6 semantic check"
    - "Locked error message format: Attempt {N}: Query failed due to [Exception|Empty Result|Semantic Mismatch]. Context: [detail]"
    - "PASS:/FAIL: prefix protocol for Haiku semantic gate responses"
    - "Early return after Step 1 failure (Step 2 never called on driver errors)"
key_files:
  created: []
  modified:
    - "src/workflow/nodes/validate.py"
    - "tests/workflow/test_validate.py"
    - "tests/workflow/test_graph.py"
    - "tests/workflow/test_state.py"
decisions:
  - "RETRY_CAP=3 constant defined in validate.py — hard cap enforced at generation routing, not at validation"
  - "Haiku called only when Step 1 passes — empty result/exception skips semantic gate entirely"
  - "Success path returns only {'db_results': [...]} — no retry_count or validation_errors keys on success (AGENT-07)"
  - "test_state.py updated to use mock driver + mock validate LLM since null-driver shortcut removed in real implementation"
metrics:
  duration: "~15 minutes"
  completed_date: "2026-03-15"
  tasks_completed: 2
  files_modified: 4
---

# Phase 02 Plan 03: VALIDATE Node Two-Step Hybrid Gate Summary

**One-liner:** VALIDATE node with deterministic driver execution gate and Haiku 4.6 semantic correctness gate, supporting three failure modes with locked error message format.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | VALIDATE node hybrid gate implementation and unit tests (TDD) | a6fea44 | src/workflow/nodes/validate.py, tests/workflow/test_validate.py |
| 2 | Update graph routing tests for real validate logic with hybrid gate | 396f176 | tests/workflow/test_graph.py, tests/workflow/test_state.py |

## What Was Built

### validate.py — Two-Step Hybrid Gate

**Step 1 (Deterministic):** Executes `driver.execute_query(cypher, database_="neo4j")`.
- Exception path: formats `"Attempt {N}: Query failed due to Exception. Context: {ExcType}: {msg}"`, increments retry_count, returns immediately (skips Step 2).
- Empty result path: formats `"Attempt {N}: Query failed due to Empty Result. Context: Query returned no records..."`, increments retry_count, returns immediately (skips Step 2).

**Step 2 (Haiku 4.6 Semantic Gate):** Called only when Step 1 returns non-empty records.
- Calls `get_llm(role="validator")` to get Haiku 4.6.
- Passes SystemMessage with `SEMANTIC_GATE_SYSTEM_PROMPT` + HumanMessage with user_query and db_results JSON.
- Parses response: `PASS:` prefix → returns `{"db_results": [...]}` only.
- `FAIL:` prefix → formats `"Attempt {N}: Query failed due to Semantic Mismatch. Context: {haiku_explanation}"`, increments retry_count.

**Success path:** Returns `{"db_results": [dict(r) for r in records]}` — exactly one key (AGENT-07 contract).

### Test Coverage

**test_validate.py** — 20 unit tests:
- 5 tests for Step 1 exception mode
- 4 tests for Step 1 empty result mode
- 1 test for general failure assertions
- 10 tests for Step 2 semantic gate (pass, fail, format, role, retry increment)

**test_graph.py** — 4 integration tests updated + 5 router unit tests unchanged:
- `test_full_graph_happy_path`: patches all 3 LLM modules including validate
- `test_single_retry_routes_back_to_generate_cypher`: empty result on attempt 1, success on attempt 2
- `test_retry_cap_exhausted_routes_to_format_error`: verify Haiku never called, driver called exactly 3 times
- `test_semantic_fail_triggers_retry`: Haiku FAIL on attempt 1, PASS on attempt 2 — confirms semantic failures route through same retry loop as driver failures

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] test_state.py used null driver shortcut removed in real validate.py**
- **Found during:** Task 2, running `pytest tests/workflow/`
- **Issue:** `test_stub_nodes_return_only_owned_keys` passed `mock_driver = None` to `validate_node`. The stub validate.py had a `if driver is None: return {"db_results": [...]}` shortcut. The real implementation has no such shortcut — None driver causes AttributeError caught as Exception, returning failure keys instead of `{"db_results": ...}`.
- **Fix:** Updated `test_state.py` to use `MagicMock()` driver returning `([{"name": "Aldo"}], None, None)` and patched `src.workflow.nodes.validate.get_llm` to return PASS response, exercising the success code path.
- **Files modified:** tests/workflow/test_state.py
- **Commit:** 396f176

## Verification Results

```
pytest tests/workflow/ -x --tb=short
50 passed in 0.15s
```

All 50 workflow tests pass:
- test_validate.py: 20/20
- test_graph.py: 9/9
- test_state.py: 3/3
- test_plan.py: 6/6
- test_cypher.py: 10/10
- test_analyze.py: 1/1
- test_format.py: 1/1

## Self-Check: PASSED

- src/workflow/nodes/validate.py: FOUND
- tests/workflow/test_validate.py: FOUND
- tests/workflow/test_graph.py: FOUND
- Commit a6fea44: FOUND
- Commit 396f176: FOUND
