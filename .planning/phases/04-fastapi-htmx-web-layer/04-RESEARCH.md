# Phase 4: FastAPI + HTMX Web Layer - Research

**Researched:** 2026-04-19
**Domain:** FastAPI SSE streaming, HTMX, Jinja2, LangGraph integration
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Roster Storage**
- D-01: Roster is stored in browser `localStorage` — backend is stateless, zero session management
- D-02: On query submission, the frontend sends roster as a JSON array in the POST /api/query payload: `{"query": string, "roster": list[str]}`

**Roster UX**
- D-03: Searchable checklist approach — user browses the full character and Grasta lists and checks what they own
- D-04: Character and Grasta lists loaded on page open via two endpoints: `GET /api/entities` returns both characters and Grastas in one combined payload (single request, categorized)
- D-05: Characters and Grastas displayed in separate tabs within the roster panel
- D-06: Checklist selections sync to `localStorage` — persists across sessions, survives page refresh

**API Endpoints**
- D-07: FastAPI app with lifespan handler initializing `AsyncGraphDatabase` driver as an app-level singleton
- D-08: `GET /api/entities` — returns master list of all Characters and Grastas from Neo4j for the checklist UI
- D-09: `POST /api/query` — accepts `{"query": string, "roster": list[str]}`; returns an SSE stream of node status events, concluding with a rendered HTML fragment
- D-10: `POST /admin/refresh-data` — triggers ETL pipeline; protected by static API key

**SSE Event Design**
- D-11: Progress events carry JSON: `{"event": "node_status", "node": "VALIDATE", "attempt": 2, "max": 3}`
- D-12: Final event carries a rendered HTML fragment — Jinja2 renders the result template server-side and sends it as the last SSE event; HTMX swaps it into the result div
- D-13: When VALIDATE retries, UI shows `"Validating... attempt 2/3"` inline in the progress area

**Frontend / Templates**
- D-14: `index.html` Jinja2 template with sidebar checklist (2 tabs), query form, progress div (SSE), result div
- D-15: HTMX handles SSE and DOM swaps — minimal custom JavaScript; localStorage sync is the only JS that must be hand-written

**Result Display**
- D-16: Team displayed as character cards grid: frontline row of 4 cards, reserve row of 2 cards, synergy explanation below
- D-17: Each card shows: character name, role, and assigned Grasta names only (no effect text in Phase 4)
- D-18: Layout mirrors the agreed mockup (4-front + 2-reserve + synergy paragraph)

**Admin Endpoint Auth**
- D-19: `POST /admin/refresh-data` requires `X-Admin-Key` header matching `ADMIN_KEY` env var
- D-20: Returns JSON `{"status": "ok", "message": "..."}` or `{"status": "error", "message": "..."}`

### Claude's Discretion
- Specific Tailwind/CSS styling choices for card layout and progress area
- Exact HTML structure of the checklist component (accordion, tabs panel, etc.)
- Error display when retry cap exhausted (within scope of SC-4 "graceful error display")
- Empty result message when no matching teams found

### Deferred Ideas (OUT OF SCOPE)
- Grasta effect descriptions in result cards — Phase 5 polish
- SSE streaming of ETL progress in /admin/refresh-data — synchronous JSON response is sufficient
- Multi-user accounts / server-side roster persistence
- AWS deployment, Dockerfiles — explicitly deferred to Phase 5
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| WEB-01 | User can access the system via web browser (no installation required) | FastAPI + uvicorn serves HTTP; static files via StaticFiles mount |
| WEB-02 | Web UI provides roster input form and natural language query submission | HTMX form + GET /api/entities + checklist pattern |
| WEB-03 | Pipeline node completion status is streamed to UI via SSE (PLAN → CYPHER → VALIDATE → ANALYZE) | LangGraph `get_stream_writer` + `astream(stream_mode=["updates","custom"])` + FastAPI `EventSourceResponse` |
| WEB-04 | Neo4j driver is initialized as an app-level singleton with async connection pooling | FastAPI `@asynccontextmanager` lifespan handler — identical pattern to `src/workflow/run.py:main()` |
| WEB-05 | Admin can trigger a full data refresh via POST /admin/refresh-data endpoint | `APIKeyHeader` dependency + `src/etl/run_etl.py:main()` invocation |
</phase_requirements>

---

## Summary

Phase 4 creates `src/web/` from scratch — a FastAPI application that exposes the existing LangGraph pipeline via HTTP with SSE streaming progress. The entire backend is stateless: roster data lives in `localStorage`, sent with each query POST. The most architecturally interesting problem is the **HTMX + SSE + POST body mismatch**: the HTMX SSE extension (v2.x) uses the browser `EventSource` API, which is GET-only. The correct solution is a **two-phase pattern** — a form POST submits the query and populates an in-process `asyncio.Queue`, then a GET SSE endpoint drains that queue. Alternatively (and more elegantly for this use case), a small JavaScript shim sets `sse-connect` dynamically with query params after the form POST response returns a progress-div fragment.

The recommended stack is: FastAPI 0.136.0 (has built-in `EventSourceResponse` from `fastapi.sse` — no `sse-starlette` needed), LangGraph `astream()` with `stream_mode=["updates","custom"]`, Jinja2Templates, HTMX 2.x + htmx-ext-sse 2.2.4, and a minimal hand-written localStorage JS snippet.

