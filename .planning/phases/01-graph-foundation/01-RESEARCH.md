# Phase 1: Graph Foundation - Research

**Researched:** 2026-03-14
**Domain:** Web scraping (httpx/BeautifulSoup), Pydantic v2 ETL, Neo4j 5.x graph loading, Docker Compose, pytest integration testing
**Confidence:** HIGH — wiki audit was performed live against the actual site; library patterns verified from official docs

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **Ore graph placement:** `(Ore)-[:ENHANCES]->(Grasta)` — bare edge, no relationship properties; Ore stats live on the Ore node itself. Corrects prior schema error (previously Ore→Character).
- **Scraper architecture:** Port `master_scraper.py` logic to async `httpx` + `asyncio`. Verified CSS selectors must be reused. Pydantic v2 models at the ETL boundary.
- **Neo4j target:** Local Docker Neo4j 5.x Community for Phases 1–4. `docker-compose.yml` is a Phase 1 deliverable.
- **ETL failure handling:** `ETL_MODE=strict` (fail-fast) is the development default. `ETL_MODE=lenient` (skip-with-warnings) for production runs. Mode is an environment variable.
- **Future architecture target:** Async batch designed for future AWS Lambda serverless deployment (no sync blocking I/O).

### Claude's Discretion

- Rate limiting strategy for async httpx requests (concurrent connection pool size, semaphore limit).
- Grasta `activating_trait` vs `personality_req` distinction — researcher to verify during Plan 01-01 wiki audit; schema can be extended if the game distinguishes equip vs activation trait.

### Deferred Ideas (OUT OF SCOPE)

- AWS Lambda deployment packaging — future target only, not part of Phase 1–4.
- Grasta activating_trait schema extension — implement only if wiki audit confirms the game distinguishes equip vs activation trait.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DATA-01 | Scrape character data (name, element, weapon, light_shadow, personalities) from anothereden.wiki | Wiki audit confirmed: `tr.character-row-entry` rows, data attributes all present and populated |
| DATA-02 | Scrape Grasta data for all 5 categories including tier, stats, personality_req, is_shareable | Wiki audit confirmed: `tr.grasta-row-entry` rows across 5 URLs; data attributes confirmed; column mapping documented with critical corrections |
| DATA-03 | Scrape Ore data (name, category, stats, source) | Wiki audit confirmed: `tr.equip-row-entry` rows at `/w/Grasta_Ores`; 4-column layout verified |
| DATA-04 | ETL pipeline is idempotent — re-running safely overwrites stale data | Neo4j MERGE + uniqueness constraints pattern documented; UNWIND batching pattern for performance |
| DATA-05 | Schema version tracked as constant; post-load assertion confirms expected node types exist | `constants.py` placement recommended; pytest assertion script pattern documented |
| GRAPH-01 | Character nodes with element, weapon, light_shadow, name properties | All properties confirmed in `data-element`, `data-weapon`, `data-type` (light_shadow), `data-name` attributes |
| GRAPH-02 | Character nodes linked to Trait nodes via HAS_TRAIT relationships | personalities from `data-personality` (comma-separated) → Trait node union pattern from `separate_trait_grasta.py` |
| GRAPH-03 | Grasta nodes with is_shareable, personality_req, category, tier, stats properties | Confirmed: `data-share`, `data-personality`, `data-type`, `data-tier` attributes; stats from col[3] |
| GRAPH-04 | Grasta shareability via is_shareable property; activating_trait distinguishes equip from activation | `data-share="1"` = is_shareable; activating_trait research finding: wiki does NOT distinguish equip vs activation in data attributes — defer schema extension |
| GRAPH-05 | Grasta nodes linked to Trait nodes via REQUIRES_TRAIT relationships | `data-personality` on grasta rows → REQUIRES_TRAIT edge; VC grastas have no data-personality (character-specific, not trait-based) |
| GRAPH-06 | Ore nodes with stats and source properties; linked to Grasta via ENHANCES | `tr.equip-row-entry`: col[1]=name, col[2]=stats, col[3]=source; ENHANCES relationship confirmed architecture |
| GRAPH-07 | Graph schema documented in SCHEMA.md as versioned contract before LLM prompts | SCHEMA.md structure and Neo4jGraph.get_schema() format documented; version constant placement in constants.py |
</phase_requirements>

---

## Summary

Phase 1 builds the Neo4j graph foundation that all subsequent LLM agent phases depend on. The wiki scraper, Pydantic ETL validation layer, Neo4j MERGE loading, and SCHEMA.md contract must all be complete and verified before Phase 2 begins.

