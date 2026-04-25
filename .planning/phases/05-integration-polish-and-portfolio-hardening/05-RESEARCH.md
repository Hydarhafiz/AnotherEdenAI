# Phase 5: Integration, Polish, and Portfolio Hardening — Research

**Researched:** 2026-04-25
**Domain:** Output format hardening, LangGraph empty-path branching, SSE accordion UI, pytest integration test suite, FastAPI latency measurement, AWS ECS deployment via GitHub Actions
**Confidence:** HIGH (codebase verified directly; AWS deployment flags one CRITICAL finding)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Top-3 Alternatives (OUTPUT-04)**
- D-01: Top-3 alternatives trigger only on empty `db_results` — VALIDATE already detects this; no ambiguity in trigger condition.
- D-02: Each "alternative" is a distinct full team composition (3 different team comps), not individual character substitutions. ANALYZE generates all 3 in one LLM pass using its knowledge of roster + query intent — no new Cypher queries.
- D-03: UI displays alternatives as collapsed accordion cards: 3 labelled sections (Alternative 1, Alternative 2, Alternative 3), first one expanded by default. Same character card layout inside each (frontline/reserve grid). No separate "alternatives" page.
- D-04: ANALYZE detects the empty path and generates alternatives in a single pass — no retry loop, no new graph queries.

