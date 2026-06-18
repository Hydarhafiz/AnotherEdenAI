"""Shared pytest fixtures for workflow tests.

Provides:
    stub_driver: Function-scoped MagicMock simulating Neo4j driver.
                 execute_query is an AsyncMock (validate_node is now async).
    mock_llm: Function-scoped MagicMock simulating ChatAnthropic.
    sample_state: Function-scoped complete initial WorkflowState dict.

Note: stub_driver.execute_query is AsyncMock because validate_node is async
(Phase 3 change). Tests that invoke the full graph must use graph.ainvoke().
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from langchain_core.messages import AIMessage


@pytest.fixture
def stub_driver():
    """Function-scoped mock of a Neo4j async driver.

    Default behavior:
        driver.execute_query() returns ([{"name": "Aldo"}], None, None)
        — a non-empty result representing a successful query.
        execute_query is an AsyncMock to match validate_node's async boundary.

    Override in tests:
        stub_driver.execute_query.return_value = ([], None, None)   # fail
        stub_driver.execute_query.side_effect = [...]               # sequence
    """
    driver = MagicMock()
    driver.execute_query = AsyncMock(return_value=([{"name": "Aldo"}], None, None))
    return driver


@pytest.fixture
def mock_llm():
    """Function-scoped mock of a LangChain chat model (e.g. ChatAnthropic).

    Default behavior:
        llm.invoke() returns AIMessage(content="mock response")
    """
    llm = MagicMock()
    llm.invoke.return_value = AIMessage(content="mock response")
    return llm


@pytest.fixture
def sample_state():
    """Function-scoped complete initial WorkflowState with default values.

    All state keys are present and set to sensible defaults for testing.
    """
    return {
        "user_query": "best fire team",
        "roster": ["Aldo", "Ciel"],
        "owned_sidekicks": [],
        "plan_strategy": "",
        "boss_context": "",
        "cypher_query": "",
        "db_results": [],
        "validation_errors": [],
        "retry_count": 0,
        "analysis_result": "",
        "alternatives": "",
        "final_output": {},
    }
