"""Shared pytest fixtures for AnotherEden test suite.

Provides:
- async_driver: Session-scoped async Neo4j driver (reused across all tests in a session)
- loaded_db: Session-scoped fixture that ensures the DB is populated exactly once per session
- clean_db: Function-scoped fixture that wipes the DB before each test (used only by idempotency tests)

Pitfall avoided: Use @pytest_asyncio.fixture(loop_scope="session") for session-scoped async
fixtures to prevent RuntimeError: Event loop is closed when combined with function-scoped tests.
See: https://github.com/pytest-dev/pytest-asyncio/issues/706

asyncio_default_test_loop_scope = session in pytest.ini ensures all tests share the same
event loop as the session-scoped async_driver, eliminating the "different loop" RuntimeError.
"""
import logging
import os
import pytest
import pytest_asyncio
from dotenv import load_dotenv
from neo4j import AsyncGraphDatabase

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_AUTH = tuple(os.getenv("NEO4J_AUTH", "neo4j/anothereden").split("/", 1))


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def async_driver():
    """Session-scoped async Neo4j driver.

    Reused across all tests in a session to avoid connection overhead.
    Closed automatically after all tests complete.
    """
    driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)
    yield driver
    await driver.close()


async def db_has_characters(driver, minimum: int = 100) -> bool:
    """Return True if the DB contains at least `minimum` Character nodes."""
    records, _, _ = await driver.execute_query(
        "MATCH (n:Character) RETURN count(n) AS cnt",
        database_="neo4j",
    )
    return records[0]["cnt"] >= minimum


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def loaded_db(async_driver):
    """Session-scoped fixture that ensures Neo4j DB is populated.

    Checks if data already exists; if not, runs the full ETL pipeline (scraper + loader).
    Runs at most once per test session. ETL failures are caught and logged — the fixture
    yields regardless so individual tests can decide whether to skip.

    Use this fixture in integration tests that query known graph nodes.
    Do NOT use in idempotency tests (they manage their own DB state).
    """
    try:
        if not await db_has_characters(async_driver):
            from src.etl.run_etl import main as run_etl_main
            await run_etl_main(driver=async_driver)
    except Exception as e:
        logging.getLogger(__name__).warning(
            "DB check or ETL failed — skipping load: %s", e
        )
    yield


@pytest_asyncio.fixture(scope="function")
async def clean_db(async_driver):
    """Function-scoped fixture that wipes all nodes and relationships.

    Run before each test to ensure a clean state.
    WARNING: Deletes ALL data in the connected Neo4j database.
    Only use in test environments, and only in tests that manage their own data load
    (e.g., idempotency tests that load static fixture data).
    """
    await async_driver.execute_query("MATCH (n) DETACH DELETE n", database_="neo4j")
    yield
    # No teardown needed — next test will clean before it runs