**Integration Test Suite (SC-1, 05-02)**
- D-05: Integration tests require a real Neo4j database — use AuraDB Free (Neo4j's free cloud tier). README walks through: create AuraDB instance → set `NEO4J_URI` + `NEO4J_AUTH` in `.env` → run ETL once → run `pytest`.
- D-06: Tests split by marker: `pytest --tb=short` runs full suite (unit + integration). `pytest -m 'not integration'` runs unit-only with no DB dependency. `pytest.mark.integration` is already registered in pytest.ini.
- D-07: 5 integration test scenarios required: happy path team recommendation, name normalization, empty-result graceful degradation (triggers D-01 path), retry cap exhaustion (3 VALIDATE attempts all fail), and `/admin/refresh-data` trigger.

**AWS Deployment (DEPLOY-01 through DEPLOY-03, 05-04)**
- D-08: Deployment target is AWS App Runner — simpler pipeline (ECR push → App Runner auto-deploys), handles HTTPS/scaling automatically, appropriate cost profile for intermittent portfolio traffic.
- D-09: Secrets stored in AWS Secrets Manager — App Runner pulls `NEO4J_URI`, `NEO4J_AUTH`, `ANTHROPIC_API_KEY`, `ADMIN_KEY` at service start via IAM role.
- D-10: Dockerfile is python:3.12-slim, single-stage — install `uv`, copy `src/`, install dependencies, expose port 8000. ETL is NOT run at container startup.
- D-11: GitHub Actions pipeline on merge to main: build Docker image → push to ECR → deploy to App Runner. Public URL accessible after deploy with no manual intervention.

**Source Attribution (OUTPUT-02)**
- D-12: Attribution embedded in `synergy_explanation` text — no schema change to `CharacterSlot` or `TeamOutput`.
- D-13: `ANALYZE_SYSTEM_PROMPT` updated with mandatory per-character citation rule: "For each character, cite the specific Grasta name and personality trait that enables their role. Format: `[CharacterName]: [Grasta name] ([trait name]) — [effect]`."

### Claude's Discretion
- Specific accordion CSS/HTML structure (HTMX or vanilla JS toggle)
- Exact text labels for alternative team headings ("Alternative 1" vs descriptive labels)
- Latency measurement approach (structured log line vs inline timing — as long as 15s SLA is verifiable)
- README section structure and ordering

### Deferred Ideas (OUT OF SCOPE)
- Grasta effect descriptions in result cards (beyond Grasta name)
- SSE streaming of ETL progress in `/admin/refresh-data`
- Multi-user server-side roster persistence
- Per-character structured attribution fields (`attributions: [{grasta, trait, effect}]`)
- ECS Fargate deployment
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| OUTPUT-01 | System returns team recommendations in 4-frontline/2-reserve format | TeamOutput Pydantic model already enforces this; ANALYZE prompt rules already set; needs end-to-end verification test |
| OUTPUT-02 | Each recommendation includes personality + Grasta synergy explanation with source attribution | ANALYZE_SYSTEM_PROMPT update with D-13 citation rule; FORMAT validates non-empty synergy_explanation |
| OUTPUT-03 | Each character in the lineup includes a role annotation | CharacterSlot.role already exists in schema; ANALYZE prompt already assigns roles; needs integration test assertion |
| OUTPUT-04 | When no perfect match exists, system returns top 3 closest alternatives with explanation of tradeoffs | Requires: new `AlternativesOutput` model in format.py, empty-path branch in analyze_node, new Jinja2 partial, WorkflowState key `alternatives` |
| OUTPUT-05 | Validation progress is visible to user during pipeline execution | Already implemented via SSE node_status events; needs end-to-end test that VALIDATE retry shows attempt 2/3 |
| DEPLOY-01 | GitHub Actions CI/CD pipeline builds Docker image and pushes to AWS on merge to main | New `.github/workflows/deploy.yml`; ECR repo; GitHub Actions OIDC role |
| DEPLOY-02 | App deployed to AWS with env vars from AWS Secrets Manager | CRITICAL: App Runner closing to new customers April 30, 2026 — ECS Express Mode is the viable alternative |
| DEPLOY-03 | Production-ready: health checks pass, service auto-restarts on failure, public URL accessible | ECS Express Mode provisions ALB + health checks automatically |
</phase_requirements>

---

## Summary

Phase 5 has four distinct work streams. The codebase is in strong shape after Phase 4.1 gap closure: 26 format tests and 108 workflow tests pass. The main research findings are:

**Work stream 1 (Output hardening):** The `CharacterSlot` and `TeamOutput` models in `format.py` already have the right schema (`name`, `role`, `grastas`). OUTPUT-01/02/03 primarily require updating `ANALYZE_SYSTEM_PROMPT` with the D-13 citation rule and adding end-to-end integration tests to verify the prompt produces the expected structure. OUTPUT-04 (alternatives) is the heaviest change: it requires a new `AlternativesOutput` Pydantic model, a new branch in `analyze_node` (detected via `db_results` being empty), a new `alternatives` key in `WorkflowState`, a new render path in `streaming.py`, and a new `partials/alternatives.html` Jinja2 partial.

**Work stream 2 (Integration tests):** Five test scenarios map cleanly onto the existing `tests/integration/` structure and use the existing `async_driver`/`loaded_db` conftest fixtures. The admin `/admin/refresh-data` test needs `httpx.AsyncClient` + TestClient because the endpoint triggers ETL. The retry-cap-exhaustion test needs VALIDATE to be stubbed for 3 consecutive empty results without a real graph round-trip.

**Work stream 3 (Latency + README):** Latency measurement belongs in `streaming.py` as a structured log line emitted after the FORMAT node completes. `time.monotonic()` before `graph.astream()` and after the `format` chunk is the right measurement point. README needs an AuraDB Free quickstart section.

**Work stream 4 (Deployment): CRITICAL FINDING.** AWS App Runner is **closing to new customers on April 30, 2026** — five days from today. The locked decision D-08 is no longer viable for new accounts. The AWS-recommended replacement is **Amazon ECS Express Mode**, which provides the same operational simplicity (single API call, no VPC/ALB/subnet management, HTTPS auto-provisioned). ECS Express Mode has a dedicated GitHub Action (`aws-actions/amazon-ecs-deploy-express-service`) and an official AWS sample for GitHub Actions CI/CD. The planner must decide whether to proceed with ECS Express Mode (requires updating D-08/D-09/D-11) or keep App Runner if the user has an existing AWS account with App Runner access.

**Primary recommendation:** Implement work streams 1-3 in parallel (they have no cross-dependencies). Resolve the App Runner vs ECS Express Mode question before starting work stream 4, since the Dockerfile and pipeline structure are essentially identical but the deploy step differs.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Output format hardening (OUTPUT-01/02/03) | LangGraph node (ANALYZE/FORMAT) | — | ANALYZE prompt generates content; FORMAT validates structure |
| Alternatives path (OUTPUT-04) | LangGraph node (ANALYZE) + FORMAT | Web layer (SSE + template) | ANALYZE generates alternatives; FORMAT wraps them; streaming.py renders the right partial |
| Validation retry progress (OUTPUT-05) | SSE streaming layer | LangGraph graph | streaming.py already handles validate node_status with attempt/max; no graph change needed |
| Integration test suite (DEPLOY-01 equiv) | pytest test layer | conftest fixtures | Extends existing pattern in tests/integration/ |
| Latency measurement | SSE streaming layer | FastAPI logging | time.monotonic() around graph.astream() in streaming.py; structured log line |
| Docker containerization | Container/build layer | — | New Dockerfile at repo root |
| CI/CD pipeline | GitHub Actions | ECR + ECS | New .github/workflows/deploy.yml |
| Secrets management | AWS IAM + Secrets Manager | App config | Instance role pulls secrets at service start |

---

## Standard Stack

### Core (already installed — verified in pyproject.toml)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic | 2.12.5 | `AlternativesOutput` model, validate alternatives structure | Already used for `TeamOutput` |
| langchain-anthropic | 1.3.5 | ANALYZE node LLM calls (including alternatives generation) | Already the LLM provider |
| langgraph | 1.0.10 | Graph routing for empty-path branch | Already powers the workflow |
| fastapi | 0.136.0 | SSE streaming, API routes | Already the web framework |

### New for Phase 5
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| httpx | already in project | Async HTTP client for integration testing `/admin/refresh-data` | When testing admin endpoints end-to-end |
| pytest-asyncio | >=0.23 (already installed) | Integration test async fixtures | Already used; no change |

### AWS Deployment Stack
| Tool | Version | Purpose | Notes |
|------|---------|---------|-------|
| Docker (python:3.12-slim) | latest | Container base image | Single-stage build per D-10 |
| Amazon ECR | — | Container registry | Private registry for Docker image |
| Amazon ECS Express Mode | — | Container hosting | Replaces App Runner (D-08 override) |
| GitHub Actions OIDC | — | AWS credential federation | Short-lived credentials, no stored keys |

**Version verification:** All Python packages confirmed from `pip show` and `pyproject.toml`. [VERIFIED: local pip]

---

## Architecture Patterns

### System Architecture Diagram

```
User Query (browser)
        |
        v
POST /api/query (FastAPI)
        |
        v
pipeline_sse_generator() ─── time.monotonic() START
        |
        v
graph.astream(initial_state)
        |
   ┌────┴────┐
   │         │
  plan     [empty db_results path]
   │         │
 cypher    analyze_node(alternatives=True)
   │         │
 validate → AlternativesOutput
   |         │
   │ empty? ─┘ ──→ FORMAT node (alternatives branch)
   │                    │
   │                    v
   │             partials/alternatives.html
   │
   │ non-empty:
   │
 analyze_node (normal)
   │
 format_node (TeamOutput)
   │
   v
partials/result.html
        |
        v
SSE "result" event → browser (innerHTML swap)
        |
time.monotonic() STOP → log "latency_ms: NNNN"
```

### Recommended Project Structure Changes for Phase 5
```
src/
├── workflow/
│   ├── nodes/
│   │   ├── analyze.py          # UPDATE: add alternatives branch, update ANALYZE_SYSTEM_PROMPT
│   │   └── format.py           # UPDATE: add AlternativesOutput model, handle alternatives key
│   └── state.py                # UPDATE: add `alternatives` key (list[dict])
└── web/
    ├── streaming.py            # UPDATE: add alternatives render path + latency logging
    └── templates/
        └── partials/
            └── alternatives.html  # NEW: accordion for 3 alternative team comps

tests/
└── integration/
    └── test_e2e_phase5.py      # NEW: 5 integration scenarios (D-07)

.github/
└── workflows/
    └── deploy.yml              # NEW: ECR push + ECS Express Mode deploy

Dockerfile                      # NEW: python:3.12-slim single-stage
```

### Pattern 1: AlternativesOutput Pydantic Model

The CONTEXT.md `<specifics>` section flags the design decision: FORMAT needs either a new `AlternativesOutput` model OR a flag on `TeamOutput`. The cleanest approach (no flag proliferation) is a separate model + a new `WorkflowState` key.

```python
# In format.py — source: codebase analysis + Pydantic v2 pattern
class AlternativesOutput(BaseModel):
    """Three alternative full team compositions when db_results is empty.

    Each alternative is a complete TeamOutput (frontline + reserve + explanation).
    label: human-readable heading for the accordion card.
    """
    alternatives: list[TeamOutput] = Field(min_length=3, max_length=3)
    reason: str  # Why alternatives were needed (empty db_results)
```

State key addition in `state.py`:
```python
# WorkflowState — add after analysis_result
alternatives: list[dict]   # Written by ANALYZE on empty-path; FORMAT reads this
```

FORMAT routing logic:
```python
# format_node: check for alternatives key before parsing analysis_result
if state.get("alternatives"):
    # validate via AlternativesOutput, produce final_output with alternatives=True flag
    ...
```

### Pattern 2: ANALYZE Empty-Path Detection

```python
# In analyze_node — source: codebase analysis of validate.py + graph.py
db_results = state.get("db_results", [])

if not db_results:
    # Empty-path: generate 3 alternative teams
    # ANALYZE already has roster + plan_strategy context — no new graph queries
    messages = [
        SystemMessage(content=ALTERNATIVES_SYSTEM_PROMPT),
        HumanMessage(content=human_content),
    ]
    response = llm.invoke(messages)
    return {"alternatives": _extract_alternatives_json(response.content)}
```

The `route_after_validate` in `graph.py` routes to "analyze" only when `db_results` is non-empty. When `db_results` is empty and `retry_count >= 3`, it routes to "format" directly. The alternatives path needs a NEW routing option: when `db_results` is empty AND `retry_count >= 3`, route to "analyze" for alternatives generation, THEN format. This changes the conditional edge logic.

**Alternative routing option:** Add a new `"analyze_alternatives"` node, or reuse the existing `"analyze"` node with the empty-path detection inside it. Reusing the existing node is simpler — no new graph node, just a branch inside `analyze_node`.

Revised `route_after_validate` logic:
```python
def route_after_validate(state) -> Literal["generate_cypher", "analyze", "format"]:
    if state.get("db_results"):
        return "analyze"          # normal path
    if state.get("retry_count", 0) >= 3:
        return "analyze"          # alternatives path (analyze handles empty db_results)
    return "generate_cypher"      # retry
```

The `format` node is no longer the terminal for retry-cap exhaustion — `analyze` handles alternatives, then `format` structures them. The old error schema path in `format_node` (retry_count >= 3 and empty db_results) becomes the fallback only if ANALYZE itself fails.

### Pattern 3: SSE Alternatives Rendering

```python
# In streaming.py — source: codebase analysis of existing result render path
# After format node completes:
if node_name == "format" and "final_output" in state_update:
    final_output = state_update["final_output"]

# In finally block:
is_alternatives = bool(final_output.get("alternatives"))
template_name = "partials/alternatives.html" if is_alternatives else "partials/result.html"
template = templates.env.get_template(template_name)
html = template.render(result=final_output)
yield ServerSentEvent(raw_data=html, event="result")
```

### Pattern 4: Latency Logging

```python
# In streaming.py — before graph.astream()
import time
start_ms = time.monotonic()

# After format node chunk received:
elapsed_ms = int((time.monotonic() - start_ms) * 1000)
logger.info("latency_ms: %d", elapsed_ms)
```

This pattern produces a structured log line visible in ECS/CloudWatch logs without additional tooling. [ASSUMED: ECS Express Mode forwards container stdout/stderr to CloudWatch Logs by default — verify via AWS console after deploy]

### Pattern 5: Accordion HTML (Alternatives Partial)

PicoCSS (already used in index.html via CDN) includes `<details>` / `<summary>` elements that provide native accordion behavior without JavaScript:

```html
<!-- partials/alternatives.html — rendered when final_output.alternatives is set -->
<article>
  <header><h3>No exact match — Top 3 Alternatives</h3></header>
  <p>{{ result.reason }}</p>

  {% for alt in result.alternatives %}
  <details {% if loop.first %}open{% endif %}>
    <summary><strong>Alternative {{ loop.index }}</strong></summary>
    <div class="frontline-grid">
      {% for char in alt.frontline %}
      <div class="char-card">
        <strong>{{ char.name }}</strong>
        <div class="role">{{ char.role }}</div>
        {% if char.grastas %}
        <div class="grastas"><small>Grasta: {{ char.grastas | join(', ') }}</small></div>
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
      </div>
      {% endfor %}
    </div>
    {% endif %}
    <div class="synergy-box"><strong>Synergy:</strong> {{ alt.synergy_explanation }}</div>
  </details>
  {% endfor %}
</article>
```

`<details open>` expands the first accordion card by default (D-03). No JavaScript required. [VERIFIED: PicoCSS styles `<details>` natively; confirmed from index.html CDN link `@picocss/pico@2`]

### Pattern 6: Integration Test for Alternatives Path

```python
# tests/integration/test_e2e_phase5.py
@pytest.mark.integration
async def test_empty_result_returns_alternatives(async_driver, loaded_db):
    """OUTPUT-04: Empty db_results triggers alternatives generation.

    Use a query so specific that no characters match, forcing the retry cap.
    The final_output should contain alternatives (list of 3 team dicts), not an error.
    """
    roster = ["Aldo"]
    query = "impossibly specific query that returns no graph results at all XYZ999"
    result = await run.main(roster, query)
    # Either alternatives or normal team — but NOT a plain error with no alternatives
    assert isinstance(result, dict)
    # Must have alternatives OR frontline (not just an error with empty teams)
    has_team = bool(result.get("frontline"))
    has_alternatives = bool(result.get("alternatives"))
    assert has_team or has_alternatives, (
        f"Expected either a team or alternatives, got: {result}"
    )
```

### Pattern 7: Retry Cap Exhaustion Test (without full graph round-trip)

The existing `test_end_to_end_pipeline_with_latency` in `test_query_pipeline.py` invokes `run.main()` with a real query. For retry-cap exhaustion, a real query might succeed — we need to mock the VALIDATE node to always fail.

Approach: patch `validate_node` to return `{"validation_errors": [...], "retry_count": N}` three times:

```python
@pytest.mark.integration  
async def test_retry_cap_exhaustion_returns_error_or_alternatives(async_driver):
    """AGENT-05 + OUTPUT-04: After 3 VALIDATE failures, FORMAT produces error or alternatives.

    Stubs validate_node to return empty db_results + retry_count=3 on the third call.
    Uses pytest.mark.integration for DB-dependent marker consistency (D-06).
    """
    from unittest.mock import patch, AsyncMock

    call_count = 0
    async def always_fail_validate(state, driver):
        nonlocal call_count
        call_count += 1
        rc = state.get("retry_count", 0) + 1
        return {"validation_errors": [f"Stub fail {rc}"], "retry_count": rc}

    with patch("src.workflow.nodes.validate.validate_node", side_effect=always_fail_validate):
        result = await run.main(["Aldo"], "test query")
    assert call_count == 3
    assert isinstance(result, dict)
```

### Anti-Patterns to Avoid
- **Adding new fields to `CharacterSlot`:** D-12 locks this — attribution lives in `synergy_explanation` text, not as separate fields.
- **Running ETL in the Dockerfile CMD:** D-10 explicitly defers ETL to `/admin/refresh-data` after deploy. `CMD` should be `uvicorn src.web.app:app --host 0.0.0.0 --port 8000`.
- **Using `db_results` as the alternatives trigger in FORMAT:** FORMAT is LLM-free and must not re-check state routing conditions. Use a dedicated `alternatives` WorkflowState key written by ANALYZE.
- **Storing AWS credentials in GitHub Secrets as long-lived keys:** Use GitHub OIDC + IAM role assumption for short-lived credentials.
- **App Runner for new deployments:** Service closed to new customers April 30, 2026 — use ECS Express Mode.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Accordion UI | Custom JavaScript toggle | HTML `<details>/<summary>` | Native, zero JS, PicoCSS already styles it |
| Docker multi-stage Python builds | Custom build scripts | `python:3.12-slim` + `uv pip install` | Standard pattern; uv 10x faster than pip |
| AWS credential rotation in CI | Static AWS_ACCESS_KEY stored in GitHub Secrets | GitHub OIDC + `aws-actions/configure-aws-credentials@v4` with `role-to-assume` | Credential compromise protection; official AWS pattern |
| ECS service/ALB/VPC setup | Manual CloudFormation | `aws-actions/amazon-ecs-deploy-express-service` | Express Mode provisions entire application stack in one action call |
| ECR image push logic | Custom Docker CLI scripting | `aws-actions/amazon-ecr-login@v2` + `docker/build-push-action` | Standard GitHub Actions pattern with caching |
| JSON extraction from LLM alternatives output | Custom regex | Extend existing `_extract_json()` in format.py | Already handles markdown fences + outermost `{}` extraction |

**Key insight:** The accordion, Docker, and AWS deployment are all solved problems with zero-config official patterns. The only genuinely new logic is the `AlternativesOutput` model and the `analyze_node` empty-path branch.

---

## Common Pitfalls

### Pitfall 1: `route_after_validate` Sends Retry-Cap to `format` Instead of `analyze`

**What goes wrong:** The current `graph.py` routing sends `retry_count >= 3` directly to `format`, producing an empty-team error dict. Phase 5 needs this path to go to `analyze` for alternatives generation instead.
**Why it happens:** The Phase 2 design had no alternatives path — `format` was always the error terminal.
**How to avoid:** Revise `route_after_validate` to return `"analyze"` for both success (non-empty `db_results`) and retry-cap-exhaustion. The `analyze_node` detects which case it's in via `db_results` presence. Keep the old error path as a `format_node` internal fallback only if ANALYZE itself throws.
**Warning signs:** Integration test `test_empty_result_returns_alternatives` returns `{"frontline": [], "error": "..."}` instead of alternatives.

### Pitfall 2: WorkflowState Missing `alternatives` Key

**What goes wrong:** `analyze_node` returns `{"alternatives": [...]}` but `WorkflowState` TypedDict doesn't declare `alternatives` — LangGraph will raise a key-validation error.
**Why it happens:** Phase 2 WorkflowState was designed before the alternatives path existed.
**How to avoid:** Add `alternatives: list[dict]` to `WorkflowState` before any implementation.
**Warning signs:** `KeyError` or Pydantic validation error on graph invoke with empty db_results.

### Pitfall 3: AuraDB Free Uses `neo4j+s://` URI, Not `bolt://`

**What goes wrong:** Tests connect using `bolt://` (localhost Docker pattern) but AuraDB Free requires `neo4j+s://xxxxxxxx.databases.neo4j.io` (TLS + cluster routing).
**Why it happens:** The existing conftest.py uses `NEO4J_AUTH` in `user/pass` format with `/` split — this works for AuraDB but only if the format matches exactly.
**How to avoid:** README must show `NEO4J_URI=neo4j+s://xxxxxxxx.databases.neo4j.io` and `NEO4J_AUTH=neo4j/<password>`. Confirm conftest's `tuple(os.getenv("NEO4J_AUTH", ...).split("/", 1))` works with AuraDB password (avoid passwords containing `/`).
**Warning signs:** `ServiceUnavailable` or `AuthError` from driver during `pytest -m integration`.

### Pitfall 4: `AlternativesOutput.alternatives` Must Have Exactly 3 Items

**What goes wrong:** ANALYZE generates 2 or 4 alternatives; `AlternativesOutput.alternatives = Field(min_length=3, max_length=3)` raises `ValidationError` in FORMAT; FORMAT catches it and returns the malformed-team error schema.
**Why it happens:** LLMs don't always obey numeric constraints without explicit instruction.
**How to avoid:** `ALTERNATIVES_SYSTEM_PROMPT` must explicitly instruct "Output EXACTLY 3 alternative team JSON objects in the `alternatives` array — no more, no fewer."
**Warning signs:** FORMAT returns `"LLM returned malformed team structure"` on the alternatives path.

### Pitfall 5: Docker `CMD` Must Use `uv run` or Direct `uvicorn` (Not `python -m`)

**What goes wrong:** `CMD ["python", "-m", "uvicorn", "src.web.app:app", "--port", "8000"]` fails if Python path is not configured for the `src` package.
**Why it happens:** `pyproject.toml` uses setuptools with `packages.find = [{where=["."], include=["src*"]}]` — the package is only importable after `pip install -e .` or `uv pip install -e .`.
**How to avoid:** Dockerfile must run `uv pip install -e .` (or `pip install -e .`) so `src` package is importable. Alternatively, `PYTHONPATH=/app CMD uvicorn src.web.app:app ...`.
**Warning signs:** `ModuleNotFoundError: No module named 'src'` in container logs.

### Pitfall 6: GitHub Actions OIDC Requires Trust Policy on IAM Role

**What goes wrong:** Pipeline fails at "Configure AWS credentials" step with `AccessDenied` even though the IAM role has the right policies.
**Why it happens:** OIDC federated roles require a trust policy that explicitly allows `token.actions.githubusercontent.com` as the OIDC provider with conditions for the repo (`repo:owner/repo:ref:refs/heads/main`).
**How to avoid:** Create the OIDC provider in IAM before creating the role. The trust policy must include the condition `"StringEquals": {"token.actions.githubusercontent.com:sub": "repo:<org>/<repo>:ref:refs/heads/main"}`.
**Warning signs:** `An error occurred (AccessDenied) when calling the AssumeRoleWithWebIdentity operation`.

### Pitfall 7: App Runner Is Closed to New Accounts (April 30, 2026)

**What goes wrong:** D-08 specifies App Runner as the deployment target. As of April 30, 2026, App Runner will not accept new customer accounts.
**Why it happens:** AWS announced maintenance mode for App Runner and is directing customers to ECS Express Mode.
**How to avoid:** Use ECS Express Mode instead. The GitHub Actions workflow is nearly identical — swap `awslabs/amazon-app-runner-deploy` for `aws-actions/amazon-ecs-deploy-express-service`. The Dockerfile is unchanged.
**Warning signs:** AWS console shows "App Runner is not available for new customers" when attempting to create a service.

---

## Code Examples

### Example 1: Revised `route_after_validate`
```python
# src/workflow/graph.py — source: codebase analysis
def route_after_validate(state: WorkflowState) -> Literal["generate_cypher", "analyze", "format"]:
    """
    - db_results non-empty  -> "analyze"  (success path)
    - retry_count >= 3      -> "analyze"  (alternatives path — analyze_node detects empty db_results)
    - otherwise             -> "generate_cypher"  (retry)
    """
    if state.get("db_results"):
        return "analyze"
    if state.get("retry_count", 0) >= 3:
        return "analyze"   # CHANGED: was "format" — now analyze generates alternatives
    return "generate_cypher"
```

### Example 2: `analyze_node` Alternatives Branch
```python
# src/workflow/nodes/analyze.py — source: codebase analysis
def analyze_node(state: WorkflowState) -> dict:
    db_results = state.get("db_results", [])

    if not db_results:
        # Empty-path: generate 3 alternative teams from roster knowledge
        return _generate_alternatives(state)

    # Normal path (unchanged)
    ...

def _generate_alternatives(state: WorkflowState) -> dict:
    llm = get_llm(role="analyzer")
    roster_str = ", ".join(state.get("roster", []))
    user_query = state.get("user_query", "")
    plan_strategy = state.get("plan_strategy", "")

    messages = [
        SystemMessage(content=ALTERNATIVES_SYSTEM_PROMPT),
        HumanMessage(content=(
            f"User query: {user_query}\n"
            f"Player roster: {roster_str}\n"
            f"Original traversal strategy: {plan_strategy}\n"
            "No database results were found. Generate 3 alternative team compositions."
        )),
    ]
    response = llm.invoke(messages)
    return {"alternatives": response.content}  # format_node parses this
```

### Example 3: Dockerfile (python:3.12-slim + uv)
```dockerfile
# source: D-10 decision + Python packaging patterns [ASSUMED: uv install pattern]
FROM python:3.12-slim

WORKDIR /app

# Install uv (fast pip replacement)
RUN pip install --no-cache-dir uv

# Copy project files
COPY pyproject.toml .
COPY src/ src/

# Install dependencies (including src package as editable)
RUN uv pip install --system -e .

EXPOSE 8000

CMD ["uvicorn", "src.web.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Example 4: GitHub Actions Workflow (ECS Express Mode)
```yaml
# .github/workflows/deploy.yml — source: AWS official ECS Express Mode blog + aws-samples
name: Build and Deploy to ECS Express Mode

on:
  push:
    branches: [ main ]

permissions:
  id-token: write   # Required for OIDC
  contents: read

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials (OIDC)
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_DEPLOY_ROLE_ARN }}
          aws-region: ${{ secrets.AWS_REGION }}

      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Build, tag, and push image to ECR
        id: build-image
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          ECR_REPOSITORY: anothereden-ai
          IMAGE_TAG: ${{ github.sha }}
        run: |
          docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
          echo "image=$ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG" >> $GITHUB_OUTPUT

      - name: Deploy to ECS Express Mode
        uses: aws-actions/amazon-ecs-deploy-express-service@v1
        with:
          service-name: anothereden-ai
          image: ${{ steps.build-image.outputs.image }}
          execution-role-arn: ${{ secrets.ECS_EXECUTION_ROLE_ARN }}
          infrastructure-role-arn: ${{ secrets.ECS_INFRASTRUCTURE_ROLE_ARN }}
          container-port: 8000
          cluster: anothereden-cluster
