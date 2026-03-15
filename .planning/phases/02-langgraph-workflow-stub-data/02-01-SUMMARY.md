---
phase: 02-langgraph-workflow-stub-data
plan: 01
subsystem: workflow
tags: [langgraph, langchain-anthropic, langchain-ollama, stategraph, typeddict, pytest]

# Dependency graph
requires:
  - phase: 01-graph-foundation
    provides: Neo4j schema (Character, Grasta, Ore, Trait nodes) and ETL pipeline

provides:
  - WorkflowState TypedDict with 9 keys and operator.add reducer on validation_errors
  - Compilable LangGraph StateGraph with 5 stub nodes and conditional 3-way routing from validate
  - get_llm(role) factory in src/workflow/llm.py with LLM_PROVIDER env toggle
  - Wave 0 test fixtures (stub_driver, mock_llm, sample_state) in tests/workflow/conftest.py
  - Graph routing tests: happy path, single retry, retry cap at 3

affects:
  - 02-02 (PLAN + GENERATE_CYPHER LLM nodes — wire against WorkflowState and graph topology)
  - 02-03 (VALIDATE node — real driver integration against graph topology)
  - 02-04 (ANALYZE + FORMAT LLM nodes — wire against WorkflowState)

# Tech tracking
tech-stack:
  added:
    - langchain-anthropic>=0.3 (ChatAnthropic, Claude Sonnet/Haiku)
    - langchain-ollama>=0.2 (ChatOllama for local dev)
    - langgraph>=1.0 (StateGraph, conditional edges)
  patterns:
    - LLM_PROVIDER env toggle — all nodes call get_llm(role=...) never import ChatAnthropic directly
    - Driver injection via closure — build_graph(driver) wraps validate_node with lambda
    - Annotated[list[str], operator.add] reducer pattern for accumulating validation errors
    - Stub-first node design — each stub returns exactly its owned keys, testable in isolation

key-files:
  created:
    - src/workflow/__init__.py
    - src/workflow/state.py
    - src/workflow/graph.py
    - src/workflow/llm.py
    - src/workflow/nodes/__init__.py
    - src/workflow/nodes/plan.py
    - src/workflow/nodes/cypher.py
    - src/workflow/nodes/validate.py
    - src/workflow/nodes/analyze.py
    - src/workflow/nodes/format.py
    - tests/workflow/__init__.py
    - tests/workflow/conftest.py
    - tests/workflow/test_state.py
    - tests/workflow/test_graph.py
    - tests/workflow/test_plan.py
    - tests/workflow/test_cypher.py
    - tests/workflow/test_validate.py
    - tests/workflow/test_analyze.py
    - tests/workflow/test_format.py
  modified:
    - pyproject.toml (added 3 new dependencies)
    - .env.example (added LLM_PROVIDER, OLLAMA_MODEL, ANTHROPIC_API_KEY documentation)

key-decisions:
  - "validate stub calls driver.execute_query() to enable routing tests — stub behavior depends on driver return value, not hardcoded"
  - "format stub checks retry_count >= 3 and empty db_results to return error key — needed for retry cap graph test"
  - "analysis_result intermediate key in WorkflowState resolves ANALYZE->FORMAT ambiguity — ANALYZE writes text, FORMAT reads it and produces structured dict"
  - "LLM_PROVIDER env toggle centralised in get_llm(role) — validator role uses cheaper Haiku, all others use Sonnet"

patterns-established:
  - "Owned-key isolation: each node function returns only the keys it owns — verified by test_stub_nodes_return_only_owned_keys"
  - "Closure injection for driver: build_graph(driver) uses lambda s: validate_node(s, driver) — keeps node signature testable"
  - "Wave 0 scaffolds: placeholder test files created for all nodes at plan 02-01, populated by later plans"

requirements-completed: [AGENT-04, AGENT-05, AGENT-07, AGENT-08]

# Metrics
duration: 11min
completed: 2026-03-15
---

# Phase 2 Plan 01: WorkflowState + LangGraph Skeleton Summary

**LangGraph StateGraph with 5 stub nodes, 3-way conditional routing, WorkflowState TypedDict, LLM_PROVIDER factory, and Wave 0 test fixtures — 31 tests pass**

## Performance

- **Duration:** 11 min
- **Started:** 2026-03-15T05:06:13Z
- **Completed:** 2026-03-15T05:17:00Z
- **Tasks:** 2
- **Files modified:** 21 (19 created, 2 modified)

## Accomplishments

- WorkflowState TypedDict with 9 keys; validation_errors uses Annotated[list[str], operator.add] reducer
- Compilable StateGraph with 5 stub nodes and conditional 3-way routing from validate (success/retry/cap)
- get_llm(role) factory with LLM_PROVIDER toggle — anthropic (Sonnet/Haiku by role) or ollama
- Wave 0 test infrastructure: 16 workflow tests pass (state contract, graph routing, node existence stubs)

