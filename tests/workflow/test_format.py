"""Placeholder tests for the FORMAT node.

Full tests added in plan 02-04 when LLM logic is implemented.
"""
from src.workflow.nodes.format import format_node


def test_format_node_exists():
    """format_node must be importable and callable."""
    assert callable(format_node)
