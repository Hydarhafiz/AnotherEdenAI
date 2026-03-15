# Phase 2: LangGraph Workflow (Stub Data) - Context

**Gathered:** 2026-03-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the complete PLAN → GENERATE_CYPHER → VALIDATE → ANALYZE → FORMAT LangGraph pipeline and wire it into a compiled StateGraph. All five nodes are implemented with full logic; Neo4j and LLM calls are mocked for testing. Agent logic bugs are isolated from data bugs before any real graph is touched. No live LLM calls and no live Neo4j connections required to run the test suite.

</domain>

<decisions>
## Implementation Decisions

### WorkflowState schema
- TypedDict with `typing.Annotated` reducers on appendable lists
- Keys and ownership:
  - `user_query: str` — set by caller, read-only throughout
  - `roster: list[str]` — set by caller, read-only throughout
  - `plan_strategy: str` — written by PLAN node only
  - `cypher_query: str` — written by GENERATE_CYPHER node only
  - `db_results: list[dict]` — written by VALIDATE node only (result of execution)
  - `validation_errors: list[str]` — appendable (Annotated reducer); VALIDATE appends on each failure
  - `retry_count: int` — incremented by VALIDATE node only (starts at 0, cap at 3)
  - `final_output: dict` — written by FORMAT node only
- Each node must return **only the keys it modifies** — no shared mutation across nodes (AGENT-07)

### VALIDATE node scope and error format
- Haiku 4.6 acts as both **syntax checker** and **semantic gate**
- VALIDATE executes the Cypher against the mock/real database; it is not a static linter
- Two failure modes trapped:
  - (A) Database execution exception (syntax error, schema mismatch, missing label/property)
  - (B) Empty result set — generator hallucinated a non-existent synergy or traversal path
- Error message format passed back to GENERATE_CYPHER (appended to `validation_errors`):
  ```
  Attempt {retry_count}: Query failed due to [Exception/Empty Result]. Context: [Detailed reason]
  ```
- Conditional edge logic:
  - Pass → route to ANALYZE
  - Fail + retry_count < 3 → route to GENERATE_CYPHER (with error context in state)
  - Fail + retry_count >= 3 → route to FORMAT (graceful error path)

### FORMAT node output structure
- Output is a **structured dict** (not plain text or markdown string)
- Phase 4 (FastAPI + Jinja2 templates) iterates over this structure directly — no parsing required
- Schema:
  ```python
  {
      "frontline": [
          {"name": str, "role": str, "grastas": [...]},
          # ... up to 4
      ],
      "reserve": [
          {"name": str, "role": str, "grastas": [...]},
          # ... up to 2
      ],
      "synergy_explanation": str
  }
  ```
- On graceful error path (retry cap exhausted): FORMAT returns `{"error": str, "frontline": [], "reserve": [], "synergy_explanation": ""}` — same schema, safe for web layer to render

### LLM provider abstraction
- `src/workflow/llm.py` provides `get_llm(role: str) -> BaseChatModel` factory (AGENT-08)
- `LLM_PROVIDER=ollama` in `.env` returns `ChatOllama` (local testing, zero API cost)
- `LLM_PROVIDER=anthropic` (default) returns `ChatAnthropic` with the correct model for the role:
  - `role="planner"` or `role="cypher"` or `role="analyzer"` → `claude-sonnet-4-6`
  - `role="validator"` → `claude-haiku-4-6-20251001` (cost/latency optimized)
- All nodes call `get_llm(role=...)` — no node imports `ChatAnthropic` directly
- Tests patch `src.workflow.llm.get_llm` (one patch point for all nodes)
- `.env` file must include `LLM_PROVIDER` (defaulting to `anthropic` in `.env.example`)

### Module and file structure
- All workflow code lives under `src/workflow/` (new directory this phase)
- Layout:
  ```
  src/workflow/
    __init__.py
    state.py          # TypedDict definitions, Annotated reducers
    graph.py          # StateGraph wiring, conditional edges, compile()
    llm.py            # get_llm(role) factory — BaseChatModel, LLM_PROVIDER toggle
    nodes/
      __init__.py
      plan.py         # PLAN node — calls get_llm(role="planner")
      cypher.py       # GENERATE_CYPHER node — calls get_llm(role="cypher")
      validate.py     # VALIDATE node — calls get_llm(role="validator")
      analyze.py      # ANALYZE node — calls get_llm(role="analyzer")
      format.py       # FORMAT node — no LLM (structured transformation)
  ```
- One file per node — maximizes mockability and test isolation
- `graph.py` imports from `nodes/` and from `state.py`; no circular dependencies
- `llm.py` has no imports from within `src/workflow/` — it is a leaf module

### Claude's Discretion
- Exact few-shot prompt examples injected into GENERATE_CYPHER (structure TBD by researcher)
- Mock implementation details (pytest-mock vs manual stub) — choose based on test isolation needs
- LangGraph version and exact `StateGraph` API patterns — researcher to verify against current docs

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tests/conftest.py`: `async_driver`, `loaded_db`, `clean_db` fixtures — Phase 2 tests add a new `mock_driver` or `stub_db` fixture following the same session-scoped async pattern
- `src/etl/constants.py`: `NEO4J_URI`, `NEO4J_AUTH` env var pattern — workflow nodes should follow the same env var loading pattern for LLM API keys
- `src/etl/models.py`: Pydantic v2 model pattern — apply same validation discipline to `WorkflowState` and `final_output` schema

### Established Patterns
- Pydantic v2 at all data boundaries (Phase 1 pattern — carry forward to WorkflowState and FORMAT output)
- `@pytest_asyncio.fixture(loop_scope="session")` for session-scoped async fixtures — Phase 2 test fixtures must follow this to avoid event loop errors
- `asyncio_mode = "auto"` in `pyproject.toml` — already configured, no pytest.ini changes needed
- `pytest.mark.integration` registered — use for tests requiring the mock driver vs pure unit tests

### Integration Points
- `src/etl/run_etl.py` → `get_schema()` output (via `langchain_neo4j.Neo4jGraph`) is injected into GENERATE_CYPHER prompts — Phase 2 must mock this return value in unit tests
- `docker-compose.yml` Neo4j instance remains the shared target; Phase 2 adds no new services
- `src/workflow/graph.py` exports a compiled graph — Phase 3 (real data) and Phase 4 (web) import and invoke it

</code_context>

<specifics>
## Specific Ideas

- `validation_errors` uses `Annotated` reducer (list append) so error history accumulates across retries — GENERATE_CYPHER receives the full error trail, not just the last error
- FORMAT node on error path returns same schema shape as success path — Phase 4 web layer never needs to branch on "did it error?"
- `src/workflow/nodes/` one-file-per-node layout is intentional for portfolio readability — demonstrates separation of concerns to reviewers
- Error message format `"Attempt {retry_count}: Query failed due to [Exception/Empty Result]. Context: [Detailed reason]"` is the literal string template VALIDATE must produce

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 02-langgraph-workflow-stub-data*
*Context gathered: 2026-03-15*
