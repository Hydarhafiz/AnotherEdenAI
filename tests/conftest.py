"""Shared pytest fixtures for AnotherEden test suite.

Provides:
- async_driver: Session-scoped async Neo4j driver (reused across all tests in a session)
- clean_db: Function-scoped fixture that wipes the DB before each integration test

Pitfall avoided: Use @pytest_asyncio.fixture(loop_scope="session") for session-scoped async
fixtures to prevent RuntimeError: Event loop is closed when combined with function-scoped tests.
See: https://github.com/pytest-dev/pytest-asyncio/issues/706
"""
import os
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


@pytest_asyncio.fixture(scope="function")
async def clean_db(async_driver):
    """Function-scoped fixture that wipes all nodes and relationships.

    Run before each integration test to ensure a clean state.
    WARNING: Deletes ALL data in the connected Neo4j database.
    Only use in test environments.
    """
    await async_driver.execute_query("MATCH (n) DETACH DELETE n", database_="neo4j")
    yield
    # No teardown needed — next test will clean before it runs
