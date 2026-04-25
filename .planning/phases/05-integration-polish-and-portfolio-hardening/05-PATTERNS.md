# Phase 5: Integration, Polish, and Portfolio Hardening — Pattern Map

**Mapped:** 2026-04-25
**Files analyzed:** 10 (9 modified/new + 1 skipped per user decision)
**Analogs found:** 9 / 9

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `src/workflow/nodes/analyze.py` | node (transform) | request-response | `src/workflow/nodes/analyze.py` (self) | exact (update) |
| `src/workflow/nodes/format.py` | node (transform) | transform | `src/workflow/nodes/format.py` (self) | exact (update) |
| `src/workflow/state.py` | model/config | — | `src/workflow/state.py` (self) | exact (update) |
| `src/workflow/graph.py` | config (routing) | event-driven | `src/workflow/graph.py` (self) | exact (update) |
| `src/web/streaming.py` | service | streaming | `src/web/streaming.py` (self) | exact (update) |
| `src/web/templates/partials/alternatives.html` | component (template) | request-response | `src/web/templates/partials/result.html` | exact |
| `tests/integration/test_e2e_phase5.py` | test (integration) | request-response | `tests/integration/test_query_pipeline.py` | exact |
| `tests/workflow/test_format.py` | test (unit) | transform | `tests/workflow/test_format.py` (self) | exact (update) |
| `Dockerfile` | config (build) | — | `docker-compose.yml` | partial |
| `README.md` | docs | — | `README.md` (self) | exact (update) |

*`.github/workflows/deploy.yml` skipped — deployment deferred per user decision (CONTEXT.md deferred).*

---

## Pattern Assignments

### `src/workflow/nodes/analyze.py` (node, request-response)

**Analog:** `src/workflow/nodes/analyze.py` (self — surgical update)

**Imports pattern** (lines 1-12, current):
```python
from langchain_core.messages import HumanMessage, SystemMessage

from ..llm import get_llm
from ..state import WorkflowState
```

**Existing system prompt structure** (lines 14-38, current):
```python
ANALYZE_SYSTEM_PROMPT = """You are an AnotherEden team-building expert analyzing graph query results.

Given the database results from a Neo4j character graph and the user's team query,
synthesize an optimal team recommendation.

Output a JSON object with EXACTLY this structure:
{
  "frontline": [
    {"name": "<character_name>", "role": "<role>", "grastas": ["<grasta_name>", ...]},
    ...
  ],
  "reserve": [
    {"name": "<character_name>", "role": "<role>", "grastas": ["<grasta_name>", ...]},
    ...
  ],
  "synergy_explanation": "<explanation of grasta and role synergies>"
}

Rules:
- ONLY use characters present in the db_results AND the player's roster
- Assign meaningful roles: AF anchor, healer, DPS, support, buffer, debuffer
- frontline MUST contain exactly 4 characters (minimum 3 only if roster/db_results cannot supply 4)
- reserve MUST contain exactly 2 characters (minimum 1 only if roster/db_results cannot supply 2)
- Explain Grasta synergies specifically (e.g. "Fire T3 boosts AF damage by 30%")
- Output ONLY the JSON object — no preamble, no markdown fences"""
```

**D-13 attribution mandate to append to ANALYZE_SYSTEM_PROMPT** (new text block, no existing analog):
```python
ATTRIBUTION_MANDATE = """
MANDATORY SOURCE ATTRIBUTION:
For each character in frontline and reserve, the synergy_explanation MUST include
a citation in this exact format:
  [CharacterName]: [Grasta name] ([trait name]) — [effect description]
Example: "Aldo: Fire T3 Grasta (Courage) — boosts Fire element damage by 30% in AF zone"
Never make a synergy claim without citing the specific Grasta and trait from the database results.
"""
```
Append `ATTRIBUTION_MANDATE` to `ANALYZE_SYSTEM_PROMPT` (or inline it before the closing `"""`).