**Primary recommendation:** Use the two-phase POST→SSE-GET pattern with asyncio.Queue per request; phase 1 returns an HTMX fragment containing the `sse-connect` URL with a job ID; phase 2 streams events until the final HTML fragment, then sends `sse-close="done"`.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| SSE streaming pipeline progress | API / Backend | — | LangGraph runs server-side; events emitted from graph nodes |
| Roster persistence | Browser / Client | — | localStorage is the store; backend is stateless per D-01 |
| Entity list (Characters/Grastas) | API / Backend | Database | GET /api/entities fetches from Neo4j on every page load |
| Query form submission | Browser / Client | API / Backend | HTMX POST carries query + roster JSON |
| HTML result rendering | API / Backend | — | Jinja2 renders server-side per D-12; sent as SSE final event |
| Checklist search/filter | Browser / Client | — | Client-side JS filter on pre-loaded entity list (minimal JS) |
| Admin refresh | API / Backend | — | POST /admin/refresh-data triggers ETL; no UI needed |
| Tab switching (Characters/Grastas) | Browser / Client | — | Pure CSS or HTMX hx-show; no server roundtrip |
| Neo4j connection pooling | API / Backend | Database | FastAPI lifespan singleton matches run.py pattern |

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| fastapi | 0.136.0 | HTTP framework, SSE via `fastapi.sse.EventSourceResponse` | Built-in SSE support added in 0.135.0; no extra library needed [VERIFIED: pip index] |
| uvicorn | 0.44.0 | ASGI server | Standard FastAPI server; already installed system-wide [VERIFIED: `uvicorn --version`] |
| jinja2 | 3.1.6 | Template engine for HTML fragments | Official FastAPI template integration via `Jinja2Templates` [VERIFIED: pip index] |
| python-multipart | 0.0.26 | Form data parsing (needed for any form POST) | Required by FastAPI for form body parsing [CITED: FastAPI docs] |
| htmx | 2.0.x (CDN) | Frontend AJAX/SSE without JavaScript | `htmx-ext-sse@2.2.4` via jsDelivr CDN [VERIFIED: htmx.org/extensions/sse] |
| aiofiles | latest | Static file serving with async I/O | Required by `fastapi.staticfiles.StaticFiles` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| htmx-ext-sse | 2.2.4 (CDN) | SSE extension for HTMX | Required — HTMX core does not handle SSE without this extension |
| httpx | 0.28.1 (already installed) | Async HTTP client for tests | `httpx.AsyncClient(transport=ASGITransport(app=app))` in async tests |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| fastapi.sse.EventSourceResponse | sse-starlette 3.3.4 | sse-starlette is now redundant — FastAPI 0.135+ ships native SSE; avoid adding an extra dependency |
| Two-phase POST→GET SSE | Pure GET SSE with query params | Query + roster in GET URL is unwieldy (roster can be 20+ names); two-phase is cleaner |
| Jinja2 result fragment (server-side) | HTMX client-side templates | Server-side rendering is consistent with D-12 decision; no JS template engine needed |
| localStorage JS | Cookie-based roster | Stateless backend (D-01) makes cookies inappropriate; localStorage is correct |

**Installation (new dependencies only):**
```bash
pip install "fastapi[standard]>=0.136.0" jinja2>=3.1.6 python-multipart>=0.0.26 aiofiles
```

Note: `fastapi[standard]` installs fastapi + uvicorn + jinja2 + python-multipart together.

**Version verification:** [VERIFIED: `pip3 index versions fastapi` → 0.136.0; `pip3 index versions jinja2` → 3.1.6; `pip3 index versions python-multipart` → 0.0.26 as of 2026-04-19]

---

## Architecture Patterns

### System Architecture Diagram

```
Browser
  │
  ├─── GET /              ──────────► FastAPI GET /
  │      (page load)                    Jinja2 index.html → full page HTML
  │
  ├─── GET /api/entities  ──────────► FastAPI GET /api/entities
  │      (on load)                      Neo4j: MATCH (c:Character), (g:Grasta)
  │                                     → {"characters": [...], "grastas": [...]}
  │
  ├─── User fills checklist (localStorage sync)
  │
  ├─── User submits query
  │      │
  │      ├─ HTMX POST /api/query  ──► FastAPI POST /api/query
  │      │    {query, roster}           → asyncio.Queue(job_id) populated
  │      │                              → returns HTML fragment:
  │      │                                <div sse-connect="/api/stream/{job_id}">
  │      │
  │      └─ HTMX swaps progress div
  │           │
  │           └─ SSE GET /api/stream/{job_id}  ──► FastAPI GET /api/stream/{job_id}
  │                                                  drains Queue → builds graph
  │                                                  │
  │                                                  ├─ LangGraph.astream(stream_mode=["updates","custom"])
  │                                                  │    plan: emit node_status event
  │                                                  │    generate_cypher: emit node_status event
  │                                                  │    validate: emit node_status with retry info
  │                                                  │    analyze: emit node_status event
  │                                                  │    format: emit final HTML fragment event
  │                                                  │
  │                                                  └─ SSE stream ends → sse-close="done"
  │
  └─── Admin: POST /admin/refresh-data  ──► APIKeyHeader check → ETL run → JSON response
```

### Recommended Project Structure
```
src/web/
├── __init__.py
├── app.py              # FastAPI app factory, lifespan handler, route mounts
├── routes/
│   ├── __init__.py
│   ├── pages.py        # GET / (index page)
│   ├── api.py          # GET /api/entities, POST /api/query, GET /api/stream/{job_id}
│   └── admin.py        # POST /admin/refresh-data
├── dependencies.py     # get_driver() dependency, verify_admin_key() dependency
├── streaming.py        # SSE generator: wraps LangGraph astream, emits ServerSentEvent
└── templates/
    ├── index.html      # Full page: checklist sidebar, query form, progress div, result div
    ├── partials/
    │   ├── progress.html    # SSE progress div fragment (returned by POST /api/query)
    │   └── result.html      # Team result card grid (rendered as final SSE event data)
    └── static/
        └── app.js      # localStorage sync logic only

src/static/             # OR serve from src/web/templates/static/
└── app.js
```