A live wiki audit was performed against all seven anothereden.wiki pages. The core CSS selectors from `master_scraper.py` are confirmed working. However, the audit revealed two critical schema corrections that the planner must act on: (1) the grasta `data-name` attribute for VC category includes the character's name appended, so the display name must be extracted from col[1] instead; (2) the grasta "stats" column is col[3] (not col[2] as master_scraper.py attempts) — col[2] is the personality/character requirement column. The wiki is Cloudflare-fronted static MediaWiki HTML, loads in ~0.5s per page, and shows no rate-limit headers during normal sequential access.

The Pydantic v2 + Neo4j async driver + pytest-asyncio stack is well-documented and fits the ETL_MODE=strict/lenient toggle pattern. The SCHEMA.md contract must match what `Neo4jGraph.get_schema()` returns; both follow a "Node properties / Relationship properties / Relationships" text format. The `docker-compose.yml` pattern for Neo4j 5.x Community is straightforward with health check via `wget localhost:7474`.

**Primary recommendation:** Implement a 4-file ETL structure: `scraper.py` (async httpx), `models.py` (Pydantic v2), `loader.py` (Neo4j MERGE via UNWIND), `assert_schema.py` (post-load verification). All four files are independently testable.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| httpx | >=0.27 | Async HTTP client replacing requests | First-class async/await, connection pooling, drop-in requests replacement |
| beautifulsoup4 | >=4.12 | HTML parsing (reuse from master_scraper.py) | Already proven against anothereden.wiki selectors |
| pydantic | >=2.8 | ETL boundary validation models | v2.8+ adds FailFast validation; strict/lax toggle per-call |
| neo4j | >=5.x (driver) | Async Neo4j driver | AsyncGraphDatabase.driver(), execute_query(), transaction functions |
| langchain-neo4j | >=0.8 | Neo4jGraph.get_schema() for SCHEMA.md verification | Current package (langchain-community version deprecated since 0.3.8) |
| pytest | >=8.x | Test framework | Industry standard; asyncio support via pytest-asyncio |
| pytest-asyncio | >=0.23 | Async test support | Required for async driver fixtures and ETL integration tests |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| asyncio.Semaphore | stdlib | Concurrent request throttling | Rate-limit wiki fetches to N concurrent connections |
| python-dotenv | >=1.0 | Load .env for ETL_MODE, NEO4J_URI, NEO4J_AUTH | Development environment config |
| lxml | >=5.x | Faster HTML parser for BeautifulSoup | Optional: substitute `html.parser` if parse speed matters |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| httpx async | aiohttp | httpx has cleaner API, sync/async parity; aiohttp is faster for high volume but adds complexity |
| beautifulsoup4 | lxml directly | bs4 is already proven with these selectors; lxml direct is faster but different API |
| pytest-asyncio | anyio | pytest-asyncio is more common; anyio needed if mixing asyncio/trio backends |

### Installation

```bash
pip install httpx beautifulsoup4 pydantic>=2.8 neo4j langchain-neo4j \
            pytest pytest-asyncio python-dotenv
```

---

## Architecture Patterns

### Recommended Project Structure

```
src/
├── etl/
│   ├── scraper.py       # async httpx fetches, BeautifulSoup parse, returns raw dicts
│   ├── models.py        # Pydantic v2 CharacterRow, GrastaRow, OreRow models
│   ├── loader.py        # Neo4j MERGE via UNWIND, constraint creation, ETL orchestration
│   └── constants.py     # SCHEMA_VERSION, ETL_MODE, NEO4J_URI defaults
├── assert_schema.py     # post-load assertion script (exits 0 on success, 1 on failure)
├── SCHEMA.md            # versioned human-readable schema contract
├── docker-compose.yml   # Neo4j 5.x Community
└── tests/
    ├── conftest.py      # async Neo4j driver fixture, fresh DB fixture
    ├── unit/
    │   ├── test_models.py    # Pydantic validation, strict vs lenient toggle
    │   └── test_scraper.py   # parse functions with fixture HTML
    └── integration/
        ├── test_idempotency.py    # run ETL twice, compare node/rel counts
        └── test_known_nodes.py    # cypher queries for known character/grasta/ore
```

### Pattern 1: Async Scraper with Semaphore Rate Limiting

**What:** AsyncClient with connection limits + asyncio.Semaphore to cap concurrent wiki requests.
**When to use:** All wiki page fetches.