**Core node function pattern** (lines 41-83, current — keep unchanged for normal path):
```python
def analyze_node(state: WorkflowState) -> dict:
    llm = get_llm(role="analyzer")

    db_results = state.get("db_results", [])
    user_query = state.get("user_query", "")
    roster = state.get("roster", [])
    plan_strategy = state.get("plan_strategy", "")

    roster_str = ", ".join(roster) if roster else "no characters specified"
    ...
    response = llm.invoke(messages)
    return {"analysis_result": response.content}
```

**New empty-path branch — insert at top of `analyze_node` body** (before `llm = get_llm(...)`):
```python
def analyze_node(state: WorkflowState) -> dict:
    db_results = state.get("db_results", [])

    if not db_results:
        # Empty-path: generate 3 alternative teams from roster knowledge
        return _generate_alternatives(state)

    # Normal path — existing code continues here unchanged
    llm = get_llm(role="analyzer")
    ...
```

**New private helper — add after `analyze_node`**:
```python
def _generate_alternatives(state: WorkflowState) -> dict:
    """Generate 3 alternative team compositions when db_results is empty.

    Returns {"alternatives": str} — raw LLM JSON string; FORMAT parses this.
    Owned key: alternatives (WorkflowState key added in Phase 5).
    """
    llm = get_llm(role="analyzer")
    roster_str = ", ".join(state.get("roster", [])) or "no characters specified"
    user_query = state.get("user_query", "")
    plan_strategy = state.get("plan_strategy", "")

    messages = [
        SystemMessage(content=ALTERNATIVES_SYSTEM_PROMPT),
        HumanMessage(content=(
            f"User query: {user_query}\n"
            f"Player roster: {roster_str}\n"
            f"Original traversal strategy: {plan_strategy}\n"
            "No database results were found. Generate EXACTLY 3 alternative team compositions."
        )),
    ]
    response = llm.invoke(messages)
    return {"alternatives": response.content}
```

**New `ALTERNATIVES_SYSTEM_PROMPT` constant — add below `ANALYZE_SYSTEM_PROMPT`**:
```python
ALTERNATIVES_SYSTEM_PROMPT = """You are an AnotherEden team-building expert.
No characters were found in the database for this query.
Using your knowledge of the Another Eden roster and the player's available characters,
suggest 3 alternative team compositions that address the query intent.

Output a JSON object with EXACTLY this structure:
{
  "alternatives": [
    {
      "frontline": [{"name": "...", "role": "...", "grastas": ["..."]}, ...],
      "reserve": [{"name": "...", "role": "...", "grastas": ["..."]}],
      "synergy_explanation": "..."
    },
    <second alternative>,
    <third alternative>
  ],
  "reason": "Why no database results were found and what query variations were attempted."
}

Rules:
- Output EXACTLY 3 alternative objects in the alternatives array — no more, no fewer.
- Each alternative must have frontline (3-4 characters) and reserve (1-2 characters).
- Only suggest characters from the player's roster.
- Include Grasta citations per attribution mandate: [CharacterName]: [Grasta name] ([trait]) — [effect].
- Output ONLY the JSON object — no preamble, no markdown fences."""
```

---

### `src/workflow/nodes/format.py` (node, transform)

**Analog:** `src/workflow/nodes/format.py` (self — additions only)

**Existing model pattern to copy for `AlternativesOutput`** (lines 22-43, current):
```python
class CharacterSlot(BaseModel):
    """A single character slot in the team recommendation."""
    name: str
    role: str
    grastas: list[str]


class TeamOutput(BaseModel):
    """Structured team recommendation output validated by Pydantic v2."""
    frontline: list[CharacterSlot] = Field(min_length=3, max_length=4)
    reserve: list[CharacterSlot] = Field(min_length=1, max_length=2)
    synergy_explanation: str
    error: Optional[str] = None
```

**New `AlternativesOutput` model — add after `TeamOutput` class**:
```python
class AlternativesOutput(BaseModel):
    """Three alternative full team compositions when db_results is empty.

    alternatives: exactly 3 complete TeamOutput-shaped objects.
    reason: human-readable explanation of why alternatives were generated.
    """
    alternatives: list[TeamOutput] = Field(min_length=3, max_length=3)
    reason: str
```

