"""GENERATE_CYPHER node — translates plan strategy into a Neo4j Cypher query.

Stub implementation: returns a placeholder Cypher query.
Real LLM implementation added in plan 02-02.
"""
from ..state import WorkflowState


def generate_cypher_node(state: WorkflowState) -> dict:
    """Generate a Cypher query based on the plan strategy.

    Owned keys: cypher_query

    Args:
        state: Current WorkflowState.

    Returns:
        Dict containing only cypher_query.
    """
    return {"cypher_query": "MATCH (n) RETURN n"}
