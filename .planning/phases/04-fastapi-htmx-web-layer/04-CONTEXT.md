# Phase 4: FastAPI + HTMX Web Layer - Context

**Gathered:** 2026-04-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Expose the working LangGraph pipeline via HTTP with a streaming progress UI. Users open a browser, manage their owned character/Grasta roster (persisted in localStorage), submit a natural language query, and see pipeline node status update in real time via SSE. The backend remains entirely stateless — all roster state lives in the browser. No AWS deployment, no Dockerfiles — those are Phase 5.

</domain>

<decisions>
## Implementation Decisions

### Roster Storage
- **D-01:** Roster is stored in browser `localStorage` — backend is stateless, zero session management
- **D-02:** On query submission, the frontend sends roster as a JSON array in the POST /api/query payload: `{"query": string, "roster": list[str]}`

### Roster UX
- **D-03:** Searchable checklist approach — user browses the full character and Grasta lists and checks what they own
- **D-04:** Character and Grasta lists loaded on page open via two endpoints: `GET /api/entities` returns both characters and Grastas in one combined payload (single request, categorized)
- **D-05:** Characters and Grastas displayed in **separate tabs** within the roster panel — keeps large lists navigable
- **D-06:** Checklist selections sync to `localStorage` — persists across sessions, survives page refresh

### API Endpoints
- **D-07:** FastAPI app with lifespan handler initializing `AsyncGraphDatabase` driver as an app-level singleton (same pattern as existing `run.py`)
- **D-08:** `GET /api/entities` — returns master list of all Characters and Grastas from Neo4j for the checklist UI
- **D-09:** `POST /api/query` — accepts `{"query": string, "roster": list[str]}`; returns an SSE stream of node status events, concluding with a rendered HTML fragment (the final result card)
- **D-10:** `POST /admin/refresh-data` — triggers ETL pipeline; protected by static API key

### SSE Event Design
- **D-11:** Progress events carry **JSON**: `{"event": "node_status", "node": "VALIDATE", "attempt": 2, "max": 3}`
- **D-12:** Final event carries a **rendered HTML fragment** — Jinja2 renders the result template server-side and sends it as the last SSE event; HTMX swaps it into the result div
- **D-13:** When VALIDATE retries, UI shows `"Validating... attempt 2/3"` inline in the progress area — no animation, no banner, just clear text

### Frontend / Templates
- **D-14:** `index.html` Jinja2 template with:
  - Sidebar or section for searchable checklist (2 tabs: Characters, Grastas)
  - Natural language query form
  - Progress div using `hx-ext="sse"` wired to `/api/query` stream
  - Result div swapped when final HTML fragment arrives
- **D-15:** HTMX handles SSE and DOM swaps — minimal custom JavaScript; localStorage sync is the only JS that must be hand-written

### Result Display
- **D-16:** Team displayed as **character cards grid**: frontline row of 4 cards, reserve row of 2 cards, synergy explanation paragraph below
- **D-17:** Each card shows: character name, role, and assigned Grasta **names only** (no effect text in Phase 4)
- **D-18:** Layout mirrors the agreed mockup:
  ```
  [ Aldo ]    [ Ciel ]    [ Shion ]    [ Amy ]
    Attacker   Buffer     DPS        Healer
    Grasta: A  Grasta: B  Grasta: C  Grasta: D

  [ Reserve 1 ]   [ Reserve 2 ]
    Versatile       Support

  ──────────────────────────────────────────
   Synergy: Blunt zone team with personality X...
  ──────────────────────────────────────────
  ```

### Admin Endpoint Auth
- **D-19:** `POST /admin/refresh-data` requires `X-Admin-Key` header matching `ADMIN_KEY` env var — static API key, stateless, no session
- **D-20:** Returns JSON on success/failure: `{"status": "ok", "message": "ETL complete: N chars, M Grastas loaded"}` or `{"status": "error", "message": "..."}`

### Claude's Discretion
- Specific Tailwind/CSS styling choices for card layout and progress area
- Exact HTML structure of the checklist component (accordion, tabs panel, etc.)
- Error display when retry cap exhausted (within scope of SC-4 "graceful error display")
- Empty result message when no matching teams found

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Workflow Output Contract
- `src/workflow/nodes/format.py` — FORMAT node output schema: `{frontline: [{name, role, grastas}], reserve: [{name, role, grastas}], synergy_explanation: str}` — Phase 4 templates iterate this directly
- `src/workflow/run.py` — existing async main() and Neo4j driver initialization pattern; Phase 4 FastAPI lifespan reuses the same `AsyncGraphDatabase` pattern
- `src/workflow/graph.py` — `build_graph(driver)` signature; Phase 4 calls this at request time

### Phase Context
- `.planning/phases/02-langgraph-workflow-stub-data/02-CONTEXT.md` — FORMAT output structure and WorkflowState schema decisions (locked in Phase 2)
- `.planning/REQUIREMENTS.md` — WEB-01 through WEB-05 acceptance criteria for Phase 4

### ETL (for /admin/refresh-data)
- `src/etl/run_etl.py` — ETL entry point that `/admin/refresh-data` must invoke
- `src/etl/constants.py` — EXPECTED_NODE_COUNTS (used to report counts in success message)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/workflow/run.py:main()` — async pipeline runner; Phase 4 calls this from the SSE endpoint; Neo4j driver initialization pattern is identical to what the lifespan handler needs
- `src/workflow/graph.py:build_graph(driver)` — accepts the singleton driver; already async-compatible
- `src/etl/run_etl.py` — ETL entry point for `/admin/refresh-data` to invoke

### Established Patterns
- Full async architecture throughout (asyncio + AsyncGraphDatabase) — FastAPI lifespan + async endpoints are the natural fit
- No existing web layer — Phase 4 creates `src/web/` or `src/api/` directory from scratch
- FORMAT output is a structured dict (not a string), meaning Jinja2 templates iterate it directly with `{% for char in result.frontline %}`

### Integration Points
- `build_graph(driver)` is the call site for the SSE endpoint — driver is the lifespan singleton
- Neo4j `AsyncGraphDatabase` driver must be shared across requests (singleton), not recreated per request
- ETL pipeline in `src/etl/run_etl.py` is the target of `/admin/refresh-data`

</code_context>

<specifics>
## Specific Ideas

- User's architecture note (verbatim intent): "I want the client side/frontend to support character/Grasta owned by user, so that the AI agent recommendation is based on list of what the user have in their game account. Allow them to add any character/Grasta manually if they got new one."
- The final SSE event delivers a rendered HTML fragment (not raw JSON) — Jinja2 renders the team result server-side; HTMX swaps it into the result div. This keeps the template logic server-side consistent with the Jinja2 approach used elsewhere.
- `GET /api/entities` returns both Characters and Grastas in one combined payload (not two separate endpoints) — minimizes round trips on page load.

</specifics>

<deferred>
## Deferred Ideas

- Grasta effect descriptions in result cards — Phase 5 polish or future enhancement
- SSE streaming of ETL progress in /admin/refresh-data — deferred; synchronous JSON response is sufficient for Phase 4
- Multi-user accounts / server-side roster persistence — deferred; localStorage + stateless backend covers Phase 4 scope
- AWS deployment, Dockerfiles — explicitly deferred to Phase 5

</deferred>

---

*Phase: 04-fastapi-htmx-web-layer*
*Context gathered: 2026-04-19*
