# Roadmap: Another Eden AI — GraphRAG Team Builder

## Overview

Five phases, hard-sequenced by dependency. Phase 1 builds the Neo4j graph schema and ETL pipeline before any LLM prompt is written — GENERATE_CYPHER requires injected schema to avoid hallucination, so the schema must be stable first. Phase 2 builds the full LangGraph state machine against mocked Neo4j, isolating agent logic bugs from data bugs. Phase 3 connects the verified workflow to the real graph and validates roster filtering and Grasta traversal against live data. Phase 4 wraps the working pipeline in a FastAPI + HTMX web layer with SSE streaming progress. Phase 5 hardens the end-to-end system for portfolio demonstration — integration tests, graceful degradation, and the 15s response time SLO.

## Phases

- [x] **Phase 1: Graph Foundation** - Finalized, stable Neo4j schema and idempotent ETL pipeline before any LLM prompt is written (completed 2026-03-14)
- [ ] **Phase 2: LangGraph Workflow (Stub Data)** - Full PLAN → GENERATE_CYPHER → VALIDATE → ANALYZE state machine built and tested against mocked Neo4j
- [ ] **Phase 3: Connect Workflow to Real Neo4j** - Swap mock responses for real Cypher; validate roster filtering and Grasta traversal against live graph data
- [ ] **Phase 4: FastAPI + HTMX Web Layer** - Expose working pipeline via HTTP with SSE streaming progress UI
- [ ] **Phase 5: Integration, Polish, and Portfolio Hardening** - End-to-end verified, error paths hardened, recruiter can clone and run pytest cold

## Phase Details

### Phase 1: Graph Foundation
**Goal**: Finalized, stable Neo4j schema and idempotent ETL pipeline are complete before any LLM prompt is written
**Depends on**: Nothing (first phase)
**Requirements**: DATA-01, DATA-02, DATA-03, DATA-04, DATA-05, GRAPH-01, GRAPH-02, GRAPH-03, GRAPH-04, GRAPH-05, GRAPH-06, GRAPH-07
**Success Criteria** (what must be TRUE):
  1. Running the ETL pipeline twice against a clean Neo4j instance produces identical node and relationship counts both times (idempotency verified)
  2. A Cypher query for a known character returns correct element, weapon, light_shadow, and linked Trait nodes with no missing properties
  3. A Cypher query for a known shareable Grasta correctly distinguishes is_shareable=true and returns the linked REQUIRES_TRAIT relationship
  4. SCHEMA.md exists, documents all node labels, properties, and relationship types with a version constant, and matches what `get_schema()` returns from the loaded graph
  5. Post-load assertion script runs after ETL and exits 0 when expected node types (Character, Trait, Grasta, Ore) exist in the graph

**Research flag**: anothereden.wiki page structure is unverified — Phase 1 planning must begin with a wiki audit (page layout, data completeness, rate limiting) before writing the scraper.

Plans:
- [x] 01-01: Wiki audit and schema design — inspect anothereden.wiki page structure for Character, Grasta, and Ore data; define final node labels, properties, and relationship types; write SCHEMA.md v1 contract
- [ ] 01-02: ETL scraper implementation — async httpx scraper for Character, Grasta, and Ore pages; Pydantic v2 models for ETL boundary validation; idempotent MERGE-based Neo4j loader
- [ ] 01-03: Schema validation and assertions — schema version constant in ETL; post-load assertion query confirming expected node types; pytest tests confirming idempotency and known-good node properties

