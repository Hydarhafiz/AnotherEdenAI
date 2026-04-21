---
phase: 04-fastapi-htmx-web-layer
reviewed: 2026-04-21T00:00:00Z
depth: standard
files_reviewed: 15
files_reviewed_list:
  - src/web/app.py
  - src/web/dependencies.py
  - src/web/routes/api.py
  - src/web/routes/admin.py
  - src/web/routes/pages.py
  - src/web/streaming.py
  - src/web/static/app.js
  - src/web/templates/index.html
  - src/web/templates/partials/progress.html
  - src/web/templates/partials/result.html
  - src/web/templates/partials/error.html
  - src/web/templates/partials/empty.html
  - tests/web/unit/test_streaming.py
  - tests/web/unit/test_api.py
  - tests/web/unit/test_admin.py
findings:
  critical: 2
  warning: 4
  info: 3
  total: 9
status: issues_found
---

# Phase 04: Code Review Report

**Reviewed:** 2026-04-21
**Depth:** standard
**Files Reviewed:** 15
**Status:** issues_found

## Summary

The FastAPI/HTMX web layer is well-structured overall. The two-phase POST→SSE-GET pattern is correctly implemented, the admin key comparison uses `secrets.compare_digest` (timing-safe), and the Jinja2 templates auto-escape by default, which neutralises most server-side XSS paths. The SSE generator has solid disconnect-detection and always emits a `done` event from `finally`.

Two security issues require immediate attention: stored database values are injected unsanitised into `innerHTML` in `app.js`, and the `NEO4J_AUTH` environment variable parsing will raise an unhandled `ValueError` at startup if the variable does not contain a `/` separator. Four additional logic issues could cause bugs at runtime or mislead callers. Three informational items round out the review.

---

## Critical Issues

### CR-01: Stored XSS via unsanitised `innerHTML` injection in `app.js`

**File:** `src/web/static/app.js:46-54`

**Issue:** `buildChecklistHTML()` constructs HTML by direct template-literal string interpolation of `name` values returned from `GET /api/entities`. The `data-name` attribute and checkbox `value` attribute are not HTML-encoded before insertion:

```js
ul.innerHTML = names.map(name => `
  <div class="roster-item" data-name="${name}">
    <label>
      <input type="checkbox" class="${checkboxClass}" value="${name}"
             ${saved.includes(name) ? "checked" : ""}>
      ${name}
    </label>
  </div>
`).join("");
```

A character name containing `"><img src=x onerror=alert(1)>` (or a double-quote that breaks the attribute) stored in Neo4j will execute arbitrary JavaScript in any browser that loads the page. The `run_etl` import path in `admin.py` shows ETL is user-triggerable, widening the attack surface.

**Fix:** Replace `innerHTML` with DOM construction, or HTML-encode every interpolated value before insertion:

```js
function escapeHtml(str) {
  const el = document.createElement("span");
  el.textContent = str;
  return el.innerHTML;
}

// Then in buildChecklistHTML:
ul.innerHTML = names.map(name => `
  <div class="roster-item" data-name="${escapeHtml(name)}">
    <label>
      <input type="checkbox" class="${checkboxClass}" value="${escapeHtml(name)}"
             ${saved.includes(name) ? "checked" : ""}>
      ${escapeHtml(name)}
    </label>
  </div>
`).join("");
```

Alternatively, build each element with `document.createElement` + `textContent`/`setAttribute`, which never interprets markup.

---

### CR-02: `NEO4J_AUTH` parsing crashes at startup when env var contains no `/`

**File:** `src/web/app.py:22`

**Issue:** The auth tuple is parsed as:

```python
NEO4J_AUTH = tuple(os.getenv("NEO4J_AUTH", "bolt://localhost:7687").split("/", 1))
```

Wait — re-reading line 22: the default string is `"neo4j/anothereden"` which contains a `/`. However, if an operator sets `NEO4J_AUTH=neo4j` (no slash), `split("/", 1)` returns a one-element list and `tuple(...)` becomes a 1-tuple `("neo4j",)`. The Neo4j driver's `auth=` parameter expects a 2-tuple `(user, password)` and will raise a `TypeError` or `AuthError` immediately at driver construction time inside the lifespan — which propagates as an unhandled startup exception, crashing uvicorn with no informative message.

**Fix:** Validate the parsed tuple length at startup and raise a clear `ValueError`:

```python
_auth_raw = os.getenv("NEO4J_AUTH", "neo4j/anothereden").split("/", 1)
if len(_auth_raw) != 2:
    raise ValueError(
        "NEO4J_AUTH must be in 'user/password' format, got: "
        + os.getenv("NEO4J_AUTH", "")
    )
NEO4J_AUTH = tuple(_auth_raw)
```

---

## Warnings

### WR-01: ETL exception message leaked directly to API caller

**File:** `src/web/routes/admin.py:28-29`

**Issue:** The raw exception string is returned to the HTTP caller without filtering:

```python
except Exception as exc:
    return {"status": "error", "message": str(exc)}
```

`str(exc)` can contain internal filesystem paths, database connection strings, or third-party library internals (e.g., `ConnectionRefusedError: [Errno 111] Connection refused to bolt://internal-host:7687`). This leaks infrastructure topology to anyone who holds the admin key.

