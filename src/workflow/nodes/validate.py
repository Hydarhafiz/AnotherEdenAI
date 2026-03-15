"""VALIDATE node — executes the Cypher query against Neo4j and validates results.

Stub implementation: calls driver.execute_query() and handles success/failure
routing based on whether results are returned.

Real implementation with full error handling added in plan 02-03.

The driver is injected via closure in graph.py:
    builder.add_node("validate", lambda s: validate_node(s, driver))
"""
from ..state import WorkflowState


def validate_node(state: WorkflowState, driver) -> dict:
    """Execute the Cypher query and validate the results.

    Owned keys: db_results, validation_errors, retry_count

    On success (non-empty results): returns db_results, leaves retry_count unchanged.
    On failure (empty results):     increments retry_count, appends to validation_errors.

    Args:
        state: Current WorkflowState.
        driver: Neo4j driver instance (injected via closure).

    Returns:
        Dict with owned keys updated based on query outcome.
    """
    cypher = state.get("cypher_query", "MATCH (n) RETURN n")
    current_retry = state.get("retry_count", 0)

    if driver is None:
        # No driver available — treat as success with stub data
        return {"db_results": [{"stub": True}]}

    records, _, _ = driver.execute_query(cypher)

    if records:
        return {"db_results": list(records)}
    else:
        return {
            "db_results": [],
            "validation_errors": [f"Query returned no results (attempt {current_retry + 1})"],
            "retry_count": current_retry + 1,
        }
