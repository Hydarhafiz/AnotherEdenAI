"""Unit tests for the PLAN node.

All tests use mocked LLM via unittest.mock.patch on src.workflow.nodes.plan.get_llm.
normalize_roster and augment_with_f2p are also mocked to isolate plan_node logic.
No live API calls are made; no live Neo4j calls are made.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage

from src.workflow.nodes.plan import plan_node


@pytest.fixture
def mock_llm_response():
    """Return a MagicMock LLM whose invoke() returns a predictable AIMessage."""
    llm = MagicMock()
    llm.invoke.return_value = AIMessage(content="strategy: find fire characters with attack grastas")
    return llm


@pytest.fixture
def stub_driver_plan():
    """Stub async driver for plan_node; normalize_roster is mocked so driver is unused."""
    driver = MagicMock()
    driver.execute_query = AsyncMock(return_value=([], None, None))
    return driver


@pytest.mark.asyncio
async def test_plan_node_returns_plan_strategy_and_roster(sample_state, stub_driver_plan, mock_llm_response):
    """plan_node must return a dict with plan_strategy and roster keys."""
    with patch("src.workflow.nodes.plan.get_llm", return_value=mock_llm_response), \
         patch("src.workflow.nodes.plan.normalize_roster", new_callable=AsyncMock,
               return_value=["Aldo", "Ciel"]) as mock_norm, \
         patch("src.workflow.nodes.plan.augment_with_f2p", return_value=["Aldo", "Ciel", "Feinne"]):
        result = await plan_node(sample_state, stub_driver_plan)

    assert "plan_strategy" in result
    assert "roster" in result


@pytest.mark.asyncio
async def test_plan_node_plan_strategy_content_from_llm(sample_state, stub_driver_plan, mock_llm_response):
    """plan_strategy must be taken from LLM response.content."""
    with patch("src.workflow.nodes.plan.get_llm", return_value=mock_llm_response), \
         patch("src.workflow.nodes.plan.normalize_roster", new_callable=AsyncMock,
               return_value=["Aldo", "Ciel"]), \
         patch("src.workflow.nodes.plan.augment_with_f2p", return_value=["Aldo", "Ciel"]):
        result = await plan_node(sample_state, stub_driver_plan)

    assert result["plan_strategy"] == "strategy: find fire characters with attack grastas"


@pytest.mark.asyncio
async def test_plan_node_uses_get_llm_with_planner_role(sample_state, stub_driver_plan, mock_llm_response):
    """plan_node must call get_llm(role='planner') — not ChatAnthropic directly."""
    with patch("src.workflow.nodes.plan.get_llm", return_value=mock_llm_response) as mock_factory, \
         patch("src.workflow.nodes.plan.normalize_roster", new_callable=AsyncMock,
               return_value=["Aldo"]), \
         patch("src.workflow.nodes.plan.augment_with_f2p", return_value=["Aldo"]):
        await plan_node(sample_state, stub_driver_plan)

    mock_factory.assert_called_once_with(role="planner")


@pytest.mark.asyncio
async def test_plan_node_passes_user_query_in_human_message(sample_state, stub_driver_plan, mock_llm_response):
    """plan_node must include the user_query in the HumanMessage passed to the LLM."""
    with patch("src.workflow.nodes.plan.get_llm", return_value=mock_llm_response), \
         patch("src.workflow.nodes.plan.normalize_roster", new_callable=AsyncMock,
               return_value=["Aldo", "Ciel"]), \
         patch("src.workflow.nodes.plan.augment_with_f2p", return_value=["Aldo", "Ciel"]):
        await plan_node(sample_state, stub_driver_plan)

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


@pytest.mark.asyncio
async def test_plan_node_passes_roster_in_human_message(sample_state, stub_driver_plan, mock_llm_response):
    """plan_node must include full_roster character names in the HumanMessage."""
    full_roster = ["Aldo", "Ciel", "Feinne"]
    with patch("src.workflow.nodes.plan.get_llm", return_value=mock_llm_response), \
         patch("src.workflow.nodes.plan.normalize_roster", new_callable=AsyncMock,
               return_value=["Aldo", "Ciel"]), \
         patch("src.workflow.nodes.plan.augment_with_f2p", return_value=full_roster):
        await plan_node(sample_state, stub_driver_plan)

    call_args = mock_llm_response.invoke.call_args
    messages = call_args[0][0]

    from langchain_core.messages import HumanMessage
    human_messages = [m for m in messages if isinstance(m, HumanMessage)]
    assert len(human_messages) == 1

    human_content = human_messages[0].content
    for character in full_roster:
        assert character in human_content, (
            f"Roster character '{character}' not found in HumanMessage"
        )


@pytest.mark.asyncio
async def test_plan_node_uses_system_message(sample_state, stub_driver_plan, mock_llm_response):
    """plan_node must include a SystemMessage with graph traversal instructions."""
    with patch("src.workflow.nodes.plan.get_llm", return_value=mock_llm_response), \
         patch("src.workflow.nodes.plan.normalize_roster", new_callable=AsyncMock,
               return_value=["Aldo"]), \
         patch("src.workflow.nodes.plan.augment_with_f2p", return_value=["Aldo"]):
        await plan_node(sample_state, stub_driver_plan)

    call_args = mock_llm_response.invoke.call_args
    messages = call_args[0][0]

    from langchain_core.messages import SystemMessage
    system_messages = [m for m in messages if isinstance(m, SystemMessage)]
    assert len(system_messages) == 1, "Expected exactly one SystemMessage"
    # System prompt must instruct on decomposing into graph traversal sub-goals
    assert len(system_messages[0].content) > 0, "SystemMessage must not be empty"


@pytest.mark.asyncio
async def test_plan_node_normalizes_roster_and_augments_f2p(sample_state, stub_driver_plan, mock_llm_response):
    """plan_node calls normalize_roster then augment_with_f2p and returns augmented roster."""
    normalized = ["Aldo", "Ciel"]
    augmented = ["Aldo", "Ciel", "Feinne", "Cyrus"]
    with patch("src.workflow.nodes.plan.get_llm", return_value=mock_llm_response), \
         patch("src.workflow.nodes.plan.normalize_roster", new_callable=AsyncMock,
               return_value=normalized) as mock_norm, \
         patch("src.workflow.nodes.plan.augment_with_f2p", return_value=augmented) as mock_aug:
        result = await plan_node(sample_state, stub_driver_plan)

    mock_norm.assert_called_once_with(stub_driver_plan, sample_state["roster"])
    mock_aug.assert_called_once_with(normalized)
    assert result["roster"] == augmented


@pytest.mark.asyncio
async def test_plan_node_lowercase_roster_name_normalized(sample_state, stub_driver_plan, mock_llm_response):
    """plan_node normalizes lowercase 'aldo' in roster to canonical 'Aldo' via normalize_roster."""
    state_with_lowercase = dict(sample_state)
    state_with_lowercase["roster"] = ["aldo", "ciel"]
    normalized = ["Aldo", "Ciel"]

    with patch("src.workflow.nodes.plan.get_llm", return_value=mock_llm_response), \
         patch("src.workflow.nodes.plan.normalize_roster", new_callable=AsyncMock,
               return_value=normalized) as mock_norm, \
         patch("src.workflow.nodes.plan.augment_with_f2p", return_value=normalized):
        result = await plan_node(state_with_lowercase, stub_driver_plan)

    mock_norm.assert_called_once_with(stub_driver_plan, ["aldo", "ciel"])
    assert "Aldo" in result["roster"]
    assert "Ciel" in result["roster"]
