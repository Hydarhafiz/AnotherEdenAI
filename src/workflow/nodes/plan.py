"""PLAN node — decomposes the user query into graph traversal sub-goals.

Calls get_llm(role='planner') from src.workflow.llm.
Returns only: {"plan_strategy": str}
"""
from langchain_core.messages import HumanMessage, SystemMessage

from ..llm import get_llm
from ..state import WorkflowState

PLAN_SYSTEM_PROMPT = """You are a strategy planner for an AnotherEden character team-building assistant.

Given a user's team-building query and their available roster, decompose the request into
concrete graph traversal sub-goals that will be used to generate a Neo4j Cypher query.

Your output should identify:
1. Which elements, weapons, or personality traits are required
2. Which Character-Trait-Grasta paths to explore in the graph
3. Whether grastas need to be shareable or restricted to specific characters
4. Any roster constraints (only characters the player owns are valid)

Focus on STRATEGY DECOMPOSITION — do not write Cypher queries yourself.
Output a structured breakdown of what graph data to retrieve to answer the question.
Be concise and specific."""


def plan_node(state: WorkflowState) -> dict:
    """Generate a traversal strategy for the user's team-building query.

    Owned keys: plan_strategy

    Args:
        state: Current WorkflowState containing user_query and roster.

    Returns:
        Dict containing only {"plan_strategy": str}.
    """
    llm = get_llm(role="planner")

    roster_str = ", ".join(state["roster"]) if state["roster"] else "no characters specified"
    human_content = (
        f"Query: {state['user_query']}\n"
        f"Available roster: {roster_str}"
    )

    messages = [
        SystemMessage(content=PLAN_SYSTEM_PROMPT),
        HumanMessage(content=human_content),
    ]

    response = llm.invoke(messages)
    return {"plan_strategy": response.content}