```python
# Source: https://www.python-httpx.org/advanced/resource-limits/
import asyncio
import httpx
from bs4 import BeautifulSoup

SEMAPHORE = asyncio.Semaphore(5)  # max 5 concurrent requests
LIMITS = httpx.Limits(max_keepalive_connections=5, max_connections=10)
HEADERS = {"User-Agent": "Mozilla/5.0 (AnotherEdenAI-research-bot)"}

async def fetch_page(client: httpx.AsyncClient, url: str) -> BeautifulSoup:
    async with SEMAPHORE:
        response = await client.get(url, timeout=15.0)
        response.raise_for_status()
        return BeautifulSoup(response.text, "html.parser")

async def scrape_all() -> dict:
    async with httpx.AsyncClient(limits=LIMITS, headers=HEADERS) as client:
        tasks = [fetch_page(client, url) for url in WIKI_URLS.values()]
        soups = await asyncio.gather(*tasks, return_exceptions=True)
    return soups
```

### Pattern 2: Pydantic v2 ETL Models with ETL_MODE Toggle

**What:** Models validate raw scraped dicts; `ETL_MODE` controls strict vs lenient behavior via per-call `model_validate()`.
**When to use:** All scraped rows before Neo4j loading.

```python
# Source: https://docs.pydantic.dev/latest/concepts/strict_mode/
import os
from pydantic import BaseModel, field_validator
from typing import Optional

ETL_MODE = os.getenv("ETL_MODE", "strict")
STRICT = ETL_MODE == "strict"

class CharacterRow(BaseModel):
    name: str
    element: str
    weapon: str
    light_shadow: str
    personalities: list[str]

    @field_validator("personalities", mode="before")
    @classmethod
    def parse_personalities(cls, v):
        if isinstance(v, str):
            return [p.strip() for p in v.split(",") if p.strip()]
        return v

def parse_character(raw: dict) -> Optional[CharacterRow]:
    try:
        return CharacterRow.model_validate(raw, strict=STRICT)
    except Exception as exc:
        if STRICT:
            raise  # ETL_MODE=strict: fail-fast, bubble up
        print(f"WARN: Skipping character {raw.get('name')}: {exc}")
        return None
```

### Pattern 3: Neo4j UNWIND + MERGE Idempotent Loading

**What:** Batch all records into a single UNWIND+MERGE query per node type. Constraints make MERGE index-backed.
**When to use:** All node and relationship creation.

```python
# Source: https://neo4j.com/docs/python-manual/current/performance/
async def ensure_constraints(driver):
    constraints = [
        "CREATE CONSTRAINT char_name IF NOT EXISTS FOR (c:Character) REQUIRE c.name IS UNIQUE",
        "CREATE CONSTRAINT trait_name IF NOT EXISTS FOR (t:Trait) REQUIRE t.name IS UNIQUE",
        "CREATE CONSTRAINT grasta_name IF NOT EXISTS FOR (g:Grasta) REQUIRE g.name IS UNIQUE",
        "CREATE CONSTRAINT ore_name IF NOT EXISTS FOR (o:Ore) REQUIRE o.name IS UNIQUE",
    ]
    for cql in constraints:
        await driver.execute_query(cql, database_="neo4j")

async def load_characters(driver, rows: list[dict]):
    await driver.execute_query(
        """
        UNWIND $rows AS row
        MERGE (c:Character {name: row.name})
        ON CREATE SET c.element = row.element,
                      c.weapon = row.weapon,
                      c.light_shadow = row.light_shadow
        ON MATCH SET  c.element = row.element,
                      c.weapon = row.weapon,
                      c.light_shadow = row.light_shadow
        WITH c, row
        UNWIND row.personalities AS trait_name
        MERGE (t:Trait {name: trait_name})
        MERGE (c)-[:HAS_TRAIT]->(t)
        """,
        rows=rows,
        database_="neo4j",
    )
```

### Pattern 4: Docker Neo4j 5.x Health Check

**What:** docker-compose.yml for Neo4j 5.x Community with health check, named volume, and `.env` support.
**When to use:** Phase 1 deliverable — enables `docker compose up` for any dev.

```yaml
# docker-compose.yml
services:
  neo4j:
    image: neo4j:5-community
    ports:
      - "7474:7474"   # Browser
      - "7687:7687"   # Bolt
    environment:
      - NEO4J_AUTH=${NEO4J_AUTH:-neo4j/anothereden}
      - NEO4J_PLUGINS=[]
      - NEO4J_dbms_memory_heap_max__size=512m
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs
    healthcheck:
      test: ["CMD-SHELL", "wget --no-verbose --tries=1 --spider localhost:7474 || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 10
      start_period: 30s

volumes:
  neo4j_data:
  neo4j_logs:
```

### Pattern 5: Post-Load Assertion Script

**What:** `assert_schema.py` runs after ETL and exits 0 if all expected node types exist with minimum counts.
**When to use:** CI gate after ETL; verifies DATA-05.

