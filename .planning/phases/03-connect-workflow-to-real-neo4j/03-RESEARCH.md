# Phase 3: Connect Workflow to Real Neo4j - Research

**Researched:** 2026-03-16
**Domain:** Neo4j async driver integration, Cypher roster filtering, character name normalization, integration testing
**Confidence:** HIGH

## Summary

Phase 3 replaces the Phase 2 MagicMock driver stub with a real `AsyncGraphDatabase` driver connected to the loaded Phase 1 graph. The workflow already accepts a `driver` parameter via closure in `build_graph(driver)` — swapping to real Neo4j is surgical: pass a live `AsyncGraphDatabase.driver(...)` instance instead of a `MagicMock`. The primary new logic is (1) character name normalization before Cypher parameters are constructed, and (2) roster filtering that explicitly includes F2P characters alongside owned characters.

The AF (Another Force) zone mechanics research flag resolves to **no schema extension needed for Phase 3**. AF synergy operates through character traits, zone-setting Grastas (Support category), and the existing `REQUIRES_TRAIT`/`HAS_TRAIT` graph paths. The PLAN agent's natural language → sub-goal decomposition will naturally surface AF-relevant Grastas via the existing schema. A new relationship type (`ENABLES_ZONE` or similar) would only be warranted in a v2 pass that explicitly models zone types as nodes — defer to OPT-03.

The existing `conftest.py` async fixture pattern (`pytest_asyncio.fixture(scope="session", loop_scope="session")`) is already established and battle-tested through Phase 1 integration tests. Phase 3 integration tests extend this pattern with query-level tests against the loaded graph.

**Primary recommendation:** Wire real `AsyncGraphDatabase` driver through the existing `build_graph()` closure, add a `normalize_character_name()` helper that queries the graph with `toLower()` fuzzy matching, add `F2P_CHARACTERS` as a constant list, and confirm all existing Cypher patterns use `$roster` parameter binding (they already do per `cypher.py` few-shot examples).

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| QUERY-01 | User can input owned character roster (manually, as text list or CSV) | WorkflowState.roster already accepts `list[str]`; input parsing (CSV split) needed in the entry point before graph.invoke() |
| QUERY-02 | All recommendations are constrained to owned characters plus explicitly F2P units | F2P_CHARACTERS constant list + PLAN agent roster augmentation + Cypher WHERE name IN ($roster + $f2p) pattern |
| QUERY-03 | User can submit natural language team-building queries | Already wired: WorkflowState.user_query accepts free text; PLAN node decomposes it; GENERATE_CYPHER translates |
| QUERY-04 | Character name input is normalized to canonical graph names before roster filtering | normalize_character_name() helper; Cypher MATCH toLower(c.name) CONTAINS toLower($input) lookup; called in plan_node before strategy |
</phase_requirements>

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `neo4j` (AsyncGraphDatabase) | >=5.0 (already in pyproject.toml) | Async driver for live Neo4j queries | Official Neo4j Python driver; already installed; async API matches existing `AsyncGraphDatabase` use in `tests/conftest.py` |
| `pytest-asyncio` | >=0.23 (already in pyproject.toml) | Async test fixtures | Already in use; `asyncio_mode=auto` + `asyncio_default_test_loop_scope=session` configured in `pytest.ini` |
| `python-dotenv` | >=1.0 (already in pyproject.toml) | Load `NEO4J_URI` / `NEO4J_AUTH` from `.env` | Already loaded in `tests/conftest.py` via `load_dotenv()` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `langchain-neo4j` | >=0.8 (already in pyproject.toml) | `Neo4jGraph.get_schema()` for schema injection | Already used via `SCHEMA_CONTEXT` constant in `cypher.py`; NOT used for live queries at runtime — driver handles queries directly |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `AsyncGraphDatabase.driver()` for live queries | `Neo4jGraph` from `langchain_neo4j` for queries | `Neo4jGraph` is synchronous and designed for schema inspection; `AsyncGraphDatabase` is the correct async runtime driver |
| Constant `F2P_CHARACTERS` list | `is_f2p` property on Character nodes | Adding graph property requires ETL re-run; constant list is simpler for Phase 3 and can be refactored in v2 |
| Graph APOC fuzzy match for normalization | Python-side `difflib.get_close_matches` | Graph-side is accurate but APOC adds dependency; Python-side is simpler and sufficient for first-pass normalization |