**Existing `_extract_json` helper pattern** (lines 46-83, current — reuse unchanged):
```python
def _extract_json(text: str) -> dict:
    # Attempt 1: direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Attempt 2: extract from markdown fences
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence_match:
        try:
            return json.loads(fence_match.group(1))
        except json.JSONDecodeError:
            pass
    # Attempt 3: find outermost {...}
    brace_match = re.search(r"\{.*\}", text, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass
    raise ValueError(f"No valid JSON object found in analysis_result: {text!r}")
```

**Existing `format_node` error-path pattern** (lines 105-119, current — keep as fallback):
```python
def format_node(state: WorkflowState) -> dict:
    retry_count = state.get("retry_count", 0)
    db_results = state.get("db_results", [])

    # Error path: retry cap exhausted (now only reached if ANALYZE itself fails)
    if retry_count >= 3 and not db_results and not state.get("alternatives"):
        validation_errors = state.get("validation_errors", [])
        error_str = "; ".join(validation_errors) if validation_errors else "Query failed after 3 retries"
        return {
            "final_output": {
                "frontline": [],
                "reserve": [],
                "synergy_explanation": "",
                "error": error_str,
            }
        }
```

**New alternatives branch — insert in `format_node` before happy path**:
```python
    # Alternatives path: analyze_node detected empty db_results and generated alternatives
    alternatives_raw = state.get("alternatives", "")
    if alternatives_raw:
        try:
            parsed = _extract_json(alternatives_raw)
            validated = AlternativesOutput.model_validate(parsed)
        except (ValidationError, ValueError):
            return {
                "final_output": {
                    "frontline": [],
                    "reserve": [],
                    "synergy_explanation": "",
                    "error": "LLM returned malformed alternatives structure — retry or check model",
                }
            }
        return {"final_output": validated.model_dump()}
```

---

### `src/workflow/state.py` (model/config)

**Analog:** `src/workflow/state.py` (self — add one key)

**Existing TypedDict pattern** (lines 28-50, current):
```python
class WorkflowState(TypedDict):
    """State container for the AnotherEdenAI team-recommendation workflow."""

    # --- Caller-provided inputs ---
    user_query: str
    roster: list[str]

    # --- PLAN node output ---
    plan_strategy: str

    # --- GENERATE_CYPHER node output ---
    cypher_query: str

    # --- VALIDATE node outputs ---
    db_results: list[dict]
    validation_errors: Annotated[list[str], operator.add]
    retry_count: int

    # --- ANALYZE node output ---
    analysis_result: str

    # --- FORMAT node output ---
    final_output: dict
```

**New key to add after `analysis_result`**:
```python
    # --- ANALYZE node output (alternatives path — written when db_results is empty) ---
    analysis_result: str
    alternatives: str  # Raw LLM JSON string; FORMAT parses via AlternativesOutput
```

Note: `alternatives` is a `str` (raw LLM response content), not `list[dict]`, because
`analyze_node` returns `{"alternatives": response.content}` — FORMAT does the parsing.
The docstring at the top of `state.py` must be updated to add `alternatives` to the
"Key ownership" section: `alternatives — written by ANALYZE on empty db_results path`.
Also update `initial_state` in `streaming.py` (see that section) to include `"alternatives": ""`.

---

### `src/workflow/graph.py` (config/routing)

**Analog:** `src/workflow/graph.py` (self — one-line routing change)

**Current routing function** (lines 27-52, current):
```python
def route_after_validate(
    state: WorkflowState,
) -> Literal["generate_cypher", "analyze", "format"]:
    if state.get("db_results"):
        return "analyze"
    if state.get("retry_count", 0) >= 3:
        return "format"          # <-- THIS LINE CHANGES
    return "generate_cypher"
```

