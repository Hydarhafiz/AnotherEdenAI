# Phase 5: Integration, Polish, and Portfolio Hardening - Context

**Gathered:** 2026-04-25
**Status:** Ready for planning

<domain>
## Phase Boundary

End-to-end verification, output format hardening, full integration test suite, portfolio documentation, and AWS deployment via GitHub Actions CI/CD. A recruiter can clone the repo, run `pytest --tb=short` with AuraDB Free credentials, and browse to a live public URL on AWS App Runner. No new features — this phase closes all open output requirements (OUTPUT-01 through OUTPUT-05) and all deployment requirements (DEPLOY-01 through DEPLOY-03).

</domain>

<decisions>
## Implementation Decisions

### Top-3 Alternatives (OUTPUT-04)

- **D-01:** Top-3 alternatives trigger **only on empty `db_results`** — the VALIDATE node already detects this; no ambiguity in the trigger condition.
- **D-02:** Each "alternative" is a **distinct full team composition** (3 different team comps), not individual character substitutions. ANALYZE generates all 3 in one LLM pass using its knowledge of the roster + query intent — no new Cypher queries.
- **D-03:** UI displays alternatives as **collapsed accordion cards**: 3 labelled sections (Alternative 1, Alternative 2, Alternative 3), first one expanded by default. Same character card layout inside each (frontline/reserve grid). No separate "alternatives" page.
- **D-04:** ANALYZE detects the empty path and generates alternatives **in a single pass** — no retry loop, no new graph queries. ANALYZE already has roster + plan_strategy context.

### Integration Test Suite (SC-1, 05-02)