**Installation:** No new packages required. All dependencies are already in `pyproject.toml`.

---

## Architecture Patterns

### Recommended Project Structure

No new top-level directories needed. Changes are additive within existing structure:

```
src/
├── workflow/
│   ├── nodes/
│   │   ├── plan.py          # Add normalize_character_name() call + roster augmentation
│   │   └── cypher.py        # No change needed (already uses $roster parameter)
│   ├── normalize.py         # NEW: normalize_character_name(driver, input_name) -> str
│   ├── f2p.py               # NEW: F2P_CHARACTERS constant + augment_roster() helper
│   └── graph.py             # No topology change; driver injection already works
tests/
├── integration/
│   └── test_query_pipeline.py  # NEW: end-to-end integration tests
└── conftest.py              # No change needed; async_driver + loaded_db fixtures reused
```

### Pattern 1: AsyncGraphDatabase Driver Injection

**What:** Pass a real driver to `build_graph(driver=...)` instead of the `None`/mock used in Phase 2.
**When to use:** Production entry point (`run.py` or `__main__.py`) and integration tests.
**Example:**
```python
# Source: neo4j Python Driver async API docs
# https://neo4j.com/docs/api/python-driver/current/async_api.html
import os
from neo4j import AsyncGraphDatabase
from dotenv import load_dotenv

load_dotenv()
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_AUTH = tuple(os.getenv("NEO4J_AUTH", "neo4j/anothereden").split("/", 1))

driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)
graph = build_graph(driver=driver)
result = await graph.ainvoke(initial_state)
await driver.close()
```

**Critical detail:** `graph.invoke()` (sync) works when the validate_node driver call is sync. The existing `validate.py` calls `driver.execute_query()` synchronously. For a real async driver the call must become `await driver.execute_query()`. This means `validate_node` must become `async def validate_node(...)` and the graph must use `await graph.ainvoke(...)`. See pitfall below.

### Pattern 2: Character Name Normalization via Graph Lookup

**What:** Before passing roster to the workflow, normalize user-supplied names (e.g., "aldo", "ALDO", "Aldo AS") to exact canonical graph names via case-insensitive Cypher lookup.
**When to use:** In `plan_node` or as a preprocessing step before `graph.ainvoke()`.
**Example:**
```python
# Source: Neo4j Cypher Manual — toLower() function
async def normalize_character_name(driver, input_name: str) -> str | None:
    """Return canonical Character.name for input_name, or None if not found."""
    records, _, _ = await driver.execute_query(
        """
        MATCH (c:Character)
        WHERE toLower(c.name) = toLower($input)
           OR toLower(c.name) CONTAINS toLower($input)
        RETURN c.name AS canonical
        ORDER BY size(c.name) ASC
        LIMIT 1
        """,
        input=input_name,
        database_="neo4j",
    )
    return records[0]["canonical"] if records else None


async def normalize_roster(driver, roster: list[str]) -> list[str]:
    """Normalize all roster entries; skip entries with no match."""
    normalized = []
    for name in roster:
        canonical = await normalize_character_name(driver, name)
        if canonical:
            normalized.append(canonical)
    return normalized
```

### Pattern 3: F2P Roster Augmentation

**What:** Merge a constant F2P_CHARACTERS list with the user's owned roster before Cypher execution.
**When to use:** In the Cypher query or in `plan_node` before constructing the strategy.
**Example:**
```python
# src/workflow/f2p.py
# F2P characters are always included in roster regardless of user input.
# Source: anothereden.wiki/w/Free_Characters
F2P_CHARACTERS = [
    "Aldo",          # Main story protagonist, always free
    "Feinne",        # Main story companion
    "Cyrus",         # Main story
    "Deirdre",       # Episode free character
    "Azami",         # Chance encounter free character
    "Gariyu",        # Prismatic Weapons side story free character
    "Cerrine",       # Chance encounter free character
    "Levia",         # Ocean Palace episode free character
    # NOTE: This list is not exhaustive. Augment from wiki/Free_Characters as needed.
    # Do NOT include collaboration characters (Joker, Morgana) — they have limited
    # availability windows and may not be in all player accounts.
]

def augment_with_f2p(roster: list[str]) -> list[str]:
    """Return roster with F2P characters appended (deduped)."""
    combined = list(roster)
    for f2p in F2P_CHARACTERS:
        if f2p not in combined:
            combined.append(f2p)
    return combined
```