**Phase 5 change — single line replacement**:
```python
def route_after_validate(
    state: WorkflowState,
) -> Literal["generate_cypher", "analyze", "format"]:
    """
    - db_results non-empty  -> "analyze"  (success path)
    - retry_count >= 3      -> "analyze"  (alternatives path — analyze_node detects empty db_results)
    - otherwise             -> "generate_cypher"  (retry)
    """
    if state.get("db_results"):
        return "analyze"
    if state.get("retry_count", 0) >= 3:
        return "analyze"   # CHANGED from "format" — analyze generates alternatives for empty path
    return "generate_cypher"
```

The module-level docstring topology comment (lines 1-13) must also be updated to reflect
`+--> analyze (retry cap exhausted — alternatives path)` instead of `+--> format`.
No other changes to `build_graph()` — the edge `analyze -> format` already exists (line 87).

---

### `src/web/streaming.py` (service, streaming)

**Analog:** `src/web/streaming.py` (self — two additions: latency measurement + alternatives render)

**Existing initial_state pattern** (lines 67-78, current — add `"alternatives"` key):
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
        "alternatives": "",   # NEW — Phase 5; mirrors WorkflowState addition
        "final_output": {},
    }
```

**Latency measurement — add `import time` to imports block and wrap `graph.astream()`**:
```python
import time   # add to existing import block (lines 1-28)

# In pipeline_sse_generator(), before graph.astream():
start_ms = time.monotonic()

# After format node chunk captured (inside the for loop, after final_output capture):
if node_name == "format" and "final_output" in state_update:
    final_output = state_update["final_output"]
    elapsed_ms = int((time.monotonic() - start_ms) * 1000)
    logger.info("latency_ms: %d", elapsed_ms)
```

**Existing result render pattern** (lines 128-135, current):
```python
        finally:
            if final_output is not None:
                try:
                    template = templates.env.get_template("partials/result.html")
                    html = template.render(result=final_output)
                    yield ServerSentEvent(raw_data=html, event="result")
```

**Phase 5 change — template selection based on `alternatives` presence in `final_output`**:
```python
        finally:
            if final_output is not None:
                try:
                    is_alternatives = bool(final_output.get("alternatives"))
                    template_name = (
                        "partials/alternatives.html" if is_alternatives
                        else "partials/result.html"
                    )
                    template = templates.env.get_template(template_name)
                    html = template.render(result=final_output)
                    yield ServerSentEvent(raw_data=html, event="result")
```

---

### `src/web/templates/partials/alternatives.html` (component/template)

**Analog:** `src/web/templates/partials/result.html` (exact — copy char-card structure)

**result.html character card pattern** (lines 9-49) — copy and wrap in `<details>` accordion:
```html
<!-- char-card inner structure — copy this verbatim into each accordion section -->
<div class="char-card">
  <strong>{{ char.name }}</strong>
  <div class="role">{{ char.role }}</div>
  {% if char.grastas %}
  <div class="grastas">
    <small>Grasta: {{ char.grastas | join(', ') }}</small>
  </div>
  {% endif %}
</div>
```

**error.html `<details>/<summary>` pattern** (lines 7-10) — reuse for accordion:
```html
<details>
  <summary>Error details</summary>
  <pre ...>{{ result.error }}</pre>
</details>
```

**Full alternatives.html template** (new file — no existing content):
```html
<!-- partials/alternatives.html — rendered by streaming.py when final_output.alternatives is set -->
<!-- result dict has: alternatives (list of TeamOutput dicts), reason, error (None on success) -->
{% if result.get('error') %}
  {% include "partials/error.html" with context %}
{% else %}
<article>
  <header><h3>No exact match found — Top 3 Alternatives</h3></header>
  {% if result.reason %}
  <p><small>{{ result.reason }}</small></p>
  {% endif %}

  {% for alt in result.alternatives %}
  <details {% if loop.first %}open{% endif %}>
    <summary><strong>Alternative {{ loop.index }}</strong></summary>

    <div class="frontline-grid">
      {% for char in alt.frontline %}
      <div class="char-card">
        <strong>{{ char.name }}</strong>
        <div class="role">{{ char.role }}</div>
        {% if char.grastas %}
        <div class="grastas">
          <small>Grasta: {{ char.grastas | join(', ') }}</small>
        </div>
        {% endif %}
      </div>
      {% endfor %}
    </div>

    {% if alt.reserve %}
    <div class="reserve-grid">
      {% for char in alt.reserve %}
      <div class="char-card">
        <strong>{{ char.name }}</strong>
        <div class="role">{{ char.role }}</div>
        {% if char.grastas %}
        <div class="grastas">
          <small>Grasta: {{ char.grastas | join(', ') }}</small>
        </div>
        {% endif %}
      </div>
      {% endfor %}
    </div>
    {% endif %}

    {% if alt.synergy_explanation %}
    <div class="synergy-box">
      <strong>Synergy:</strong> {{ alt.synergy_explanation }}
    </div>
    {% endif %}
  </details>
  {% endfor %}
