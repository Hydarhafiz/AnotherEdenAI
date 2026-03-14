"""Integration tests for ETL pipeline idempotency.

Wave 0 stubs — these tests are skipped until the full ETL pipeline is implemented in Plan 01-02/01-03.
Requires a running Neo4j instance (docker compose up).

Requirements covered:
- DATA-04: ETL pipeline is idempotent (re-running produces identical node and relationship counts)
"""
import pytest


@pytest.mark.skip(reason="TODO Plan 01-03: implement loader.py and full ETL pipeline")
async def test_etl_idempotent(clean_db, async_driver):
    """Run ETL twice and assert node and relationship counts are identical both runs.

    TODO: Import and invoke the ETL entry point (e.g., src/etl/loader.run_etl()).
    Run once, record (Character, Grasta, Ore, Trait) node counts and relationship counts.
    Run again, compare counts — all must be identical.

    Expected behavior: MERGE statements with unique constraints prevent duplicate creation.
    If counts differ between runs, either MERGE is missing a constraint or CREATE is used instead.

    Reference: 01-RESEARCH.md Pattern 3 — Neo4j UNWIND + MERGE Idempotent Loading
    Reference: 01-RESEARCH.md Pitfall 5 — Missing Constraints Cause Duplicate Nodes on Re-run
    """
    pass
