"""Unit tests for the GENERATE_CYPHER node.

All tests use mocked LLM via unittest.mock.patch on src.workflow.nodes.cypher.get_llm.
No live API calls are made.
"""
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage

from src.workflow.nodes.cypher import LINEUP_RECOMMENDATION_QUERY, generate_cypher_node


@pytest.fixture
def mock_llm_cypher():
    """Return a MagicMock LLM whose invoke() returns a predictable Cypher query."""
    llm = MagicMock()
    llm.invoke.return_value = AIMessage(
        content="MATCH (c:Character {element: 'Fire'})-[:HAS_TRAIT]->(t:Trait) RETURN c.name, t.name"
    )
    return llm


@pytest.fixture
def state_with_plan(sample_state):
    """Sample state with plan_strategy populated."""
    return {
        **sample_state,
        "plan_strategy": "Find fire characters and their traits, then find attack grastas requiring those traits",
    }


def test_cypher_node_returns_only_cypher_query(state_with_plan, mock_llm_cypher):
    """generate_cypher_node must return a dict with exactly one key: cypher_query."""
    with patch("src.workflow.nodes.cypher.get_llm", return_value=mock_llm_cypher):
        result = generate_cypher_node(state_with_plan)

    assert list(result.keys()) == ["cypher_query"], (
        f"Expected only ['cypher_query'], got {list(result.keys())}"
    )


def test_cypher_node_uses_get_llm_with_cypher_role(state_with_plan, mock_llm_cypher):
    """generate_cypher_node must call get_llm(role='cypher') — not ChatAnthropic directly."""
    with patch("src.workflow.nodes.cypher.get_llm", return_value=mock_llm_cypher) as mock_factory:
        generate_cypher_node(state_with_plan)

    mock_factory.assert_called_once_with(role="cypher")


def test_cypher_node_injects_schema(state_with_plan, mock_llm_cypher):
    """SystemMessage must include graph schema labels and relationship types."""
    with patch("src.workflow.nodes.cypher.get_llm", return_value=mock_llm_cypher):
        generate_cypher_node(state_with_plan)

    call_args = mock_llm_cypher.invoke.call_args
    messages = call_args[0][0]

    from langchain_core.messages import SystemMessage
    system_messages = [m for m in messages if isinstance(m, SystemMessage)]
    assert len(system_messages) == 1, "Expected exactly one SystemMessage"

    system_content = system_messages[0].content
    # Must include all node labels
    for label in ["Character", "Grasta", "Trait", "Ore"]:
        assert label in system_content, (
            f"Schema label '{label}' not found in SystemMessage"
        )
    # Must include relationship types
    for rel in ["HAS_TRAIT", "REQUIRES_TRAIT"]:
        assert rel in system_content, (
            f"Relationship type '{rel}' not found in SystemMessage"
        )


def test_cypher_node_includes_few_shot_examples(state_with_plan, mock_llm_cypher):
    """SystemMessage must include at least one MATCH example (few-shot Cypher)."""
    with patch("src.workflow.nodes.cypher.get_llm", return_value=mock_llm_cypher):
        generate_cypher_node(state_with_plan)

    call_args = mock_llm_cypher.invoke.call_args
    messages = call_args[0][0]

    from langchain_core.messages import SystemMessage
    system_messages = [m for m in messages if isinstance(m, SystemMessage)]
    system_content = system_messages[0].content

    assert "MATCH" in system_content, "SystemMessage must include at least one MATCH few-shot example"


def test_cypher_node_includes_constraints(state_with_plan, mock_llm_cypher):
    """SystemMessage must include the constraint notes (no ENHANCES, Ore standalone, VC no REQUIRES_TRAIT)."""
    with patch("src.workflow.nodes.cypher.get_llm", return_value=mock_llm_cypher):
        generate_cypher_node(state_with_plan)

    call_args = mock_llm_cypher.invoke.call_args
    messages = call_args[0][0]

    from langchain_core.messages import SystemMessage
    system_messages = [m for m in messages if isinstance(m, SystemMessage)]
    system_content = system_messages[0].content

    assert "ENHANCES" in system_content, "SystemMessage must mention ENHANCES constraint"
    assert "Ore" in system_content, "SystemMessage must mention Ore standalone note"
    assert "VC" in system_content, "SystemMessage must mention VC no REQUIRES_TRAIT constraint"