### Phase 2: LangGraph Workflow (Stub Data)
**Goal**: Complete PLAN → GENERATE_CYPHER → VALIDATE → ANALYZE → FORMAT pipeline is built, wired, and tested against mocked Neo4j — agent logic bugs are isolated from data bugs before any real graph is touched
**Depends on**: Phase 1 (SCHEMA.md and `get_schema()` output required for prompt injection)
**Requirements**: AGENT-01, AGENT-02, AGENT-03, AGENT-04, AGENT-05, AGENT-06, AGENT-07, AGENT-08
**Success Criteria** (what must be TRUE):
  1. A test query flows through all five nodes (PLAN → GENERATE_CYPHER → VALIDATE → ANALYZE → FORMAT) against mocked Neo4j and returns a structured result with no unhandled exceptions
  2. When VALIDATE returns a failure, the workflow routes back to GENERATE_CYPHER with the full error message included in state, and the retry counter increments correctly
  3. When VALIDATE fails three consecutive times, the workflow routes to graceful error formatting instead of a fourth attempt — retry counter never exceeds 3
  4. WorkflowState is a TypedDict with Pydantic v2 validation; a node that attempts to write a key it does not own raises a validation error in tests
  5. `pytest` passes with all nodes mocked — no live LLM calls, no live Neo4j connections required to run the test suite
  6. `src/workflow/llm.py` provides a `get_llm(role)` factory; setting `LLM_PROVIDER=ollama` in `.env` routes all LLM calls through Ollama for local budget-safe debugging

Plans:
- [ ] 02-01: WorkflowState and graph wiring — define WorkflowState TypedDict with Pydantic v2; wire StateGraph with all nodes and edges including the VALIDATE conditional edge with retry cap; no node logic yet, just the skeleton
- [ ] 02-02: PLAN and GENERATE_CYPHER node implementation — Sonnet 4.6 PLAN agent decomposes query into sub-goals; Sonnet 4.6 GENERATE_CYPHER agent produces Cypher with full schema injected via get_schema() and few-shot examples
- [ ] 02-03: VALIDATE node and retry loop — Haiku 4.6 VALIDATE agent checks Cypher syntax and non-empty results; conditional edge routes pass → ANALYZE, fail-with-retries → GENERATE_CYPHER (with error context), fail-at-cap → graceful error
- [ ] 02-04: ANALYZE and FORMAT nodes plus test suite — Sonnet 4.6 ANALYZE synthesizes results into team recommendation; FORMAT structures final output; pytest-mock unit tests covering happy path, single retry, and retry cap exhaustion

### Phase 3: Connect Workflow to Real Neo4j
**Goal**: Mock Neo4j responses are replaced with real Cypher queries against the Phase 1 graph; roster filtering and Grasta synergy traversal are validated against live data
**Depends on**: Phase 2 (verified workflow logic), Phase 1 (loaded graph with real data)
**Requirements**: QUERY-01, QUERY-02, QUERY-03, QUERY-04
**Success Criteria** (what must be TRUE):
  1. A query submitted with a list of owned character names returns recommendations that include only characters from that list plus explicitly F2P units — no unowned characters appear in results
  2. A character name with a common variation (e.g., "Aldo" vs canonical wiki name) is normalized to the correct graph node before roster filtering is applied
  3. A known-good synergy pair (verified manually against the wiki) is returned by the pipeline with correct Grasta and personality attribution
  4. Integration tests against AuraDB Free (or local Docker Neo4j fallback) pass with at least 3 known-good query scenarios covering different team archetypes

**Research flag**: AF (Another Force) zone mechanics may require schema extension beyond Phase 1 nodes — the Phase 3 plan should evaluate whether ENHANCES or a new relationship type is needed for AF synergy queries.

Plans:
- [ ] 03-01: Neo4j connection wiring and name normalization — replace mock Neo4j with live AsyncGraphDatabase driver; implement character name normalization in PLAN agent (canonical name lookup against graph); confirm roster filtering query returns only owned + F2P units
- [ ] 03-02: Grasta synergy traversal validation — run known-good synergy queries against live graph; verify REQUIRES_TRAIT and HAS_TRAIT path traversal returns correct results; document any schema extensions needed for AF mechanics
- [ ] 03-03: Integration test suite — pytest integration tests covering happy path, empty-roster edge case, name normalization, and known-good synergy pairs; measure end-to-end latency baseline against 15s SLO