```python
# assert_schema.py
import sys
from neo4j import GraphDatabase
import os

EXPECTED = {
    "Character": 300,  # actual wiki has 393 — set floor
    "Grasta": 500,     # actual wiki has 647 — set floor
    "Ore": 50,         # actual wiki has 61 — set floor
    "Trait": 10,       # at least some traits must exist
}

driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI", "bolt://localhost:7687"),
    auth=tuple(os.getenv("NEO4J_AUTH", "neo4j/anothereden").split("/"))
)
failed = False
with driver.session() as session:
    for label, min_count in EXPECTED.items():
        result = session.run(f"MATCH (n:{label}) RETURN count(n) AS cnt")
        cnt = result.single()["cnt"]
        if cnt < min_count:
            print(f"FAIL: {label} count {cnt} < expected minimum {min_count}")
            failed = True
        else:
            print(f"OK: {label} = {cnt}")
driver.close()
sys.exit(1 if failed else 0)
```

### Anti-Patterns to Avoid

- **Silent exception swallowing:** `master_scraper.py` uses bare `except: continue`. Replace with explicit Pydantic validation and ETL_MODE-controlled re-raise.
- **CREATE instead of MERGE:** Using CREATE without constraints creates duplicates on re-run; always MERGE with unique constraint backing.
- **Multiple httpx client instances in loops:** Creating `AsyncClient` per-request eliminates connection pooling. Use one client for all fetches.
- **Hard-coding VC tier as 4:** The wiki `data-tier` for all 310 VC grastas is `"3"` — `master_scraper.py` hard-coded `tier=4` which is wrong.
- **Using `data-name` for VC grasta node names:** VC `data-name` = "Proof Name + Character Name" (e.g., `"Yin-Yang Cat Proof Nekoko"`). The display name (grasta name only) is in col[1]. Use col[1] for the Grasta node's `name` property.

---

## Wiki Audit Results (CRITICAL — Corrections to master_scraper.py)

### Characters Page (`/w/Characters`)

| Property | Value |
|----------|-------|
| Selector | `tr.character-row-entry` |
| Row count | 393 |
| data-name | Character name (may be comma-separated for variant names) |
| data-element | Element string |
| data-weapon | Weapon type |
| data-type | `"Light"` or `"Shadow"` — maps to `light_shadow` |
| data-personality | Comma-separated personality trait names |
| Extra attrs | data-sidekick, data-gender, data-free, data-rarity, data-stellar, data-role_strict |

**Status:** master_scraper.py selectors are correct for CHARACTER data. No corrections needed.

### Grasta Pages (`/w/Grasta_Attack`, `/w/Grasta_Life`, `/w/Grasta_Support`, `/w/Grasta_Special`, `/w/Grasta_VC`)

| Category | Row count | Selector |
|----------|-----------|---------|
| Attack | 231 | `tr.grasta-row-entry` |
| Life | 46 | `tr.grasta-row-entry` |
| Support | 56 | `tr.grasta-row-entry` |
| Special | 4 | `tr.grasta-row-entry` |
| VC | 310 | `tr.grasta-row-entry` |
| **Total** | **647** | |

**Column layout (6 columns, 0-indexed):**

| col | Content | Notes |
|-----|---------|-------|
| col[0] | Category + tier (e.g., "Attack (T3)") | Redundant with data-type/data-tier |
| col[1] | Grasta display name | **Use for VC node name** (data-name includes character) |
| col[2] | Personality or "Character: {name}" | Empty for weapon-based grastas |
| col[3] | Stats (e.g., "INT +10 SPD +10") | **This is stats** — master_scraper.py used col[2] which is wrong |
| col[4] | Effect text | Activated/Awakened effect description |
| col[5] | Source/location | Drop location |

**Data attributes on grasta rows:**

| Attribute | Values | Notes |
|-----------|--------|-------|
| data-name | Grasta name (+ character name for VC) | For VC, parse col[1] instead |
| data-type | "Attack", "Life", "Support", "Special", "VC" | Maps to category |
| data-tier | "3" for all current grastas | **master_scraper.py hard-coded VC tier=4, which is wrong** |
| data-share | "0" or "1" | is_shareable flag |
| data-personality | Specific trait name or empty | personality_req; empty for weapon/character-based |
| data-any_personality | "any" or empty | "any" = has a personality requirement (but may not be the specific one) |
| data-staff/sword/katana/etc | "0" or "1" | Weapon-type equip requirement flags |
| data-element | Usually empty | Element restriction if any |
| data-unreleased | "0" or "1" | Filter unreleased content |