## Task Commits

Each task was committed atomically:

1. **Task 1: Install langchain-anthropic and create WorkflowState + stub nodes** - `2103f3a` (feat)
2. **Task 2: Wave 0 test infrastructure** - `fc549bc` (feat)

## Files Created/Modified

- `src/workflow/state.py` - WorkflowState TypedDict with 9 keys and operator.add reducer
- `src/workflow/graph.py` - StateGraph with 5 nodes, route_after_validate, build_graph(driver), compiled_graph
- `src/workflow/llm.py` - get_llm(role) factory with LLM_PROVIDER env var toggle
- `src/workflow/nodes/plan.py` - plan_node stub returning {"plan_strategy": "stub"}
- `src/workflow/nodes/cypher.py` - generate_cypher_node stub returning Cypher placeholder
- `src/workflow/nodes/validate.py` - validate_node stub calling driver.execute_query() with retry logic
- `src/workflow/nodes/analyze.py` - analyze_node stub returning {"analysis_result": "stub analysis"}
- `src/workflow/nodes/format.py` - format_node stub with error path for retry cap exhaustion
- `tests/workflow/conftest.py` - stub_driver, mock_llm, sample_state fixtures
- `tests/workflow/test_state.py` - 9-key check, operator.add reducer, owned-key assertions
- `tests/workflow/test_graph.py` - happy path, single retry, retry cap, route_after_validate unit tests
- `pyproject.toml` - added langchain-anthropic>=0.3, langchain-ollama>=0.2, langgraph>=1.0
- `.env.example` - documented LLM_PROVIDER, OLLAMA_MODEL, ANTHROPIC_API_KEY

## Decisions Made

- validate stub calls driver.execute_query() to enable routing tests — stub behavior depends on driver return value, not hardcoded (required for retry test correctness)
- format stub checks retry_count >= 3 and empty db_results to include error key — needed for retry cap graph test
- analysis_result intermediate key in WorkflowState resolves ANALYZE->FORMAT ambiguity — ANALYZE writes synthesis text, FORMAT reads it and produces structured final_output dict
- LLM_PROVIDER env toggle centralised in get_llm(role) — validator role uses cheaper Haiku, all others use Sonnet

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] validate_node stub updated to call driver and handle retry state**
- **Found during:** Task 2 (graph routing tests)
- **Issue:** Original stub returned hardcoded `{"db_results": [{"stub": True}]}` regardless of driver — routing tests requiring retry behavior (fail once, succeed next) would fail since validate never returned empty results or incremented retry_count
- **Fix:** Updated validate_node to call `driver.execute_query(cypher)` and return `{db_results, validation_errors, retry_count}` on failure vs `{db_results}` on success. None driver path preserved for test_state owned-key test.
- **Files modified:** src/workflow/nodes/validate.py
- **Verification:** test_single_retry_routes_back_to_generate_cypher and test_retry_cap_exhausted_routes_to_format_error pass
- **Committed in:** fc549bc (Task 2 commit)

**2. [Rule 1 - Bug] format_node stub updated to return error key on retry cap exhaustion**
- **Found during:** Task 2 (graph routing tests)
- **Issue:** Original stub returned uniform structure; test_retry_cap_exhausted_routes_to_format_error asserts `final_output` has `"error"` key on cap-exhausted path
- **Fix:** format_node checks `retry_count >= 3 and not db_results` — returns error structure with `"error"` key if true, normal stub structure otherwise
- **Files modified:** src/workflow/nodes/format.py
- **Verification:** test_retry_cap_exhausted_routes_to_format_error passes with error key present
- **Committed in:** fc549bc (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 — stub behavior insufficient for routing test correctness)
**Impact on plan:** Both fixes necessary for graph routing tests to verify retry logic. Both are within stub scope — no architectural changes, no new state keys.

## Issues Encountered

None — plan executed cleanly after auto-fixing the two stub behavior issues.

## User Setup Required

None - no external service configuration required for this plan. LangChain packages installed; no API key needed for stub tests (LLM not called in stubs).

## Next Phase Readiness

- WorkflowState contract and graph topology are locked — plans 02-02 through 02-04 implement against this skeleton
- test fixtures (stub_driver, mock_llm, sample_state) available in tests/workflow/conftest.py
- Placeholder test files exist for all 5 nodes — ready to be populated by later plans
- langchain-anthropic and langchain-ollama installed and importable

---
*Phase: 02-langgraph-workflow-stub-data*
*Completed: 2026-03-15*
