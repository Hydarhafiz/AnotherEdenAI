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
- Output ONLY the JSON object — no preamble, no markdown fences

MANDATORY SOURCE ATTRIBUTION (per D-13):
For each character in frontline and reserve, the synergy_explanation MUST cite:
  [CharacterName]: [Grasta name] ([trait name]) — [effect description]
Example: "Aldo: Fire T3 Grasta (Courage) — boosts Fire element damage by 30% in AF zone"
Never make a synergy claim without citing the Grasta and trait from the database results."""


ALTERNATIVES_SYSTEM_PROMPT = """You are an AnotherEden team-building expert.
No characters were found in the database for this query.
Using your knowledge of the Another Eden roster and the player's available characters,
suggest 3 alternative team compositions that address the query intent.

Output a JSON object with EXACTLY this structure:
{
  "alternatives": [
    {
      "frontline": [{"name": "...", "role": "...", "grastas": ["..."]}, ...],
      "reserve": [{"name": "...", "role": "...", "grastas": ["..."]}],
      "synergy_explanation": "..."
    },
    <second alternative>,
    <third alternative>
  ],
  "reason": "Why no database results were found and what the query attempted."
}

Rules:
- Output EXACTLY 3 alternative objects in the alternatives array — no more, no fewer.
- Each alternative must have frontline (3-4 characters) and reserve (1-2 characters).
- Only suggest characters from the player's roster.
- Include Grasta citations: [CharacterName]: [Grasta name] ([trait]) — [effect].
- Output ONLY the JSON object — no preamble, no markdown fences."""


def analyze_node(state: WorkflowState) -> dict:
    """Synthesize db_results into a team recommendation using Sonnet 4.6.

    Owned keys: analysis_result (normal path), alternatives (empty db_results path)

    Reads:
        db_results    — Neo4j query results (list of dicts)
        user_query    — original user question
        roster        — player's available characters
        plan_strategy — PLAN node's traversal strategy

    Returns:
        Normal path:       {"analysis_result": str} — raw LLM JSON string.
        Empty-results path: {"alternatives": str}   — raw LLM JSON string with 3 alternatives.
    """
    import logging
    logger = logging.getLogger(__name__)

    db_results = state.get("db_results", [])
    if not db_results:
        try:
            return _generate_alternatives(state)
        except Exception:
            logger.exception("_generate_alternatives failed — returning empty for format error path")
            return {}

    llm = get_llm(role="analyzer")

    user_query = state.get("user_query", "")
    roster = state.get("roster", [])
    plan_strategy = state.get("plan_strategy", "")
    boss_context = state.get("boss_context", "")

    roster_str = ", ".join(roster) if roster else "no characters specified"

    # Cap records to avoid exceeding free-tier model context/timeout limits
    MAX_RECORDS = 40
    trimmed = db_results[:MAX_RECORDS]
    trim_note = f" (truncated to {MAX_RECORDS} of {len(db_results)})" if len(db_results) > MAX_RECORDS else ""

    human_content = (
        f"User query: {user_query}\n"
        f"Player roster: {roster_str}\n"
        f"Traversal strategy: {plan_strategy}\n"
        f"Superboss mechanics context: {boss_context or 'none'}\n"
        f"Database results{trim_note}:\n{trimmed}"
    )

    messages = [
        SystemMessage(content=ANALYZE_SYSTEM_PROMPT),
        HumanMessage(content=human_content),
    ]

    response = llm.invoke(messages)
    return {"analysis_result": response.content}


def _generate_alternatives(state: WorkflowState) -> dict:
    """Generate 3 alternative team compositions when db_results is empty.

    Returns {"alternatives": str} — raw LLM JSON string; FORMAT parses this.
    Owned key: alternatives (WorkflowState key added Phase 5).
    """
    llm = get_llm(role="analyzer")
    roster_str = ", ".join(state.get("roster", [])) or "no characters specified"
    user_query = state.get("user_query", "")
    plan_strategy = state.get("plan_strategy", "")
    boss_context = state.get("boss_context", "")

    messages = [
        SystemMessage(content=ALTERNATIVES_SYSTEM_PROMPT),
        HumanMessage(content=(
            f"User query: {user_query}\n"
            f"Player roster: {roster_str}\n"
            f"Original traversal strategy: {plan_strategy}\n"
            f"Superboss mechanics context: {boss_context or 'none'}\n"
            "No database results were found. Generate EXACTLY 3 alternative team compositions."
        )),
    ]
    response = llm.invoke(messages)
    return {"alternatives": response.content}