**Critical correction on master_scraper.py `scrape_grasta_general()`:**
```python
# WRONG in master_scraper.py:
stats_text = cols[2].get_text(strip=True)  # col[2] is personality_req, NOT stats

# CORRECT:
personality_req = cols[2].get_text(strip=True)  # or row.get("data-personality")
stats_text = cols[3].get_text(" ", strip=True)   # col[3] is stats
```

**VC Grasta special case:**
- `data-name` = grasta name + character name concatenated: `"Yin-Yang Cat Proof Nekoko"`
- col[1] = grasta display name only: `"Yin-Yang Cat Proof"`
- col[2] = `"Character: Nekoko"` (character requirement, not a Trait)
- `data-personality` is always empty for VC grastas
- VC grastas should NOT create REQUIRES_TRAIT edges (they require a specific character, not a personality trait)

**GRAPH-04 finding — activating_trait vs personality_req:**
The wiki does NOT expose an "activation trait" vs "equip trait" distinction in data attributes. The `data-personality` is the personality required to equip the grasta. The effect text (col[4]) describes what happens when activated/awakened. No separate `activating_trait` field is needed for Phase 1 — the CONTEXT.md deferred this to "implement if wiki audit confirms distinction." Audit result: distinction not present in wiki data attributes. Recommend keeping schema to `personality_req` only in Phase 1.

### Ore Page (`/w/Grasta_Ores`)

| Property | Value |
|----------|-------|
| Selector | `tr.equip-row-entry` |
| Row count | 61 |
| data-accessory | "Grasta Upgrade Item" (all rows) |

**Column layout (4 columns, 0-indexed):**

| col | Content | Example |
|-----|---------|---------|
| col[0] | Image (empty text) | — |
| col[1] | Ore name (as text or anchor tag) | "AF After Victory Ore" |
| col[2] | Stats/effect description | "Restore AF after victory..." |
| col[3] | Source/location | "Fog People Vendor in Laranssa Plains..." |

**master_scraper.py `scrape_ores()` is correct** for col[1], col[2], col[3] extraction pattern.

### Rate Limiting

- Server: Cloudflare-fronted static MediaWiki HTML
- Response time: ~0.5s per page (7 pages total = ~3.5s sequential)
- No `Retry-After` or rate-limit headers observed
- Recommendation: asyncio.Semaphore(5) with httpx.Limits(max_connections=10) is safe and polite
- All 7 pages can be fetched concurrently without issue at this scale

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Async HTTP with pooling | Custom socket connection reuse | `httpx.AsyncClient` with `httpx.Limits` | Connection pooling, timeout handling, keep-alive managed automatically |
| ETL validation with fail-fast | Custom dict validation functions | Pydantic v2 `model_validate()` with `strict=` param | Type coercion, field validators, error messages, per-call mode toggle |
| Neo4j duplicate prevention | Custom pre-check SELECT before INSERT | `MERGE` with uniqueness constraint | MERGE is atomic; pre-check SELECT+CREATE has TOCTOU race condition |
| Async test fixtures | Custom event loop management | pytest-asyncio with `asyncio_mode = "auto"` | Event loop scope bugs are well-documented; let pytest-asyncio manage lifecycle |
| Schema introspection | Custom CALL db.schema.visualization() parsing | `Neo4jGraph.get_schema()` from langchain-neo4j | Returns formatted string already suitable for LLM prompt injection |

**Key insight:** The wiki scraping problem is solved (7 pages, known selectors, static HTML). The complexity in Phase 1 is in the ETL validation layer and graph loading idempotency — both have mature library solutions.

---

## Common Pitfalls

### Pitfall 1: VC Grasta data-name Includes Character Name

**What goes wrong:** Using `row.get("data-name")` for VC grastas yields `"Yin-Yang Cat Proof Nekoko"` instead of `"Yin-Yang Cat Proof"`. If this name is used as the Grasta node's `name` property, every character-specific VC grasta gets a unique node even if the same grasta effect exists for multiple characters.
**Why it happens:** The wiki uses data-name as a unique ID for the filter system, appending character name to distinguish variants.
**How to avoid:** For VC category, use `cols[1].get_text(strip=True)` as the Grasta node name. Parse `cols[2]` to extract the character name (strip `"Character: "` prefix) if needed for a future EQUIPPABLE_BY relationship.
**Warning signs:** Grasta node count is 2–3x higher than expected after loading.

### Pitfall 2: Stats in Wrong Column

**What goes wrong:** `master_scraper.py` reads `cols[2]` as stats for all grasta categories. Column 2 is actually the personality/character requirement. Stats are in col[3].
**Why it happens:** The original scraper was written from inspection and had column numbering wrong.
**How to avoid:** Column mapping is now verified: col[2]=personality_req (may be empty), col[3]=stats.
**Warning signs:** Grasta `stats` property contains trait names like "Straw Dummy" instead of "INT +10 SPD +10".

