# Phase 4: FastAPI + HTMX Web Layer - Pattern Map

**Mapped:** 2026-04-19
**Files analyzed:** 12 new files + 2 existing files called at integration points
**Analogs found:** 10 / 12 (2 have no close analog — new patterns for FastAPI/SSE)

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/web/__init__.py` | config | — | `src/etl/__init__.py` (implicit package) | structural-match |
| `src/web/app.py` | config/provider | request-response | `src/workflow/run.py` | role-match (async driver init pattern identical) |
| `src/web/routes/api.py` | controller | request-response + streaming | `src/workflow/run.py` (initial_state build) | partial-match |
| `src/web/routes/admin.py` | controller | request-response | `src/etl/run_etl.py` (driver + try/finally pattern) | role-match |
| `src/web/routes/pages.py` | controller | request-response | `src/workflow/run.py` | partial-match |
| `src/web/streaming.py` | service | streaming | `src/workflow/graph.py` (build_graph call pattern) | partial-match |
| `src/web/dependencies.py` | middleware/utility | request-response | `tests/conftest.py` (driver fixture pattern) | partial-match |
| `src/web/templates/index.html` | component | request-response | — | no-analog |
| `src/web/templates/partials/result.html` | component | request-response | `src/workflow/nodes/format.py` (TeamOutput schema) | data-contract-match |
| `tests/web/conftest.py` | test | — | `tests/workflow/conftest.py` | exact |
| `tests/web/unit/test_app.py` | test | request-response | `tests/workflow/test_graph.py` | role-match |
| `tests/web/unit/test_api.py` | test | request-response | `tests/workflow/test_validate.py` | role-match |
| `tests/web/unit/test_streaming.py` | test | streaming | `tests/workflow/test_graph.py` | role-match |
| `tests/web/unit/test_admin.py` | test | request-response | `tests/workflow/test_validate.py` | role-match |

---

## Pattern Assignments

### `src/web/app.py` (config/provider, request-response)

**Analog:** `src/workflow/run.py`

**Imports pattern** (`src/workflow/run.py` lines 1-16):
```python
import os

from dotenv import load_dotenv
from neo4j import AsyncGraphDatabase

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_AUTH = tuple(os.getenv("NEO4J_AUTH", "neo4j/anothereden").split("/", 1))
```

**Core lifespan pattern** (adapted from `src/workflow/run.py` lines 32-53 + RESEARCH.md Pattern 1):
```python
# Copy driver creation from run.py lines 32-33; wrap in asynccontextmanager for FastAPI
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup — same driver creation as run.py line 32
    app.state.driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)
    yield
    # Shutdown — same pattern as run.py finally block (line 53)
    await app.state.driver.close()

app = FastAPI(lifespan=lifespan)
```

**Error handling pattern** (`src/workflow/run.py` lines 48-51):
```python
    except Exception as exc:  # noqa: BLE001
        # Graceful degradation: return error dict instead of raising.
        # Covers LLM credential errors, Neo4j connection failures, etc.
        return {"error": str(exc), "error_type": type(exc).__name__}
```
Adapt this for JSON HTTP responses in admin and api routes: `{"status": "error", "message": str(exc)}`.

---

### `src/web/routes/api.py` (controller, request-response + streaming)

**Analog:** `src/workflow/run.py` (initial_state construction) + `src/workflow/graph.py` (build_graph call)

**Initial state construction** (`src/workflow/run.py` lines 34-45):
```python
        initial_state = {
            "user_query": query,
            "roster": roster,
            "plan_strategy": "",
            "cypher_query": "",
            "db_results": [],
            "validation_errors": [],
            "retry_count": 0,
            "analysis_result": "",
            "final_output": {},
        }
```
Copy this dict verbatim into `streaming.py` — it is the canonical initial state shape.

**Entities endpoint Neo4j pattern** (adapted from `tests/conftest.py` lines 40-46):
```python
async def db_has_characters(driver, minimum: int = 100) -> bool:
    records, _, _ = await driver.execute_query(
        "MATCH (n:Character) RETURN count(n) AS cnt",
        database_="neo4j",
    )
    return records[0]["cnt"] >= minimum