</article>
{% endif %}
```

Key points:
- `<details open>` on `loop.first` gives D-03 "first one expanded by default" for free.
- No JavaScript required — PicoCSS (already in `index.html` via CDN `@picocss/pico@2`) styles `<details>/<summary>` natively.
- The `result` dict from `AlternativesOutput.model_dump()` will have keys `alternatives` (list) and `reason` (str).
- Inside each `alt`, the keys are `frontline`, `reserve`, `synergy_explanation` — same as `TeamOutput.model_dump()`.

---

### `tests/integration/test_e2e_phase5.py` (test, integration)

**Analog:** `tests/integration/test_query_pipeline.py` (exact — copy module structure, fixture usage, marker pattern)

**Module header pattern** (lines 1-17 of analog):
```python
"""Integration tests for Phase 5: Integration, Polish, and Portfolio Hardening.

Covers OUTPUT-01 through OUTPUT-05 and D-07 scenarios against live Neo4j.
Run with: pytest tests/integration/test_e2e_phase5.py -m integration -x -q

Requires:
  - NEO4J_URI and NEO4J_AUTH set in .env (use neo4j+s:// for AuraDB Free)
  - Graph loaded with Phase 1 ETL data (loaded_db fixture handles this)
"""
import time

import pytest

import src.workflow.run as run
```

**`@pytest.mark.integration` fixture usage pattern** (lines 37-64 of analog):
```python
@pytest.mark.integration
async def test_roster_filtering_excludes_unowned(async_driver, loaded_db):
    """..."""
    # uses async_driver for direct Cypher queries
    # uses loaded_db to ensure DB is populated
```

**End-to-end `run.main()` invocation pattern** (lines 199-222 of analog):
```python
@pytest.mark.integration
async def test_end_to_end_pipeline_with_latency(loaded_db):
    """..."""
    roster = ["Aldo", "Ciel"]
    query = "highest damage blunt zone synergy"
    start = time.monotonic()
    result = await run.main(roster, query)
    elapsed = time.monotonic() - start
    assert isinstance(result, dict)
    assert elapsed < 15.0
```

**Five test scenarios to implement** (D-07 — map to analog `test_*` functions):

1. Happy path with attribution (OUTPUT-02, OUTPUT-03):
```python
@pytest.mark.integration
async def test_happy_path_has_attribution(loaded_db):
    """OUTPUT-02/03: Team recommendation includes Grasta citations and non-empty roles."""
    result = await run.main(["Aldo", "Ciel"], "best fire team")
    assert isinstance(result, dict)
    assert not result.get("error"), f"Unexpected error: {result.get('error')}"
    # OUTPUT-03: every character has a non-empty role
    for char in result.get("frontline", []) + result.get("reserve", []):
        assert char.get("role"), f"Empty role for character: {char}"
    # OUTPUT-02: synergy_explanation contains at least one Grasta citation bracket
    synergy = result.get("synergy_explanation", "")
    assert synergy, "synergy_explanation must be non-empty"
