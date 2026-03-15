"""Unit tests for the PLAN node.

All tests use mocked LLM via unittest.mock.patch on src.workflow.nodes.plan.get_llm.
No live API calls are made.
"""
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage

from src.workflow.nodes.plan import plan_node


@pytest.fixture
def mock_llm_response():
    """Return a MagicMock LLM whose invoke() returns a predictable AIMessage."""
    llm = MagicMock()
    llm.invoke.return_value = AIMessage(content="strategy: find fire characters with attack grastas")
    return llm


def test_plan_node_returns_only_plan_strategy(sample_state, mock_llm_response):
    """plan_node must return a dict with exactly one key: plan_strategy (AGENT-07 key ownership)."""
    with patch("src.workflow.nodes.plan.get_llm", return_value=mock_llm_response):
        result = plan_node(sample_state)

    assert list(result.keys()) == ["plan_strategy"], (
        f"Expected only ['plan_strategy'], got {list(result.keys())}"
    )


def test_plan_node_plan_strategy_content_from_llm(sample_state, mock_llm_response):
    """plan_strategy must be taken from LLM response.content."""
    with patch("src.workflow.nodes.plan.get_llm", return_value=mock_llm_response):
        result = plan_node(sample_state)

    assert result["plan_strategy"] == "strategy: find fire characters with attack grastas"


def test_plan_node_uses_get_llm_with_planner_role(sample_state, mock_llm_response):
    """plan_node must call get_llm(role='planner') — not ChatAnthropic directly."""
    with patch("src.workflow.nodes.plan.get_llm", return_value=mock_llm_response) as mock_factory:
        plan_node(sample_state)

    mock_factory.assert_called_once_with(role="planner")


def test_plan_node_passes_user_query_in_human_message(sample_state, mock_llm_response):
    """plan_node must include the user_query in the HumanMessage passed to the LLM."""
    with patch("src.workflow.nodes.plan.get_llm", return_value=mock_llm_response):
        plan_node(sample_state)

    # Inspect the messages passed to llm.invoke()
    call_args = mock_llm_response.invoke.call_args
    messages = call_args[0][0]  # positional first argument is the messages list

    # Find the HumanMessage content
    from langchain_core.messages import HumanMessage
    human_messages = [m for m in messages if isinstance(m, HumanMessage)]
    assert len(human_messages) == 1, "Expected exactly one HumanMessage"
    assert sample_state["user_query"] in human_messages[0].content, (
        f"user_query '{sample_state['user_query']}' not found in HumanMessage"
    )


def test_plan_node_passes_roster_in_human_message(sample_state, mock_llm_response):
    """plan_node must include roster character names in the HumanMessage."""
    with patch("src.workflow.nodes.plan.get_llm", return_value=mock_llm_response):
        plan_node(sample_state)

    call_args = mock_llm_response.invoke.call_args
    messages = call_args[0][0]

    from langchain_core.messages import HumanMessage
    human_messages = [m for m in messages if isinstance(m, HumanMessage)]
    assert len(human_messages) == 1

    human_content = human_messages[0].content
    for character in sample_state["roster"]:
        assert character in human_content, (
            f"Roster character '{character}' not found in HumanMessage"
        )


def test_plan_node_uses_system_message(sample_state, mock_llm_response):
    """plan_node must include a SystemMessage with graph traversal instructions."""
    with patch("src.workflow.nodes.plan.get_llm", return_value=mock_llm_response):
        plan_node(sample_state)

    call_args = mock_llm_response.invoke.call_args
    messages = call_args[0][0]

    from langchain_core.messages import SystemMessage
    system_messages = [m for m in messages if isinstance(m, SystemMessage)]
    assert len(system_messages) == 1, "Expected exactly one SystemMessage"
    # System prompt must instruct on decomposing into graph traversal sub-goals
    assert len(system_messages[0].content) > 0, "SystemMessage must not be empty"