**Fix:** Log the full exception internally and return a generic user-facing message:

```python
except Exception as exc:
    logger.exception("ETL failed: %s", exc)
    return {"status": "error", "message": "ETL pipeline failed — see server logs for details"}
```

---

### WR-02: `QueryRequest` fields have no length or content constraints

**File:** `src/web/routes/api.py:17-19`

**Issue:** `QueryRequest.query` and `QueryRequest.roster` have no Pydantic field constraints. A caller can send a 10 MB query string or a roster list with tens of thousands of entries. Both are passed directly into `app.state.jobs` (unbounded in-memory dict) and eventually fed to the LangGraph pipeline. This can exhaust server memory and tie up the single-worker SSE connection indefinitely.

**Fix:** Add `max_length` and `max_items` constraints:

```python
from pydantic import BaseModel, Field

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    roster: list[str] = Field(..., max_length=500)
```

---

### WR-03: `app.state.jobs` grows without bound — no TTL or size cap

**File:** `src/web/routes/api.py:51-54`

**Issue:** Every `POST /api/query` stores an entry in `app.state.jobs`. The job is removed only when `GET /api/stream/{job_id}` is called. If a client submits many queries but never opens the SSE connection (e.g., tab closed, network error between the POST response and the HTMX SSE connect), the `jobs` dict grows indefinitely for the lifetime of the process. On a long-lived server this is a memory leak and could also be exploited to fill RAM by repeatedly POST-ing without streaming.

**Fix:** Evict stale jobs that have not been consumed within a TTL (e.g., 60 seconds). A minimal approach stores a timestamp alongside the payload and prunes in a background task or lazily at POST time:

```python
import time
request.app.state.jobs[job_id] = {
    "query": body.query,
    "roster": body.roster,
    "created_at": time.monotonic(),
}
```

Then add a lifespan background task that periodically purges entries older than 60 seconds.

---

### WR-04: Test `test_post_query_stores_job_in_state` has state leak between runs

**File:** `tests/web/unit/test_api.py:50-59`

**Issue:** The test asserts `len(web_app.state.jobs) >= 1` but never consumes or clears the stored job. If this test runs before other tests that inspect `app.state.jobs`, those tests may see stale entries. The assertion `>= 1` also means the test passes vacuously if prior runs left jobs behind — masking a regression where the new job is not stored at all.

**Fix:** Assert equality on the count relative to the baseline, or clear `web_app.state.jobs` in the test:

```python
def test_post_query_stores_job_in_state(self, test_client):
    from src.web.app import app as web_app
    web_app.state.jobs.clear()  # reset before test
    response = test_client.post(
        "/api/query",
        json={"query": "best team", "roster": ["Aldo"]},
    )
    assert response.status_code == 200
    assert len(web_app.state.jobs) == 1
```

---

## Info

### IN-01: Hardcoded default credentials in `app.py`

**File:** `src/web/app.py:22`

**Issue:** The fallback value for `NEO4J_AUTH` is `"neo4j/anothereden"`. If a deployment omits the `.env` file, the app will silently connect using this well-known default password. This is fine for local dev but a risk if a production container is misconfigured.

**Fix:** Either remove the default entirely (requiring the env var to be set) or add a startup warning when the default is used:

```python
NEO4J_AUTH_RAW = os.getenv("NEO4J_AUTH")
if NEO4J_AUTH_RAW is None:
    import warnings
    warnings.warn("NEO4J_AUTH not set — using insecure default credentials", stacklevel=1)
    NEO4J_AUTH_RAW = "neo4j/anothereden"
```

---

### IN-02: `EventSourceResponse` import unused in `api.py`

**File:** `src/web/routes/api.py:5`

**Issue:** `EventSourceResponse` is imported but never used as a constructor — it appears only in `response_class=EventSourceResponse` annotation on the `stream_job` route decorator, which is valid usage. However, the comment on lines 79-82 warns against wrapping in `EventSourceResponse(generator)`, suggesting there was previously a direct usage that was removed. The import is legitimate as a type marker, but the inline comment is now slightly misleading about why the pattern was changed.

**Fix:** No code change required; consider clarifying the comment to indicate `response_class=EventSourceResponse` is the correct usage (sets `Content-Type: text/event-stream`) without constructing an instance.

---

### IN-03: `progress.html` inline `<script>` re-added on every form submission

**File:** `src/web/templates/partials/progress.html:25-75`

**Issue:** The `<script>` block inside `progress.html` is injected fresh into the DOM on every `POST /api/query` (via `container.innerHTML = await resp.text()` in `app.js:107`). The `document.addEventListener("htmx:sseMessage", ...)` listener is added each time the fragment is swapped in. Rapid successive submissions (or a user clicking "Find Best Team" multiple times) will attach duplicate listeners, causing each SSE event to be processed `N` times — showing duplicate progress text updates or race conditions on `statusDiv.textContent`.

**Fix:** Move the SSE message listener into `app.js` (registered once on `DOMContentLoaded`), guarded by an event type check. In `progress.html`, keep only the markup. Alternatively, use `{ once: true }` or explicitly remove the previous listener before attaching:

```js
// In app.js, register once:
document.addEventListener("htmx:sseMessage", handleSseMessage);
```

---

_Reviewed: 2026-04-21_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
