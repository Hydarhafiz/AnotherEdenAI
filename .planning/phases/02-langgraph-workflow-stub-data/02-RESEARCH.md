# Phase 2: LangGraph Workflow (Stub Data) - Research

**Researched:** 2026-03-15
**Domain:** LangGraph 1.0.x StateGraph, LangChain Anthropic integration, pytest mocking patterns
**Confidence:** HIGH (core LangGraph API verified via official docs; mocking patterns verified against existing codebase conventions)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- WorkflowState is a TypedDict with `typing.Annotated` reducers on appendable lists
- State keys and ownership:
  - `user_query: str` — set by caller, read-only throughout
  - `roster: list[str]` — set by caller, read-only throughout
  - `plan_strategy: str` — written by PLAN node only
  - `cypher_query: str` — written by GENERATE_CYPHER node only
  - `db_results: list[dict]` — written by VALIDATE node only (result of execution)
  - `validation_errors: list[str]` — appendable (Annotated reducer); VALIDATE appends on each failure
  - `retry_count: int` — incremented by VALIDATE node only (starts at 0, cap at 3)
  - `final_output: dict` — written by FORMAT node only
- Each node must return only the keys it modifies — no shared mutation across nodes (AGENT-07)
- VALIDATE executes Cypher (not static lint) — traps execution exceptions AND empty results
- Two VALIDATE failure modes: (A) execution exception, (B) empty result set
- Error message format: `"Attempt {retry_count}: Query failed due to [Exception/Empty Result]. Context: [Detailed reason]"`
- Conditional edge logic: Pass → ANALYZE | Fail + retry < 3 → GENERATE_CYPHER | Fail + retry >= 3 → FORMAT
- FORMAT output schema (structured dict, not plain text):
  ```python
  {
      "frontline": [{"name": str, "role": str, "grastas": [...]}, ...],  # up to 4
      "reserve":   [{"name": str, "role": str, "grastas": [...]}, ...],  # up to 2
      "synergy_explanation": str
  }
  ```
- Graceful error path FORMAT schema: `{"error": str, "frontline": [], "reserve": [], "synergy_explanation": ""}`
- Module layout:
  ```
  src/workflow/
    __init__.py
    state.py          # TypedDict definitions, Annotated reducers
    graph.py          # StateGraph wiring, conditional edges, compile()
    nodes/
      __init__.py
      plan.py         # PLAN node — Sonnet 4.6
      cypher.py       # GENERATE_CYPHER node — Sonnet 4.6
      validate.py     # VALIDATE node — Haiku 4.6
      analyze.py      # ANALYZE node — Sonnet 4.6
      format.py       # FORMAT node — no LLM (structured transformation)
  ```
- `graph.py` imports from `nodes/` and from `state.py`; no circular dependencies

### Claude's Discretion
- Exact few-shot prompt examples injected into GENERATE_CYPHER (structure TBD)
- Mock implementation details — choose based on test isolation needs
- LangGraph version and exact StateGraph API patterns — researcher to verify

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| AGENT-01 | PLAN agent (Sonnet 4.6) receives user query + roster and decomposes into graph traversal sub-goals | Node function receives `WorkflowState`, calls `ChatAnthropic(model="claude-haiku-4-6")`, returns `{"plan_strategy": str}` |
| AGENT-02 | GENERATE_CYPHER agent (Sonnet 4.6) produces Cypher with full schema injected via `Neo4jGraph.get_schema()` and few-shot examples | Node injects schema string into system prompt; few-shot examples are literal Cypher strings documented in SCHEMA.md |
| AGENT-03 | VALIDATE agent (Haiku 4.6) verifies Cypher syntax and confirms non-empty results against game rules | Node executes Cypher via `driver.execute_query()`, catches exceptions AND empty `records` list |
| AGENT-04 | VALIDATE agent routes failed queries back to GENERATE_CYPHER with full error context | Conditional edge router reads `retry_count`; node appends to `validation_errors` list via Annotated reducer |
| AGENT-05 | Retry loop hard-capped at 3 via conditional edge in WorkflowState; exceeding cap routes to graceful error | `add_conditional_edges("validate", route_after_validate)` with `Literal["generate_cypher", "analyze", "format"]` |
| AGENT-06 | ANALYZE agent (Sonnet 4.6) synthesizes validated query results into final team recommendation | Node reads `db_results: list[dict]` from state; writes `final_output` dict via FORMAT node |
| AGENT-07 | WorkflowState is TypedDict validated by Pydantic v2; each node returns only the keys it modifies | TypedDict + `operator.add` reducers enforced at LangGraph layer; Pydantic v2 validates `final_output` structure at FORMAT boundary |
</phase_requirements>