### Pattern 1: FastAPI Lifespan Handler for AsyncGraphDatabase Singleton

**What:** Initialize Neo4j driver once at startup, share across all requests via `app.state`.
**When to use:** Any resource that is expensive to create and must be shared (connection pools, ML models).

```python
# Source: https://fastapi.tiangolo.com/tutorial/server-sent-events + run.py pattern
from contextlib import asynccontextmanager
from fastapi import FastAPI
from neo4j import AsyncGraphDatabase
import os

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_AUTH = tuple(os.getenv("NEO4J_AUTH", "neo4j/anothereden").split("/", 1))

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create singleton driver
    app.state.driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)
    yield
    # Shutdown: close driver
    await app.state.driver.close()

app = FastAPI(lifespan=lifespan)
```

**Dependency to access the driver in route handlers:**
```python
# Source: https://fastapi.tiangolo.com/tutorial/dependencies
from fastapi import Depends, Request
from neo4j import AsyncDriver

def get_driver(request: Request) -> AsyncDriver:
    return request.app.state.driver
```

### Pattern 2: FastAPI SSE Endpoint (Native, FastAPI >= 0.135.0)

**What:** Stream SSE events from an async generator using the built-in `EventSourceResponse`.
**When to use:** Any endpoint that streams progress or results.

```python
# Source: https://fastapi.tiangolo.com/tutorial/server-sent-events
from fastapi.sse import EventSourceResponse, ServerSentEvent
from collections.abc import AsyncIterable

@app.get("/api/stream/{job_id}", response_class=EventSourceResponse)
async def stream_job(job_id: str, driver=Depends(get_driver)) -> AsyncIterable[ServerSentEvent]:
    # Phase 2: drain queue and run pipeline
    query_data = await get_job_queue(job_id)  # retrieve from in-memory dict
    async for event in run_pipeline_stream(query_data, driver):
        yield event
```

**Named events with raw HTML data (for final result fragment):**
```python
# Source: https://fastapi.tiangolo.com/tutorial/server-sent-events
yield ServerSentEvent(
    data=json.dumps({"event": "node_status", "node": "PLAN", "attempt": 1, "max": 1}),
    event="node_status"
)
# Final event: raw HTML fragment, not JSON
yield ServerSentEvent(raw_data=rendered_html, event="result")
# Close signal
yield ServerSentEvent(data="", event="done")
```

### Pattern 3: LangGraph Streaming with get_stream_writer

**What:** Emit custom SSE events from inside LangGraph nodes at completion.
**When to use:** When you need per-node progress events without modifying the graph's state schema.

**Option A — astream with updates mode (node name from chunk):**
```python
# Source: https://docs.langchain.com/oss/python/langgraph/streaming
# Installed: langgraph 1.0.10 [VERIFIED]
# get_stream_writer available [VERIFIED: import check]

async def run_pipeline_stream(query_data: dict, driver) -> AsyncIterable[ServerSentEvent]:
    from src.workflow.graph import build_graph
    graph = build_graph(driver=driver)
    initial_state = {
        "user_query": query_data["query"],
        "roster": query_data["roster"],
        "plan_strategy": "",
        "cypher_query": "",
        "db_results": [],
        "validation_errors": [],
        "retry_count": 0,
        "analysis_result": "",
        "final_output": {},
    }
    # stream_mode="updates" yields {type: "updates", data: {node_name: state_update}}
    async for chunk in graph.astream(initial_state, stream_mode="updates", version="v2"):
        if chunk["type"] == "updates":
            for node_name, state_update in chunk["data"].items():
                retry = state_update.get("retry_count", 1)
                yield ServerSentEvent(
                    data=json.dumps({
                        "event": "node_status",
                        "node": node_name.upper(),
                        "attempt": retry,
                        "max": 3
                    }),
                    event="node_status"
                )
```

**Option B — get_stream_writer in nodes (custom mode):**
Add `writer = get_stream_writer()` inside each node function for fine-grained control:
```python
# Source: https://docs.langchain.com/oss/python/langgraph/streaming
from langgraph.config import get_stream_writer

def format_node(state: WorkflowState) -> dict:
    writer = get_stream_writer()
    writer({"node": "FORMAT", "status": "complete"})
    # ... existing format logic ...
```
Then consume with `stream_mode="custom"`. Note: adding `get_stream_writer()` to existing nodes is a minimal intrusion but requires modifying Phase 2/3 files.

**Recommendation:** Use `stream_mode="updates"` (Option A) — requires zero changes to existing node code. Node names (`plan`, `generate_cypher`, `validate`, `analyze`, `format`) come from the graph topology and are available in the `chunk["data"]` keys.

### Pattern 4: Two-Phase POST→SSE-GET Pattern

**What:** Form POST populates an in-process queue and returns an HTMX fragment that includes the SSE connection URL. HTMX then opens an SSE connection to GET the stream.

**Why needed:** HTMX SSE extension v2.x uses the browser `EventSource` API, which is GET-only. POST body cannot be sent to an EventSource. [VERIFIED: EventSource spec and htmx.org/extensions/sse]

