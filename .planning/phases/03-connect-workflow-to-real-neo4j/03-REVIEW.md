---
phase: 03-connect-workflow-to-real-neo4j
reviewed: 2026-04-18T00:00:00Z
depth: standard
files_reviewed: 2
files_reviewed_list:
  - tests/conftest.py
  - tests/integration/test_known_nodes.py
findings:
  critical: 0
  warning: 2
  info: 3
  total: 5
status: issues_found
---

# Phase 03: Code Review Report

**Reviewed:** 2026-04-18
**Depth:** standard
**Files Reviewed:** 2
**Status:** issues_found

## Summary

Reviewed two test infrastructure files: `tests/conftest.py` (shared fixtures including the new
`db_has_characters()` helper and revised `loaded_db` fixture) and
`tests/integration/test_known_nodes.py` (new `populated_db` session fixture and six integration tests).

No critical security or data-loss issues were found. Two warnings were identified: a logic gap
in the `loaded_db` fixture's exception handling that contradicts its own docstring guarantee,
and a subtle pytest-asyncio interaction in `populated_db` where `pytest.skip()` is raised before
`yield` in a session-scoped async fixture. Three informational items cover a defensive coding gap
in env-var parsing, a redundant Neo4j round-trip, and an unconventional import pattern.

---

## Warnings

### WR-01: `db_has_characters()` call in `loaded_db` is outside the `try/except` block

**File:** `tests/conftest.py:60`

**Issue:** The docstring for `loaded_db` states "ETL failures are caught and logged — the fixture
yields regardless." However, the call to `db_has_characters(async_driver)` on line 60 sits
**before** the `try` block on line 61. If Neo4j is unreachable (e.g., Docker not running), this
call raises `neo4j.exceptions.ServiceUnavailable`, which propagates out of the fixture unhandled.
The fixture errors — it does not yield — and all dependent tests are reported as `ERROR` rather
than being skipped by `populated_db`'s skip guard. The "yields regardless" contract is broken
precisely in the scenario it was designed to handle.

**Current code:**
```python
async def loaded_db(async_driver):
    if not await db_has_characters(async_driver):   # line 60 — outside try; raises if DB down
        try:
            from src.etl.run_etl import main as run_etl_main
            await run_etl_main(driver=async_driver)
        except Exception as e:
            logging.getLogger(__name__).warning(
                f"ETL load skipped — wiki unavailable: {e}"
            )
    yield
```

**Fix:** Wrap the entire pre-yield block in the `try/except` so all failures — including the
initial connectivity check — are caught and logged:

```python
async def loaded_db(async_driver):
    try:
        if not await db_has_characters(async_driver):
            from src.etl.run_etl import main as run_etl_main
            await run_etl_main(driver=async_driver)
    except Exception as e:
        logging.getLogger(__name__).warning(
            "DB check or ETL load failed — DB may be unreachable: %s", e
        )
    yield
```

This ensures `loaded_db` always yields and `populated_db`'s `db_has_characters` check (which
also runs outside a try block) then returns `False`, triggering `pytest.skip()` as intended.

---

### WR-02: `pytest.skip()` before `yield` in a session-scoped async fixture may produce `ERROR` instead of `SKIP` for some tests

**File:** `tests/integration/test_known_nodes.py:23-25`

**Issue:** `populated_db` raises `pytest.skip()` before reaching `yield`. For a session-scoped
fixture, pytest caches the fixture result after first setup. In pytest 9.0.2 with
`pytest-asyncio` 1.3.0 and `asyncio_mode = auto`, when `pytest.skip()` is raised inside an
`async` session-scoped fixture before `yield`:

- The first test that triggers the fixture gets a proper `SKIP` outcome.
- Subsequent tests in the same session that depend on the same fixture may see `ERROR`
  (fixture setup failed, no cached value), because the fixture never reached `yield` and the
  session-scoped instance is stored as failed rather than as "skip this consumer."

This is a known edge case in pytest-asyncio when `Skipped` is raised before the first `yield`
of an async generator fixture. Synchronous session fixtures propagate `Skipped` more reliably
because pytest directly catches it at the collection level.

**Current code:**
```python
@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def populated_db(async_driver, loaded_db):
    if not await db_has_characters(async_driver):
        pytest.skip("Neo4j DB not populated — wiki may be unreachable")
    yield
```

**Fix option A — use `pytest.importorskip` pattern with a module-level skip:**
Add a session-autouse fixture in the module's conftest or use `pytest.mark.skipif` at module
level based on a synchronous check. This avoids raising skip inside an async session fixture.

