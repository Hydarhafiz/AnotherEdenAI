"""LangGraph StateGraph wiring for the AnotherEdenAI workflow.

Graph topology:
    START -> plan -> superboss_context -> generate_cypher -> validate
      validate success -> prepare_candidates -> analyze -> format -> END
      validate retry   -> generate_cypher
      retry cap        -> format classified retrieval failure -> END

Candidate preparation is the hard-field authority. ANALYZE may make one initial
selection call and at most two correction calls; FORMAT retains only legal lineups.
"""
from typing import Literal

from langgraph.graph import END, START, StateGraph

from .candidates import prepare_candidates_node
from .nodes.analyze import analyze_node
from .nodes.cypher import generate_cypher_node
from .nodes.format import format_and_validate_node
from .nodes.plan import plan_node
from .superboss import retrieve_superboss_context_node
from .nodes.validate import validate_node
from .state import WorkflowState


def route_after_validate(
    state: WorkflowState,
) -> Literal["generate_cypher", "prepare_candidates", "format"]:
    """Route success through candidates and exhausted retrieval to failure.

    Non-empty results proceed to deterministic candidate preparation. Failed
    retrieval retries Cypher up to the existing cap; exhausted retrieval bypasses
    unconstrained alternatives and is classified by FORMAT.
    """
    if state.get("db_results"):
        return "prepare_candidates"
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
    async def _superboss_context(s):
        return await retrieve_superboss_context_node(s, driver)

    builder.add_node("superboss_context", _superboss_context)
    builder.add_node("generate_cypher", generate_cypher_node)
    # validate_node is async — use an async wrapper so LangGraph awaits it correctly.
    async def _validate(s):
        return await validate_node(s, driver)

    builder.add_node("validate", _validate)
    async def _prepare_candidates(s):
        return await prepare_candidates_node(s, driver)

    builder.add_node("prepare_candidates", _prepare_candidates)
    builder.add_node("analyze", analyze_node)
    async def _format(s):
        return await format_and_validate_node(s, driver)

    builder.add_node("format", _format)

    # --- Add edges ---
    builder.add_edge(START, "plan")
    builder.add_edge("plan", "superboss_context")
    builder.add_edge("superboss_context", "generate_cypher")
    builder.add_edge("generate_cypher", "validate")
    builder.add_edge("prepare_candidates", "analyze")
    builder.add_edge("analyze", "format")
    builder.add_edge("format", END)

    # --- Conditional edge from validate ---
    builder.add_conditional_edges(
        "validate",
        route_after_validate,
        ["generate_cypher", "prepare_candidates", "format"],
    )

    return builder.compile()


# Module-level compiled graph (driver=None for stub/test use).
# Subsequent plans replace stub nodes with real implementations.
compiled_graph = build_graph()