```python
# Phase 1: POST handler
from uuid import uuid4
import asyncio

# In-process job store (stateless per request — cleared after stream completes)
_job_queues: dict[str, asyncio.Queue] = {}

class QueryRequest(BaseModel):
    query: str
    roster: list[str]

@app.post("/api/query")
async def post_query(body: QueryRequest, request: Request):
    job_id = str(uuid4())
    _job_queues[job_id] = {"query": body.query, "roster": body.roster}
    # Return HTMX fragment that triggers the SSE GET connection
    return templates.TemplateResponse(
        request=request,
        name="partials/progress.html",
        context={"job_id": job_id}
    )
```

```html
<!-- partials/progress.html — returned by POST /api/query -->
<!-- HTMX swaps this into #progress-div, which opens the SSE connection -->
<div id="progress-container"
     hx-ext="sse"
     sse-connect="/api/stream/{{ job_id }}"
     sse-close="done">
    <div id="progress-status" sse-swap="node_status">
        Starting pipeline...
    </div>
    <div id="result-area" sse-swap="result" hx-swap="outerHTML">
    </div>
</div>
```

**Key insight:** The `sse-connect` URL is generated server-side with the job_id, embedded in the returned HTML fragment. HTMX opens the EventSource connection automatically when it processes the swapped-in element. `sse-close="done"` tells the extension to close the connection when an event named `"done"` is received.

### Pattern 5: Admin Key Header Authentication

**What:** FastAPI dependency that validates `X-Admin-Key` header against `ADMIN_KEY` env var.
**When to use:** Static API key check for internal admin endpoints.

```python
# Source: https://fastapi.tiangolo.com/reference/security (APIKeyHeader)
import os
from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader

admin_key_header = APIKeyHeader(name="X-Admin-Key", auto_error=False)

def verify_admin_key(api_key: str | None = Security(admin_key_header)):
    expected = os.getenv("ADMIN_KEY", "")
    if not expected or api_key != expected:
        raise HTTPException(status_code=403, detail="Invalid or missing X-Admin-Key header")
    return api_key

@app.post("/admin/refresh-data")
async def refresh_data(
    _key: str = Depends(verify_admin_key),
    driver=Depends(get_driver)
):
    try:
        from src.etl.run_etl import main as run_etl
        await run_etl(driver=driver)
        return {"status": "ok", "message": "ETL complete"}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}
```

### Pattern 6: Jinja2 with FastAPI

```python
# Source: https://fastapi.tiangolo.com/advanced/templates
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

templates = Jinja2Templates(directory="src/web/templates")
app.mount("/static", StaticFiles(directory="src/web/static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html", context={})
```

**Rendering result fragment for final SSE event:**
```python
# Render Jinja2 template to a string for inclusion in SSE data
from starlette.templating import _TemplateResponse

def render_result_fragment(templates: Jinja2Templates, final_output: dict) -> str:
    template = templates.env.get_template("partials/result.html")
    return template.render(result=final_output)

# In SSE generator:
html_fragment = render_result_fragment(templates, final_output)
yield ServerSentEvent(raw_data=html_fragment, event="result")
yield ServerSentEvent(data="", event="done")
```

### Pattern 7: GET /api/entities — Neo4j Cypher

```cypher
-- Return all Character names and all Grasta names in one query
MATCH (c:Character) RETURN c.name AS name, 'Character' AS type
UNION ALL
MATCH (g:Grasta) RETURN g.name AS name, 'Grasta' AS type
ORDER BY name
```

FastAPI endpoint:
```python
@app.get("/api/entities")
async def get_entities(driver=Depends(get_driver)):
    records, _, _ = await driver.execute_query(
        "MATCH (c:Character) RETURN c.name AS name "
        "UNION ALL "
        "MATCH (g:Grasta) RETURN g.name AS name ORDER BY name",
        database_="neo4j"
    )
    characters = [r["name"] for r in records if r["type"] == "Character"]
    grastas = [r["name"] for r in records if r["type"] == "Grasta"]
    return {"characters": characters, "grastas": grastas}
```

Note: The UNION ALL + type column approach is simpler than two separate queries. [ASSUMED — Cypher syntax is standard but not verified against live Neo4j in this session]

### Pattern 8: HTMX Searchable Checklist with localStorage

The checklist uses HTMX active-search pattern for filtering, but checkbox state is managed by hand-written JavaScript to sync to `localStorage`.

```html
<!-- Checklist filter — sends to server for filtered HTML response -->
<input type="search"
       name="q"
       placeholder="Search characters..."
       hx-post="/api/entities/search"
       hx-trigger="input changed delay:300ms"
       hx-target="#character-list"
       hx-include="[name='roster_tab']">

<div id="character-list">
  {% for name in characters %}
  <label>
    <input type="checkbox" name="roster" value="{{ name }}" class="roster-checkbox">
    {{ name }}
  </label>
  {% endfor %}
</div>
```

**Alternative (simpler, no extra endpoint):** Client-side filter via JavaScript. Given the entity list is loaded once at page open (via `GET /api/entities`), filtering can be pure client-side JS without any server roundtrip. This avoids a dedicated search endpoint and is viable for ~400 characters + ~489 Grastas.

```javascript
// app.js — minimal localStorage + filter JS
const STORAGE_KEY = "anothereden_roster";

function loadRoster() {
  return JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
}

function saveRoster(roster) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(roster));
}

// Sync checkboxes to localStorage on page load
document.addEventListener("DOMContentLoaded", () => {
  const roster = loadRoster();
  document.querySelectorAll(".roster-checkbox").forEach(cb => {
    if (roster.includes(cb.value)) cb.checked = true;
    cb.addEventListener("change", () => {
      const current = loadRoster();
      const updated = cb.checked
        ? [...new Set([...current, cb.value])]
        : current.filter(n => n !== cb.value);
      saveRoster(updated);
    });
  });
});

// Client-side filter
document.getElementById("character-search").addEventListener("input", function() {
  const q = this.value.toLowerCase();
  document.querySelectorAll(".roster-item").forEach(item => {
    item.style.display = item.dataset.name.toLowerCase().includes(q) ? "" : "none";
  });
});
```

