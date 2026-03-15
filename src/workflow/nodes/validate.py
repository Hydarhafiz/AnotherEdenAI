"""VALIDATE node — executes the Cypher query against Neo4j and validates results.

Stub implementation: returns placeholder db_results.
Real implementation added in plan 02-03.

The driver is injected via closure in graph.py:
    builder.add_node("validate", lambda s: validate_node(s, driver))
"""
from ..state import WorkflowState


def validate_node(state: WorkflowState, driver) -> dict:
    """Execute the Cypher query and validate the results.

    Owned keys: db_results, validation_errors, retry_count

    Args:
        state: Current WorkflowState.
        driver: Neo4j driver instance (injected via closure).

    Returns:
        Dict containing only db_results (validation_errors and retry_count
        are updated via Annotated reducer and direct assignment respectively).
    """
    return {"db_results": [{"stub": True}]}