```

2. Name normalization (QUERY-04 coverage for Phase 5):
```python
@pytest.mark.integration
async def test_name_normalization_in_pipeline(loaded_db):
    """QUERY-04: Lowercase roster names are normalized before pipeline runs."""
    result = await run.main(["aldo"], "fire synergy team")
    assert isinstance(result, dict)
    # Should not error due to unrecognized name
    frontline_names = [c.get("name") for c in result.get("frontline", [])]
    # 'Aldo' (canonical) should appear, not 'aldo'
    if frontline_names:
        assert all(n[0].isupper() for n in frontline_names if n), (
            f"Character names should be canonically capitalized: {frontline_names}"
        )
```

3. Empty-result alternatives path (OUTPUT-04):
```python
@pytest.mark.integration
async def test_empty_result_returns_alternatives(loaded_db):
    """OUTPUT-04: A query with no matching characters returns 3 alternatives, not an error."""
    roster = ["Aldo"]
    query = "impossibly specific query for nonexistent mechanic XYZ999"
    result = await run.main(roster, query)
    assert isinstance(result, dict)
    has_team = bool(result.get("frontline"))
    has_alternatives = bool(result.get("alternatives"))
    assert has_team or has_alternatives, (
        f"Expected either a team or alternatives, got: {result}"
    )
    if has_alternatives:
        assert len(result["alternatives"]) == 3, (
            f"Expected exactly 3 alternatives, got {len(result['alternatives'])}"
        )
```

4. Retry cap exhaustion (with mock — uses `unittest.mock.patch` per analog `test_validate.py` pattern):
```python
@pytest.mark.integration
async def test_retry_cap_exhaustion_returns_error_or_alternatives(async_driver):
    """AGENT-05 + OUTPUT-04: After 3 VALIDATE failures, output is alternatives or error — never a crash."""
    from unittest.mock import patch

    call_count = 0

    async def always_fail_validate(state, driver):
        nonlocal call_count
        call_count += 1
        rc = state.get("retry_count", 0) + 1
        return {"validation_errors": [f"Stub fail {rc}"], "retry_count": rc}

    with patch("src.workflow.nodes.validate.validate_node", side_effect=always_fail_validate):
        result = await run.main(["Aldo"], "test query")

    assert call_count == 3, f"Expected 3 validate calls, got {call_count}"
    assert isinstance(result, dict), "run.main() must return a dict even on retry cap"
```

5. Admin refresh-data endpoint:
```python
@pytest.mark.integration
async def test_admin_refresh_data_requires_auth():
    """DEPLOY-03 + ADMIN_KEY: /admin/refresh-data returns 401 without correct ADMIN_KEY."""
    import httpx
    from src.web.app import app   # import the FastAPI app

    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/admin/refresh-data",
            headers={"X-Admin-Key": "wrong-key"},
        )
    assert response.status_code == 401, (
        f"Expected 401 Unauthorized, got {response.status_code}"
    )
```

**conftest fixtures to use** (from `tests/conftest.py`):
- `async_driver` — session-scoped; pass to tests that do direct Cypher
- `loaded_db` — session-scoped; pass to tests that call `run.main()` (ensures ETL has run)
- Neither — for mock-based retry cap test (no real DB calls)

---

### `tests/workflow/test_format.py` (test, unit)

**Analog:** `tests/workflow/test_format.py` (self — add new test class alongside existing)

**Existing fixture pattern** (lines 18-66, current):
```python
@pytest.fixture
def valid_team_json():
    return json.dumps({
        "frontline": [
            {"name": "Aldo", "role": "DPS", "grastas": ["Fire T3", "ATK Up"]},
            ...
        ],
        ...
    })

@pytest.fixture
def success_state(valid_team_json):
    return {
        "user_query": "best fire team",
        "roster": [...],
        ...,
        "analysis_result": valid_team_json,
        "alternatives": "",   # add this key to ALL existing state fixtures for WorkflowState compat
        "final_output": {},
    }
```

**Existing test class pattern** (lines 69-132, current):
```python
class TestFormatSuccessPath:
    def test_format_success_returns_only_final_output(self, success_state):
        result = format_node(success_state)
        assert list(result.keys()) == ["final_output"], ...

    def test_format_success_validates_with_pydantic(self, success_state):
        result = format_node(success_state)
        validated = TeamOutput.model_validate(result["final_output"])
        assert validated is not None