```

### Example 5: ANALYZE Attribution Mandate (D-13)
```python
# src/workflow/nodes/analyze.py — updated ANALYZE_SYSTEM_PROMPT addition
ATTRIBUTION_MANDATE = """
MANDATORY SOURCE ATTRIBUTION:
For each character in frontline and reserve, the synergy_explanation MUST include
a citation in this exact format:
  [CharacterName]: [Grasta name] ([trait name]) — [effect description]
Example: "Aldo: Fire T3 Grasta (Courage) — boosts Fire element damage by 30% in AF zone"
Never make a synergy claim without citing the specific Grasta and trait from the database results.
"""
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| App Runner for simple container hosting | ECS Express Mode | Jan 2026 (AWS announced) | D-08 needs override; same simplicity but different action in pipeline |
| `awslabs/amazon-app-runner-deploy` GH Action | `aws-actions/amazon-ecs-deploy-express-service` | Q1 2026 | Direct replacement; parameters differ slightly |
| Static AWS access keys in GitHub Secrets | OIDC role assumption | 2022-present | `aws-actions/configure-aws-credentials@v4` with `role-to-assume` |
| `pip install` in Dockerfile | `uv pip install` | 2024-present | 10x faster image build; same `pip`-compatible interface |

**Deprecated/outdated:**
- App Runner for new accounts: Closed April 30, 2026. Existing accounts retain access; new portfolio deployments must use ECS Express Mode.
- `awslabs/amazon-app-runner-deploy` GitHub Action: Still functional for existing App Runner customers but should not be adopted for new deployments.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | ECS Express Mode CloudWatch Logs receives container stdout by default (latency_ms log line visible without configuration) | Architecture Patterns, Pattern 4 | Latency log might not appear in service logs; would need explicit log driver config in ECS task definition |
| A2 | `uv pip install --system -e .` works in the python:3.12-slim base image without additional system packages | Code Examples, Example 3 | Docker build fails; fallback is `pip install -e .` (slower but guaranteed) |
| A3 | AuraDB Free allows connections from GitHub Actions runner IPs (no IP allowlist restriction) | Common Pitfalls, Pitfall 3 | Integration tests in CI would fail on DB connection; needs AuraDB Free network settings check |
| A4 | The existing `NEO4J_AUTH` split-on-`/` pattern in conftest.py works for AuraDB passwords (assumes no `/` in password) | Common Pitfalls, Pitfall 3 | Auth fails silently; mitigated by README instruction to avoid `/` in AuraDB password |
| A5 | `aws-actions/amazon-ecs-deploy-express-service` creates the ALB and HTTPS endpoint automatically without apprunner.yaml equivalent | Code Examples, Example 4 | Manual ALB configuration needed; check action's README for required vs optional parameters |