```
`GET /api/entities` uses `driver.execute_query(...)` with `database_="neo4j"` — the same three-tuple unpack `records, _, _`.

**Pydantic request model** (pattern from `src/workflow/nodes/format.py` lines 22-43 as structural reference):
```python
from pydantic import BaseModel

class QueryRequest(BaseModel):
    query: str
    roster: list[str]
```

---

### `src/web/routes/admin.py` (controller, request-response)

**Analog:** `src/etl/run_etl.py`

**ETL invocation pattern** (`src/etl/run_etl.py` lines 29-53):
```python
async def main(driver=None) -> None:
    _own_driver = driver is None
    if _own_driver:
        driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)
    try:
        await driver.verify_connectivity()
        # ... ETL steps ...
    finally:
        if _own_driver:
            await driver.close()
```
Key insight: `run_etl.main()` accepts `driver=` kwarg — pass the lifespan singleton directly. `_own_driver = False` path will skip closing the shared driver.

**Error handling pattern** (`src/etl/run_etl.py` + `src/workflow/run.py` lines 48-51):
```python
    try:
        from src.etl.run_etl import main as run_etl
        await run_etl(driver=driver)
        return {"status": "ok", "message": "ETL complete"}
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "message": str(exc)}
```

**Expected counts source** (`src/etl/constants.py` lines 24-29):
```python
EXPECTED_NODE_COUNTS = {
    "Character": 300,  # wiki has 393
    "Grasta": 460,     # wiki audit 2026-03-15: actual=489
    "Ore": 50,         # wiki has 61
    "Trait": 10,
}
```
Use `EXPECTED_NODE_COUNTS` to report counts in success message: import from `src.etl.constants`.

---

### `src/web/streaming.py` (service, streaming)

**Analog:** `src/workflow/graph.py` + `src/workflow/run.py`

**Graph invocation pattern** (`src/workflow/run.py` lines 34-47 and `src/workflow/graph.py` lines 55-96):
```python
    # From run.py — build graph with singleton driver (not per-request driver creation)
    graph = build_graph(driver=driver)  # graph.py line 55: driver injected via closure
    result = await graph.ainvoke(initial_state)  # run.py line 46: always ainvoke, never invoke
```
For streaming, replace `ainvoke` with `astream(initial_state, stream_mode="updates", version="v2")`.

**Node name mapping** (from `src/workflow/graph.py` lines 69-80 — the `add_node` call strings are the SSE labels):
```python
# graph.py add_node calls define the exact keys in astream chunks:
builder.add_node("plan", _plan)           # → chunk["data"]["plan"]
builder.add_node("generate_cypher", ...)  # → chunk["data"]["generate_cypher"]
builder.add_node("validate", _validate)   # → chunk["data"]["validate"]
builder.add_node("analyze", analyze_node) # → chunk["data"]["analyze"]
builder.add_node("format", format_node)   # → chunk["data"]["format"]

# Map to display labels in streaming.py:
NODE_LABELS = {
    "plan": "PLAN",
    "generate_cypher": "CYPHER",
    "validate": "VALIDATE",
    "analyze": "ANALYZE",
    "format": "FORMAT",
}
```

**Retry count pattern** (`src/workflow/nodes/format.py` lines 104-108 and `tests/workflow/test_validate.py` lines 62-72):
```python
# format_node shows the retry_count boundary: retry_count >= 3 is exhausted
retry_count = state.get("retry_count", 0)
# In streaming.py, for VALIDATE events: attempt = retry_count + 1
# (retry_count in the update is the NEW value after increment)
```

**Final output schema** (`src/workflow/nodes/format.py` lines 37-43):
```python
class TeamOutput(BaseModel):
    frontline: list[CharacterSlot]   # list of {name, role, grastas: list[str]}
    reserve: list[CharacterSlot]
    synergy_explanation: str
    error: Optional[str] = None
```
`streaming.py` passes `final_output` dict (already `model_dump()`'d by format_node) to Jinja2 template.

---

### `src/web/dependencies.py` (utility, request-response)

**Analog:** `tests/conftest.py` (driver fixture as structural reference)

**Session-scoped driver from conftest** (`tests/conftest.py` lines 28-37):
```python
@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def async_driver():
    driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)
    yield driver
    await driver.close()