### Pitfall 3: VC Grastas Creating Spurious REQUIRES_TRAIT Edges

**What goes wrong:** Attempting to create REQUIRES_TRAIT edges for VC grastas based on col[2] content like "Character: Nekoko" would create Trait nodes named "Character: Nekoko".
**Why it happens:** Uniform processing of personality_req column without checking the grasta category.
**How to avoid:** In the loader, gate REQUIRES_TRAIT creation on `grasta.category != "VC"` AND `grasta.personality_req is not None`. VC grastas have no Trait requirement.
**Warning signs:** Trait nodes named "Character: ..." appear in the graph.

### Pitfall 4: pytest-asyncio Event Loop Scope Bugs

**What goes wrong:** Session-scoped async fixtures fail with `RuntimeError: Event loop is closed` when combined with function-scoped tests.
**Why it happens:** pytest-asyncio event loop scope mismatch between fixture and test scope.
**How to avoid:** Use `asyncio_mode = "auto"` in `pytest.ini`. For the Neo4j driver fixture, use `scope="session"` and decorate with `@pytest_asyncio.fixture(loop_scope="session")`. This is a known issue with multiple GitHub threads as of 2024.
**Warning signs:** Tests pass in isolation but fail when run together.

### Pitfall 5: Missing Constraints Cause Duplicate Nodes on Re-run

**What goes wrong:** MERGE without a uniqueness constraint scans the entire label to find matches — is slow and not guaranteed unique if run concurrently.
**Why it happens:** Forgetting to create constraints before the first MERGE.
**How to avoid:** Always run `ensure_constraints()` first in the ETL entry point. Use `CREATE CONSTRAINT ... IF NOT EXISTS` so re-runs are safe.
**Warning signs:** Node counts double on second ETL run; graph contains duplicate Character/Grasta/Ore nodes.

### Pitfall 6: Hard-Coded VC Tier Value

**What goes wrong:** master_scraper.py hard-codes `tier=4` for all VC grastas. All 310 VC grastas currently show `data-tier="3"` on the wiki.
**Why it happens:** Assumed VC tier before verifying.
**How to avoid:** Always read `data-tier` from the row attribute, even for VC. The ETL model should parse it from the data attribute.
**Warning signs:** All Grasta VC nodes have tier=4 when a Cypher query reveals the wiki reports tier=3.

---

## Code Examples

### Neo4j Constraint Creation (Idempotent)

```cypher
-- Source: https://neo4j.com/docs/cypher-manual/current/clauses/merge/
CREATE CONSTRAINT char_name IF NOT EXISTS FOR (c:Character) REQUIRE c.name IS UNIQUE;
CREATE CONSTRAINT trait_name IF NOT EXISTS FOR (t:Trait) REQUIRE t.name IS UNIQUE;
CREATE CONSTRAINT grasta_name IF NOT EXISTS FOR (g:Grasta) REQUIRE g.name IS UNIQUE;
CREATE CONSTRAINT ore_name IF NOT EXISTS FOR (o:Ore) REQUIRE o.name IS UNIQUE;
```

### Neo4j Async Driver (Python)

```python
# Source: https://neo4j.com/docs/api/python-driver/current/async_api.html
from neo4j import AsyncGraphDatabase

async def get_driver(uri: str, auth: tuple) -> AsyncGraphDatabase:
    driver = AsyncGraphDatabase.driver(uri, auth=auth)
    await driver.verify_connectivity()
    return driver

# Usage: one driver instance per application lifetime
# Sessions are created per operation, not reused across concurrent tasks
async with driver.session(database="neo4j") as session:
    records, summary, keys = await driver.execute_query(
        "MERGE (c:Character {name: $name}) RETURN c",
        name="Aldo", database_="neo4j"
    )
```

### Pydantic v2 Per-Call Mode Toggle

```python
# Source: https://docs.pydantic.dev/latest/concepts/strict_mode/
# Strict mode: no coercion, fail on wrong types
record = CharacterRow.model_validate(raw_dict, strict=True)

# Lax mode: allows string-to-int coercion etc.
record = CharacterRow.model_validate(raw_dict, strict=False)
```

### Neo4jGraph Schema Format (for SCHEMA.md validation)

