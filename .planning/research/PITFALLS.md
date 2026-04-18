# Pitfalls Research

## Critical Pitfalls (Project-Killers)

---

### 1. Cypher Hallucination Without Schema Injection

**What goes wrong:** LLM generates Cypher referencing node labels or relationship types that don't exist in the graph (e.g., `(:CharacterUnit)` instead of `(:Character)`).

**Warning signs:** Queries return 0 results consistently; VALIDATE retry loop maxes out on every request.

**Prevention:**
- Always inject the full schema into the GENERATE_CYPHER system prompt
- Use `langchain-neo4j`'s `Neo4jGraph.get_schema()` to auto-generate the schema string
- Include example Cypher queries in the prompt (few-shot)

**Phase:** Address in Phase 2 (LangGraph workflow) — build schema injection from day one.

---

### 2. VALIDATE Loop Becomes Infinite (Budget Killer)

**What goes wrong:** Validation catches an error, retry regenerates the same broken query, loops until bills explode.

**Warning signs:** Retry count hits max on every request; no variance in regenerated queries.

**Prevention:**
- Hard cap: `if retry_count >= 3: route_to_graceful_error()`
- Pass the validation error message back to GENERATE_CYPHER as context
- Track retry count in `WorkflowState` — never in external state
- Add exponential backoff between retries (even 500ms helps)

**Phase:** Address in Phase 2 (workflow design) — bake this into the conditional edge from day one.

---

### 3. Graph Schema Drift Breaks All Queries

**What goes wrong:** Data pipeline runs, changes a property name (e.g., `light_shadow` → `alignment`), all stored Cypher patterns break silently.

**Warning signs:** Queries that worked yesterday return 0 results today.

**Prevention:**
- Define a schema version constant in the ETL script
- Add a schema validation step after loading: query the graph and assert expected node types exist
- Document the canonical schema in `SCHEMA.md` and treat it as a contract

**Phase:** Address in Phase 1 (data pipeline) — nail the schema before any agents use it.

---

### 4. ast.literal_eval on Untrusted CSV Data

**What goes wrong:** Current codebase uses `ast.literal_eval()` to parse personality lists stored as strings. This is a security risk if CSV is ever sourced from untrusted input.

**Warning signs:** CSV parsing works until someone has a character name with special characters.

**Prevention:**
- Store lists as JSON in Neo4j (native list property type)
- Use `json.loads()` for any string-to-list conversion
- Validate with Pydantic models at the ETL boundary

**Phase:** Address in Phase 1 when redesigning data pipeline — don't carry forward this pattern.

---

### 5. LangGraph State Mutation Between Nodes

**What goes wrong:** Nodes accidentally mutate shared state dicts instead of returning partial state updates, causing subtle cross-request data leakage.

**Warning signs:** Correct output for one query bleeds into the next query's response.

**Prevention:**
- Use `TypedDict` for `WorkflowState` with Pydantic validation
- Each node returns only the keys it modifies: `return {"cypher_query": result}`
- Never use mutable default values in state schema

**Phase:** Address in Phase 2 (LangGraph implementation).

---

## Common Mistakes (Annoying but Survivable)

---

### 6. Roster Input Matching Fails on Name Variations

**What goes wrong:** User types "Aldo (AS)" but Neo4j has "Aldo / Another Style". `str.contains()` match breaks.

**Prevention:** Normalize character names during ETL (lowercase, strip parenthetical variants). Add fuzzy matching in the PLAN agent prompt ("Resolve 'Aldo AS' to the canonical character name 'Aldo'").

**Phase:** Phase 3 (connecting workflow to real data).

---

### 7. Neo4j Connection Pool Exhaustion Under Load

**What goes wrong:** Each query opens a new Neo4j session without proper connection pooling, eventually hitting connection limits.

**Prevention:** Use `AsyncGraphDatabase.driver()` with connection pool configured; reuse driver as a FastAPI app-level singleton.

**Phase:** Phase 4 (FastAPI integration).

---

### 8. No Streaming = Perceived Slowness

**What goes wrong:** PLAN → CYPHER → VALIDATE → ANALYZE takes 8-12 seconds but the UI shows nothing until done.

**Prevention:** Use Server-Sent Events (SSE) or WebSocket to stream node completion status. HTMX supports SSE natively (`hx-ext="sse"`).

**Phase:** Phase 4 (frontend) — add progress events even if just "Planning... Querying graph... Validating... Analyzing..."

---

### 9. Grasta "is_shareable" Logic Is Complex

**What goes wrong:** Shareable Grasta can be equipped on multiple characters, but only one character can *activate* the personality buff. Query logic conflates these.

**Prevention:** In the graph schema, model this explicitly: `(:Grasta {is_shareable: bool, activating_trait: str})`. Document the game mechanic in the schema notes. Test with known valid synergy pairs before building the optimizer.

**Phase:** Phase 1 (graph schema design).

---

### 10. Portfolio Projects Die Without Tests

**What goes wrong:** Works on your machine, fails in recruiter demo because environment isn't set up, or a graph schema change broke queries 2 weeks ago.

**Prevention:**
- Pytest fixtures with mock Neo4j responses (no real DB needed for unit tests)
- At least one integration test that hits a real Neo4j AuraDB Free instance
- `pytest --tb=short` in README, so recruiters can verify it works

**Phase:** Thread testing through all phases, not as a final step.

---
*Generated: 2026-03-14 (training knowledge, web search unavailable)*