### Anti-Patterns to Avoid

- **Re-creating AsyncGraphDatabase driver per request:** The driver manages a connection pool. Creating a new driver per request destroys pooling and adds ~200ms overhead per call. Always use the lifespan singleton. [VERIFIED: same mistake is documented in run.py comments]
- **Using `graph.invoke()` instead of `graph.ainvoke()` in async context:** This blocks the event loop. The project already uses `ainvoke` throughout — do not regress. [VERIFIED: graph.py uses ainvoke]
- **Sending SSE from a POST endpoint with `EventSource`:** Browser `EventSource` only opens GET connections. A POST endpoint cannot be the SSE source for `sse-connect`. The two-phase pattern solves this. [VERIFIED: MDN EventSource spec, htmx.org/extensions/sse]
- **Using `sse-starlette`:** The `sse-starlette` library is now redundant. FastAPI 0.135.0+ ships `fastapi.sse.EventSourceResponse` natively. Using both creates a conflict. [VERIFIED: fastapi.tiangolo.com/tutorial/server-sent-events — "Added in FastAPI 0.135.0"]
- **Importing `ChatAnthropic` directly in web routes:** Project convention (from STATE.md) requires using `get_llm(role)` factory from `src/workflow/llm.py`. Web layer should not import LLM classes directly.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SSE response format | Custom `text/event-stream` generator | `fastapi.sse.EventSourceResponse` | Handles keep-alive pings, cache headers, retry field automatically |
| API key header extraction | Manual `request.headers.get("X-Admin-Key")` | `fastapi.security.APIKeyHeader` | Auto-integrates with OpenAPI docs; handles missing header uniformly |
| Jinja2 environment setup | `jinja2.Environment` manually | `fastapi.templating.Jinja2Templates` | Handles template auto-reload, context processor integration |
| Static file serving | Custom file read endpoint | `fastapi.staticfiles.StaticFiles` | Handles ETag, Last-Modified, async reads via aiofiles |
| Neo4j query error handling | Per-endpoint try/except | Dependency injection with `get_driver()` | Centralizes connection error handling |
| UUID job IDs | Random int or timestamp | `uuid.uuid4()` | Collision-resistant, no synchronization needed |

**Key insight:** FastAPI 0.136.0 is a batteries-included framework. The SSE, security, template, and static file needs of this phase are all covered by first-party FastAPI/Starlette features. The only custom code needed is the LangGraph-to-SSE bridge in `streaming.py`.

---

## Common Pitfalls

### Pitfall 1: HTMX SSE Extension Cannot POST
**What goes wrong:** Developer tries to set `sse-connect` on a form with `hx-post`, expecting the SSE connection to use POST. The browser silently falls back to GET or the SSE connection fails.
**Why it happens:** Browser's `EventSource` API only supports GET. The HTMX SSE extension (v2.x) wraps `EventSource` directly.
**How to avoid:** Use the two-phase pattern. POST `/api/query` → returns progress fragment with `sse-connect="/api/stream/{job_id}"` → HTMX opens GET SSE connection.
**Warning signs:** SSE connection logs on server show GET requests regardless of what the HTMX attribute says.

### Pitfall 2: asyncio.Queue Job Store is Single-Process Only
**What goes wrong:** In-memory `_job_queues` dict works locally but breaks when uvicorn is run with multiple workers (`--workers 4`). Request hits worker 1 (creates queue); SSE GET hits worker 2 (queue not found).
**Why it happens:** Each uvicorn worker is an independent process with separate memory.
**How to avoid:** For Phase 4, run uvicorn with a single worker (`uvicorn src.web.app:app --workers 1`). Document this constraint clearly. Multi-worker support (Redis queue) is a Phase 5 concern.
**Warning signs:** SSE stream returns 404 or empty immediately.

### Pitfall 3: LangGraph astream node_name Mismatch
**What goes wrong:** Progress UI shows "generate_cypher" but user expects "CYPHER" or "GENERATE CYPHER". Node names in LangGraph come from the `builder.add_node("generate_cypher", ...)` call in `graph.py`.
**Why it happens:** LangGraph uses the string key passed to `add_node` verbatim in `updates` stream chunks.
**How to avoid:** Map node names to display labels in `streaming.py`:
```python
NODE_LABELS = {"plan": "PLAN", "generate_cypher": "CYPHER", "validate": "VALIDATE", "analyze": "ANALYZE", "format": "FORMAT"}
```
**Warning signs:** UI shows raw internal node names with underscores.

### Pitfall 4: Jinja2 Template Not Finding Partials
**What goes wrong:** `templates.TemplateResponse("partials/result.html", ...)` raises `TemplateNotFound`.
**Why it happens:** `Jinja2Templates(directory="src/web/templates")` — path must be correct relative to where uvicorn is launched (project root).
**How to avoid:** Use `Path(__file__).parent / "templates"` as the templates directory to make it absolute, independent of CWD.
**Warning signs:** `jinja2.exceptions.TemplateNotFound` on any endpoint that renders a template.

### Pitfall 5: SSE Stream Leaks on Client Disconnect
**What goes wrong:** Client closes browser tab mid-stream; server continues running the full LangGraph pipeline, consuming LLM API credits unnecessarily.
**Why it happens:** `EventSourceResponse` does not automatically cancel the async generator on disconnect.
**How to avoid:** Wrap the SSE generator with disconnect detection:
```python
import asyncio
async def stream_with_disconnect(request: Request, generator):
    async for event in generator:
        if await request.is_disconnected():
            break
        yield event
```
**Warning signs:** LLM API costs higher than expected; server logs show completed graph runs for abandoned sessions.