---

## Open Questions

1. **App Runner vs ECS Express Mode for D-08**
   - What we know: App Runner is closed to new customers April 30, 2026 (5 days from today). ECS Express Mode is the official AWS replacement with a dedicated GitHub Action.
   - What's unclear: Whether the user's AWS account pre-exists (and thus has App Runner access) or is a new account. If pre-existing, App Runner remains viable.
   - Recommendation: **Planner should flag this to the user as a blocking question before starting 05-04.** The Dockerfile and all other work streams are unaffected by this decision.

2. **AlternativesOutput schema: 3 × TeamOutput or `List[dict]`**
   - What we know: D-04 says "ANALYZE detects empty path and generates alternatives in a single pass." The CONTEXT.md `<specifics>` says FORMAT may need a new `AlternativesOutput` model.
   - What's unclear: Whether the LLM output for alternatives should be a JSON `{"alternatives": [TeamOutput, TeamOutput, TeamOutput]}` (fully structured) or a simpler format that FORMAT assembles. The fully structured approach is more consistent with the existing `TeamOutput` validation pattern.
   - Recommendation: Use `{"alternatives": [TeamOutput, TeamOutput, TeamOutput], "reason": str}` for the ANALYZE output. FORMAT validates with `AlternativesOutput`. Store as `final_output = {"alternatives": [...], "reason": "...", "error": None}` for the web layer.