### Pattern 4: Async validate_node for Live Driver

**What:** The validate_node currently calls `driver.execute_query()` synchronously. A real `AsyncGraphDatabase` driver requires `await`.
**When to use:** When wiring real driver to the graph.
**Example:**
```python
# Source: Existing validate.py pattern + neo4j async API
async def validate_node(state: WorkflowState, driver) -> dict:
    cypher = state.get("cypher_query", "MATCH (n) RETURN n")
    retry_count = state.get("retry_count", 0)
    try:
        records, _, _ = await driver.execute_query(
            cypher,
            roster=state.get("roster", []),
            database_="neo4j",
        )
    except Exception as exc:
        ...
```

The `build_graph()` closure already supports this: `lambda s: validate_node(s, driver)` becomes `lambda s: asyncio.coroutine or async lambda`. In LangGraph, async nodes are supported natively — just make the node an `async def` and LangGraph handles it during `ainvoke`.

### Anti-Patterns to Avoid

- **Sync driver with async runtime:** Never use `GraphDatabase.driver()` (sync) inside an async LangGraph pipeline. Use `AsyncGraphDatabase.driver()`.
- **String-interpolating roster into Cypher:** Never `f"WHERE c.name IN {roster}"`. Always use `$roster` parameter binding. This is already correct in the existing few-shot examples.
- **Hardcoding F2P list in Cypher strings:** Do not embed F2P names into the schema context or Cypher examples. Use Python-side augmentation before passing `roster` to the graph — this keeps the Cypher clean and the constant maintainable.
- **Blocking event loop with sync driver.session():** The existing `tests/conftest.py` uses `async with driver.session()`. The production wiring must do the same.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Async Neo4j session management | Custom connection pool | `AsyncGraphDatabase.driver()` built-in pool | Driver manages pool automatically; closing/reopening connections is error-prone |
| Case-insensitive name matching | Levenshtein distance library | Cypher `toLower()` lookup + Python `difflib` fallback | Graph already stores canonical names; a simple toLower match covers 90% of cases cheaply |
| Cypher parameter escaping | Manual string sanitization | `driver.execute_query(cypher, param=value)` named parameters | Driver handles all escaping; injection is impossible with named params |
| pytest async session sharing | Custom event loop management | `pytest_asyncio.fixture(loop_scope="session")` | Already established pattern in `tests/conftest.py`; do not duplicate |

**Key insight:** The hardest part of Phase 3 is the sync/async boundary in `validate_node`. Everything else is wiring existing pieces together.

---

## Common Pitfalls

### Pitfall 1: Sync validate_node with Async Driver

**What goes wrong:** Calling `await driver.execute_query()` inside a sync `def validate_node()` raises `RuntimeError: coroutine was never awaited`. Calling `driver.execute_query()` on an `AsyncDriver` without `await` returns a coroutine object instead of records.

**Why it happens:** Phase 2 used a `MagicMock` driver which is synchronous. `MagicMock().execute_query()` returns a configured tuple immediately. The real `AsyncDriver.execute_query()` is a coroutine.

**How to avoid:** Change `validate_node` to `async def validate_node(state, driver)`. LangGraph natively supports async node functions when using `ainvoke()`. Update `build_graph()` closure to `lambda s: validate_node(s, driver)` — no change needed since LangGraph resolves the coroutine.

**Warning signs:** `TypeError: object tuple can't be used in 'await' expression` or `RuntimeWarning: coroutine 'AsyncDriver.execute_query' was never awaited`.

### Pitfall 2: roster Parameter Not Passed to execute_query

**What goes wrong:** Cypher uses `$roster` parameter (confirmed in `cypher.py` few-shot examples), but `validate_node` calls `driver.execute_query(cypher, database_="neo4j")` without passing `roster=state["roster"]`. Cypher returns empty results or raises `ParameterMissing` error.

**Why it happens:** Phase 2 validate_node executes the Cypher query to check non-empty results — the mock driver ignores parameters. The real driver requires all Cypher parameters to be passed.

**How to avoid:** In `validate_node`, extract the roster from state and pass it:
```python
records, _, _ = await driver.execute_query(
    cypher,
    roster=state.get("roster", []),
    database_="neo4j",
)
```

**Warning signs:** Neo4j `ParameterMissing` exception on Cypher queries that reference `$roster`.

### Pitfall 3: F2P List Misses Characters Already In Roster