```
The web dependency reads from `app.state` instead of creating its own; it mirrors the fixture's intent (one driver, shared):
```python
from fastapi import Request
from neo4j import AsyncDriver

def get_driver(request: Request) -> AsyncDriver:
    return request.app.state.driver
```

---

### `src/web/templates/partials/result.html` (component, request-response)

**Analog:** `src/workflow/nodes/format.py` (TeamOutput schema defines the template's iteration contract)

**Template iteration contract** (`src/workflow/nodes/format.py` lines 37-43 + lines 122-124):
```python
# format_node returns model_dump() of TeamOutput — template receives this as `result`:
# result.frontline = [{"name": str, "role": str, "grastas": [str, ...]}]  ← up to 4 items
# result.reserve   = [{"name": str, "role": str, "grastas": [str, ...]}]  ← up to 2 items
# result.synergy_explanation = str
# result.error = str | None  (error path when retry cap exhausted)

# Template must handle both happy path and error path:
# {% if result.error %} ... show error ... {% else %} ... show team grid ... {% endif %}
```

**Error path detection** (`src/workflow/nodes/format.py` lines 108-117):
```python
    if retry_count >= 3 and not db_results:
        return {
            "final_output": {
                "frontline": [],
                "reserve": [],
                "synergy_explanation": "",
                "error": error_str,
            }
        }
```
Template guard: `{% if result.get('error') %}` shows error message; `{% else %}` renders the card grid.

---

### `tests/web/conftest.py` (test config)

**Analog:** `tests/workflow/conftest.py` (exact structural copy, adapted for web layer)

**Full conftest pattern** (`tests/workflow/conftest.py` lines 1-63):
```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from langchain_core.messages import AIMessage

@pytest.fixture
def stub_driver():
    driver = MagicMock()
    driver.execute_query = AsyncMock(return_value=([{"name": "Aldo"}], None, None))
    return driver
```
Web conftest needs the same `stub_driver` fixture plus:
- `mock_graph` — `MagicMock()` with `astream` as an `AsyncMock` (async generator)
- `mock_templates` — `MagicMock()` with `env.get_template(...).render(...)` returning stub HTML
- `test_app` — FastAPI app instance with overridden `get_driver` dependency pointing to `stub_driver`

---

### `tests/web/unit/test_app.py` (test, request-response)

**Analog:** `tests/workflow/test_graph.py`

**Async test class pattern** (`tests/workflow/test_graph.py` lines 79-92):
```python
class TestGraphHappyPath:
    @pytest.mark.asyncio
    async def test_full_graph_happy_path(self, stub_driver, sample_state):
        graph = build_graph(driver=stub_driver)
        result = await graph.ainvoke(sample_state)
        assert "final_output" in result
```

**TestClient with lifespan pattern** (adapted from RESEARCH.md Code Examples):
```python
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

def test_lifespan_creates_driver():
    with patch("src.web.app.AsyncGraphDatabase.driver") as mock_driver_factory:
        mock_driver_factory.return_value = MagicMock()
        with TestClient(app) as client:  # TestClient triggers lifespan on __enter__
            assert hasattr(app.state, "driver")
            assert app.state.driver is mock_driver_factory.return_value
```

---

### `tests/web/unit/test_api.py` (test, request-response)

**Analog:** `tests/workflow/test_validate.py`

**AsyncMock driver pattern** (`tests/workflow/test_validate.py` lines 39-46):
```python
def _make_driver(records=None, raise_exc=None):
    driver = MagicMock()
    if raise_exc:
        driver.execute_query = AsyncMock(side_effect=raise_exc)
    else:
        driver.execute_query = AsyncMock(return_value=(records or [], None, None))
    return driver
```
Copy this helper into `tests/web/conftest.py` or inline it in `test_api.py`.

**Patch pattern** (`tests/workflow/test_validate.py` lines 57-66):
```python
        with patch("src.workflow.nodes.validate.get_llm", return_value=mock_haiku):
            result = await validate_node(state, driver)
