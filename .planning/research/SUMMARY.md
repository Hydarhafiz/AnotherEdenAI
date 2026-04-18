# Project Research Summary

**Project:** Another Eden AI — GraphRAG Multi-Agent Team Builder
**Domain:** JRPG game optimizer / GraphRAG AI pipeline / portfolio MLOps
**Researched:** 2026-03-14
**Confidence:** HIGH

## Executive Summary

This is a GraphRAG decision support tool for a complex JRPG, built as a portfolio artifact demonstrating enterprise-grade MLOps patterns. The product's core loop is: user inputs roster + natural language query → multi-agent LangGraph pipeline generates and validates Neo4j Cypher → synthesized team recommendation with explanations. The stack is locked (Python, Neo4j, LangGraph, Sonnet 4.6 / Haiku 4.6), and all chosen technologies are well-matched to the problem. The `langchain-neo4j` library provides pre-built GraphRAG primitives (schema extraction, Text2Cypher, graph QA chains) that eliminate substantial boilerplate. FastAPI + HTMX keeps the frontend lean without a JS build toolchain, which is appropriate given the portfolio focus is the AI/MLOps layer, not frontend engineering.

The recommended approach is dependency-driven: build the Neo4j graph schema and data pipeline before any agents, then build the LangGraph workflow against stub data, then connect them, then add the web layer. This sequencing is non-negotiable — the GENERATE_CYPHER agent requires an injected schema to avoid hallucination, which means the schema must be finalized before LLM prompts are written. The biggest validation risk is the VALIDATE retry loop becoming a cost sink; the hard cap of 3 retries with error context passed back to GENERATE_CYPHER must be baked into the conditional edge from day one, not retrofitted.

The key non-obvious insight is that **accuracy is the trust mechanism, not the feature set**. Analogues from Genshin and Arknights community tools confirm that a single hallucinated game mechanic destroys user trust permanently. The VALIDATE node is not just a correctness layer — it is the credibility layer. This shapes the entire testing strategy: mock Neo4j responses must cover known valid synergy pairs so CI catches regressions before they reach users. The Grasta shareability mechanic (one item, multiple equipped, one activating) is the most semantically complex game rule and must be modeled explicitly in the schema before any agent queries it.

---

## Key Findings

### Recommended Stack

The locked stack is well-chosen and production-grade. `langchain-neo4j` is the key library — it provides `Neo4jGraph`, `GraphCypherQAChain`, and `Neo4jVector` without custom implementation. The direct `anthropic` SDK is preferred over the LangChain Anthropic wrapper to reduce indirection. `uv` replaces pip for dependency management (faster, better lockfile). All async: `httpx` for scraping, `AsyncGraphDatabase.driver()` for Neo4j, FastAPI's native async for the web layer.

**Core technologies:**
- **LangGraph 0.2.x**: Multi-agent state machine — `StateGraph` with typed state and conditional edges for the retry loop
- **Neo4j 5.x + langchain-neo4j**: Graph DB with pre-built GraphRAG primitives; `get_schema()` auto-generates schema string for prompt injection
- **anthropic 0.27+**: Direct SDK for Sonnet 4.6 (PLAN, GENERATE_CYPHER, ANALYZE) and Haiku 4.6 (VALIDATE)
- **FastAPI + HTMX + Jinja2**: Async web layer with server-rendered UI; no JS build toolchain
- **Pydantic v2**: Required by LangGraph; handles typed `WorkflowState` and ETL boundary validation
- **pytest + pytest-asyncio + pytest-mock**: Mock LLM calls and Neo4j sessions; essential for a working portfolio demo

### Expected Features

Game optimizer tools live or die on accuracy and trust. Every feature decision flows from this.

**Must have (table stakes):**
- Roster filtering — recommendations constrained to owned units only; anything else is useless
- Game rule accuracy — zero hallucinated mechanics; the VALIDATE loop enforces this
- Response explainability — users need "why" not just "what"; Arknights-style role annotations per character
- 4-frontline/2-reserve format — this is the standard layout players recognize
- Source attribution — "this synergy is valid because [Grasta name] + [personality]"
- Error feedback with retry transparency — users see "Validating... (attempt 2/3)", not a black box

