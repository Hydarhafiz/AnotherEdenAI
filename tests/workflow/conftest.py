"""Shared pytest fixtures for workflow tests.

Provides:
    stub_driver: Function-scoped sync MagicMock simulating Neo4j driver.
    mock_llm: Function-scoped MagicMock simulating ChatAnthropic.
    sample_state: Function-scoped complete initial WorkflowState dict.

Note: All fixtures are sync (no async). Phase 2 workflow tests do not require
a real Neo4j connection — the driver is always a MagicMock.
"""
import pytest
from unittest.mock import MagicMock
from langchain_core.messages import AIMessage


@pytest.fixture
def stub_driver():
    """Function-scoped sync mock of a Neo4j driver.

    Default behavior:
        driver.execute_query() returns ([{"name": "Aldo"}], None, None)
        — a non-empty result representing a successful query.

    Override in tests:
        stub_driver.execute_query.return_value = ([], None, None)   # fail
        stub_driver.execute_query.side_effect = [...]               # sequence
    """
    driver = MagicMock()
    driver.execute_query.return_value = ([{"name": "Aldo"}], None, None)
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

    All 9 keys are present and set to sensible defaults for testing.
    """
    return {
        "user_query": "best fire team",
        "roster": ["Aldo", "Ciel"],
        "plan_strategy": "",
        "cypher_query": "",
        "db_results": [],
        "validation_errors": [],
        "retry_count": 0,
        "analysis_result": "",
        "final_output": {},
    }