3. **`analyze_node` is currently synchronous; `validate_node` is async**
   - What we know: `analyze_node` is a regular `def` (synchronous) in `graph.py`. The `_plan` and `_validate` wrappers are async because those nodes need `await`.
   - What's unclear: If ANALYZE uses `llm.invoke()` (synchronous Anthropic call) this is fine; if it switches to `llm.ainvoke()` for alternatives, the node needs an async wrapper.
   - Recommendation: Keep `analyze_node` synchronous and use `llm.invoke()` for both normal and alternatives paths. No async wrapper change needed.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 | All | ✓ | 3.12.3 | — |
| uv | Dockerfile, fast installs | ✗ (not installed on WSL host) | — | `pip install` in Dockerfile; `pip` works fine |
| Docker | 05-04 container build | ✗ (WSL integration not configured) | — | Build in GitHub Actions runner (ubuntu-latest has Docker) |
| AWS CLI | 05-04 IAM setup | ✓ | 2.32.21 | — |
| AuraDB Free | Integration tests | ✓ (cloud service, no local install) | Neo4j 5.x | Local Docker Neo4j (already in docker-compose.yml) |
| GitHub Actions runner | 05-04 CI/CD | ✓ (cloud, no local config needed) | — | — |

**Missing dependencies with no fallback for local dev:**
- Docker (WSL integration required for local container testing) — not needed for tests; GitHub Actions handles the actual build and push.