**Should have (differentiators):**
- Natural language query — "best blunt-zone synergy" beats dropdowns
- Personality + Grasta graph traversal — mathematically correct path-finding, not heuristics
- Another Force (AF) synergy awareness — AF zone mechanics are a key team-building axis
- Per-character role annotation — "Aldo as AF anchor" vs "Tsukiha as off-element mule"
- Graceful degradation — "no perfect match found — here are the closest 3 options"

**Defer to v2+:**
- Exact stat optimization (combinatorial explosion)
- Farming route optimizer (different data model)
- Boss rotation generator (separate data requirements)
- Social features (sharing builds)
- Account OCR / screen reading

### Architecture Approach

The system has five clearly bounded components that map cleanly to build phases. The LangGraph workflow is a `StateGraph` with a single `WorkflowState` TypedDict — each node receives full state and returns only the keys it modifies. The VALIDATE conditional edge controls all routing: pass routes to ANALYZE, fail with retries remaining routes back to GENERATE_CYPHER (with error context), fail at retry cap routes to graceful error formatting. The data pipeline is fully independent from the query workflow and must be idempotent so re-runs safely overwrite stale data.

**Major components:**
1. **Data Pipeline (scraper + ETL)** — scrapes anothereden.wiki, transforms to graph format, loads Neo4j idempotently; runs independently on demand
2. **Neo4j Graph Schema** — nodes: Character, Trait, Grasta, Ore; relationships: HAS_TRAIT, REQUIRES_TRAIT, ENHANCES; schema version-controlled as a contract
3. **LangGraph Workflow** — PLAN → GENERATE_CYPHER → VALIDATE (3x retry cap) → ANALYZE → FORMAT; stateless per-request
4. **FastAPI API Layer** — POST /api/query, GET / (HTMX UI), POST /admin/refresh-data; Neo4j driver as app-level singleton
5. **HTMX Frontend** — form for roster input + query; HTMX posts to API, swaps result div; SSE for pipeline progress

### Critical Pitfalls

1. **Cypher hallucination without schema injection** — LLM generates node labels that don't exist in the graph, queries return 0 results, VALIDATE maxes out on every request. Prevention: always inject full schema via `Neo4jGraph.get_schema()` into the GENERATE_CYPHER system prompt; include few-shot Cypher examples. Must be addressed in Phase 2 from day one.

2. **VALIDATE loop becomes infinite (budget killer)** — validation catches an error, retry regenerates the same broken query, loops until API bills explode. Prevention: hard cap at 3 retries in conditional edge; pass full error message back to GENERATE_CYPHER as context; track retry count in `WorkflowState` only, never external state. Must be baked into Phase 2 conditional edge design, not retrofitted.

3. **Graph schema drift silently breaks all queries** — data pipeline re-run renames a property (e.g., `light_shadow` → `alignment`), all generated Cypher patterns break with 0 results and no error. Prevention: version the schema as a constant in ETL; add post-load assertion query confirming expected node types exist; maintain `SCHEMA.md` as a contract. Must be addressed in Phase 1 before any agents use the graph.

4. **LangGraph state mutation between nodes** — nodes accidentally mutate shared state dicts, causing cross-request data leakage where one query's output bleeds into the next. Prevention: `TypedDict` for `WorkflowState` with Pydantic validation; each node returns only the keys it modifies; no mutable default values in state schema.

5. **Grasta shareability logic conflated** — shareable Grasta can be equipped on multiple characters but only one can activate the personality buff; confusing equip vs. activate in queries produces wrong recommendations. Prevention: model explicitly in schema with `is_shareable` and `activating_trait` properties; document the mechanic in schema notes; test with known valid synergy pairs before building optimizer.

---

## Implications for Roadmap

