"""Integration tests for ETL pipeline idempotency.

Requires a running Neo4j instance (docker compose up).

Requirements covered:
- DATA-04: ETL pipeline is idempotent (re-running produces identical node and relationship counts)
"""
import pytest
from src.etl.run_etl import main as run_etl_main


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
    """Run ETL twice and assert node and relationship counts are identical both runs.

    Expected behavior: MERGE statements with unique constraints prevent duplicate creation.
    If counts differ between runs, either MERGE is missing a constraint or CREATE is used instead.

    Reference: 01-RESEARCH.md Pattern 3 — Neo4j UNWIND + MERGE Idempotent Loading
    Reference: 01-RESEARCH.md Pitfall 5 — Missing Constraints Cause Duplicate Nodes on Re-run
    """
    await run_etl_main(driver=async_driver)  # First run
    counts_1 = await get_counts(async_driver)
    await run_etl_main(driver=async_driver)  # Second run
    counts_2 = await get_counts(async_driver)
    assert counts_1 == counts_2, f"ETL not idempotent: {counts_1} != {counts_2}"
    assert counts_1["Character"] >= 300
    assert counts_1["Grasta"] >= 500
    assert counts_1["Ore"] >= 50