### Phase 4: FastAPI + HTMX Web Layer
**Goal**: The working pipeline is exposed via HTTP with a streaming progress UI — users can submit roster and query through a browser and see pipeline node status update in real time
**Depends on**: Phase 3 (end-to-end pipeline verified against real graph)
**Requirements**: WEB-01, WEB-02, WEB-03, WEB-04, WEB-05
**Success Criteria** (what must be TRUE):
  1. A user can open the app in a browser, enter their roster and a natural language query, submit the form, and receive a team recommendation without any installation or command-line interaction
  2. While the pipeline runs, the UI updates to show current node status in sequence (PLAN → CYPHER → VALIDATE → ANALYZE) via SSE — the page does not go blank or require a refresh
  3. When VALIDATE retries, the UI shows "Validating... attempt 2/3" (or equivalent) so the user knows the system is working, not stalled
  4. POSTing to /admin/refresh-data triggers the ETL pipeline and returns a success/failure response; the endpoint is not exposed to anonymous users

Plans:
- [ ] 04-01: FastAPI app skeleton and Neo4j singleton — FastAPI app with lifespan handler initializing AsyncGraphDatabase driver as app-level singleton; POST /api/query endpoint wired to LangGraph workflow; POST /admin/refresh-data wired to ETL pipeline
- [ ] 04-02: SSE streaming and HTMX UI — SSE endpoint emitting pipeline node status events; Jinja2 template with HTMX roster input form and query submission; hx-ext="sse" wired to progress div; result div swapped on completion
- [ ] 04-03: UI polish and error display — validation retry progress rendered in UI ("attempt 2/3"); graceful error display when retry cap is exhausted; empty-result message when no matching teams found; smoke test with browser

### Phase 5: Integration, Polish, and Portfolio Hardening
**Goal**: The system is end-to-end verified, all error paths are hardened, and the Dockerized app is deployed to AWS via GitHub Actions CI/CD — a recruiter can clone the repo, run pytest, and browse to a live public URL
**Depends on**: Phase 4 (full stack running)
**Requirements**: OUTPUT-01, OUTPUT-02, OUTPUT-03, OUTPUT-04, OUTPUT-05, DEPLOY-01, DEPLOY-02, DEPLOY-03
**Success Criteria** (what must be TRUE):
  1. Running `pytest --tb=short` on a clean clone (with env vars set per README) produces a passing suite with no manual setup beyond `uv sync` and env configuration
  2. A query that returns no perfect team match produces a response listing the top 3 closest alternatives with a brief explanation of each tradeoff — it does not return an error or empty page
  3. Every character in a returned lineup has a role annotation (e.g., "AF anchor", "off-element mule", "healer") alongside their name
  4. Every team recommendation includes source attribution — which Grasta plus which personality trait creates each synergy, with no assertion that cannot be traced back to a graph node
  5. End-to-end response time from query submission to recommendation display is measured and confirmed at or below 15 seconds under normal conditions
  6. A GitHub Actions pipeline builds the Docker image and deploys to AWS App Runner (or ECS Fargate) on merge to main — a public URL is accessible after deploy with no manual intervention

Plans:
- [ ] 05-01: Output format hardening — enforce 4-frontline/2-reserve structure in FORMAT node; add per-character role annotations; add Grasta + personality source attribution to every synergy claim; add top-3 alternatives for empty/partial matches
- [ ] 05-02: Full integration test suite — end-to-end pytest tests covering: happy path team recommendation, name normalization, empty-result graceful degradation, retry cap exhaustion, and /admin/refresh-data trigger; all tests runnable cold from README instructions
- [ ] 05-03: Portfolio hardening — measure and log end-to-end latency; update README with `pytest --tb=short` instructions, env var list, and AuraDB Free setup steps; confirm recruiter cold-clone path works end to end
- [ ] 05-04: AWS Serverless Deployment — write Dockerfile for FastAPI + HTMX app; write GitHub Actions CI/CD pipeline (build → push to ECR → deploy to AWS App Runner or ECS Fargate); configure env vars from AWS Secrets Manager or Parameter Store; verify public URL accessible after merge to main

## Progress

**Execution Order:**
Phases execute in strict dependency order: 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Graph Foundation | 3/3 | Complete   | 2026-03-14 |
| 2. LangGraph Workflow (Stub Data) | 0/4 | Not started | - |
| 3. Connect Workflow to Real Neo4j | 0/3 | Not started | - |
| 4. FastAPI + HTMX Web Layer | 0/3 | Not started | - |
| 5. Integration, Polish, and Portfolio Hardening | 0/4 | Not started | - |