Architecture research and pitfall analysis both converge on the same build order. The dependencies are hard: schema must exist before prompts are written; prompts must work against stub data before connecting to real graph; workflow must be stable before adding the HTTP layer.

### Phase 1: Graph Foundation
**Rationale:** GENERATE_CYPHER requires an injected schema to avoid hallucination. The schema must be finalized and stable before any LLM prompt is written. Schema drift is a project-killer that's trivially prevented if the schema is treated as a versioned contract from day one.
**Delivers:** Working Neo4j schema with seeded data; idempotent ETL pipeline from anothereden.wiki; schema validation assertions; `SCHEMA.md` contract document
**Addresses:** Roster filtering, game rule accuracy (data layer), source attribution (data model)
**Avoids:** Schema drift (Pitfall 3), Grasta shareability conflation (Pitfall 5), `ast.literal_eval` security debt (Pitfall 4)

### Phase 2: LangGraph Workflow (Stub Data)
**Rationale:** Build and test the entire agent state machine — including the retry loop — before connecting to real Neo4j. Mocking the graph layer isolates agent logic bugs from data bugs. The VALIDATE retry cap and state mutation patterns must be correct before they're obscured by real query complexity.
**Delivers:** Full PLAN → GENERATE_CYPHER → VALIDATE (3x retry) → ANALYZE → FORMAT pipeline with mocked Neo4j responses; schema injected into prompts; WorkflowState TypedDict with Pydantic; unit tests with pytest-mock
**Uses:** LangGraph 0.2.x, anthropic SDK, Pydantic v2, pytest-asyncio
**Avoids:** Cypher hallucination via schema injection (Pitfall 1), infinite retry loop (Pitfall 2), state mutation (Pitfall 5)

### Phase 3: Connect Workflow to Real Neo4j
**Rationale:** Swap mock Neo4j responses for real queries against the graph built in Phase 1. This is where roster filtering, character name normalization, and the Grasta synergy traversal paths get validated against real data.
**Delivers:** End-to-end pipeline with real Cypher against live Neo4j; character name fuzzy matching in PLAN agent; known-good synergy pairs tested; integration tests hitting AuraDB Free
**Addresses:** Roster filtering, personality + Grasta graph traversal, AF synergy awareness (data validation)
**Avoids:** Roster name variation matching failures (Pitfall 6)

### Phase 4: FastAPI + HTMX Web Layer
**Rationale:** Expose the working pipeline via HTTP. Adding the web layer last means the pipeline logic is already verified and the API surface is obvious from the workflow's `WorkflowState` and `final_response` dict.
**Delivers:** POST /api/query, GET / with HTMX UI, POST /admin/refresh-data, SSE progress streaming (PLAN → CYPHER → VALIDATE → ANALYZE status), Neo4j driver as app-level connection pool singleton
**Uses:** FastAPI, uvicorn, HTMX + Jinja2, SSE via `hx-ext="sse"`
**Avoids:** Neo4j connection pool exhaustion (Pitfall 7), perceived slowness without streaming (Pitfall 8)

### Phase 5: Integration, Polish, and Portfolio Hardening
**Rationale:** End-to-end validation against real queries, error path hardening, and ensuring the project is demonstrable by a recruiter who clones the repo cold. Portfolio projects die when they only work on the author's machine.
**Delivers:** Full integration test suite; graceful degradation for empty-result queries; `pytest --tb=short` in README; AuraDB Free integration test; explainability layer with per-character role annotations; response time within 15s target
**Addresses:** Explainability, graceful degradation, retry transparency, response time SLO
**Avoids:** Portfolio failure without tests (Pitfall 10)

### Phase Ordering Rationale

