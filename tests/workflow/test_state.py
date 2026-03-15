"""Tests for WorkflowState TypedDict definition.

Covers AGENT-07: State contract verification.
- Correct number and names of keys
- validation_errors uses operator.add reducer (Annotated)
- Each stub node returns only its owned keys
"""
import operator
import typing

import pytest

from src.workflow.state import WorkflowState
from src.workflow.nodes.plan import plan_node
from src.workflow.nodes.cypher import generate_cypher_node
from src.workflow.nodes.validate import validate_node
from src.workflow.nodes.analyze import analyze_node
from src.workflow.nodes.format import format_node


EXPECTED_KEYS = {
    "user_query",
    "roster",
    "plan_strategy",
    "cypher_query",
    "db_results",
    "validation_errors",
    "retry_count",
    "analysis_result",
    "final_output",
}


def test_workflow_state_has_all_keys():
    """WorkflowState must define exactly 9 keys."""
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


def test_stub_nodes_return_only_owned_keys(sample_state):
    """Each stub node must return only its owned keys — no side effects."""
    mock_driver = None  # validate stub handles None driver

    cases = [
        (plan_node(sample_state),               {"plan_strategy"}),
        (generate_cypher_node(sample_state),    {"cypher_query"}),
        (validate_node(sample_state, mock_driver), {"db_results"}),
        (analyze_node(sample_state),            {"analysis_result"}),
        (format_node(sample_state),             {"final_output"}),
    ]

    for result, expected_keys in cases:
        assert set(result.keys()) == expected_keys, (
            f"Node returned unexpected keys. Expected: {expected_keys}. Got: {set(result.keys())}"
        )
