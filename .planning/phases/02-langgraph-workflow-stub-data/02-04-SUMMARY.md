---
phase: 02-langgraph-workflow-stub-data
plan: "04"
subsystem: workflow
tags: [langgraph, langchain, anthropic, sonnet, pydantic, tdd]

# Dependency graph
requires:
  - phase: 02-03
    provides: VALIDATE node with hybrid gate (Haiku semantic check), retry routing via route_after_validate

provides:
  - ANALYZE node: calls get_llm(role="analyzer") (Sonnet 4.6), reads db_results/user_query/roster/plan_strategy, returns analysis_result string
  - FORMAT node: parses analysis_result JSON, validates with Pydantic v2 TeamOutput model, returns final_output dict
  - TeamOutput/CharacterSlot Pydantic models (format.py) — web layer output schema
  - Error path FORMAT: retry_count>=3 + no db_results produces {frontline:[], reserve:[], synergy_explanation:"", error:str}
  - End-to-end graph tests: happy path, single retry, cap-exhausted, semantic fail, no-live-calls smoke test
  - Complete 5-node pipeline tested end-to-end with mocked LLM and Neo4j

affects: [phase-03-real-graph, phase-04-web-layer, phase-05-deployment]

# Tech tracking
tech-stack:
  added: [pydantic v2 (BaseModel, model_validate, model_dump), json stdlib, re stdlib]
  patterns:
    - TDD red-green cycle for LLM nodes (patch get_llm, assert on AIMessage.content)
    - Pydantic v2 model_validate for structured output validation at FORMAT boundary
    - JSON extraction with fallback regex for LLM markdown fence handling
    - Error path same-schema pattern (error key in TeamOutput) for web layer compatibility
    - Separate get_llm patches per node module (not shared) for precise mock control

key-files:
  created:
    - tests/workflow/test_analyze.py
    - tests/workflow/test_format.py
  modified:
    - src/workflow/nodes/analyze.py
    - src/workflow/nodes/format.py
    - tests/workflow/test_graph.py
    - tests/workflow/test_state.py

key-decisions:
  - "TeamOutput/CharacterSlot Pydantic v2 models live in format.py — FORMAT is the output boundary; web layer imports from there"
  - "FORMAT is LLM-free (pure Python) — deterministic, easily testable, no mocking needed for unit tests"
  - "JSON extraction uses 3-step fallback: direct parse -> markdown fence regex -> outermost brace regex"
  - "Error path FORMAT produces same schema keys as success path — error=None on success, error=str on cap exhaustion — for web layer compatibility"
  - "analyze_node uses role='analyzer' (maps to Sonnet 4.6 in get_llm) — not role='default'"

patterns-established:
  - "Pattern: All node return dicts have exactly one key — AGENT-07 contract enforced by unit test"
  - "Pattern: get_llm always patched at node-module level (src.workflow.nodes.X.get_llm) not at llm module level"
  - "Pattern: test_state.py test_stub_nodes_return_only_owned_keys patches all LLM nodes and provides valid state per node"

requirements-completed: [AGENT-06, AGENT-07]

# Metrics
duration: 4min
completed: 2026-03-15
---

# Phase 2 Plan 04: ANALYZE and FORMAT Nodes Summary

**Sonnet 4.6 ANALYZE node and Pydantic v2 FORMAT node completing the 5-node pipeline, with end-to-end graph tests covering all routing paths using fully mocked LLM and Neo4j**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-03-15T05:21:44Z
- **Completed:** 2026-03-15T05:25:10Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- ANALYZE node reads db_results/user_query/roster/plan_strategy and calls Sonnet 4.6 (role="analyzer") to produce JSON team recommendation
- FORMAT node parses analysis_result JSON and validates with Pydantic v2 TeamOutput/CharacterSlot models — no LLM required, fully deterministic
- Error path produces same schema (error key in TeamOutput) for web layer compatibility
- End-to-end graph tests: happy path asserts Aldo/Ciel in output, single retry, cap-exhausted, semantic fail, no-live-calls smoke test
- 89/89 tests pass across all suites, no regressions

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: ANALYZE and FORMAT unit tests** - `44215dd` (test)
2. **Task 1 GREEN: Implement ANALYZE and FORMAT nodes** - `9459f18` (feat)
3. **Task 2: End-to-end graph tests with all real nodes** - `ac0c5d0` (feat)

_Note: TDD task has RED commit (test) and GREEN commit (feat) as separate atomic commits._

## Files Created/Modified

- `src/workflow/nodes/analyze.py` - ANALYZE node: Sonnet 4.6 team synthesis from db_results, returns analysis_result string
- `src/workflow/nodes/format.py` - FORMAT node: TeamOutput/CharacterSlot Pydantic v2 models, JSON extraction with fallback regex, error path
- `tests/workflow/test_analyze.py` - 7 unit tests: return key contract, LLM prompt content (db_results/user_query/roster/plan_strategy), role="analyzer", result content
- `tests/workflow/test_format.py` - 18 unit tests: success path (6), error path (6), TeamOutput model (3), edge cases (3)
- `tests/workflow/test_graph.py` - 10 tests: updated 4 existing + added test_full_pipeline_no_live_calls; all assert on real ANALYZE output structure
- `tests/workflow/test_state.py` - Fixed test_stub_nodes_return_only_owned_keys: added analyze mock, valid analysis_result for format_node

## Decisions Made

- `TeamOutput/CharacterSlot` Pydantic v2 models live in `format.py` — FORMAT is the output boundary; Phase 4 web layer imports from there
- `FORMAT` is LLM-free (pure Python) — deterministic and easily testable without mocking; ANALYZE produces the text, FORMAT structures it
- JSON extraction uses 3-step fallback: direct parse -> markdown fence regex -> outermost brace regex — handles LLM preamble gracefully
- Error path produces same schema keys as success path (`error=None` on success, `error=str` on cap exhaustion) — web layer reads `final_output` uniformly

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test_state.py test_stub_nodes_return_only_owned_keys calling analyze_node without get_llm mock**
- **Found during:** Task 2 (end-to-end tests)
- **Issue:** test_stub_nodes_return_only_owned_keys called `analyze_node(sample_state)` inside a `with patch(...)` block that didn't patch `src.workflow.nodes.analyze.get_llm`. Since analyze_node is now a real LLM node, this triggered a live Anthropic API call and failed with auth error.
- **Fix:** Added `patch("src.workflow.nodes.analyze.get_llm", return_value=mock_analyze_llm)` to the context manager. Also provided `format_state` with valid `analysis_result` JSON for format_node to parse (sample_state has empty analysis_result which would fail JSON parse).
- **Files modified:** tests/workflow/test_state.py
- **Verification:** All 89 tests pass including the fixed test
- **Committed in:** `ac0c5d0` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug)
**Impact on plan:** Necessary fix for correctness — prior test relied on stub behavior; real LLM node requires mock. No scope creep.

## Issues Encountered

None beyond the auto-fixed test_state.py issue above.

## User Setup Required

None - no external service configuration required. All tests use mocked LLM and Neo4j.

## Next Phase Readiness

- Phase 2 is complete: all 5 nodes implemented (PLAN, GENERATE_CYPHER, VALIDATE, ANALYZE, FORMAT), 89 tests pass
- FORMAT output schema (TeamOutput dict) is the contract for Phase 4 web layer
- Phase 3 (Real Graph) can now build on the complete pipeline — replace stub ETL data with production Neo4j data
- No blockers

---
*Phase: 02-langgraph-workflow-stub-data*
*Completed: 2026-03-15*
