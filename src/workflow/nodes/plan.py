"""PLAN node — generates a query strategy from the user request.

Stub implementation: returns placeholder plan_strategy.
Real LLM implementation added in plan 02-02.
"""
from ..state import WorkflowState


def plan_node(state: WorkflowState) -> dict:
    """Generate a plan/strategy for answering the user query.

    Owned keys: plan_strategy

    Args:
        state: Current WorkflowState.

    Returns:
        Dict containing only plan_strategy.
    """
    return {"plan_strategy": "stub"}
