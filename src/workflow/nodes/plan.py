"""PLAN node — decomposes the user query into graph traversal sub-goals.

Calls get_llm(role='planner') from src.workflow.llm.
Returns: {"plan_strategy": str, "roster": list[str]}

Roster is normalized (canonical graph names) and augmented with F2P characters
before the LLM prompt is built.
"""
from langchain_core.messages import HumanMessage, SystemMessage

from ..legality import normalize_sidekicks
from ..llm import get_llm
from ..normalize import normalize_roster
from ..f2p import augment_with_f2p
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


async def plan_node(state: WorkflowState, driver) -> dict:
    """Generate a traversal strategy for the user's team-building query.

    Normalizes player-supplied roster names to canonical graph names, augments
    the roster with F2P characters, then calls the LLM planner.

    Owned keys: plan_strategy, roster

    Args:
        state: Current WorkflowState containing user_query and roster.
        driver: Async Neo4j driver for name normalization queries.

    Returns:
        Dict containing {"plan_strategy": str, "roster": list[str]} where
        roster is the normalized + F2P-augmented canonical name list.
    """
    # Step 1: normalize user-supplied names to canonical graph names
    normalized = await normalize_roster(driver, state["roster"])
    # Step 2: augment with F2P characters (deduped)
    full_roster = augment_with_f2p(normalized)
    owned_sidekicks = await normalize_sidekicks(driver, state.get("owned_sidekicks", []))

    llm = get_llm(role="planner")

    roster_str = ", ".join(full_roster) if full_roster else "no characters specified"
    sidekick_str = ", ".join(owned_sidekicks) if owned_sidekicks else "no sidekicks selected"
    human_content = (
        f"Query: {state['user_query']}\n"
        f"Available roster: {roster_str}\n"
        f"Owned sidekicks: {sidekick_str}"
    )

    messages = [
        SystemMessage(content=PLAN_SYSTEM_PROMPT),
        HumanMessage(content=human_content),
    ]

    response = llm.invoke(messages)
    return {"plan_strategy": response.content, "roster": full_roster, "owned_sidekicks": owned_sidekicks}