**Missing dependencies with fallback:**
- uv: `pip install` in Dockerfile is a fully viable fallback; the Dockerfile can use `RUN pip install --no-cache-dir -e .` instead.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.23 |
| Config file | `pytest.ini` (root) |
| Quick run command | `pytest -m 'not integration' --tb=short -q` |
| Full suite command | `pytest --tb=short` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| OUTPUT-01 | 4-frontline/2-reserve structure enforced | unit (existing) | `pytest tests/workflow/test_format.py -x` | ✅ (26 tests) |
| OUTPUT-02 | synergy_explanation contains Grasta+trait citations | integration | `pytest tests/integration/test_e2e_phase5.py::test_happy_path_has_attribution -x -m integration` | ❌ Wave 0 |
| OUTPUT-03 | Each CharacterSlot.role is non-empty | integration | `pytest tests/integration/test_e2e_phase5.py::test_happy_path_role_annotations -x -m integration` | ❌ Wave 0 |
| OUTPUT-04 | Empty db_results returns 3 alternatives | integration | `pytest tests/integration/test_e2e_phase5.py::test_empty_result_returns_alternatives -x -m integration` | ❌ Wave 0 |
| OUTPUT-05 | VALIDATE retry shows attempt 2/3 in SSE | unit (streaming) | `pytest tests/web/unit/test_streaming.py -x` | ✅ (existing) |
| DEPLOY-01 | GitHub Actions workflow file exists and is valid YAML | manual/CI | CI pipeline run itself | ❌ Wave 0 |
| DEPLOY-02 | App running on public URL with env from Secrets Manager | manual smoke test | `curl https://<ecs-url>/` | ❌ Wave 0 |
| DEPLOY-03 | Health check endpoint returns 200 | manual/integration | `curl https://<ecs-url>/` | ❌ Wave 0 (needs `/health` endpoint) |