- **D-05:** Integration tests require a **real Neo4j database** — use **AuraDB Free** (Neo4j's free cloud tier). README walks through: create AuraDB instance → set `NEO4J_URI` + `NEO4J_AUTH` in `.env` → run ETL once → run `pytest`.
- **D-06:** Tests split by marker: `pytest --tb=short` runs full suite (unit + integration). `pytest -m 'not integration'` runs unit-only with no DB dependency. **`pytest.mark.integration` is already registered in pytest.ini** — use this existing marker for all DB-dependent tests.
- **D-07:** 5 integration test scenarios required (from ROADMAP SC-1 / 05-02): happy path team recommendation, name normalization, empty-result graceful degradation (triggers D-01 path), retry cap exhaustion (3 VALIDATE attempts all fail), and `/admin/refresh-data` trigger.

### AWS Deployment (DEPLOY-01 through DEPLOY-03, 05-04)

- **D-08:** Deployment target is **AWS App Runner** — simpler pipeline (ECR push → App Runner auto-deploys), handles HTTPS/scaling automatically, appropriate cost profile for intermittent portfolio traffic.
- **D-09:** Secrets stored in **AWS Secrets Manager** — App Runner pulls `NEO4J_URI`, `NEO4J_AUTH`, `ANTHROPIC_API_KEY`, `ADMIN_KEY` at service start via IAM role. Demonstrates production-grade secrets management.
- **D-10:** Dockerfile is **python:3.12-slim, single-stage** — install `uv`, copy `src/`, install dependencies, expose port 8000. ETL is NOT run at container startup; it's triggered via `/admin/refresh-data` after deploy.
- **D-11:** GitHub Actions pipeline on merge to main: build Docker image → push to ECR → deploy to App Runner. Public URL accessible after deploy with no manual intervention.

### Source Attribution (OUTPUT-02)

- **D-12:** Attribution is **embedded in `synergy_explanation` text** — no schema change to `CharacterSlot` or `TeamOutput`. FORMAT doesn't parse the text; it validates non-empty.
- **D-13:** `ANALYZE_SYSTEM_PROMPT` updated with a **mandatory per-character citation rule**: "For each character, cite the specific Grasta name and personality trait that enables their role. Format: `[CharacterName]: [Grasta name] ([trait name]) — [effect]`. Never make a synergy claim without a Grasta node to back it."

### Claude's Discretion

- Specific accordion CSS/HTML structure (HTMX or vanilla JS toggle)
- Exact text labels for alternative team headings ("Alternative 1" vs descriptive labels)
- Latency measurement approach (structured log line vs inline timing — as long as 15s SLA is verifiable)
- README section structure and ordering

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Output Contract
- `src/workflow/nodes/format.py` — `TeamOutput` and `CharacterSlot` Pydantic v2 models; `CharacterSlot(name, role, grastas)` is the locked schema — no field additions in Phase 5
- `src/workflow/nodes/analyze.py` — `ANALYZE_SYSTEM_PROMPT` constant; Phase 5 updates this with per-character attribution mandate (D-13)

### Workflow Architecture
- `src/workflow/graph.py` — `build_graph(driver)` signature; ANALYZE node handles empty `db_results` branch (D-04)
- `src/workflow/state.py` — `WorkflowState` TypedDict; any new state keys (e.g. for alternatives path) must be added here
- `src/workflow/nodes/validate.py` — VALIDATE node routes on empty results; Phase 5 must trace this path for alternatives trigger (D-01)

### Web Layer
- `src/web/app.py` — FastAPI app, lifespan handler, SSE streaming endpoint
- `src/web/streaming.py` — SSE event emission; Phase 5 adds accordion result fragment for alternatives
- `src/web/templates/` — Jinja2 templates; Phase 5 adds alternatives accordion partial

### Tests
- `pytest.ini` — `pytest.mark.integration` already registered; use this for all DB-dependent tests (D-06)
- `tests/integration/` — existing integration test files; Phase 5 adds 5 new scenarios (D-07)

### Requirements
- `.planning/REQUIREMENTS.md` — OUTPUT-01 through OUTPUT-05, DEPLOY-01 through DEPLOY-03 (the acceptance criteria for this phase)
- `.planning/phases/04-fastapi-htmx-web-layer/04-CONTEXT.md` — locked UI decisions (card grid layout, SSE event design, ADMIN_KEY auth)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/workflow/nodes/format.py:TeamOutput` — Pydantic v2 model already validates frontline (3-4) and reserve (1-2); no change needed for normal path
- `src/workflow/nodes/analyze.py:ANALYZE_SYSTEM_PROMPT` — already assigns roles ("AF anchor, healer, DPS, support, buffer, debuffer") and requests specific Grasta citations; Phase 5 hardens attribution requirement
- `src/web/templates/partials/` — existing SSE partials pattern for injecting HTML fragments; alternatives accordion adds a new partial here
- `pytest.mark.integration` — already registered in `pytest.ini`; existing integration tests in `tests/integration/` cover ETL and query pipeline

### Established Patterns
- ANALYZE receives `db_results`, `user_query`, `roster`, `plan_strategy` — all context needed to generate fallback alternatives when `db_results` is empty
- FORMAT node is LLM-free (pure Python); it validates structure but does not interpret `synergy_explanation` content
- SSE final event delivers rendered Jinja2 HTML fragment; HTMX swaps into result div — alternatives accordion follows the same pattern

### Integration Points
- ANALYZE node is the single point where the empty-path branch logic lives (D-04)
- FORMAT node receives ANALYZE output; needs to handle both normal TeamOutput AND alternatives (3 × TeamOutput) — may need a new model or a flag
- Accordion UI must be a new Jinja2 partial rendered by the SSE final event, same mechanism as the existing result card

</code_context>

<specifics>
## Specific Ideas

- D-04 implication: FORMAT node likely needs a new `AlternativesOutput` model (wrapping 3 × TeamOutput) OR a flag on TeamOutput that switches the template. Planner should decide the cleanest approach.
- The 15-second SLA (SC-5) applies to the happy path query-to-recommendation round trip. Latency should be logged as a structured line (`latency_ms: NNNN`) so it's visible in App Runner logs without additional tooling.
- The `ADMIN_KEY` env var is already documented in README's env table (Phase 4.1 gap closure). Phase 5 only needs to add it to AWS Secrets Manager config — no app-level change.
- AuraDB Free has a single-region constraint and connection limits; integration tests should use a dedicated AuraDB instance separate from any dev/production instance.

</specifics>

<deferred>
## Deferred Ideas

- Grasta effect descriptions in result cards (beyond Grasta name) — noted in Phase 4 deferred, still deferred
- SSE streaming of ETL progress in `/admin/refresh-data` — still deferred
- Multi-user server-side roster persistence — still deferred
- Per-character structured attribution fields (`attributions: [{grasta, trait, effect}]`) — discussed, deferred in favor of embedded text (D-12)
- ECS Fargate deployment — discussed, App Runner chosen (D-08); ECS Fargate remains as a future upgrade if traffic warrants it

</deferred>

---

*Phase: 05-integration-polish-and-portfolio-hardening*
*Context gathered: 2026-04-25*