---

## Summary

Phase 2 builds the complete five-node LangGraph pipeline (PLAN → GENERATE_CYPHER → VALIDATE → ANALYZE → FORMAT) as a compiled `StateGraph` with all real node logic implemented. The key constraint is that the entire test suite must run with no live LLM calls and no live Neo4j connections — mocking is the critical technical discipline of this phase.

LangGraph 1.0.10 is already installed. The `StateGraph` API is stable: TypedDict state with `Annotated[list, operator.add]` reducers, `add_node` / `add_edge` / `add_conditional_edges`, and `compile()`. The primary gap is that `langchain-anthropic` is NOT currently installed — it must be added to `pyproject.toml` before any node can import `ChatAnthropic`. All LLM calls are mocked with `unittest.mock.MagicMock` (the project's established pattern — `pytest-mock` is not used).

The most important architectural decision to research was the VALIDATE conditional edge: `add_conditional_edges` in LangGraph 1.0 accepts either a `dict` path_map or a `list` of node names (when the router return value matches the node name directly). Using `Literal` type hints on the router function signature is the recommended pattern — it makes the routing explicit and tool-readable.

**Primary recommendation:** Use `unittest.mock.MagicMock` with `side_effect` lists for all LLM mocks; inject mocks via dependency injection (pass `llm=` as a parameter to node constructor functions or use `mocker.patch` at the module level). This approach aligns with `test_models.py` which already uses `unittest.mock.patch`.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `langgraph` | 1.0.10 (installed) | StateGraph engine, node/edge wiring, compile | Already in venv; official LangGraph package |
| `langchain-core` | 1.2.19 (installed) | `AIMessage`, `HumanMessage`, `SystemMessage`, `FakeListChatModel` | Already installed via langchain-neo4j dependency |
| `langchain-anthropic` | latest | `ChatAnthropic` — real LLM calls for Sonnet 4.6 / Haiku 4.6 | **NOT INSTALLED** — must add to `pyproject.toml` |
| `pydantic` | 2.12.5 (installed) | Validates `final_output` dict structure at FORMAT node boundary | Already installed, v2 used throughout Phase 1 |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `langchain_core.language_models.fake_chat_models.FakeListChatModel` | via langchain-core 1.2.19 | Drop-in fake LLM for unit tests; cycles through response list | All unit tests where LLM response content matters |
| `unittest.mock.MagicMock` | stdlib | General mock for LLM and Neo4j driver | Preferred by project — already used in `test_models.py` |
| `operator.add` | stdlib | Reducer function for `validation_errors` list accumulation | `Annotated[list[str], operator.add]` on WorkflowState |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `unittest.mock` | `pytest-mock` (mocker fixture) | pytest-mock is syntactic sugar over unittest.mock; project already uses unittest.mock — do NOT add pytest-mock |
| `FakeListChatModel` | `MagicMock()` with `return_value=AIMessage(...)` | MagicMock is simpler for tests that don't care about content; FakeListChatModel better when testing prompt content flows through to response |
| `Literal` return type on router | explicit `path_map` dict | Both work in LangGraph 1.0; Literal is cleaner and LangGraph-Studio-readable |

### Installation

```bash
# Add to pyproject.toml [project] dependencies:
# "langchain-anthropic>=0.3",

# Then:
uv pip install langchain-anthropic
# or
pip install langchain-anthropic
```

---

## Architecture Patterns

### Recommended Project Structure

```
src/workflow/
├── __init__.py          # exports: compiled_graph (the result of graph.compile())
├── state.py             # WorkflowState TypedDict + validate_final_output() Pydantic helper
├── graph.py             # StateGraph wiring, conditional edges, compile()
└── nodes/
    ├── __init__.py
    ├── plan.py          # PLAN node — Sonnet 4.6
    ├── cypher.py        # GENERATE_CYPHER node — Sonnet 4.6, schema injection
    ├── validate.py      # VALIDATE node — executes Cypher, Haiku 4.6 semantic check
    ├── analyze.py       # ANALYZE node — Sonnet 4.6, team synthesis
    └── format.py        # FORMAT node — no LLM, pure structured transformation

tests/workflow/
├── __init__.py
├── conftest.py          # mock_llm, stub_driver fixtures
├── test_state.py        # WorkflowState reducer behavior, key isolation
├── test_graph.py        # full graph happy path, retry routing, retry cap
├── test_plan.py         # PLAN node unit test
├── test_cypher.py       # GENERATE_CYPHER node unit test
├── test_validate.py     # VALIDATE node unit test (success, exception, empty)
├── test_analyze.py      # ANALYZE node unit test
└── test_format.py       # FORMAT node unit test (success path + error path)
```

### Pattern 1: WorkflowState TypedDict with Annotated Reducer

**What:** TypedDict state schema where `validation_errors` accumulates across retries using `operator.add`
**When to use:** Any list field that must append (not overwrite) across multiple node invocations

```python
# src/workflow/state.py
# Source: https://docs.langchain.com/oss/python/langgraph/use-graph-api
import operator
from typing import Annotated
from typing_extensions import TypedDict


class WorkflowState(TypedDict):
    user_query: str                                  # set by caller, read-only
    roster: list[str]                               # set by caller, read-only
    plan_strategy: str                              # written by PLAN only
    cypher_query: str                               # written by GENERATE_CYPHER only
    db_results: list[dict]                          # written by VALIDATE only
    validation_errors: Annotated[list[str], operator.add]  # VALIDATE appends on failure
    retry_count: int                                # incremented by VALIDATE only
    final_output: dict                              # written by FORMAT only
```

**Key rule:** `operator.add` on a list means `existing + new` — nodes returning `{"validation_errors": ["new error"]}` append; they do not overwrite.

### Pattern 2: StateGraph Wiring with Conditional Edge

**What:** Full graph assembly pattern with retry routing from VALIDATE
**When to use:** Whenever a conditional edge depends on accumulated state (retry_count, validation_errors)

```python
# src/workflow/graph.py
# Source: https://docs.langchain.com/oss/python/langgraph/use-graph-api
from typing import Literal
from langgraph.graph import StateGraph, START, END
from .state import WorkflowState
from .nodes.plan import plan_node
from .nodes.cypher import generate_cypher_node
from .nodes.validate import validate_node
from .nodes.analyze import analyze_node
from .nodes.format import format_node


def route_after_validate(state: WorkflowState) -> Literal["generate_cypher", "analyze", "format"]:
    """Route VALIDATE output: pass→analyze, fail+retry→generate_cypher, fail+cap→format."""
    if state.get("validation_errors") and len(state["validation_errors"]) > state.get("retry_count", 0):
        # New error was appended — check retry cap
        if state["retry_count"] >= 3:
            return "format"   # graceful error path
        return "generate_cypher"
    return "analyze"


builder = StateGraph(WorkflowState)

builder.add_node("plan", plan_node)
builder.add_node("generate_cypher", generate_cypher_node)
builder.add_node("validate", validate_node)
builder.add_node("analyze", analyze_node)
builder.add_node("format", format_node)

builder.add_edge(START, "plan")
builder.add_edge("plan", "generate_cypher")
builder.add_edge("generate_cypher", "validate")
builder.add_conditional_edges(
    "validate",
    route_after_validate,
    # path_map as list — return value must match node name exactly
    ["generate_cypher", "analyze", "format"],
)
builder.add_edge("analyze", "format")
builder.add_edge("format", END)

compiled_graph = builder.compile()
```

### Pattern 3: Node Function Signature (returns only owned keys)

**What:** Each node is a plain Python function receiving full state, returning only the keys it modifies
**When to use:** All five nodes — this is the AGENT-07 requirement

```python
# src/workflow/nodes/plan.py
# Source: https://docs.langchain.com/oss/python/langgraph/use-graph-api
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from ..state import WorkflowState


def plan_node(state: WorkflowState) -> dict:
    """PLAN node: Sonnet 4.6 decomposes query into graph traversal sub-goals."""
    llm = ChatAnthropic(model="claude-sonnet-4-6")
    messages = [
        SystemMessage(content=PLAN_SYSTEM_PROMPT),
        HumanMessage(content=f"Query: {state['user_query']}\nRoster: {state['roster']}"),
    ]
    response = llm.invoke(messages)
    return {"plan_strategy": response.content}  # only owned key
```

### Pattern 4: VALIDATE Node — Execute Cypher, Trap Both Failure Modes

**What:** VALIDATE executes Cypher against Neo4j driver (passed via state or injected), traps two error types
**When to use:** This is the core of AGENT-03 and AGENT-04

```python
# src/workflow/nodes/validate.py
from ..state import WorkflowState

RETRY_CAP = 3


def validate_node(state: WorkflowState, driver) -> dict:
    """VALIDATE: execute Cypher, trap exception and empty result."""
    retry_count = state.get("retry_count", 0)
    cypher = state["cypher_query"]

    try:
        records, _, _ = driver.execute_query(cypher, database_="neo4j")
        if not records:
            # Failure mode B: empty result
            error_msg = (
                f"Attempt {retry_count + 1}: Query failed due to Empty Result. "
                f"Context: Query returned no records — possible hallucinated traversal path."
            )
            return {
                "validation_errors": [error_msg],
                "retry_count": retry_count + 1,
            }
    except Exception as exc:
        # Failure mode A: execution exception
        error_msg = (
            f"Attempt {retry_count + 1}: Query failed due to Exception. "
            f"Context: {type(exc).__name__}: {exc}"
        )
        return {
            "validation_errors": [error_msg],
            "retry_count": retry_count + 1,
        }

    # Pass: write db_results, do NOT append error
    return {"db_results": list(records)}
```

**Challenge:** `driver` is not in WorkflowState — see Pitfall 2 below for the recommended injection pattern.

### Pattern 5: FORMAT Node — Structured Dict Output (no LLM)

**What:** Pure Python transformation from ANALYZE output to final_output schema
**When to use:** FORMAT is intentionally LLM-free — deterministic and easily testable

```python
# src/workflow/nodes/format.py
from pydantic import BaseModel
from typing import Optional
from ..state import WorkflowState


class CharacterSlot(BaseModel):
    name: str
    role: str
    grastas: list[str]


class TeamOutput(BaseModel):
    frontline: list[CharacterSlot]
    reserve: list[CharacterSlot]
    synergy_explanation: str
    error: Optional[str] = None


def format_node(state: WorkflowState) -> dict:
    """FORMAT: structure ANALYZE output into final_output dict. No LLM."""
    # Check for graceful error path (retry cap exhausted)
    if state.get("retry_count", 0) >= 3 and not state.get("db_results"):
        return {
            "final_output": {
                "error": "; ".join(state.get("validation_errors", [])),
                "frontline": [],
                "reserve": [],
                "synergy_explanation": "",
            }
        }
    # Happy path: parse final_output from ANALYZE
    analyze_result = state.get("final_output", {})
    # Validate with Pydantic before returning
    validated = TeamOutput.model_validate(analyze_result)
    return {"final_output": validated.model_dump()}
```

### Pattern 6: Mocking LLM and Driver in Tests

**What:** `unittest.mock.MagicMock` to mock `ChatAnthropic.invoke()` and `driver.execute_query()`
**When to use:** All unit tests — no live LLM or Neo4j permitted

```python
# tests/workflow/test_plan.py
from unittest.mock import MagicMock, patch
from langchain_core.messages import AIMessage
from src.workflow.nodes.plan import plan_node


def test_plan_node_returns_plan_strategy():
    """Plan node writes plan_strategy and only plan_strategy."""
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(content="Focus on Fire element synergy")

    with patch("src.workflow.nodes.plan.ChatAnthropic", return_value=mock_llm):
        state = {
            "user_query": "best fire team",
            "roster": ["Aldo", "Ciel"],
            "plan_strategy": "",
            "cypher_query": "",
            "db_results": [],
            "validation_errors": [],
            "retry_count": 0,
            "final_output": {},
        }
        result = plan_node(state)

    assert "plan_strategy" in result
    assert list(result.keys()) == ["plan_strategy"]  # AGENT-07: only owned key
    mock_llm.invoke.assert_called_once()
```

```python
# tests/workflow/test_validate.py
from unittest.mock import MagicMock
from neo4j.exceptions import CypherSyntaxError
from src.workflow.nodes.validate import validate_node


def test_validate_execution_exception():
    """Failure mode A: execution exception appends to validation_errors."""
    mock_driver = MagicMock()
    mock_driver.execute_query.side_effect = Exception("Unknown label 'Foo'")

    state = {
        "cypher_query": "MATCH (n:Foo) RETURN n",
        "retry_count": 0,
        "validation_errors": [],
        "db_results": [],
    }
    result = validate_node(state, mock_driver)

    assert len(result["validation_errors"]) == 1
    assert "Attempt 1" in result["validation_errors"][0]
    assert result["retry_count"] == 1


def test_validate_empty_result():
    """Failure mode B: empty result appends to validation_errors."""
    mock_driver = MagicMock()
    mock_driver.execute_query.return_value = ([], None, None)

    state = {"cypher_query": "MATCH (n:Character) RETURN n", "retry_count": 0, "validation_errors": [], "db_results": []}
    result = validate_node(state, mock_driver)

    assert "Empty Result" in result["validation_errors"][0]
    assert result["retry_count"] == 1
```

### Pattern 7: Full Graph Test — Happy Path

**What:** Test the compiled graph end-to-end with all LLM calls mocked
**When to use:** `test_graph.py` — covers the full state machine flow

```python
# tests/workflow/test_graph.py
from unittest.mock import MagicMock, patch
from langchain_core.messages import AIMessage
from src.workflow.graph import compiled_graph


def test_full_graph_happy_path():
    """All five nodes run; final_output has correct schema on success."""
    mock_llm = MagicMock()
    mock_llm.invoke.side_effect = [
        AIMessage(content="Plan: find Fire characters"),      # PLAN
        AIMessage(content="MATCH (c:Character) RETURN c"),    # GENERATE_CYPHER
        AIMessage(content="Looks valid"),                      # VALIDATE semantic check (if used)
        AIMessage(content='{"frontline": [...], "reserve": [...], "synergy_explanation": "..."}'),  # ANALYZE
    ]
    mock_driver = MagicMock()
    mock_driver.execute_query.return_value = ([{"c": {"name": "Aldo"}}], None, None)

    with patch("src.workflow.nodes.plan.ChatAnthropic", return_value=mock_llm), \
         patch("src.workflow.nodes.cypher.ChatAnthropic", return_value=mock_llm), \
         patch("src.workflow.nodes.analyze.ChatAnthropic", return_value=mock_llm):

        result = compiled_graph.invoke({
            "user_query": "best fire team",
            "roster": ["Aldo"],
            "plan_strategy": "",
            "cypher_query": "",
            "db_results": [],
            "validation_errors": [],
            "retry_count": 0,
            "final_output": {},
        })

    assert "final_output" in result
    assert "frontline" in result["final_output"]
    assert "reserve" in result["final_output"]
    assert "synergy_explanation" in result["final_output"]
```

### Anti-Patterns to Avoid

- **Importing ChatAnthropic at module level without mock injection:** If `ChatAnthropic(...)` is called at module import time (e.g., as a module-level global), `patch` cannot intercept it before the import. Instantiate `ChatAnthropic` inside the node function or pass it as a parameter.
- **Returning full state from a node:** Each node MUST return only `{"owned_key": value}`. Returning the full state dict will overwrite ALL state keys, breaking the Annotated reducer for `validation_errors`.
- **Using `operator.add` on non-list types:** `operator.add` on `str` or `int` will concatenate/sum unexpectedly — only use it on `list` fields.
- **Testing the router in isolation without state:** The `route_after_validate` function must be tested with realistic state dicts (including `retry_count` and `validation_errors`) — never with empty state.
- **Calling `driver.execute_query()` with `await`:** The Phase 2 tests use sync driver; Phase 3 switches to `AsyncGraphDatabase`. Do NOT make VALIDATE node async in Phase 2 unless the mock driver is also async.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| State merging/accumulation | Custom dict-merge logic in nodes | `Annotated[list, operator.add]` in TypedDict | LangGraph handles reducer invocation automatically |
| Conditional routing map | `if/elif` chains in graph wiring code | `add_conditional_edges` with `Literal` router function | LangGraph validates paths at compile time, raises `KeyError` for missing routes |
| Graph execution engine | Custom async task runner | `compiled_graph.invoke()` / `compiled_graph.ainvoke()` | LangGraph handles node sequencing, state passing, error propagation |
| LLM fake responses in tests | Custom HTTP mock server | `FakeListChatModel` from `langchain_core` or `MagicMock` | Already in installed packages; zero config |

**Key insight:** The LangGraph `StateGraph` handles all state merging, node sequencing, and routing — never replicate this logic manually in nodes or tests.

---

## Common Pitfalls

### Pitfall 1: `validation_errors` Reducer Not Firing in Tests
**What goes wrong:** Unit tests that call `validate_node()` directly (not via the compiled graph) will see the raw return dict `{"validation_errors": ["error"]}` — the `operator.add` reducer is NOT applied. Only `compiled_graph.invoke()` applies reducers.
**Why it happens:** Reducers are a LangGraph-layer concern, not a Python-layer concern.
**How to avoid:** Unit tests on individual node functions test the raw return value (the list with one new error). Only graph-level tests (test_graph.py) test the accumulated list. Document this distinction clearly in test docstrings.
**Warning signs:** Test asserting `result["validation_errors"] == ["Attempt 1...", "Attempt 2..."]` when calling `validate_node()` directly — this will always fail.

### Pitfall 2: Neo4j Driver Not In State — Injection Problem
**What goes wrong:** `validate_node` needs a live (or mock) Neo4j driver, but `WorkflowState` doesn't contain a driver. Hardcoding `AsyncGraphDatabase.driver(...)` inside the node makes it unmockable.
**Why it happens:** State is data; infrastructure clients are dependencies.
**How to avoid:** Two valid patterns:
  1. **Dependency injection via closure:** `graph.py` creates the driver once and wraps the node: `builder.add_node("validate", lambda state: validate_node(state, driver))`. Tests pass `mock_driver` to `validate_node()` directly.
  2. **Module-level singleton with patch:** `validate.py` imports a module-level driver from `src/workflow/config.py` — tests `patch("src.workflow.nodes.validate.driver", mock_driver)`.

  **Recommendation:** Closure/lambda pattern (option 1) — simpler for Phase 2, easier to swap for async driver in Phase 3.
**Warning signs:** `RuntimeError: No event loop` or `ServiceUnavailable` during tests with no mock.

### Pitfall 3: `add_conditional_edges` Path Map Missing Routes
**What goes wrong:** `KeyError` at graph invoke time: router returns `"format"` but path_map only has `["generate_cypher", "analyze"]`.
**Why it happens:** LangGraph validates that every router return value appears in the path_map.
**How to avoid:** Always include ALL possible Literal values in the path_map list. With the retry logic, that is exactly three values: `"generate_cypher"`, `"analyze"`, `"format"`.
**Warning signs:** `KeyError` mentioning the missing route string at `compiled_graph.invoke()` time.

### Pitfall 4: `langchain-anthropic` Not Installed — Import Error at Runtime
**What goes wrong:** `ImportError: No module named 'langchain_anthropic'` when any node file is imported.
**Why it happens:** `langchain-anthropic` is NOT in the current venv (confirmed 2026-03-15). Only `langchain-core` and `langchain-classic` are installed.
**How to avoid:** Add `"langchain-anthropic>=0.3"` to `pyproject.toml` `[project] dependencies` immediately in plan 02-01. Run `pip install langchain-anthropic` before implementing any node.
**Warning signs:** Clean test run fails at import with `ModuleNotFoundError`.

### Pitfall 5: Session Event Loop Conflict with Async Driver
**What goes wrong:** `RuntimeError: Event loop is closed` or `different event loop` if Phase 2 introduces async fixtures without following the `loop_scope="session"` pattern.
**Why it happens:** The project uses `asyncio_default_fixture_loop_scope = "session"` in pytest.ini — all async fixtures MUST use `@pytest_asyncio.fixture(scope="session", loop_scope="session")`.
**How to avoid:** Phase 2 workflow tests are sync (no async driver in Phase 2). If adding a `stub_driver` fixture, make it sync-scoped `@pytest.fixture(scope="function")` to avoid async conflicts.
**Warning signs:** Tests pass individually but fail when run together as `pytest tests/workflow/`.

### Pitfall 6: GENERATE_CYPHER Prompt Missing Schema
**What goes wrong:** LLM hallucinates non-existent labels or relationship types (e.g., `ENHANCES`) because SCHEMA.md content is not injected into the system prompt.
**Why it happens:** AGENT-02 explicitly requires full schema injection via `get_schema()`.
**How to avoid:** In tests, mock `get_schema()` to return the SCHEMA.md content as a string. In node implementation, call `get_schema()` at node invocation time (not at module import). The actual SCHEMA.md is at `/home/shogunix/AnotherEdenAI/SCHEMA.md` — its content is the ground truth for few-shot examples.
**Warning signs:** VALIDATE consistently rejects GENERATE_CYPHER output with schema mismatch errors.

---

## Code Examples

### Few-Shot Cypher Examples for GENERATE_CYPHER Prompt

These are verified against SCHEMA.md (v1.0.0, confirmed matching graph state as of 2026-03-15):

```python
# Source: SCHEMA.md v1.0.0 — all node labels, properties, and relationships verified
FEW_SHOT_EXAMPLES = """
Example 1: Find all Fire characters in roster
MATCH (c:Character)
WHERE c.element CONTAINS 'Fire' AND c.name IN $roster
RETURN c.name, c.element, c.weapon, c.light_shadow

Example 2: Find characters with a specific trait
MATCH (c:Character)-[:HAS_TRAIT]->(t:Trait)
WHERE t.name = 'Straw Dummy' AND c.name IN $roster
RETURN c.name, t.name

Example 3: Find shareable Grastas matching character trait
MATCH (c:Character)-[:HAS_TRAIT]->(t:Trait)<-[:REQUIRES_TRAIT]-(g:Grasta)
WHERE c.name IN $roster AND g.is_shareable = true
RETURN c.name, g.name, g.category, g.tier, g.stats

Example 4: Find Attack Grastas available to roster
MATCH (g:Grasta)-[:REQUIRES_TRAIT]->(t:Trait)<-[:HAS_TRAIT]-(c:Character)
WHERE c.name IN $roster AND g.category = 'Attack'
RETURN g.name, g.tier, g.stats, g.is_shareable, collect(c.name) AS usable_by
ORDER BY g.tier DESC
"""
```

**Critical constraints from SCHEMA.md:**
- Never use `ENHANCES` — this relationship does NOT exist
- Ore nodes are standalone — no relationships to query through
- VC Grastas have no `REQUIRES_TRAIT` edges — filter `category <> 'VC'` when joining on traits
- `personality_req` is `null` for VC and weapon-based grastas

### WorkflowState Initial State Template

```python
# Template for compiled_graph.invoke() — all keys must be present
INITIAL_STATE: WorkflowState = {
    "user_query": "",       # caller sets this
    "roster": [],           # caller sets this
    "plan_strategy": "",
    "cypher_query": "",
    "db_results": [],
    "validation_errors": [],
    "retry_count": 0,
    "final_output": {},
}
```

### Retry Cap Test Pattern

```python
# tests/workflow/test_graph.py
def test_retry_cap_exhausted_routes_to_graceful_error():
    """After 3 VALIDATE failures, FORMAT returns error schema (never attempt 4)."""
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(content="MATCH (n) RETURN n")

    mock_driver = MagicMock()
    mock_driver.execute_query.return_value = ([], None, None)  # always empty

    with patch("src.workflow.nodes.plan.ChatAnthropic", return_value=mock_llm), \
         patch("src.workflow.nodes.cypher.ChatAnthropic", return_value=mock_llm), \
         patch("src.workflow.nodes.analyze.ChatAnthropic", return_value=mock_llm):

        result = compiled_graph.invoke(INITIAL_STATE | {"user_query": "test", "roster": ["Aldo"]})

    assert result["retry_count"] == 3
    assert len(result["validation_errors"]) == 3
    assert "error" in result["final_output"]
    assert result["final_output"]["frontline"] == []
    # Verify driver was called exactly 3 times (never a 4th)
    assert mock_driver.execute_query.call_count == 3
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual state dict passing between functions | `StateGraph` with TypedDict + Annotated reducers | LangGraph 0.1+ | State merging is automatic; nodes only return owned keys |
| `add_conditional_edges(src, fn, {"a": "nodeA"})` dict path_map | `add_conditional_edges(src, fn, ["nodeA", "nodeB"])` list path_map OR `Literal` return type | LangGraph 0.2+ | List form is valid when router returns match node names exactly |
| `ChatAnthropic` from `langchain_community` | `ChatAnthropic` from `langchain_anthropic` | langchain-anthropic package split | Must install `langchain-anthropic` separately; community version deprecated |

**Deprecated/outdated:**
- `langchain_community.chat_models.ChatAnthropic`: Deprecated — use `langchain_anthropic.ChatAnthropic` directly
- `FakeListLLM` from `langchain_community`: Use `FakeListChatModel` from `langchain_core.language_models.fake_chat_models` for chat model mocking

---

## Open Questions

1. **Driver injection pattern for VALIDATE node**
   - What we know: `driver` is not in WorkflowState; VALIDATE needs it to execute Cypher
   - What's unclear: Whether Phase 3 will use the same driver reference or a new async driver pattern
   - Recommendation: Use lambda closure in `graph.py`: `builder.add_node("validate", lambda s: validate_node(s, driver))`. Phase 3 replaces `driver` with `async_driver` using the same pattern.

2. **GENERATE_CYPHER prompt output format**
   - What we know: LLM must return raw Cypher string, not markdown or JSON
   - What's unclear: Whether the LLM reliably returns raw Cypher vs code blocks
   - Recommendation: Add output parsing in `cypher.py` to strip markdown fences: `response.content.strip().strip("```cypher").strip("```").strip()`

3. **ANALYZE node output format → FORMAT node input**
   - What we know: FORMAT receives `state["final_output"]` from ANALYZE (or from ANALYZE's output key)
   - What's unclear: Whether ANALYZE writes to `final_output` or to an intermediate `analysis_text` key not currently in WorkflowState
   - Recommendation: ANALYZE writes to a new intermediate key `analysis_result: str` in WorkflowState; FORMAT reads it and produces `final_output: dict`. This keeps ANALYZE and FORMAT clearly separated and independently testable. Add `analysis_result: str` to WorkflowState.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 + pytest-asyncio 1.3.0 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/workflow/ -x --tb=short` |
| Full suite command | `pytest --tb=short` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AGENT-01 | PLAN node writes `plan_strategy`, returns only that key | unit | `pytest tests/workflow/test_plan.py -x` | ❌ Wave 0 |
| AGENT-02 | GENERATE_CYPHER injects schema + few-shots into prompt | unit | `pytest tests/workflow/test_cypher.py -x` | ❌ Wave 0 |
| AGENT-03 | VALIDATE traps exception (mode A) and empty result (mode B) | unit | `pytest tests/workflow/test_validate.py -x` | ❌ Wave 0 |
| AGENT-04 | Failed VALIDATE appends error, routes to GENERATE_CYPHER | unit | `pytest tests/workflow/test_graph.py::test_single_retry -x` | ❌ Wave 0 |
| AGENT-05 | retry_count never exceeds 3; cap routes to FORMAT graceful error | unit | `pytest tests/workflow/test_graph.py::test_retry_cap -x` | ❌ Wave 0 |
| AGENT-06 | ANALYZE reads db_results, writes final_output via FORMAT | unit | `pytest tests/workflow/test_analyze.py tests/workflow/test_format.py -x` | ❌ Wave 0 |
| AGENT-07 | Each node returns only owned keys; reducer accumulates validation_errors | unit | `pytest tests/workflow/test_state.py tests/workflow/test_graph.py -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/workflow/ -x --tb=short`
- **Per wave merge:** `pytest --tb=short`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/workflow/__init__.py` — package marker
- [ ] `tests/workflow/conftest.py` — `stub_driver`, `mock_llm` fixtures
- [ ] `tests/workflow/test_state.py` — covers AGENT-07 (reducer behavior)
- [ ] `tests/workflow/test_graph.py` — covers AGENT-04, AGENT-05 (routing logic)
- [ ] `tests/workflow/test_plan.py` — covers AGENT-01
- [ ] `tests/workflow/test_cypher.py` — covers AGENT-02
- [ ] `tests/workflow/test_validate.py` — covers AGENT-03
- [ ] `tests/workflow/test_analyze.py` — covers AGENT-06 (analyze side)
- [ ] `tests/workflow/test_format.py` — covers AGENT-06 (format side)
- [ ] `src/workflow/__init__.py` — package marker
- [ ] `src/workflow/nodes/__init__.py` — package marker
- [ ] Dependency install: `pip install langchain-anthropic` — add to `pyproject.toml`

---

## Sources

### Primary (HIGH confidence)
- [LangGraph Use Graph API](https://docs.langchain.com/oss/python/langgraph/use-graph-api) — TypedDict state, Annotated reducers, `operator.add`, node partial updates, `add_node`/`add_edge`/`add_conditional_edges`/`compile()`
- [LangGraph Quickstart](https://docs.langchain.com/oss/python/langgraph/quickstart) — Full StateGraph assembly pattern, invocation, conditional edges
- [LangGraph Test Docs](https://docs.langchain.com/oss/python/langgraph/test) — `compiled_graph.nodes["node_name"].invoke()` for node isolation, `MemorySaver` pattern
- SCHEMA.md v1.0.0 (project file, verified 2026-03-15) — all node labels and relationship types for few-shot examples
- `pip list` output (venv inspection, 2026-03-15) — confirmed langgraph 1.0.10, langchain-core 1.2.19, langchain-anthropic NOT INSTALLED

### Secondary (MEDIUM confidence)
- [nakamasato LangGraph test patterns](https://www.nakamasato.com/gpt-training/langchain/langgraph/test/) — MagicMock patterns for LLM and retriever mocking, `side_effect` lists
- [LangGraph conditional edges guide](https://fedorkobak.github.io/python/ds_ml/langchain/langgraph/conditional_edges.html) — path_map as list vs dict, Literal return type
- [add_conditional_edges path_map issue #987](https://github.com/langchain-ai/langgraph/issues/987) — confirmed list form works when return values match node names
- Existing `tests/unit/test_models.py` (project file) — confirms `unittest.mock.patch` as project convention, NOT pytest-mock

### Tertiary (LOW confidence)
- WebSearch results for retry-cap testing patterns — not verified against official LangGraph docs; code examples in this document are original derivations from confirmed patterns

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — langgraph 1.0.10 installed and API verified via official docs
- Architecture: HIGH — patterns derived from official LangGraph docs and confirmed against project conventions
- Pitfalls: HIGH for pitfalls 1-5 (verified against installed package state and official docs); MEDIUM for pitfall 6 (LLM hallucination behavior is domain knowledge, not doc-verified)
- Few-shot examples: HIGH — derived directly from SCHEMA.md v1.0.0 which was verified against the live graph

**Research date:** 2026-03-15
**Valid until:** 2026-04-15 (LangGraph 1.x stable; anthropic model names stable; reassess if LangGraph 2.0 releases)