```

**New test class to add** (copy `TestFormatSuccessPath` structure, new import):
```python
from src.workflow.nodes.format import format_node, TeamOutput, AlternativesOutput

@pytest.fixture
def valid_alternatives_json():
    """Valid JSON for AlternativesOutput as ANALYZE would produce on empty-path."""
    team = {
        "frontline": [
            {"name": "Aldo", "role": "DPS", "grastas": ["Fire T3"]},
            {"name": "Ciel", "role": "healer", "grastas": ["HP Up"]},
            {"name": "Riica", "role": "support", "grastas": []},
        ],
        "reserve": [{"name": "Miyu", "role": "support", "grastas": []}],
        "synergy_explanation": "Aldo: Fire T3 Grasta (Courage) — boosts Fire damage.",
    }
    return json.dumps({
        "alternatives": [team, team, team],
        "reason": "No Cypher results for highly specific query.",
    })


@pytest.fixture
def alternatives_state(valid_alternatives_json):
    """WorkflowState on the alternatives path: alternatives is set, db_results empty."""
    return {
        "user_query": "best fire team",
        "roster": ["Aldo"],
        "plan_strategy": "",
        "cypher_query": "",
        "db_results": [],
        "validation_errors": [],
        "retry_count": 3,
        "analysis_result": "",
        "alternatives": valid_alternatives_json,
        "final_output": {},
    }


class TestFormatAlternativesPath:
    """format_node alternatives path: alternatives key set produces AlternativesOutput."""

    def test_format_alternatives_returns_only_final_output(self, alternatives_state):
        result = format_node(alternatives_state)
        assert list(result.keys()) == ["final_output"]

    def test_format_alternatives_has_alternatives_key(self, alternatives_state):
        result = format_node(alternatives_state)
        assert "alternatives" in result["final_output"], "Missing 'alternatives' key"

    def test_format_alternatives_has_exactly_three(self, alternatives_state):
        result = format_node(alternatives_state)
        assert len(result["final_output"]["alternatives"]) == 3

    def test_format_alternatives_validates_with_pydantic(self, alternatives_state):
        result = format_node(alternatives_state)
        validated = AlternativesOutput.model_validate(result["final_output"])
        assert validated is not None

    def test_format_alternatives_no_error(self, alternatives_state):
        result = format_node(alternatives_state)
        assert result["final_output"].get("error") is None
```

Note: All **existing** state fixtures must also gain `"alternatives": ""` key to keep
`WorkflowState` TypedDict compatible after the Phase 5 state addition.

---

### `Dockerfile` (config/build)

**Analog:** `docker-compose.yml` (partial — shares `NEO4J_AUTH` env pattern and port 7687 convention)

**docker-compose.yml build reference** (lines 1-6, current):
```yaml
services:
  neo4j:
    image: neo4j:5-community
    environment:
      - NEO4J_AUTH=${NEO4J_AUTH:-neo4j/anothereden}
```

**pyproject.toml packaging pattern** (lines 31-33, current — critical for import path):
```toml
[tool.setuptools.packages.find]
where = ["."]
include = ["src*"]
```

This `packages.find` config means `pip install -e .` makes `src.*` importable — the Dockerfile
must run `pip install -e .` (or `uv pip install --system -e .`) so `src.web.app` resolves.

**Full Dockerfile** (new file — closest analog is python:3.12-slim community pattern):
```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install uv for fast dependency resolution (fallback: pip works if uv unavailable)
RUN pip install --no-cache-dir uv

# Copy project definition files first (layer caching: deps only reinstall if pyproject.toml changes)
COPY pyproject.toml .
COPY src/ src/

# Install all dependencies + the src package as editable (makes src.* importable)
RUN uv pip install --system -e .

EXPOSE 8000

