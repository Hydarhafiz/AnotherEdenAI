---
phase: "05-integration-polish-and-portfolio-hardening"
plan: "01"
subsystem: "workflow-output-hardening"
tags: ["alternatives", "pydantic", "sse", "langgraph", "output-format"]
dependency_graph:
  requires: []
  provides:
    - "AlternativesOutput Pydantic model in src.workflow.nodes.format"
    - "WorkflowState.alternatives key"
    - "analyze_node empty-path branch via _generate_alternatives()"
    - "route_after_validate routes retry_count >= 3 to analyze (alternatives path)"
    - "streaming.py latency_ms logging and alternatives template selection"
    - "partials/alternatives.html accordion template"
  affects:
    - "src/workflow/state.py"
    - "src/workflow/nodes/analyze.py"
    - "src/workflow/nodes/format.py"
    - "src/workflow/graph.py"
    - "src/web/streaming.py"
    - "src/web/templates/partials/alternatives.html"
tech_stack:
  added:
    - "AlternativesOutput (Pydantic v2 BaseModel with min/max=3 alternatives list)"
    - "ALTERNATIVES_SYSTEM_PROMPT constant in analyze.py"
    - "_generate_alternatives() helper in analyze.py"
    - "time.monotonic() for SSE pipeline latency measurement"
    - "partials/alternatives.html PicoCSS details/summary accordion"
  patterns:
    - "TDD red-green: failing import test committed before implementation"
    - "Empty db_results path: analyze_node dispatches to _generate_alternatives, format_node validates via AlternativesOutput"
    - "Template selection by final_output key presence (alternatives vs result.html)"
key_files:
  created:
    - "src/web/templates/partials/alternatives.html"
  modified:
    - "src/workflow/state.py"
    - "src/workflow/nodes/analyze.py"
    - "src/workflow/nodes/format.py"
    - "src/workflow/graph.py"
    - "src/web/streaming.py"
    - "tests/workflow/test_format.py"
    - "tests/workflow/test_graph.py"
    - "tests/workflow/test_state.py"
    - "tests/workflow/conftest.py"
decisions:
  - "route_after_validate returns 'analyze' (not 'format') when retry_count >= 3 — analyze_node detects empty db_results and branches to _generate_alternatives"
  - "AlternativesOutput.alternatives field uses Field(min_length=3, max_length=3) — strict 3-alternative contract enforced by Pydantic"
  - "format_node error guard updated to check 'not state.get(alternatives)' — error path only fires when BOTH retry cap exhausted AND no alternatives available"
  - "streaming.py uses is_alternatives = bool(final_output.get('alternatives')) for template routing — zero-cost check on final_output dict"
  - "start_ms placed before astream loop (not inside format node handler) to capture full pipeline latency"
metrics:
  duration: "~7 minutes"
  completed_date: "2026-04-26"
  tasks_completed: 2
  files_modified: 9
  files_created: 1
---

# Phase 05 Plan 01: Output Hardening Summary

**One-liner:** AlternativesOutput Pydantic model + analyze empty-path branch produces 3 alternative teams when db_results is empty, with SSE latency logging and accordion template.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Failing tests for AlternativesOutput | d1f73c7 | tests/workflow/test_format.py |
| 1 (GREEN) | WorkflowState, analyze, format, graph implementation | 97929df | state.py, analyze.py, format.py, graph.py, conftest.py, test_graph.py, test_state.py |
| 2 | SSE latency, template selection, alternatives.html | 75922ae | streaming.py, alternatives.html |

## What Was Built

### WorkflowState extension (OUTPUT-01 to OUTPUT-05)

Added `alternatives: str` key to `WorkflowState` TypedDict. This key is written exclusively by `analyze_node` when `db_results` is empty, containing the raw LLM JSON string with 3 alternative team compositions.

### analyze_node empty-path branch

`analyze_node` now checks `db_results` at the top. If empty, it calls `_generate_alternatives(state)` which invokes the LLM with `ALTERNATIVES_SYSTEM_PROMPT` requesting exactly 3 alternatives. Returns `{"alternatives": response.content}` — format_node parses this.

`ANALYZE_SYSTEM_PROMPT` now includes the `MANDATORY SOURCE ATTRIBUTION (per D-13)` mandate requiring every synergy_explanation to cite `[CharacterName]: [Grasta name] ([trait]) — [effect]`.

### format_node alternatives branch

`AlternativesOutput` Pydantic model validates the alternatives JSON:
- `alternatives: list[TeamOutput] = Field(min_length=3, max_length=3)` — exactly 3 teams
- `reason: str` — explanation of why alternatives were generated

Error-path guard updated: `if retry_count >= 3 and not db_results and not state.get("alternatives")` — error path only fires when retry cap exhausted AND no alternatives were generated.

New alternatives branch between error-path and happy-path:
- Extracts JSON from `state["alternatives"]` via `_extract_json`
- Validates via `AlternativesOutput.model_validate`
- Returns `{"final_output": validated.model_dump()}`

### graph.py routing change

