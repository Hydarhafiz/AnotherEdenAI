"""LangGraph StateGraph wiring for the AnotherEdenAI workflow.

Graph topology:
    START -> plan -> generate_cypher -> validate --(conditional)--> analyze -> format -> END
                                            |
                                            +--> generate_cypher  (retry, retry_count < 3)
                                            |
                                            +--> format           (retry cap exhausted, retry_count >= 3)

Conditional routing after validate (route_after_validate):
    db_results non-empty  -> "analyze"          (success path)
    retry_count >= 3      -> "format"           (retry cap — error output)
    otherwise             -> "generate_cypher"  (retry)
"""
from typing import Literal

from langgraph.graph import END, START, StateGraph

from .nodes.analyze import analyze_node
from .nodes.cypher import generate_cypher_node
from .nodes.format import format_node
from .nodes.plan import plan_node
from .nodes.validate import validate_node
from .state import WorkflowState


def route_after_validate(
    state: WorkflowState,
) -> Literal["generate_cypher", "analyze", "format"]:
    """Determine which node to visit after VALIDATE.

    Logic:
        - db_results non-empty -> "analyze"         (query succeeded)
        - retry_count >= 3    -> "format"            (retry cap exhausted)
        - otherwise           -> "generate_cypher"   (retry with new query)

    Note: VALIDATE only writes db_results on success (non-empty list) and only
    increments retry_count on failure. Since db_results has no reducer (overwrites),
    and the flow never returns to VALIDATE after routing to ANALYZE, db_results is
    either [] (never succeeded) or non-empty (just succeeded).

    Args:
        state: Current WorkflowState after VALIDATE has run.

    Returns:
        One of "generate_cypher", "analyze", or "format".
    """
    if state.get("db_results"):
        return "analyze"
    if state.get("retry_count", 0) >= 3:
        return "format"
    return "generate_cypher"


def build_graph(driver=None):
    """Build and compile the AnotherEdenAI StateGraph.

    Args:
        driver: Neo4j driver instance. Injected into validate_node via closure.
                Pass None for stub/test use (stub node ignores driver).

    Returns:
        A compiled LangGraph CompiledStateGraph ready to invoke.
    """
    builder = StateGraph(WorkflowState)

    # --- Add nodes ---
    # plan_node is async — use an async wrapper so LangGraph awaits it correctly.
    async def _plan(s):
        return await plan_node(s, driver)

    builder.add_node("plan", _plan)
    builder.add_node("generate_cypher", generate_cypher_node)
    # validate_node is async — use an async wrapper so LangGraph awaits it correctly.
    async def _validate(s):
        return await validate_node(s, driver)

    builder.add_node("validate", _validate)
    builder.add_node("analyze", analyze_node)
    builder.add_node("format", format_node)

    # --- Add edges ---
    builder.add_edge(START, "plan")
    builder.add_edge("plan", "generate_cypher")
    builder.add_edge("generate_cypher", "validate")
    builder.add_edge("analyze", "format")
    builder.add_edge("format", END)

    # --- Conditional edge from validate ---
    builder.add_conditional_edges(
        "validate",
        route_after_validate,
        ["generate_cypher", "analyze", "format"],
    )

    return builder.compile()


# Module-level compiled graph (driver=None for stub/test use).
# Subsequent plans replace stub nodes with real implementations.
compiled_graph = build_graph()
