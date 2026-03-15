---
phase: 02-langgraph-workflow-stub-data
plan: 02
subsystem: workflow
tags: [langgraph, langchain-anthropic, llm-nodes, tdd, few-shot, schema-injection]

# Dependency graph
requires:
  - phase: 02-01
    provides: WorkflowState TypedDict, stub node skeletons, get_llm factory, Wave 0 test fixtures

provides:
  - PLAN node with get_llm(role='planner'), PLAN_SYSTEM_PROMPT, SystemMessage + HumanMessage construction
  - GENERATE_CYPHER node with hardcoded SCHEMA_CONTEXT, FEW_SHOT_EXAMPLES, constraint notes, markdown fence stripping
  - validation_errors injected into HumanMessage on retry so LLM self-corrects
  - 16 unit tests (6 plan + 10 cypher) — all mocked, zero live API calls

affects:
  - 02-03 (VALIDATE node — graph topology unchanged, GENERATE_CYPHER now produces real Cypher)
  - 02-04 (ANALYZE + FORMAT nodes — plan_strategy and cypher_query now real LLM outputs)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Patch-at-module-level: patch("src.workflow.nodes.plan.get_llm") not ChatAnthropic — correct for factory pattern
    - Schema hardcoded as module constant (not file read) — stable contract, avoids runtime file dependency
    - Markdown fence stripping via re.sub for both ```cypher and ``` patterns

key-files:
  created: []
  modified:
    - src/workflow/nodes/plan.py (stub replaced with full LLM implementation)
    - src/workflow/nodes/cypher.py (stub replaced with schema injection + few-shot + fence stripping)
    - tests/workflow/test_plan.py (6 unit tests replacing placeholder)
    - tests/workflow/test_cypher.py (10 unit tests replacing placeholder)
    - tests/workflow/test_graph.py (patched get_llm in 3 graph integration tests)
    - tests/workflow/test_state.py (patched get_llm in owned-key test)

key-decisions:
  - "Schema hardcoded as SCHEMA_CONTEXT string constant in cypher.py — not read from file at runtime; it is a stable Phase 1 contract and avoids file path dependencies in production"
  - "Graph integration tests (test_graph.py) and owned-key test (test_state.py) require get_llm patches — real nodes now call LLM, so graph-level tests must mock to stay unit-scoped"
  - "validation_errors appended to HumanMessage (not SystemMessage) — it is query-specific context, not stable schema"

# Metrics
duration: 3min
completed: 2026-03-15
---

# Phase 2 Plan 02: PLAN and GENERATE_CYPHER Nodes Summary

**PLAN node (get_llm planner role, SystemMessage strategy decomposition) and GENERATE_CYPHER node (hardcoded schema, 4 few-shot examples, validation_errors on retry, markdown fence stripping) — 30 workflow tests pass**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-15T05:12:14Z
- **Completed:** 2026-03-15T05:15:18Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Replaced plan_node stub with full LLM implementation: get_llm(role='planner'), PLAN_SYSTEM_PROMPT constant, constructs [SystemMessage, HumanMessage] with user_query and roster, returns {"plan_strategy": response.content}
- Replaced generate_cypher_node stub with full implementation: SCHEMA_CONTEXT (all node labels + properties + relationships), FEW_SHOT_EXAMPLES (4 annotated Cypher examples + constraints), CYPHER_SYSTEM_PROMPT combining both, validation_errors appended to HumanMessage on retry, _strip_markdown_fences() via regex, returns {"cypher_query": cleaned}
- 16 new unit tests (6 plan, 10 cypher) covering: key ownership, LLM role, query/roster in message, SystemMessage presence, schema injection, few-shot presence, constraints, plan_strategy in prompt, validation_errors on retry, markdown fence stripping for both ```cypher and ``` variants
- Fixed test_graph.py and test_state.py to patch get_llm so graph-level integration tests remain unit-scoped

## Task Commits

Each task was committed atomically:

