"""FORMAT node — produces the final structured recommendation from analysis.

Stub implementation: returns placeholder final_output.
Real LLM implementation added in plan 02-04.
"""
from ..state import WorkflowState


def format_node(state: WorkflowState) -> dict:
    """Format the analysis into a structured team recommendation.

    Owned keys: final_output

    Args:
        state: Current WorkflowState.

    Returns:
        Dict containing only final_output.
    """
    return {
        "final_output": {
            "frontline": [],
            "reserve": [],
            "synergy_explanation": "stub",
        }
    }