### Sampling Rate
- **Per task commit:** `pytest -m 'not integration' --tb=short -q`
- **Per wave merge:** `pytest --tb=short` (requires AuraDB Free `.env`)
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/integration/test_e2e_phase5.py` — covers OUTPUT-02, OUTPUT-03, OUTPUT-04, and D-07 scenarios
- [ ] `src/web/routes/health.py` (or inline in `pages.py`) — `GET /health` returns `{"status": "ok"}` for DEPLOY-03 health checks
- [ ] `src/web/templates/partials/alternatives.html` — covers OUTPUT-04 UI rendering
- [ ] `Dockerfile` — required before 05-04 can be tested in CI
- [ ] `.github/workflows/deploy.yml` — DEPLOY-01

*(Existing test infrastructure covers OUTPUT-01, OUTPUT-05)*

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | ADMIN_KEY already handled via `secrets.compare_digest()` in dependencies.py |
| V3 Session Management | no | Stateless backend; no sessions |
| V4 Access Control | yes (admin endpoint) | Already implemented: `verify_admin_key()` in dependencies.py |
| V5 Input Validation | yes | `AlternativesOutput` Pydantic model validates ANALYZE output; existing `TeamOutput` validates normal path |
| V6 Cryptography | yes (secrets in transit) | Secrets Manager + HTTPS from ECS Express Mode ALB; never stored in env vars or Docker image |

### Known Threat Patterns for Phase 5 Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Secrets in Docker image layers | Information Disclosure | Never `COPY .env` into Dockerfile; use Secrets Manager injection at service start |
| Long-lived AWS access keys in GitHub Secrets | Elevation of Privilege | OIDC role assumption — short-lived credentials per workflow run |
| LLM prompt injection via user query | Tampering | SystemMessage separation from HumanMessage already in place; no change needed |
| `/admin/refresh-data` unauthorized access | Elevation of Privilege | `verify_admin_key()` dependency already guards this endpoint; `ADMIN_KEY` in Secrets Manager |

---

## Sources

### Primary (HIGH confidence)
- Codebase direct inspection — `src/workflow/nodes/format.py`, `analyze.py`, `validate.py`, `graph.py`, `state.py` — confirmed existing patterns, schema, routing logic
- Codebase direct inspection — `src/web/streaming.py`, `app.py`, `routes/api.py`, `templates/partials/` — confirmed SSE event protocol, render path, template structure
- Codebase direct inspection — `tests/conftest.py`, `tests/integration/test_query_pipeline.py`, `pytest.ini` — confirmed test infrastructure, markers, fixtures
- `pyproject.toml` + `pip show` — confirmed library versions (pydantic 2.12.5, langgraph 1.0.10, fastapi 0.136.0, langchain-anthropic 1.3.5)
- AWS official documentation — [App Runner availability change](https://docs.aws.amazon.com/apprunner/latest/dg/apprunner-availability-change.html) — confirmed App Runner closure to new customers April 30, 2026 and ECS Express Mode as replacement

### Secondary (MEDIUM confidence)
- [AWS Blog: Automated deployments with GitHub Actions for Amazon ECS Express Mode](https://aws.amazon.com/blogs/containers/automated-deployments-with-github-actions-for-amazon-ecs-express-mode/) — confirmed `aws-actions/amazon-ecs-deploy-express-service` action parameters and OIDC workflow pattern
- [AWS Managed Policy: AWSAppRunnerServicePolicyForECRAccess](https://docs.aws.amazon.com/aws-managed-policy/latest/reference/AWSAppRunnerServicePolicyForECRAccess.html) — ECR access permissions for ECS execution role (same permissions apply)
- [Neo4j Aura Python connection](https://neo4j.com/docs/aura/auradb/connecting-applications/python/) — confirmed `neo4j+s://` URI scheme for AuraDB Free

### Tertiary (LOW confidence)
- Community sources (DEV.to, Medium) on App Runner migration to ECS Express Mode — corroborates AWS official position but not independently verified at spec level

---

## Metadata

**Confidence breakdown:**
- Output hardening (OUTPUT-01/02/03/05): HIGH — codebase verified, patterns clear, existing tests guide new tests
- Alternatives path (OUTPUT-04): HIGH — code analysis complete; routing change is surgical and well-understood
- Integration tests: HIGH — existing test structure maps directly; conftest pattern established
- Latency measurement: HIGH — standard Python `time.monotonic()` pattern; structured logging already in streaming.py
- Docker/Dockerfile: HIGH — standard pattern; uv vs pip is trivial choice
- AWS deployment: MEDIUM — ECS Express Mode is new (2026); action parameters verified from AWS blog but IAM specifics need user verification; App Runner closure is HIGH-confidence (official AWS docs)

**Research date:** 2026-04-25
**Valid until:** 2026-05-25 (AWS service announcements may change; ECS Express Mode is actively evolving)