1. **Task 1: PLAN node implementation with unit tests** - `cbc9554` (feat)
2. **Task 2: GENERATE_CYPHER node with schema injection, few-shot examples, and unit tests** - `1faa2aa` (feat)

## Files Created/Modified

- `src/workflow/nodes/plan.py` - PLAN_SYSTEM_PROMPT, get_llm(role='planner'), message construction, owned-key return
- `src/workflow/nodes/cypher.py` - SCHEMA_CONTEXT, FEW_SHOT_EXAMPLES, CYPHER_SYSTEM_PROMPT, _strip_markdown_fences, get_llm(role='cypher'), validation_errors retry injection
- `tests/workflow/test_plan.py` - 6 unit tests replacing placeholder
- `tests/workflow/test_cypher.py` - 10 unit tests replacing placeholder
- `tests/workflow/test_graph.py` - patched get_llm in 3 graph integration test methods
- `tests/workflow/test_state.py` - patched get_llm in owned-key isolation test

## Decisions Made

- Schema hardcoded as SCHEMA_CONTEXT string constant in cypher.py — not read from file at runtime; stable Phase 1 contract, avoids runtime file path dependency
- Graph integration tests require get_llm patches since plan_node and generate_cypher_node are now real LLM nodes — test_graph.py and test_state.py updated
- validation_errors appended to HumanMessage content (not SystemMessage) — it is query-specific retry context, not stable schema

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] test_graph.py: graph integration tests call real LLM after node implementation**
- **Found during:** Task 2 verification (full workflow suite)
- **Issue:** `TestGraphHappyPath` tests invoke `graph.invoke(sample_state)` which now executes real `plan_node` calling Anthropic API — fails with auth error in test environment
- **Fix:** Added `_mock_llm_factory()` helper and wrapped all 3 `TestGraphHappyPath` test methods with `patch("src.workflow.nodes.plan.get_llm")` and `patch("src.workflow.nodes.cypher.get_llm")`
- **Files modified:** tests/workflow/test_graph.py
- **Committed in:** 1faa2aa (Task 2 commit)

**2. [Rule 1 - Bug] test_state.py: owned-key isolation test calls real LLM after node implementation**
- **Found during:** Task 2 verification (full workflow suite)
- **Issue:** `test_stub_nodes_return_only_owned_keys` directly calls `plan_node(sample_state)` and `generate_cypher_node(sample_state)` without mocking — now fails with Anthropic auth error
- **Fix:** Added mock_llm setup and wrapped node calls in `patch("src.workflow.nodes.plan.get_llm")` + `patch("src.workflow.nodes.cypher.get_llm")` context manager
- **Files modified:** tests/workflow/test_state.py
- **Committed in:** 1faa2aa (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 — tests designed for stub nodes now call real LLM implementations)
**Impact:** Both fixes necessary; no architectural changes, no new state keys, no new dependencies.

## Issues Encountered

None beyond the two auto-fixed test compatibility issues above.

## Next Phase Readiness

- PLAN node and GENERATE_CYPHER node are production-ready (mocked in tests, LLM-backed in production)
- All 30 workflow tests pass — graph topology unchanged
- Plan 02-03 (VALIDATE node) can proceed — GENERATE_CYPHER now produces real Cypher queries
- Plan 02-04 (ANALYZE + FORMAT nodes) can proceed — plan_strategy and cypher_query are real LLM outputs

## Self-Check: PASSED

| Item | Status |
|------|--------|
| src/workflow/nodes/plan.py | FOUND |
| src/workflow/nodes/cypher.py | FOUND |
| tests/workflow/test_plan.py | FOUND |
| tests/workflow/test_cypher.py | FOUND |
| .planning/phases/02-langgraph-workflow-stub-data/02-02-SUMMARY.md | FOUND |
| Commit cbc9554 | FOUND |
| Commit 1faa2aa | FOUND |

---
*Phase: 02-langgraph-workflow-stub-data*
*Completed: 2026-03-15*