**What goes wrong:** Duplicate character names in the augmented roster may cause Cypher to return doubled results or confuse the ANALYZE node.

**How to avoid:** `augment_with_f2p()` deduplicates by checking `if f2p not in combined` before appending.

### Pitfall 4: Name Normalization CONTAINS Match Returns Wrong Character

**What goes wrong:** `toLower(c.name) CONTAINS toLower($input)` for input "Aldo" matches both "Aldo" and "Aldo (Another Style)" — returns whichever comes first in the DB ordering.

**How to avoid:** Order by `size(c.name) ASC` to prefer the shortest (base) match when the input is ambiguous. If the user explicitly types "Aldo AS" or "Aldo Another Style", the longer canonical name is still reachable. For the base name, shortest match is almost always correct.

**Warning signs:** Integration test `test_name_normalization_aldo` returns an AS variant instead of base Aldo.

### Pitfall 5: AuraDB Free TLS Handshake

**What goes wrong:** AuraDB Free requires `neo4j+s://` URI scheme (TLS). Using `bolt://` against AuraDB fails with `SSL handshake failed`.

**Why it happens:** Local Docker uses `bolt://localhost:7687`; AuraDB uses `neo4j+s://<instance>.databases.neo4j.io`.

**How to avoid:** The `NEO4J_URI` env var already parameterizes the URI in `tests/conftest.py`. The plan should document that AuraDB integration tests require `NEO4J_URI=neo4j+s://...` and auth format `username/password` (same env var).

**Warning signs:** `ServiceUnavailable: Failed to establish connection` when running against AuraDB.

### Pitfall 6: asyncio_default_test_loop_scope Missing for New Test Files

**What goes wrong:** New test files in `tests/integration/` or `tests/workflow/` that add async tests may fail with `RuntimeError: no current event loop` if the session loop fixture is not inherited.

**How to avoid:** `pytest.ini` already sets `asyncio_default_test_loop_scope = session` globally. New test files do not need additional configuration as long as they use `@pytest.mark.integration` and import the session-scoped fixtures from `tests/conftest.py`.

---

## AF (Another Force) Zone Mechanics — Schema Extension Evaluation

The research flag asks whether `ENHANCES` or a new relationship type is needed for AF synergy queries.

**Finding: No schema extension needed for Phase 3.**

AF synergy in team building operates through three existing graph paths:

1. **Personality-based Special Attacks:** AF Special Attacks fire when frontline characters share personality traits. This is already modeled via `(Character)-[:HAS_TRAIT]->(Trait)`. A query asking "which characters share traits for AF special attacks" already works against the current schema.

2. **Zone-setting Grastas:** Zones are activated by Support Grastas (some) or character skills. The `Grasta` nodes with `category="Support"` and relevant `stats` already capture zone-related Grastas. The PLAN agent can identify them via `REQUIRES_TRAIT` traversal or by filtering on `category="Support"`.

3. **AF Anchor Role:** The ANALYZE node already assigns role annotations including "AF anchor" — this is an LLM inference from character stats/traits, not a graph relationship.

**What IS NOT in the current schema (and would require extension for v2/OPT-03):**
- Zone types as nodes (e.g., `(:Zone {type: "Fire"})`)
- `SETS_ZONE` relationship from Character/Grasta to Zone nodes
- `BENEFITS_FROM_ZONE` relationship from Character to Zone nodes

These are v2 improvements (OPT-03: "System accounts for Another Force (AF) zone mechanics in synergy recommendations"). Phase 3 should **document** the schema gap in a code comment in `SCHEMA.md` without implementing it — the current schema supports useful AF queries through trait matching.

**Decision logged:** No new relationship types or node labels are added in Phase 3. AF-aware recommendations rely on the PLAN agent's natural language → sub-goal decomposition to infer zone synergies from trait/Grasta data. A `# TODO OPT-03` comment should be added to SCHEMA.md noting the zone extension path.

---

## Code Examples

### Example 1: Roster Filtering with F2P Augmentation

```cypher
-- Source: SCHEMA.md v1.0.0 + existing cypher.py few-shot examples
MATCH (c:Character)-[:HAS_TRAIT]->(t:Trait)<-[:REQUIRES_TRAIT]-(g:Grasta)
WHERE c.name IN $roster
  AND g.category = 'Attack'
  AND g.is_shareable = true
RETURN c.name, t.name AS trait, collect(DISTINCT g.name) AS grastas
ORDER BY c.name
-- $roster = augment_with_f2p(user_roster)  -- includes F2P names
```