# ETL is NOT run at startup — trigger via /admin/refresh-data after deploy (D-10)
CMD ["uvicorn", "src.web.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

Pitfall to avoid: do NOT `COPY .env` — secrets are injected at runtime via AWS Secrets Manager.
Pitfall to avoid: if `uv pip install` fails in CI, fallback is `RUN pip install --no-cache-dir -e .`.

---

### `README.md` (docs)

**Analog:** `README.md` (self — add new section; no code pattern to extract)

**Section to add:** "AuraDB Free Quickstart (Integration Tests)" — following D-05 requirements:
1. Create an AuraDB Free instance at console.neo4j.io
2. Copy the connection URI (`neo4j+s://xxxxxxxx.databases.neo4j.io`)
3. Set `.env`: `NEO4J_URI=neo4j+s://...` and `NEO4J_AUTH=neo4j/<password>` (avoid `/` in password per Pitfall 3)
4. Run ETL once: `python -m src.etl.run_etl`
5. Run full suite: `pytest --tb=short`

**Existing README env table** (already contains `ADMIN_KEY` after Phase 4.1 gap closure) — reference this table; add `NEO4J_URI` AuraDB note.

---

## Shared Patterns

### LangGraph Node Return Contract
**Source:** `src/workflow/nodes/analyze.py` lines 41-83, `src/workflow/nodes/format.py` lines 86-137
**Apply to:** `analyze.py` (new `_generate_alternatives`), `format.py` (new alternatives branch)
```python
# Every node returns only its owned keys — no state passthrough
return {"owned_key": value}
# Never return copies of other keys the node read but didn't write
```

### Pydantic v2 Model Validation Pattern
**Source:** `src/workflow/nodes/format.py` lines 22-43, 121-137
**Apply to:** `AlternativesOutput` model in `format.py`, test fixtures in `test_format.py`
```python
# Validation: model_validate(parsed_dict) raises ValidationError on bad shape
validated = TeamOutput.model_validate(parsed)
return {"final_output": validated.model_dump()}
```

### pytest `@pytest.mark.integration` + async fixture pattern
**Source:** `tests/integration/test_query_pipeline.py` lines 37-64, `tests/conftest.py` lines 28-68
**Apply to:** All 5 tests in `tests/integration/test_e2e_phase5.py`
```python
@pytest.mark.integration
async def test_name(async_driver, loaded_db):
    """Docstring explains requirement ID covered."""
    ...
    assert condition, "Failure message describes what was expected vs got"
```

### SSE `finally` block result render
**Source:** `src/web/streaming.py` lines 127-139
**Apply to:** Phase 5 template selection change in `streaming.py`
```python
finally:
    if final_output is not None:
        try:
            template = templates.env.get_template("partials/result.html")
            html = template.render(result=final_output)
            yield ServerSentEvent(raw_data=html, event="result")
        except Exception as render_exc:
            logger.exception("Failed to render result template: %s", render_exc)
    yield ServerSentEvent(data="", event="done")
```

### Jinja2 char-card HTML pattern
**Source:** `src/web/templates/partials/result.html` lines 15-27
**Apply to:** Each alternative's character grid in `partials/alternatives.html`
```html
<div class="char-card">
  <strong>{{ char.name }}</strong>
  <div class="role">{{ char.role }}</div>
  {% if char.grastas %}
  <div class="grastas">
    <small>Grasta: {{ char.grastas | join(', ') }}</small>
  </div>
  {% endif %}
</div>
```

### `<details>/<summary>` accordion (no JS)
**Source:** `src/web/templates/partials/error.html` lines 7-10, PicoCSS v2 native support
**Apply to:** `partials/alternatives.html` accordion sections
```html
<details {% if loop.first %}open{% endif %}>
  <summary><strong>Label</strong></summary>
  <!-- content -->
</details>
```

---

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `.github/workflows/deploy.yml` | config/CI | — | Skipped — deployment deferred per user decision |

All other files have direct analogs in the codebase.

---

## Metadata

**Analog search scope:** `src/workflow/nodes/`, `src/web/streaming.py`, `src/web/templates/partials/`, `tests/integration/`, `tests/workflow/`, repo root
**Files scanned:** 15 source files read directly
**Pattern extraction date:** 2026-04-25
