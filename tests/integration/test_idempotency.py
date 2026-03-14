"""Integration tests for ETL pipeline idempotency.

Requires a running Neo4j instance (docker compose up).

This test uses static fixture data (no scraper) to verify idempotency.
This avoids the aiohttp/event-loop conflict that arises when run_etl_main()
is called with an external async_driver — the aiohttp ClientSession binds to
its own event loop on first creation, which may differ from the driver's loop.

Requirements covered:
- DATA-04: ETL pipeline is idempotent (re-running produces identical node and relationship counts)
"""
import pytest
from src.etl.loader import ensure_constraints, load_characters, load_grastas, load_ores
from src.etl.models import CharacterRow, GrastaRow, OreRow


async def get_counts(driver):
    """Return node counts per label and total relationship count."""
    counts = {}
    for label in ["Character", "Grasta", "Ore", "Trait"]:
        records, _, _ = await driver.execute_query(
            f"MATCH (n:{label}) RETURN count(n) AS cnt",
            database_="neo4j",
        )
        counts[label] = records[0]["cnt"]
    rel_records, _, _ = await driver.execute_query(
        "MATCH ()-[r]->() RETURN count(r) AS cnt",
        database_="neo4j",
    )
    counts["relationships"] = rel_records[0]["cnt"]
    return counts


@pytest.mark.integration
async def test_etl_idempotent(async_driver, clean_db):
    """Load static fixture data twice and assert node and relationship counts are identical.

    Uses static fixture rows (no scraper) to avoid event-loop conflicts.
    Expected behavior: MERGE statements with unique constraints prevent duplicate creation.
    If counts differ between runs, either MERGE is missing a constraint or CREATE is used instead.

    Reference: 01-RESEARCH.md Pattern 3 — Neo4j UNWIND + MERGE Idempotent Loading
    Reference: 01-RESEARCH.md Pitfall 5 — Missing Constraints Cause Duplicate Nodes on Re-run
    """
    # Static fixture data — small, representative, no network required
    char_rows = [
        CharacterRow(name="Aldo", element="Wind", weapon="Sword", light_shadow="Light", personalities=["Guts"]),
        CharacterRow(name="Aina", element="Fire", weapon="Bow", light_shadow="Shadow", personalities=["Calmness"]),
    ]
    grasta_rows = [
        GrastaRow(name="Test Attack I", category="Attack", tier=1, stats="ATK+10", personality_req="Guts", is_shareable=True),
        GrastaRow(name="Test VC Grasta", category="VC", tier=3, stats="ATK+20", personality_req=None, is_shareable=False),
    ]
    ore_rows = [
        OreRow(name="Test Ore", stats="ATK+5", source="Dungeon"),
    ]

    # First load
    await ensure_constraints(async_driver)
    await load_characters(async_driver, char_rows)
    await load_grastas(async_driver, grasta_rows)
    await load_ores(async_driver, ore_rows)
    counts_1 = await get_counts(async_driver)

    # Second load — should produce identical counts (idempotency check)
    await ensure_constraints(async_driver)
    await load_characters(async_driver, char_rows)
    await load_grastas(async_driver, grasta_rows)
    await load_ores(async_driver, ore_rows)
    counts_2 = await get_counts(async_driver)

    assert counts_1 == counts_2, f"ETL not idempotent: {counts_1} != {counts_2}"
    assert counts_1["Character"] >= 2
    assert counts_1["Grasta"] >= 2
    assert counts_1["Ore"] >= 1
