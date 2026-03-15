"""FORMAT node — produces the final structured recommendation from analysis.

Stub implementation: returns placeholder final_output.
If the retry cap was exhausted (retry_count >= 3 with no db_results),
includes an "error" key to signal the failure path.

Real LLM implementation added in plan 02-04.
"""
from ..state import WorkflowState


def format_node(state: WorkflowState) -> dict:
    """Format the analysis into a structured team recommendation.

    Owned keys: final_output

    When the retry cap is exhausted (retry_count >= 3 and no db_results),
    returns an error structure instead of a normal recommendation.

    Args:
        state: Current WorkflowState.

    Returns:
        Dict containing only final_output.
    """
    retry_count = state.get("retry_count", 0)
    db_results = state.get("db_results", [])

    # Retry cap exhausted — return error structure
    if retry_count >= 3 and not db_results:
        return {
            "final_output": {
                "frontline": [],
                "reserve": [],
                "synergy_explanation": "",
                "error": "Query failed after 3 retries. No results found.",
            }
        }

    return {
        "final_output": {
            "frontline": [],
            "reserve": [],
            "synergy_explanation": "stub",
        }
    }
