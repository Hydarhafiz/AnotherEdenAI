"""Placeholder tests for the VALIDATE node.

Full tests added in plan 02-03 when real driver integration is implemented.
"""
from src.workflow.nodes.validate import validate_node


def test_validate_node_exists():
    """validate_node must be importable and callable."""
    assert callable(validate_node)