### Example 2: Name Normalization Lookup

```cypher
-- Source: Neo4j Cypher toLower() function
MATCH (c:Character)
WHERE toLower(c.name) = toLower($input)
   OR toLower(c.name) CONTAINS toLower($input)
RETURN c.name AS canonical
ORDER BY size(c.name) ASC
LIMIT 1
-- Example: $input="aldo" -> canonical="Aldo"
-- Example: $input="Aldo AS" -> canonical="Aldo (Another Style)" (if exists)
```

### Example 3: Integration Test — Owned + F2P Roster Filtering

```python
# Source: Existing tests/integration/test_known_nodes.py pattern
@pytest.mark.integration
async def test_roster_filtering_excludes_unowned(async_driver, loaded_db):
    """QUERY-02: Roster query must not return unowned characters."""
    owned_roster = ["Aldo", "Ciel"]
    # Augment with F2P for the query
    full_roster = owned_roster + ["Gariyu", "Levia"]  # known F2P subset

    records, _, _ = await async_driver.execute_query(
        """
        MATCH (c:Character)
        WHERE c.name IN $roster
        RETURN c.name AS name
        """,
        roster=full_roster,
        database_="neo4j",
    )
    returned_names = {r["name"] for r in records}
    unowned = returned_names - set(full_roster)
    assert len(unowned) == 0, f"Unowned characters returned: {unowned}"
```

### Example 4: Known-Good Synergy Traversal

```cypher
-- Source: SCHEMA.md v1.0.0 — HAS_TRAIT + REQUIRES_TRAIT path
-- Verified pattern: find characters from roster whose trait matches a shareable
-- Attack Grasta's requirement (cross-character equip scenario)
MATCH (c:Character)-[:HAS_TRAIT]->(t:Trait)<-[:REQUIRES_TRAIT]-(g:Grasta)
WHERE c.name IN $roster
  AND g.is_shareable = true
  AND g.category IN ['Attack', 'Support']
RETURN c.name AS character,
       t.name AS shared_trait,
       g.name AS grasta,
       g.tier AS tier,
       g.stats AS stats
ORDER BY g.tier DESC, c.name
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `GraphDatabase.driver()` (sync) in tests | `AsyncGraphDatabase.driver()` with session-scoped `pytest_asyncio.fixture` | Phase 1 (decided in 01-01) | No event loop closed errors |
| `asyncio_default_fixture_loop_scope` in `pyproject.toml` | `asyncio_default_test_loop_scope = session` in `pytest.ini` | quick-2 fix | Both must be present; `pytest.ini` takes precedence for test loop scope |
| Mock driver in workflow tests | Real async driver in integration tests | Phase 3 (this phase) | Live data validation for roster filtering and Grasta traversal |

**Deprecated/outdated:**
- `langchain_community.graphs.neo4j_graph.Neo4jGraph`: Still works but moved to `langchain_neo4j`. The project already uses `langchain-neo4j>=0.8`.

---

## Open Questions

1. **F2P Character List Completeness**
   - What we know: The wiki's `Free_Characters` page lists many free characters, but the set changes as new story content is added. Key confirmed F2P: Aldo, Feinne, Cyrus, Gariyu, Cerrine, Azami, Levia, Deirdre.
   - What's unclear: Whether collaboration characters (Persona 5's Joker/Morgana) should be in the F2P constant — they have limited-time availability and not all players have them.
   - Recommendation: Start with unambiguous story-permanent F2P characters. Mark the constant with `# TODO: expand from anothereden.wiki/w/Free_Characters`. Collaboration characters should NOT be in the hardcoded list.

2. **`validate_node` Sync/Async Boundary**
   - What we know: `validate_node` is currently `def` (sync); it calls `driver.execute_query()`. The mock driver in tests is sync. The real `AsyncDriver.execute_query()` is a coroutine.
   - What's unclear: Whether LangGraph's `build_graph` + `ainvoke` transparently handles a `lambda` that returns a coroutine from an `async def`, or whether the node definition itself must be `async def`.
   - Recommendation: Change `validate_node` to `async def`, update the lambda in `build_graph` to `lambda s: validate_node(s, driver)` (LangGraph resolves async node functions automatically in `ainvoke`). Update Phase 2 unit tests to mock the async call with `AsyncMock`.