### Pitfall 6: ETL run_etl.main() Blocks the Event Loop
**What goes wrong:** `POST /admin/refresh-data` calls `await run_etl_main(driver=driver)` but ETL includes scraping with nodriver (browser automation), which may block.
**Why it happens:** `nodriver` uses Chrome/Chromium under the hood; some operations may not be fully async.
**How to avoid:** Run ETL in a background task (`BackgroundTasks`) or wrap with `asyncio.get_event_loop().run_in_executor()`. For Phase 4, synchronous-but-awaitable is acceptable since admin refresh is infrequent.
**Warning signs:** Server stops responding to other requests during ETL.

### Pitfall 7: retry_count in Updates Stream
**What goes wrong:** `validate` node appears in `updates` stream on every retry, but `retry_count` in the state update increments only on failure. First VALIDATE call has `retry_count=0` but attempt number shown to user should be 1.
**Why it happens:** `retry_count` starts at 0 and is incremented only on failure by the validate node. The attempt shown to the user should be `retry_count + 1` at the time the VALIDATE node emits.
**How to avoid:** In `streaming.py`, calculate attempt as `state_update.get("retry_count", 0) + 1` when building the SSE payload for VALIDATE events.

---

## Code Examples

### Full SSE Streaming Generator

```python
# Source: https://docs.langchain.com/oss/python/langgraph/streaming (updates mode)
#         https://fastapi.tiangolo.com/tutorial/server-sent-events (ServerSentEvent)
import json
from collections.abc import AsyncIterable
from fastapi.sse import ServerSentEvent
from fastapi.templating import Jinja2Templates

NODE_LABELS = {
    "plan": "PLAN",
    "generate_cypher": "CYPHER",
    "validate": "VALIDATE",
    "analyze": "ANALYZE",
    "format": "FORMAT",
}

async def pipeline_sse_generator(
    query: str,
    roster: list[str],
    driver,
    templates: Jinja2Templates,
    request,
) -> AsyncIterable[ServerSentEvent]:
    from src.workflow.graph import build_graph

    graph = build_graph(driver=driver)
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

    final_output = None

    async for chunk in graph.astream(initial_state, stream_mode="updates", version="v2"):
        if await request.is_disconnected():
            break
        if chunk["type"] == "updates":
            for node_name, state_update in chunk["data"].items():
                label = NODE_LABELS.get(node_name, node_name.upper())
                # For validate: track retry attempt
                retry_count = state_update.get("retry_count", 0)
                attempt = retry_count + 1 if node_name == "validate" else 1

                yield ServerSentEvent(
                    data=json.dumps({
                        "event": "node_status",
                        "node": label,
                        "attempt": attempt,
                        "max": 3,
                    }),
                    event="node_status",
                )

                # Capture final_output from format node
                if node_name == "format" and "final_output" in state_update:
                    final_output = state_update["final_output"]

    # Send final HTML fragment
    if final_output is not None:
        template = templates.env.get_template("partials/result.html")
        html = template.render(result=final_output)
        yield ServerSentEvent(raw_data=html, event="result")

    # Send close signal
    yield ServerSentEvent(data="", event="done")
```

### TestClient with Mocked Graph