**Fix option B — store a flag and skip per test:**
Change `populated_db` to a non-raising fixture that stores whether the DB is populated, then
use a session-autouse fixture or a `pytestmark` to skip tests when the flag is False:

```python
@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def populated_db(async_driver, loaded_db):
    """Yields True if DB is populated, False otherwise."""
    populated = await db_has_characters(async_driver)
    yield populated


# In each test, receive populated_db and skip explicitly:
@pytest.mark.integration
async def test_character_properties(async_driver, populated_db):
    if not populated_db:
        pytest.skip("Neo4j DB not populated")
    ...
```

**Fix option C — autouse skip fixture (least invasive):**
```python
@pytest_asyncio.fixture(scope="session", loop_scope="session", autouse=True)
async def require_populated_db(async_driver, loaded_db):
    if not await db_has_characters(async_driver):
        pytest.skip("Neo4j DB not populated — wiki may be unreachable")
    yield
```
Autouse session fixtures have subtly different propagation semantics that can work more
reliably. However, Fix option B is the most explicit and test-framework-agnostic.

---

## Info

### IN-01: `NEO4J_AUTH` env var parsing is silently fragile when the value has no slash

**File:** `tests/conftest.py:25`

**Issue:** `NEO4J_AUTH` is parsed as `tuple(os.getenv(...).split("/", 1))`. If the environment
variable is set to a value without a `/` (e.g., `NEO4J_AUTH=neo4j`), `split` returns a 1-element
list, producing a 1-tuple `('neo4j',)`. Passing a 1-tuple as `auth` to
`AsyncGraphDatabase.driver()` will raise a cryptic internal error from the Neo4j driver with no
diagnostic context about the mis-configured environment variable.

**Fix:** Add a validation guard:
```python
_auth_raw = os.getenv("NEO4J_AUTH", "neo4j/anothereden")
_auth_parts = _auth_raw.split("/", 1)
if len(_auth_parts) != 2:
    raise ValueError(
        f"NEO4J_AUTH must be in 'user/password' format, got: {_auth_raw!r}"
    )
NEO4J_AUTH = tuple(_auth_parts)
```

---

### IN-02: Redundant `db_has_characters()` call in `populated_db` — extra Neo4j round-trip

**File:** `tests/integration/test_known_nodes.py:23`

**Issue:** `populated_db` calls `db_has_characters(async_driver)` a second time immediately
after `loaded_db` (which already called the same query). If `loaded_db` succeeded (DB was
already populated or ETL ran successfully), the second call always returns `True` and the
`pytest.skip()` branch is never reached. The double round-trip is harmless but unnecessary and
slightly complicates reasoning about the fixture flow.

This redundancy exists as a safety net for the case where `loaded_db`'s ETL silently failed
(the `except` swallowed the error). If WR-01 is fixed — and the `loaded_db` docstring contract
("yields regardless") is honoured — then `populated_db` still needs to re-check because
`loaded_db` yields without providing any signal about whether load succeeded. The design is
internally consistent but the intent is not documented.

**Fix:** Add a comment explaining why the re-check is intentional:
```python
@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def populated_db(async_driver, loaded_db):
    """Ensure DB is actually populated; skip all tests in module if not.

    Re-checks after loaded_db because loaded_db swallows ETL errors and yields
    regardless — this fixture is the authoritative gate for test execution.
    """
    if not await db_has_characters(async_driver):
        pytest.skip("Neo4j DB not populated — wiki may be unreachable")
    yield
```

---

### IN-03: Importing `db_has_characters` directly from `tests.conftest` is unconventional

**File:** `tests/integration/test_known_nodes.py:17`

**Issue:** `from tests.conftest import db_has_characters` imports a module-level helper from
`conftest.py`. pytest auto-discovers `conftest.py` as a plugin, not as a regular module.
Direct imports from conftest files are generally discouraged because:
1. They couple the test file to conftest's internal structure.
2. Moving or splitting the conftest breaks the import.
3. If `tests/` is not in `sys.path` (e.g., when running pytest from a subdirectory), the import
   can fail.

**Fix:** Move `db_has_characters` to a shared test utility module:
```
tests/
  utils.py       # db_has_characters() lives here
  conftest.py    # imports from tests.utils if needed
  integration/
    test_known_nodes.py  # imports from tests.utils
```
This is a low-priority refactor; the current code works in the standard `pytest` invocation
from the project root with `asyncio_mode = auto`.

---

_Reviewed: 2026-04-18_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
