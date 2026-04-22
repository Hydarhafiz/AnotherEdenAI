"""ANALYZE node — synthesizes query results into a team recommendation via Sonnet 4.6.

Reads db_results, user_query, roster, and plan_strategy from WorkflowState.
Returns only: {"analysis_result": str}

The analysis_result is a raw string from the LLM, intended to be a JSON object
with the team recommendation structure that FORMAT will parse and validate.
"""
from langchain_core.messages import HumanMessage, SystemMessage

from ..llm import get_llm
from ..state import WorkflowState

ANALYZE_SYSTEM_PROMPT = """You are an AnotherEden team-building expert analyzing graph query results.

Given the database results from a Neo4j character graph and the user's team query,
synthesize an optimal team recommendation.

Output a JSON object with EXACTLY this structure:
{
  "frontline": [
    {"name": "<character_name>", "role": "<role>", "grastas": ["<grasta_name>", ...]},
    ...
  ],
  "reserve": [
    {"name": "<character_name>", "role": "<role>", "grastas": ["<grasta_name>", ...]},
    ...
  ],
  "synergy_explanation": "<explanation of grasta and role synergies>"
}

Rules:
- ONLY use characters present in the db_results AND the player's roster
- Assign meaningful roles: AF anchor, healer, DPS, support, buffer, debuffer
- frontline MUST contain exactly 4 characters (minimum 3 only if roster/db_results cannot supply 4)
- reserve MUST contain exactly 2 characters (minimum 1 only if roster/db_results cannot supply 2)
- Explain Grasta synergies specifically (e.g. "Fire T3 boosts AF damage by 30%")
- Output ONLY the JSON object — no preamble, no markdown fences"""


def analyze_node(state: WorkflowState) -> dict:
    """Synthesize db_results into a team recommendation using Sonnet 4.6.

    Owned keys: analysis_result

    Reads:
        db_results    — Neo4j query results (list of dicts)
        user_query    — original user question
        roster        — player's available characters
        plan_strategy — PLAN node's traversal strategy

    Returns:
        Dict containing only {"analysis_result": str}.
        The value is the raw LLM response content (expected JSON string).
    """
    llm = get_llm(role="analyzer")

    db_results = state.get("db_results", [])
    user_query = state.get("user_query", "")
    roster = state.get("roster", [])
    plan_strategy = state.get("plan_strategy", "")

    roster_str = ", ".join(roster) if roster else "no characters specified"

    human_content = (
        f"User query: {user_query}\n"
        f"Player roster: {roster_str}\n"
        f"Traversal strategy: {plan_strategy}\n"
        f"Database results:\n{db_results}"
    )

    messages = [
        SystemMessage(content=ANALYZE_SYSTEM_PROMPT),
        HumanMessage(content=human_content),
    ]

    response = llm.invoke(messages)
    return {"analysis_result": response.content}