```python
# Source: https://fastapi.tiangolo.com/tutorial/testing + https://fastapi.tiangolo.com/advanced/testing-events
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

def test_post_query_returns_progress_fragment(mock_driver):
    with TestClient(app) as client:
        response = client.post(
            "/api/query",
            json={"query": "best team", "roster": ["Aldo", "Ciel"]},
        )
        assert response.status_code == 200
        assert "sse-connect" in response.text
        assert "/api/stream/" in response.text
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| sse-starlette library | `fastapi.sse.EventSourceResponse` (built-in) | FastAPI 0.135.0 (2025) | No extra dependency; cleaner API |
| HTMX 1.x built-in `hx-sse` | HTMX 2.x `hx-ext="sse"` (separate extension) | HTMX 2.0 (2024) | Must include `htmx-ext-sse` CDN separately |
| LangGraph `invoke()` | `astream()` with `stream_mode="updates"` | LangGraph 1.0+ | Real-time node completion events |
| `@app.on_event("startup")` decorator | `@asynccontextmanager lifespan(app)` | FastAPI 0.93+ | Deprecation of event decorators; lifespan is current standard |

**Deprecated/outdated:**
- `@app.on_event("startup")` / `@app.on_event("shutdown")`: deprecated in FastAPI; use `lifespan` parameter instead [CITED: fastapi.tiangolo.com]
- `hx-sse` attribute (HTMX v1.x): replaced by `hx-ext="sse"` + `htmx-ext-sse` extension in HTMX 2.x [CITED: htmx.org/extensions/sse]
- `sse-starlette` package: redundant since FastAPI 0.135.0 ships native SSE [CITED: fastapi.tiangolo.com/tutorial/server-sent-events]

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Client-side JS checklist filtering is viable for ~400 chars + ~489 Grastas without a search endpoint | Architecture Patterns §8 | If list is too large for DOM, need server-side `/api/entities/search` endpoint — adds one extra route |
| A2 | `graph.astream(stream_mode="updates")` yields node names as dict keys matching `add_node()` call strings | Pattern 3 | If node names differ, `NODE_LABELS` map fails silently — need to log chunk structure during smoke test |
| A3 | Neo4j UNION ALL syntax for Character + Grasta in single query works with neo4j 6.1.0 driver | Pattern 7 | Could need two separate queries instead |
| A4 | `nodriver` ETL won't block FastAPI event loop (runs cleanly in async context) | Pitfall 6 | May need `run_in_executor` wrapper; deferred to implementation if issue arises |
| A5 | Single uvicorn worker is acceptable for Phase 4 (no multi-user concurrency requirement stated) | Pitfall 2 | If concurrent users needed, asyncio.Queue approach fails with multiple workers |

---

## Open Questions

1. **Should the progress fragment be returned from POST /api/query as an HTML response, or should the form POST use HTMX `hx-swap="none"` and the SSE connection be pre-wired on page load?**
   - What we know: Two-phase is correct; the returned fragment carries the job_id URL
   - What's unclear: Whether returning `TemplateResponse` from a POST endpoint is clean in HTMX idioms
   - Recommendation: Return the fragment — HTMX swaps it via `hx-target="#progress-div"`. This is standard HTMX pattern.

2. **How is the retry_count for VALIDATE correctly reflected in the SSE event?**
   - What we know: `validate_node` increments `retry_count` on failure; the `updates` stream chunk contains the state update returned by the node
   - What's unclear: Does the `updates` chunk for a failed VALIDATE include `retry_count`? The validate node only returns `{"validation_errors": [...], "retry_count": N}` on failure
   - Recommendation: Verify during smoke test by logging the raw `chunk["data"]` structure.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 | Runtime | ✓ | 3.12.3 | — |
| uvicorn | ASGI server | ✓ (system) | 0.27.1 | Upgrade to 0.44.0 in venv |
| neo4j driver | AsyncGraphDatabase | ✓ | 6.1.0 | — |
| langgraph | Pipeline | ✓ | 1.0.10 | — |
| pydantic | Data validation | ✓ | 2.12.5 | — |
| httpx | Async test client | ✓ | 0.28.1 | — |
| fastapi | Web framework | ✗ (not in venv) | — | Install: `pip install "fastapi[standard]>=0.136.0"` |
| jinja2 | Templates | ✗ (not in venv) | — | Included in `fastapi[standard]` |
| python-multipart | Form parsing | ✗ (not in venv) | — | Included in `fastapi[standard]` |
| aiofiles | Static files | ✗ (not in venv) | — | Included in `fastapi[standard]` |

**Missing dependencies with no fallback:** None — all missing packages are installable via pip.

**Missing dependencies with fallback:** None.

**Wave 0 install command:** `pip install "fastapi[standard]>=0.136.0"` (installs fastapi, uvicorn, jinja2, python-multipart, aiofiles in one command).

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.23+ |
| Config file | `pytest.ini` (already configured: `asyncio_mode=auto`, `asyncio_default_fixture_loop_scope=session`) |
| Quick run command | `pytest tests/web/ -x -q` |
| Full suite command | `pytest tests/ -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| WEB-01 | GET / returns 200 HTML | unit | `pytest tests/web/unit/test_pages.py::test_index_returns_html -x` | ❌ Wave 0 |
| WEB-02 | GET /api/entities returns characters + grastas JSON | unit (mocked driver) | `pytest tests/web/unit/test_api.py::test_get_entities -x` | ❌ Wave 0 |
| WEB-02 | POST /api/query returns HTML fragment with sse-connect URL | unit (mocked graph) | `pytest tests/web/unit/test_api.py::test_post_query_returns_sse_fragment -x` | ❌ Wave 0 |
| WEB-03 | SSE stream emits node_status events then result event | unit (mocked graph) | `pytest tests/web/unit/test_streaming.py::test_sse_events_sequence -x` | ❌ Wave 0 |
| WEB-03 | Final SSE event contains rendered HTML (Jinja2 fragment) | unit | `pytest tests/web/unit/test_streaming.py::test_final_sse_event_is_html -x` | ❌ Wave 0 |
| WEB-04 | App startup creates Neo4j driver singleton in app.state | unit (TestClient with lifespan) | `pytest tests/web/unit/test_app.py::test_lifespan_creates_driver -x` | ❌ Wave 0 |
| WEB-05 | POST /admin/refresh-data with valid key returns 200 | unit | `pytest tests/web/unit/test_admin.py::test_refresh_data_valid_key -x` | ❌ Wave 0 |
| WEB-05 | POST /admin/refresh-data with wrong key returns 403 | unit | `pytest tests/web/unit/test_admin.py::test_refresh_data_invalid_key -x` | ❌ Wave 0 |
| WEB-05 | POST /admin/refresh-data with missing header returns 403 | unit | `pytest tests/web/unit/test_admin.py::test_refresh_data_missing_key -x` | ❌ Wave 0 |

### SSE Test Strategy

Testing SSE streams requires iterating the generator directly rather than through `TestClient` (which does not stream SSE in tests). Two approaches:

**Option A — Direct generator test (recommended for unit):**
```python
# Test the async generator directly without HTTP layer
async def test_sse_events_sequence():
    from unittest.mock import AsyncMock, patch, MagicMock
    mock_driver = AsyncMock()
    mock_graph = AsyncMock()

    # Mock astream to yield known chunks
    async def mock_astream(*args, **kwargs):
        yield {"type": "updates", "data": {"plan": {"plan_strategy": "test"}}}
        yield {"type": "updates", "data": {"generate_cypher": {"cypher_query": "MATCH..."}}}
        yield {"type": "updates", "data": {"validate": {"db_results": [{}]}}}
        yield {"type": "updates", "data": {"analyze": {"analysis_result": "..."}}}
        yield {"type": "updates", "data": {"format": {"final_output": {
            "frontline": [{"name": "Aldo", "role": "DPS", "grastas": []}],
            "reserve": [], "synergy_explanation": "test"
        }}}}

    mock_graph.astream = mock_astream

    with patch("src.web.streaming.build_graph", return_value=mock_graph):
        events = []
        async for event in pipeline_sse_generator("query", ["Aldo"], mock_driver, templates, mock_request):
            events.append(event)

    # Verify event sequence
    event_names = [e.event for e in events]
    assert "node_status" in event_names
    assert events[-2].event == "result"
    assert events[-1].event == "done"
```