```
For web tests: `with patch("src.web.routes.api.get_driver", return_value=stub_driver)`.

---

### `tests/web/unit/test_streaming.py` (test, streaming)

**Analog:** `tests/workflow/test_graph.py` (async generator consumption pattern)

**Async generator mock pattern** (`tests/workflow/test_graph.py` lines 86-121):
```python
    @pytest.mark.asyncio
    async def test_full_graph_happy_path(self, stub_driver, sample_state):
        with patch("src.workflow.nodes.plan.get_llm", return_value=_mock_llm_factory(...)), \
             patch("src.workflow.nodes.cypher.get_llm", return_value=_mock_llm_factory(...)):
            graph = build_graph(driver=stub_driver)
            result = await graph.ainvoke(sample_state)
```
For SSE tests, consume the async generator directly (not through TestClient):
```python
    async def mock_astream(*args, **kwargs):
        yield {"type": "updates", "data": {"plan": {"plan_strategy": "test"}}}
        yield {"type": "updates", "data": {"format": {"final_output": {...}}}}

    mock_graph.astream = mock_astream

    with patch("src.web.streaming.build_graph", return_value=mock_graph):
        events = []
        async for event in pipeline_sse_generator(...):
            events.append(event)
```

**pytest.ini setting** (`pytest.ini` lines 1-3):
```ini
[pytest]
asyncio_mode = auto
asyncio_default_fixture_loop_scope = session
asyncio_default_test_loop_scope = session
```
`asyncio_mode = auto` means `@pytest.mark.asyncio` is optional but must still be used for clarity per existing test convention (`tests/workflow/test_validate.py` uses it on every async test).

---

### `tests/web/unit/test_admin.py` (test, request-response)

**Analog:** `tests/workflow/test_validate.py` (mock + patch structure)

**Patch + assert pattern** (`tests/workflow/test_validate.py` lines 319-328):
```python
        with patch("src.workflow.nodes.validate.get_llm", return_value=mock_haiku) as mock_get_llm:
            await validate_node(state, driver)
        mock_get_llm.assert_called_once_with(role="validator")
```
For admin tests: patch `src.web.routes.admin.run_etl` to avoid live ETL execution:
```python
def test_refresh_data_valid_key(monkeypatch):
    with patch("src.web.routes.admin.run_etl", new_callable=AsyncMock) as mock_etl:
        with TestClient(app) as client:
            resp = client.post("/admin/refresh-data", headers={"X-Admin-Key": "test-key"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
        mock_etl.assert_called_once()
```

---

## Shared Patterns

### Neo4j Driver Initialization
**Source:** `src/workflow/run.py` lines 18-19 and lines 32-33
**Apply to:** `src/web/app.py` (lifespan), `tests/web/conftest.py` (mock override)
```python
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_AUTH = tuple(os.getenv("NEO4J_AUTH", "neo4j/anothereden").split("/", 1))
# Creation:
driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)
```

### Neo4j execute_query Call Convention
**Source:** `tests/conftest.py` lines 41-45 and `tests/workflow/conftest.py` lines 30-31
**Apply to:** `src/web/routes/api.py` (GET /api/entities), `tests/web/unit/test_api.py`
```python
records, _, _ = await driver.execute_query(
    "MATCH (n:Character) RETURN ...",
    database_="neo4j",
)
```
Always use `database_="neo4j"` keyword argument. Always unpack the three-tuple with `_, _` discarding summary and keys.

### Error Handling (Graceful Degradation)
**Source:** `src/workflow/run.py` lines 48-51
**Apply to:** `src/web/routes/admin.py`, `src/web/routes/api.py`, `src/web/streaming.py`
```python
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc), "error_type": type(exc).__name__}
```
Web layer variant: return `{"status": "error", "message": str(exc)}` with HTTP 500 for admin; SSE generator should yield a final `"done"` event even on error.

### AsyncMock Driver in Tests
**Source:** `tests/workflow/conftest.py` lines 17-31
**Apply to:** All `tests/web/unit/` test files
```python
@pytest.fixture
def stub_driver():
    driver = MagicMock()
    driver.execute_query = AsyncMock(return_value=([{"name": "Aldo"}], None, None))
    return driver