def test_cypher_node_includes_feature_c_retrieval_tags(state_with_plan, mock_llm_cypher):
    """Feature C: prompts expose effect tags with derivation clarity, not exact damage math."""
    with patch("src.workflow.nodes.cypher.get_llm", return_value=mock_llm_cypher):
        generate_cypher_node(state_with_plan)

    call_args = mock_llm_cypher.invoke.call_args
    messages = call_args[0][0]

    from langchain_core.messages import SystemMessage
    system_messages = [m for m in messages if isinstance(m, SystemMessage)]
    system_content = system_messages[0].content

    assert "effect_tags" in system_content
    assert "effect_tag_derivation" in system_content
    assert "'combat:af' IN g.effect_tags" in system_content
    assert "'stat:spd' IN o.effect_tags" in system_content
    assert "not exact damage math" in system_content


def test_cypher_node_includes_plan_strategy(state_with_plan, mock_llm_cypher):
    """HumanMessage must include the plan_strategy from state."""
    with patch("src.workflow.nodes.cypher.get_llm", return_value=mock_llm_cypher):
        generate_cypher_node(state_with_plan)

    call_args = mock_llm_cypher.invoke.call_args
    messages = call_args[0][0]

    from langchain_core.messages import HumanMessage
    human_messages = [m for m in messages if isinstance(m, HumanMessage)]
    assert len(human_messages) == 1, "Expected exactly one HumanMessage"

    assert state_with_plan["plan_strategy"] in human_messages[0].content, (
        "plan_strategy not found in HumanMessage"
    )


def test_cypher_node_includes_validation_errors_on_retry(sample_state, mock_llm_cypher):
    """When validation_errors is non-empty, HumanMessage must include the error history."""
    state_with_errors = {
        **sample_state,
        "plan_strategy": "find fire characters",
        "validation_errors": ["Attempt 1: Unknown relationship type ENHANCES"],
    }
    with patch("src.workflow.nodes.cypher.get_llm", return_value=mock_llm_cypher):
        generate_cypher_node(state_with_errors)

    call_args = mock_llm_cypher.invoke.call_args
    messages = call_args[0][0]

    from langchain_core.messages import HumanMessage
    human_messages = [m for m in messages if isinstance(m, HumanMessage)]
    assert len(human_messages) == 1

    human_content = human_messages[0].content
    assert "Attempt 1: Unknown relationship type ENHANCES" in human_content, (
        "validation_errors not included in HumanMessage for retry"
    )


def test_cypher_node_no_validation_errors_omits_error_section(state_with_plan, mock_llm_cypher):
    """When validation_errors is empty, the error section is not included in the prompt."""
    with patch("src.workflow.nodes.cypher.get_llm", return_value=mock_llm_cypher):
        generate_cypher_node(state_with_plan)

    call_args = mock_llm_cypher.invoke.call_args
    messages = call_args[0][0]

    from langchain_core.messages import HumanMessage
    human_messages = [m for m in messages if isinstance(m, HumanMessage)]
    human_content = human_messages[0].content

    assert "Previous errors" not in human_content, (
        "Error section should not appear when validation_errors is empty"
    )


def test_cypher_node_strips_markdown_fences(state_with_plan):
    """Markdown code fences must be stripped from LLM output."""
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(
        content="```cypher\nMATCH (n) RETURN n\n```"
    )

    with patch("src.workflow.nodes.cypher.get_llm", return_value=mock_llm):
        result = generate_cypher_node(state_with_plan)

    assert result["cypher_query"] == "MATCH (n) RETURN n", (
        f"Expected stripped Cypher, got: {result['cypher_query']!r}"
    )


def test_cypher_node_strips_plain_fences(state_with_plan):
    """Plain ``` code fences (without language tag) must also be stripped."""
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(
        content="```\nMATCH (c:Character) RETURN c.name\n```"
    )

    with patch("src.workflow.nodes.cypher.get_llm", return_value=mock_llm):
        result = generate_cypher_node(state_with_plan)

    assert result["cypher_query"] == "MATCH (c:Character) RETURN c.name", (
        f"Expected stripped Cypher, got: {result['cypher_query']!r}"
    )


def test_boss_lineup_query_uses_broad_deterministic_roster_retrieval(sample_state):
    """Feature D: boss lineup requests must not be narrowed into empty exact-match filters."""
    state = {
        **sample_state,
        "user_query": "Create a lineup to defeat Mimi",
        "plan_strategy": "Find Thunder magic attackers with narrow trait filters",
    }

    with patch("src.workflow.nodes.cypher.get_llm") as mock_get_llm:
        result = generate_cypher_node(state)

    mock_get_llm.assert_not_called()
    assert result == {"cypher_query": LINEUP_RECOMMENDATION_QUERY}
    query = result["cypher_query"]
    assert "c.name IN $roster" in query
    assert "HAS_SKILL" in query
    assert "HAS_PASSIVE_SKILL" in query
    assert "Superboss" in query
    assert "$user_query" in query
    assert "c.element = 'Thunder'" not in query
    assert "c.weapon = 'Staff'" not in query