`route_after_validate` now returns `"analyze"` for both branches:
- `db_results` non-empty → `"analyze"` (success path, unchanged)
- `retry_count >= 3` → `"analyze"` (alternatives path, was "format")

`Literal` type updated to `["generate_cypher", "analyze"]`. Conditional edges list updated to remove `"format"` as a direct route from validate.

### streaming.py (OUTPUT-05)

- `import time` added
- `start_ms = time.monotonic()` captured before `graph.astream()` call
- After FORMAT node: `elapsed_ms = int((time.monotonic() - start_ms) * 1000)` + `logger.info("latency_ms: %d", elapsed_ms)`
- `"alternatives": ""` added to `initial_state`
- Finally block: `is_alternatives = bool(final_output.get("alternatives"))` selects `alternatives.html` or `result.html`

### partials/alternatives.html

New accordion template using PicoCSS `<details>/<summary>`:
- First card has `open` attribute (expanded by default, per D-03)
- Renders `frontline` and `reserve` character grids with `char-card` CSS classes
- Shows `synergy_explanation` in `synergy-box` div
- Shows `reason` text from AlternativesOutput
- Falls through to `error.html` include if `result.error` is set

## Test Results

```
31 passed  — tests/workflow/test_format.py (26 existing + 5 new TestFormatAlternativesPath)
148 passed — full unit suite (-m 'not integration', excluding pre-existing test_llm failures)
```

New tests in `TestFormatAlternativesPath`:
1. `test_format_alternatives_returns_only_final_output`
2. `test_format_alternatives_has_alternatives_key`
3. `test_format_alternatives_has_exactly_three`
4. `test_format_alternatives_validates_with_pydantic`
5. `test_format_alternatives_no_error`

Updated existing tests:
- `test_graph.py::TestRouteAfterValidate::test_route_after_validate_cap` — now asserts `"analyze"`
- `test_graph.py::TestRouteAfterValidate::test_route_after_validate_cap_above_three` — now asserts `"analyze"`
- `test_graph.py::TestGraphHappyPath::test_retry_cap_exhausted_*` — renamed and updated to assert alternatives output (3 teams, no error)
- `test_state.py` — `EXPECTED_KEYS` updated to 10 keys including `"alternatives"`
- `conftest.py` — `sample_state` gains `"alternatives": ""`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated existing tests broken by routing and state changes**

- **Found during:** GREEN phase (Task 1)
- **Issue:** `test_graph.py` had assertions expecting `route_after_validate` returns `"format"` for retry cap — now returns `"analyze"`. `test_state.py` `EXPECTED_KEYS` was missing `"alternatives"`. `test_state.py` `test_stub_nodes_return_only_owned_keys` called `analyze_node(sample_state)` with empty `db_results`, getting `{"alternatives": ...}` instead of `{"analysis_result": ...}`.
- **Fix:** Updated routing test assertions, added `"alternatives"` to `EXPECTED_KEYS`, added `analyze_state` with non-empty `db_results` in the owned-keys test, added `"alternatives": ""` to `conftest.py sample_state`.
- **Files modified:** tests/workflow/test_graph.py, tests/workflow/test_state.py, tests/workflow/conftest.py
- **Commit:** 97929df

### Out-of-Scope Deferred Items

**Pre-existing test_llm.py failures (unrelated to this plan):**
- `TestOpenRouter::test_get_llm_openrouter_default_role_uses_sonnet` — `_OR_SONNET` in llm.py is `moonshotai/kimi-k2.5`, test expects `"sonnet"` substring
- `TestOpenRouter::test_get_llm_openrouter_validator_role_uses_haiku` — `_OR_HAIKU` is also `moonshotai/kimi-k2.5`, test expects `"haiku"` substring

These failures existed before this plan (confirmed via `git stash` verification). Logged as out-of-scope — to be addressed by the team separately.

## Requirements Closed

- OUTPUT-01: 4-frontline/2-reserve validation enforced by TeamOutput Field constraints
- OUTPUT-02: Mandatory Grasta+trait attribution in ANALYZE_SYSTEM_PROMPT (D-13)
- OUTPUT-03: Per-character role annotations required by prompt rules and CharacterSlot.role field
- OUTPUT-04: Top-3 alternatives for empty db_results via AlternativesOutput + _generate_alternatives
- OUTPUT-05: Latency measurement via time.monotonic() in SSE layer

## Self-Check: PASSED

Files exist:
- src/workflow/state.py: alternatives key present
- src/workflow/nodes/analyze.py: ALTERNATIVES_SYSTEM_PROMPT, _generate_alternatives present
- src/workflow/nodes/format.py: AlternativesOutput present
- src/workflow/graph.py: route_after_validate returns "analyze" twice
- src/web/streaming.py: latency_ms, alternatives.html, initial_state alternatives key all present
- src/web/templates/partials/alternatives.html: accordion template exists

Commits exist:
- d1f73c7 (RED phase tests)
- 97929df (GREEN phase implementation)
- 75922ae (Task 2 SSE + template)