```
`execute_query` MUST be `AsyncMock` (not `MagicMock`) because the web layer `await`s it.

### Async Test Class Pattern
**Source:** `tests/workflow/test_validate.py` lines 53-72 and `tests/workflow/test_graph.py` lines 79-92
**Apply to:** All `tests/web/unit/` test files
```python
class TestFeatureName:
    @pytest.mark.asyncio
    async def test_something(self, stub_driver):
        ...
```
Use class grouping for related test cases (e.g., `TestGetEntities`, `TestPostQuery`, `TestStreamJob`). Always add `@pytest.mark.asyncio` even with `asyncio_mode = auto` (project convention from existing tests).

### patch() Context Manager Pattern
**Source:** `tests/workflow/test_graph.py` lines 106-119
**Apply to:** All `tests/web/unit/` test files
```python
        with patch("src.workflow.nodes.plan.get_llm",
                   return_value=_mock_llm_factory("...")), \
             patch("src.workflow.nodes.cypher.get_llm",
                   return_value=_mock_llm_factory("...")):
            graph = build_graph(driver=stub_driver)
            result = await graph.ainvoke(sample_state)
```
Use `patch()` at the module-local import path (e.g., `src.web.routes.api.get_driver`, not `fastapi.Depends`).

### build_graph(driver=) Call Pattern
**Source:** `src/workflow/run.py` line 34 and `src/workflow/graph.py` lines 55-96
**Apply to:** `src/web/streaming.py`
```python
    graph = build_graph(driver=driver)  # driver is the lifespan singleton via get_driver()
    # Never create a new driver inside streaming.py — always use the injected singleton
```

---

## No Analog Found

Files with no close match in the codebase (planner should use RESEARCH.md patterns instead):

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `src/web/templates/index.html` | component | request-response | No HTML templates exist anywhere in the codebase — new pattern; use RESEARCH.md Pattern 4 + Pattern 8 for HTMX SSE attributes and localStorage JS |
| `src/web/templates/partials/progress.html` | component | streaming | No HTML templates exist — new pattern; use RESEARCH.md Pattern 4 for `sse-connect`, `sse-swap`, `sse-close` attributes |
| `src/web/static/app.js` | utility | event-driven | No JavaScript files exist in the codebase — new pattern; use RESEARCH.md Pattern 8 for the localStorage + client-side filter snippet |

---

## Key Implementation Notes for Planner

1. **`run_etl.main(driver=driver)` is safe to call with the lifespan singleton.** `src/etl/run_etl.py` line 39 (`_own_driver = driver is None`) ensures it will not close the shared driver when `driver` is passed.

2. **`build_graph(driver=driver)` call is safe per request.** `src/workflow/graph.py` lines 55-96 show `build_graph` compiles a new graph instance (cheap) but reuses the injected driver — no per-request driver creation.

3. **`ainvoke` is the only valid invocation pattern.** `src/workflow/run.py` line 46 uses `ainvoke`. `src/workflow/graph.py` line 75-80 shows `validate_node` is async — `invoke` would block the event loop.

4. **`asyncio_mode = auto` is active** (`pytest.ini` lines 1-3) — all `async def test_*` functions are automatically async tests. Still decorate with `@pytest.mark.asyncio` per project convention.

5. **Three-tuple unpack is mandatory.** `driver.execute_query()` returns `(records, summary, keys)`. Project tests always unpack as `records, _, _` — never just `records = await driver.execute_query(...)`.

6. **FORMAT node output schema is the single source of truth for templates.** `src/workflow/nodes/format.py` lines 37-43 define `CharacterSlot` and `TeamOutput` — Jinja2 templates must iterate exactly these field names: `result.frontline`, `result.reserve`, `result.synergy_explanation`, `result.error`.

---

## Metadata

**Analog search scope:** `src/workflow/`, `src/etl/`, `tests/`, `tests/workflow/`
**Files scanned:** 8 source files + 2 conftest files + 2 test files (13 total reads)
**Pattern extraction date:** 2026-04-19
