"""Shared pytest fixtures for AnotherEden test suite.

Provides:
- async_driver: Session-scoped async Neo4j driver (reused across all tests in a session)
- loaded_db: Session-scoped fixture that requires a populated integration graph
- clean_db: Function-scoped fixture that wipes the DB before each test (used only by idempotency tests)

Pitfall avoided: Use @pytest_asyncio.fixture(loop_scope="session") for session-scoped async
fixtures to prevent RuntimeError: Event loop is closed when combined with function-scoped tests.
See: https://github.com/pytest-dev/pytest-asyncio/issues/706

asyncio_default_test_loop_scope = session in pytest.ini ensures all tests share the same
event loop as the session-scoped async_driver, eliminating the "different loop" RuntimeError.
"""
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
    """Require a loaded graph without silently triggering live scraping.

    Integration tests must not turn an ordinary test run into a third-party
    browser scrape. Operators load the reviewed parsed corpus explicitly;
    dependent tests skip with an actionable reason when it is unavailable.
    """
    try:
        populated = await db_has_characters(async_driver)
    except Exception as e:
        pytest.skip(
            f"Neo4j integration graph is unavailable ({type(e).__name__}); "
            "start the service and load the reviewed parsed corpus before running integration tests."
        )
    if not populated:
        pytest.skip(
            "Neo4j integration graph has fewer than 100 Character nodes; "
            "load the reviewed parsed corpus before running integration tests."
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
    # Do not leave static integration fixtures (for example Aina) in the graph.
    await async_driver.execute_query("MATCH (n) DETACH DELETE n", database_="neo4j")