- **Schema before agents** is non-negotiable: Cypher hallucination is caused by prompts written without schema context. Writing prompts first and adding schema later doesn't work — the few-shot examples in the prompt must use real property names.
- **Stub data before real data** isolates two different failure modes. Phase 2 catches agent logic bugs (wrong conditional edge, state mutation, retry loop logic). Phase 3 catches data bugs (missing nodes, wrong relationships, name normalization). Mixing them makes debugging exponentially harder.
- **Web layer last** keeps scope tight. A working CLI-level pipeline is independently valuable and testable without HTTP concerns. FastAPI/HTMX adds no architectural complexity but does add surface area for connection pool bugs.
- **Hardening as its own phase** prevents the common trap of treating tests and error handling as afterthoughts. For a portfolio project, a recruiter failing to run `pytest` is a fatal demo failure.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 1:** anothereden.wiki scraping structure is unverified — page layout, rate limiting behavior, and data completeness for Grasta/personality data need validation against the actual wiki before writing the ETL script
- **Phase 3:** AF (Another Force) zone mechanics are complex enough that the graph schema may need extension after Phase 1; the exact property names and relationship structure for AF synergy may require iteration

Phases with well-established patterns (skip additional research):
- **Phase 2:** LangGraph StateGraph with conditional retry edges is a documented pattern; `TypedDict` state and Pydantic integration are standard
- **Phase 4:** FastAPI + HTMX + SSE is a well-documented pattern; connection pool configuration is standard
- **Phase 5:** pytest fixtures with mock Neo4j responses is standard testing practice

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All libraries are established; `langchain-neo4j` GraphRAG pattern is documented; LangGraph 0.2.x API is stable |
| Features | HIGH | Analogues from Genshin/Arknights/FFRK community tools confirm table stakes; game mechanics are from domain knowledge |
| Architecture | HIGH | LangGraph `StateGraph` with conditional retry is a canonical pattern; component boundaries are clean and dependency order is unambiguous |
| Pitfalls | HIGH | Cypher hallucination, infinite retry, and schema drift are well-documented GraphRAG failure modes; Grasta logic is game-specific but schema fix is clear |

**Overall confidence:** HIGH

### Gaps to Address

- **anothereden.wiki structure**: The scraper cannot be designed without inspecting the actual wiki page layout. Phase 1 planning should begin with a wiki audit (page structure, data completeness, rate limiting). This is low-risk — wiki scraping is straightforward — but the ETL field mappings are unknown until the wiki is inspected.
- **AF zone mechanics completeness**: The current schema models Character, Trait, Grasta, Ore. Another Force synergy may require additional node types or relationship properties that aren't in scope for v1. The Phase 1 schema should document AF as a known extension point.
- **Response time SLO under real conditions**: The 15s target for PLAN → CYPHER → VALIDATE → ANALYZE is reasonable but unvalidated against actual Sonnet 4.6 / Haiku 4.6 latency with real prompts. Phase 3 integration tests should measure end-to-end latency before Phase 4 SSE is designed.
- **AuraDB Free tier limits**: Connection count and query limits on Neo4j AuraDB Free are not confirmed. If limits are hit during Phase 3 testing, local Neo4j via Docker is the fallback.

---

## Sources

### Primary (HIGH confidence)
- LangGraph official docs — StateGraph, conditional edges, TypedDict state, node/edge patterns
- langchain-neo4j library — Neo4jGraph, GraphCypherQAChain, schema extraction
- anthropic Python SDK docs — client initialization, message construction
- FastAPI official docs — async endpoints, Pydantic integration, app lifecycle
- Neo4j 5.x driver docs — AsyncGraphDatabase.driver, connection pooling

### Secondary (MEDIUM confidence)
- Community GraphRAG implementations — Cypher hallucination patterns and schema injection solutions
- Game optimizer analogues (Keqingmains, Arknights planners) — feature expectations and trust mechanics
- HTMX SSE extension docs — `hx-ext="sse"` for streaming pipeline progress

### Tertiary (LOW confidence — needs validation)
- anothereden.wiki structure — assumed to be standard MediaWiki; page layout and data completeness unverified
- AuraDB Free tier connection limits — assumed sufficient for single-user portfolio demo; unconfirmed
- Another Eden AF zone mechanic complexity — game-specific knowledge, not externally sourced

---
*Research completed: 2026-03-14*
*Ready for roadmap: yes*
