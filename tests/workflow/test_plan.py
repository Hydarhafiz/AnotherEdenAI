"""Placeholder tests for the PLAN node.

Full tests added in plan 02-02 when LLM logic is implemented.
"""
from src.workflow.nodes.plan import plan_node


def test_plan_node_exists():
    """plan_node must be importable and callable."""
    assert callable(plan_node)