```python
# Source: https://neo4j.com/labs/genai-ecosystem/langchain/
from langchain_neo4j import Neo4jGraph

graph = Neo4jGraph(url="bolt://localhost:7687", username="neo4j", password="anothereden")
graph.refresh_schema()
print(graph.schema)
# Output format:
# Node properties:
# Character {name: STRING, element: STRING, weapon: STRING, light_shadow: STRING}
# Trait {name: STRING}
# Grasta {name: STRING, category: STRING, tier: INTEGER, stats: STRING, is_shareable: BOOLEAN, personality_req: STRING}
# Ore {name: STRING, stats: STRING, source: STRING}
# Relationship properties:
#
# The relationships:
# (:Character)-[:HAS_TRAIT]->(:Trait)
# (:Grasta)-[:REQUIRES_TRAIT]->(:Trait)
# (:Ore)-[:ENHANCES]->(:Grasta)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| langchain-community Neo4jGraph | langchain-neo4j Neo4jGraph | langchain-community 0.3.8 | Use `langchain-neo4j` package; community version deprecated |
| requests (sync) | httpx AsyncClient | Phase 1 decision | Non-blocking scrape; Lambda-ready |
| Pydantic v1 BaseModel | Pydantic v2 BaseModel + ConfigDict | v2 release (now stable) | Faster, strict mode per-call, FailFast validation |
| neo4j.GraphDatabase (sync) | neo4j.AsyncGraphDatabase | neo4j-driver 5.x | Required for async ETL pipeline |
| CREATE CONSTRAINT syntax (Neo4j 3.x) | `CREATE CONSTRAINT name IF NOT EXISTS FOR (n:Label) REQUIRE n.prop IS UNIQUE` | Neo4j 4.x+ | IF NOT EXISTS is required for idempotent constraint creation |

**Deprecated/outdated:**
- `neo4j-driver` PyPI package name: still works but `neo4j` is the canonical package name as of 5.x
- `langchain_community.graphs.neo4j_graph.Neo4jGraph`: deprecated since langchain-community 0.3.8 — use `langchain_neo4j` instead

---

## Open Questions

1. **VC Grasta uniqueness by character**
   - What we know: `data-name` for VC = "Proof Name + Character" (e.g., "Yin-Yang Cat Proof Nekoko"). Multiple characters may have grasta Proofs with identical display names (col[1]).
   - What's unclear: Should VC Grasta nodes be unique by (display_name, character_name) composite key, or is the `data-name` value (which includes character) already the correct unique identifier?
   - Recommendation: Use the full `data-name` value as the Grasta node's `name` property for VC grastas. This preserves uniqueness. Document in SCHEMA.md that VC Grasta names include the character name.

2. **data-personality comma-separated for grastas vs single value**
   - What we know: Grasta `data-personality` appears to be a single trait name (e.g., "Straw Dummy"), not comma-separated.
   - What's unclear: Can a grasta require multiple personality traits simultaneously?
   - Recommendation: Treat `data-personality` as a single value for Grasta. The REQUIRES_TRAIT edge is singular. If multi-trait grastas exist, they'll appear as multiple rows with the same grasta name (confirmed in audit: "Power of Sorcery Mind" appears twice with different personality values = two separate rows, not one row with comma-separated).

3. **Grasta Ore ENHANCES relationship specificity**
   - What we know: `(Ore)-[:ENHANCES]->(Grasta)` is the locked schema. The wiki Ore table has no column linking Ore to specific Grasta names.
   - What's unclear: The wiki doesn't explicitly list which Grasta each Ore upgrades — the ENHANCES relationship may require game knowledge not present on the Ore page.
   - Recommendation: Defer ENHANCES edges until the wiki audit during Plan 01-01 confirms if the Ore page has Grasta linkage data. If not present, Ore nodes should exist without ENHANCES edges initially, and GRAPH-06 should be scoped to just creating Ore nodes. Revisit ENHANCES if a separate wiki page documents the smelting relationships.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.23+ |
| Config file | `pytest.ini` — see Wave 0 |
| Quick run command | `pytest tests/unit/ -x -q` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DATA-01 | Characters scraped with correct attributes | unit | `pytest tests/unit/test_scraper.py::test_parse_character -x` | Wave 0 |
| DATA-02 | All 5 Grasta categories scraped correctly | unit | `pytest tests/unit/test_scraper.py::test_parse_grasta_categories -x` | Wave 0 |
| DATA-03 | Ores scraped with name, stats, source | unit | `pytest tests/unit/test_scraper.py::test_parse_ores -x` | Wave 0 |
| DATA-04 | ETL pipeline idempotent (run twice = same counts) | integration | `pytest tests/integration/test_idempotency.py -x` | Wave 0 |
| DATA-05 | Post-load assertion script exits 0 | assertion script | `python assert_schema.py` | Wave 0 |
| GRAPH-01 | Character node has element, weapon, light_shadow, name | integration | `pytest tests/integration/test_known_nodes.py::test_character_properties -x` | Wave 0 |
| GRAPH-02 | Character linked to Trait nodes via HAS_TRAIT | integration | `pytest tests/integration/test_known_nodes.py::test_character_traits -x` | Wave 0 |
| GRAPH-03 | Grasta node has is_shareable, personality_req, category, tier, stats | integration | `pytest tests/integration/test_known_nodes.py::test_grasta_properties -x` | Wave 0 |
| GRAPH-04 | Shareable Grasta has is_shareable=True | integration | `pytest tests/integration/test_known_nodes.py::test_shareable_grasta -x` | Wave 0 |
| GRAPH-05 | Grasta linked to Trait via REQUIRES_TRAIT | integration | `pytest tests/integration/test_known_nodes.py::test_grasta_requires_trait -x` | Wave 0 |
| GRAPH-06 | Ore node exists with stats and source | integration | `pytest tests/integration/test_known_nodes.py::test_ore_properties -x` | Wave 0 |
| GRAPH-07 | SCHEMA.md exists and matches get_schema() output | assertion script | `python assert_schema.py` (include SCHEMA.md diff check) | Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/unit/ -x -q`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green + `python assert_schema.py` exits 0 before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/conftest.py` — async Neo4j driver fixture, function-scoped DB wipe, session-scoped driver
- [ ] `tests/unit/test_scraper.py` — tests against fixture HTML (no network calls); covers DATA-01, DATA-02, DATA-03
- [ ] `tests/unit/test_models.py` — Pydantic strict vs lenient mode; covers DATA-02 validation
- [ ] `tests/integration/test_idempotency.py` — requires running Neo4j; covers DATA-04
- [ ] `tests/integration/test_known_nodes.py` — post-ETL cypher queries; covers GRAPH-01 through GRAPH-07
- [ ] `pytest.ini` — `asyncio_mode = "auto"`, `asyncio_default_fixture_loop_scope = "session"`
- [ ] Framework install: `pip install pytest pytest-asyncio` — if none detected

---

## Sources

### Primary (HIGH confidence — live audit or official docs)

- Live wiki audit against anothereden.wiki — performed 2026-03-14 against `/w/Characters`, `/w/Grasta_Attack`, `/w/Grasta_Life`, `/w/Grasta_Support`, `/w/Grasta_Special`, `/w/Grasta_VC`, `/w/Grasta_Ores`
- [HTTPX Resource Limits](https://www.python-httpx.org/advanced/resource-limits/) — Limits parameters and defaults
- [HTTPX Async Support](https://www.python-httpx.org/async/) — AsyncClient pattern
- [Neo4j Async API Documentation](https://neo4j.com/docs/api/python-driver/current/async_api.html) — AsyncDriver, execute_query patterns
- [Neo4j Python Manual: Performance](https://neo4j.com/docs/python-manual/current/performance/) — UNWIND+MERGE batching
- [Neo4j Cypher MERGE](https://neo4j.com/docs/cypher-manual/current/clauses/merge/) — ON CREATE/ON MATCH patterns
- [Pydantic v2 Strict Mode](https://docs.pydantic.dev/latest/concepts/strict_mode/) — per-call strict toggle
- [langchain-neo4j PyPI](https://pypi.org/project/langchain-neo4j/) — v0.8.0 current package

### Secondary (MEDIUM confidence — verified with multiple sources)

- [Neo4j Docker Compose Standalone](https://neo4j.com/docs/operations-manual/current/docker/docker-compose-standalone/) — docker-compose.yml pattern
- [Neo4j Python Manual: Concurrency](https://neo4j.com/docs/python-manual/current/concurrency/) — async transaction patterns
- WebSearch: langchain-neo4j schema format confirmed by multiple LangChain docs and community examples

### Tertiary (LOW confidence — single source, needs validation)

- `assert_schema.py` pattern: derived from first principles; exact minimum counts should be set after first successful ETL run against the actual wiki

---

## Metadata

**Confidence breakdown:**
- Wiki selectors and page structure: HIGH — live Python scrape confirmed all selectors, counts, and column layouts
- Standard stack: HIGH — official docs consulted for all libraries
- Architecture patterns: HIGH — patterns from official docs, cross-verified
- Common pitfalls: HIGH — pitfalls identified by comparing master_scraper.py against live wiki audit
- Rate limiting recommendation: MEDIUM — no documented limits observed; Semaphore(5) is conservative estimate

**Research date:** 2026-03-14
**Valid until:** 2026-06-14 (wiki structure is stable MediaWiki; library versions stable; check if langchain-neo4j version changes before Phase 2)
