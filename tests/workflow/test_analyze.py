"""Placeholder tests for the ANALYZE node.

Full tests added in plan 02-04 when LLM logic is implemented.
"""
from src.workflow.nodes.analyze import analyze_node


def test_analyze_node_exists():
    """analyze_node must be importable and callable."""
    assert callable(analyze_node)
