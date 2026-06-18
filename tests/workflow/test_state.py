"""Tests for WorkflowState TypedDict definition.

Covers AGENT-07: State contract verification.
- Correct number and names of keys
- validation_errors uses operator.add reducer (Annotated)
- Each node returns only its owned keys (LLM nodes are mocked)
"""
import operator
import typing
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage

from src.workflow.state import WorkflowState
from src.workflow.nodes.plan import plan_node
from src.workflow.nodes.cypher import generate_cypher_node
from src.workflow.nodes.validate import validate_node
from src.workflow.nodes.analyze import analyze_node
from src.workflow.nodes.format import format_node


EXPECTED_KEYS = {
    "user_query",
    "roster",
    "owned_sidekicks",
    "plan_strategy",
    "boss_context",
    "cypher_query",
    "db_results",
    "validation_errors",
    "retry_count",
    "analysis_result",
    "alternatives",
    "final_output",
}


def test_workflow_state_has_all_keys():
    """WorkflowState must define the expected graph state keys."""
    hints = typing.get_type_hints(WorkflowState)
    assert set(hints.keys()) == EXPECTED_KEYS, (
        f"Key mismatch. Expected: {EXPECTED_KEYS}. Got: {set(hints.keys())}"
    )


def test_validation_errors_reducer_is_annotated():
    """validation_errors must use operator.add as its Annotated reducer."""
    hints = typing.get_type_hints(WorkflowState, include_extras=True)
    annotation = hints["validation_errors"]

    # Must be Annotated
    assert typing.get_origin(annotation) is typing.Annotated, (
        "validation_errors must be Annotated[list[str], operator.add]"
    )

    # Metadata must include operator.add
    metadata = typing.get_args(annotation)[1:]
    assert operator.add in metadata, (
        f"validation_errors Annotated metadata must include operator.add. Got: {metadata}"
    )


@pytest.mark.asyncio
async def test_stub_nodes_return_only_owned_keys(sample_state):
    """Each node must return only its owned keys — no side effects.

    LLM-backed nodes (plan, generate_cypher, validate) are mocked to avoid live API calls.
    validate uses an AsyncMock driver that returns data so the success path is exercised.
    validate_node is async (Phase 3) so this test is async and awaits it.
    """
    mock_driver = MagicMock()
    mock_driver.execute_query = AsyncMock(return_value=([{"name": "Aldo"}], None, None))

    # Mock LLM factory for nodes that call get_llm
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(content="stub response")

    # validate's Haiku mock returns PASS so the success path (db_results only) is taken
    mock_validate_llm = MagicMock()
    mock_validate_llm.invoke.return_value = AIMessage(content="PASS: Results match.")

    import json

    # analyze_node is a real LLM node — mock returns JSON the format_node can parse
    analyze_json_response = json.dumps({
        "frontline": [
            {"name": "Aldo", "role": "DPS", "grastas": []},
            {"name": "Ciel", "role": "support", "grastas": []},
            {"name": "Riica", "role": "healer", "grastas": []},
            {"name": "Shion", "role": "DPS", "grastas": []},
        ],
        "reserve": [
            {"name": "Miyu", "role": "support", "grastas": []},
            {"name": "Feinne", "role": "healer", "grastas": []},
        ],
        "synergy_explanation": "stub",
    })
    mock_analyze_llm = MagicMock()
    mock_analyze_llm.invoke.return_value = AIMessage(content=analyze_json_response)

    # format_node needs a valid analysis_result to parse (happy path)
    format_state = dict(sample_state)
    format_state["analysis_result"] = analyze_json_response
    format_state["db_results"] = [{"name": "Aldo"}]  # non-empty to avoid error path

    # analyze_node state needs non-empty db_results so it takes the normal path
    # (returning analysis_result, not alternatives)
    analyze_state = dict(sample_state)
    analyze_state["db_results"] = [{"name": "Aldo"}]

    with patch("src.workflow.nodes.plan.get_llm", return_value=mock_llm), \
         patch("src.workflow.nodes.plan.normalize_roster",
                new_callable=AsyncMock, return_value=["Aldo", "Ciel"]), \
         patch("src.workflow.nodes.plan.augment_with_f2p", return_value=["Aldo", "Ciel"]), \
         patch("src.workflow.nodes.cypher.get_llm", return_value=mock_llm), \
         patch("src.workflow.nodes.validate.get_llm", return_value=mock_validate_llm), \
         patch("src.workflow.nodes.analyze.get_llm", return_value=mock_analyze_llm):
        # plan_node is now async and returns plan_strategy plus normalized ownership inputs
        plan_result = await plan_node(sample_state, mock_driver)
        cases = [
            (plan_result,                                          {"plan_strategy", "roster", "owned_sidekicks"}),
            (generate_cypher_node(sample_state),                   {"cypher_query"}),
            (await validate_node(sample_state, mock_driver),       {"db_results"}),
            (analyze_node(analyze_state),                          {"analysis_result"}),
            (format_node(format_state),                            {"final_output"}),
        ]

    for result, expected_keys in cases:
        assert set(result.keys()) == expected_keys, (
            f"Node returned unexpected keys. Expected: {expected_keys}. Got: {set(result.keys())}"
        )
