# Phase 4: FastAPI + HTMX Web Layer - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-19
**Phase:** 04-fastapi-htmx-web-layer
**Areas discussed:** Roster input UX, SSE event design, Result display layout, Admin endpoint auth

---

## Roster input UX

| Option | Description | Selected |
|--------|-------------|----------|
| Browser localStorage | Roster persists in browser — no login, zero backend complexity | ✓ |
| Backend session/DB | Server-side roster, requires user accounts | |
| Per-request only | User re-enters roster each session | |

**User's choice:** Browser localStorage — stateless backend

---

| Option | Description | Selected |
|--------|-------------|----------|
| Tag chip input | Type name, press Enter to add chip | |
| Textarea (comma-separated) | Free-text textarea | |
| Searchable checklist | Browse full character/Grasta list and check ownership | ✓ |

**User's choice:** Searchable checklist

---

| Option | Description | Selected |
|--------|-------------|----------|
| GET /api/characters + /api/grastas | Two separate endpoints | |
| Inline in HTML template | Jinja2 renders list into page | |
| GET /api/entities (combined) | Single endpoint, both entities | ✓ |

**User's choice:** GET /api/entities combined endpoint

---

| Option | Description | Selected |
|--------|-------------|----------|
| Separate tabs (chars + grastas) | Two tabs in roster panel | ✓ |
| Combined single list | All items in one list | |
| Characters only for MVP | Defer Grasta ownership | |

**User's choice:** Separate tabs

**Notes:** User provided a full architecture spec during this area:
- Backend stateless; frontend passes roster in JSON payload
- GET /api/entities populates checklist on page load
- POST /api/query accepts `{"query": string, "roster": list[str]}`
- SSE streaming for pipeline progress
- HTMX for dynamic updates without page refresh
- No AWS/Dockerfiles in Phase 4 (Phase 5 only)

---

## SSE Event Design

| Option | Description | Selected |
|--------|-------------|----------|
| JSON events + final HTML fragment | Progress as JSON, final event as rendered HTML | ✓ |
| All plain-text status lines | Every event is plain text | |
| Structured JSON throughout | All events JSON, frontend renders result | |

**User's choice:** JSON events + final HTML fragment (Recommended)

---

| Option | Description | Selected |
|--------|-------------|----------|
| "Validating... attempt 2/3" | Inline text in progress area | ✓ |
| Animated progress bar + text | Progress bar filling per attempt | |
| Warning banner on retry | Yellow banner on retry | |

**User's choice:** "Validating... attempt 2/3" inline text (Recommended)

---

## Result Display Layout

| Option | Description | Selected |
|--------|-------------|----------|
| Character cards grid | 4-card frontline row + 2-card reserve row | ✓ |
| Two-section list | Numbered list format | |

**User's choice:** Character cards grid

---

| Option | Description | Selected |
|--------|-------------|----------|
| Name only | Grasta names only on card | ✓ |
| Name + effect description | Name + effect text (needs FORMAT extension) | |
| None for MVP | Defer Grasta display to Phase 5 | |

**User's choice:** Name only (Recommended)

---

## Admin Endpoint Auth

| Option | Description | Selected |
|--------|-------------|----------|
| Static API key in header | X-Admin-Key header vs ADMIN_KEY env var | ✓ |
| HTTP Basic Auth | Standard browser Basic Auth | |
| Local-only (127.0.0.1 check) | 403 if not localhost | |

**User's choice:** Static API key in header (Recommended)

---

| Option | Description | Selected |
|--------|-------------|----------|
| JSON {status, message} | Structured JSON response | ✓ |
| Plain text response | 'OK' or error string | |
| SSE stream of ETL progress | Stream ETL steps | |

**User's choice:** JSON {status, message} (Recommended)

---

## Claude's Discretion

- Tailwind/CSS styling for cards and progress area
- Exact HTML structure of checklist component (tabs implementation)
- Error display when retry cap exhausted
- Empty result message styling

## Deferred Ideas

- Grasta effect descriptions in result cards — Phase 5 polish
- SSE streaming of ETL progress — deferred, synchronous JSON sufficient
- Multi-user / server-side roster persistence — future milestone
- AWS deployment, Dockerfiles — Phase 5