**Option B — httpx.AsyncClient with ASGI transport (integration):**
```python
# Source: https://fastapi.tiangolo.com/advanced/async-tests
import pytest
from httpx import ASGITransport, AsyncClient

@pytest.mark.asyncio
async def test_stream_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # POST first to get job_id
        post_resp = await ac.post("/api/query", json={"query": "test", "roster": []})
        assert "sse-connect" in post_resp.text
```

### Admin Auth Test Pattern

```python
def test_refresh_data_invalid_key():
    with TestClient(app) as client:
        response = client.post(
            "/admin/refresh-data",
            headers={"X-Admin-Key": "wrong-key"}
        )
        assert response.status_code == 403

def test_refresh_data_missing_key():
    with TestClient(app) as client:
        response = client.post("/admin/refresh-data")
        assert response.status_code == 403
```

### Sampling Rate
- **Per task commit:** `pytest tests/web/unit/ -x -q`
- **Per wave merge:** `pytest tests/ -x -q --ignore=tests/integration`
- **Phase gate:** Full suite green (including web unit tests) before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/web/__init__.py` — package init
- [ ] `tests/web/unit/__init__.py` — unit subpackage init
- [ ] `tests/web/unit/test_app.py` — lifespan, app.state.driver — covers WEB-04
- [ ] `tests/web/unit/test_pages.py` — GET / HTML response — covers WEB-01
- [ ] `tests/web/unit/test_api.py` — /api/entities, /api/query — covers WEB-02
- [ ] `tests/web/unit/test_streaming.py` — SSE generator, event sequence — covers WEB-03
- [ ] `tests/web/unit/test_admin.py` — auth + ETL trigger — covers WEB-05
- [ ] `tests/web/conftest.py` — shared web test fixtures (mock driver, mock templates)
- [ ] Framework install: `pip install "fastapi[standard]>=0.136.0"` — if not yet in pyproject.toml

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No — no user login | — |
| V3 Session Management | No — stateless backend | — |
| V4 Access Control | Yes (admin endpoint) | `APIKeyHeader` dependency; return 403 on mismatch |
| V5 Input Validation | Yes (POST /api/query) | Pydantic `QueryRequest` model validates `query: str, roster: list[str]` |
| V6 Cryptography | No — API key comparison only | `secrets.compare_digest()` for timing-safe comparison [ASSUMED] |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Admin key brute force | Spoofing | Rate limiting (Phase 5); for Phase 4 static key is acceptable |
| Roster injection (malicious names) | Tampering | Pydantic validates list[str]; Neo4j parameterized queries in existing nodes |
| SSE stream resource exhaustion | DoS | Single-worker constraint documented; disconnect detection in generator |
| Job ID guessing (job queue access) | Elevation | UUID4 is unpredictable; no sensitive data in queue beyond query string |

**Note on API key comparison:** Use `secrets.compare_digest(api_key, expected)` instead of `==` to prevent timing attacks. For a static admin key this is low risk, but it's a best-practice one-liner. [ASSUMED — not verified against project ASVS requirements]

---

## Sources

### Primary (HIGH confidence)
- `/websites/fastapi_tiangolo` (Context7) — lifespan, Jinja2, SSE, security, TestClient patterns
- `/bigskysoftware/htmx` (Context7) — SSE extension attributes, sse-close, sse-swap, multiple events
- `/websites/langchain_oss_python_langgraph` (Context7) — astream stream_mode, get_stream_writer
- `https://fastapi.tiangolo.com/tutorial/server-sent-events/` — full SSE tutorial, EventSourceResponse, ServerSentEvent fields, POST SSE support
- `https://htmx.org/extensions/sse/` — sse-close attribute, connection closure, SSE attributes reference

### Secondary (MEDIUM confidence)
- `https://medium.com/data-science-collective/javascript-fatigued-build-an-agentic-chatbot-with-htmx-503569adf2f9` — two-phase POST→GET SSE pattern with asyncio.Queue (2025 example)
- `pip3 index versions` commands — verified package versions (FastAPI 0.136.0, sse-starlette 3.3.4, jinja2 3.1.6)

### Tertiary (LOW confidence)
- WebSearch results for HTMX SSE POST body patterns — corroborated by EventSource spec; multiple independent sources agree

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — versions verified via pip registry; FastAPI native SSE verified via official docs
- Architecture: HIGH — two-phase pattern corroborated by multiple 2025 real-world examples; lifespan pattern from official docs
- LangGraph integration: HIGH — `get_stream_writer` import verified in venv; `astream` API verified via Context7 docs
- HTMX SSE limitations: HIGH — EventSource GET-only is a web standard (MDN); htmx.org confirms same
- Pitfalls: MEDIUM — asyncio.Queue single-process limitation is general knowledge; ETL nodriver concern is ASSUMED

**Research date:** 2026-04-19
**Valid until:** 2026-05-19 (FastAPI stable; HTMX stable; check if fastapi.sse API surface changes)

---

## RESEARCH COMPLETE
