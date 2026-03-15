"""ANALYZE node — synthesizes the query results into a natural-language analysis.

Stub implementation: returns placeholder analysis_result.
Real LLM implementation added in plan 02-04.
"""
from ..state import WorkflowState


def analyze_node(state: WorkflowState) -> dict:
    """Analyze the database results and produce a synthesis.

    Owned keys: analysis_result

    Args:
        state: Current WorkflowState.

    Returns:
        Dict containing only analysis_result.
    """
    return {"analysis_result": "stub analysis"}