3. **`graph.invoke()` vs `graph.ainvoke()`**
   - What we know: `build_graph()` in `graph.py` returns a compiled LangGraph. Phase 2 tests call `graph.invoke(sample_state)` (sync). With real async nodes, the caller must use `await graph.ainvoke(initial_state)`.
   - Recommendation: The entry point for Phase 3 (and later the FastAPI layer in Phase 4) should use `await graph.ainvoke(...)`. Existing Phase 2 unit tests can stay as-is by continuing to mock the driver synchronously in test fixtures.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.23.x |
| Config file | `pytest.ini` (existing) |
| Quick run command | `pytest tests/ -m "not integration" -x -q` |
| Full suite command | `pytest tests/ -x -q` (requires live Neo4j) |
| Integration only | `pytest tests/integration/ -m integration -x -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| QUERY-01 | Roster input as text list parsed correctly | unit | `pytest tests/workflow/test_plan.py -x -k "roster"` | ❌ Wave 0 |
| QUERY-02 | Recommendations only include owned + F2P chars | integration | `pytest tests/integration/test_query_pipeline.py::test_roster_filtering_excludes_unowned -x` | ❌ Wave 0 |
| QUERY-03 | Natural language query flows end-to-end | integration | `pytest tests/integration/test_query_pipeline.py::test_end_to_end_happy_path -x` | ❌ Wave 0 |
| QUERY-04 | Name normalization maps alias to canonical | integration | `pytest tests/integration/test_query_pipeline.py::test_name_normalization -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/ -m "not integration" -x -q`
- **Per wave merge:** `pytest tests/ -x -q` (with live Neo4j)
- **Phase gate:** Full suite green (including `@pytest.mark.integration`) before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/integration/test_query_pipeline.py` — covers QUERY-01, QUERY-02, QUERY-03, QUERY-04 with live DB
- [ ] `src/workflow/normalize.py` — `normalize_character_name()` and `normalize_roster()` helpers
- [ ] `src/workflow/f2p.py` — `F2P_CHARACTERS` constant and `augment_with_f2p()` helper
- [ ] Update `src/workflow/nodes/validate.py` — `async def validate_node` for real async driver

---

## Sources

### Primary (HIGH confidence)
- `tests/conftest.py` — existing `AsyncGraphDatabase.driver()` session fixture pattern (already working)
- `SCHEMA.md v1.0.0` — graph schema contract; verified at Phase 1 completion (Character=389, Grasta=489, Ore=61, Trait=126)
- `src/workflow/graph.py` — driver injection via closure is already implemented; no topology change needed
- `src/workflow/nodes/validate.py` — sync/async boundary identified in existing code
- [Neo4j Python Driver Async API](https://neo4j.com/docs/api/python-driver/current/async_api.html) — `execute_query()`, connection pooling, async session usage
- [Neo4j Cypher Parameters Manual](https://neo4j.com/docs/cypher-manual/current/syntax/parameters/) — `$roster` list parameter binding

### Secondary (MEDIUM confidence)
- [anothereden.wiki/w/Free_Characters](https://anothereden.wiki/w/Free_Characters) — F2P character list (web fetch confirmed canonical source)
- [anothereden.wiki/w/Another_Force](https://www.anothereden.wiki/w/Another_Force) — AF mechanics; no new schema types needed for basic personality-based Special Attack queries
- [anothereden.wiki/w/Zones](https://anothereden.wiki/w/Zones) — Zone mechanics; no personality-zone relationship in schema needed for Phase 3

### Tertiary (LOW confidence)
- WebSearch results re: "Another Eden name normalization" — no community tooling found; canonical names are the wiki names already in the graph. Custom `normalize_character_name()` is the right approach.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already installed and working in Phase 1/2
- Architecture: HIGH — driver injection pattern already in `build_graph(driver)`; async/sync boundary is the only new technical risk
- Pitfalls: HIGH — sync/async boundary pitfall is confirmed by code inspection of `validate.py` + `neo4j` async API
- F2P list: MEDIUM — wiki is authoritative but list is not exhaustive; hardcoded constant is the pragmatic approach
- AF schema evaluation: HIGH — confirmed no Phase 3 schema extension needed based on game mechanics research

**Research date:** 2026-03-16
**Valid until:** 2026-09-16 (stable domain; langchain-neo4j and neo4j driver APIs are stable)
