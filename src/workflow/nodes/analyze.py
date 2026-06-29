"""ANALYZE node — synthesizes query results into a team recommendation via Sonnet 4.6.

Reads db_results, user_query, roster, and plan_strategy from WorkflowState.
Returns only: {"analysis_result": str}

The analysis_result is a raw string from the LLM, intended to be a JSON object
with the team recommendation structure that FORMAT will parse and validate.
"""
import logging
from json import JSONDecodeError

from langchain_core.messages import HumanMessage, SystemMessage

from ..context_compaction import compact_records
from ..llm import get_llm
from ..state import WorkflowState


logger = logging.getLogger(__name__)
ANALYZER_TRANSPORT_ATTEMPTS = 2


def _invoke_analyzer(llm, messages):
    """Retry malformed provider response envelopes without retrying model output."""
    for attempt in range(1, ANALYZER_TRANSPORT_ATTEMPTS + 1):
        try:
            return llm.invoke(messages)
        except JSONDecodeError as exc:
            if attempt >= ANALYZER_TRANSPORT_ATTEMPTS:
                raise RuntimeError(
                    "Analyzer provider returned malformed JSON responses "
                    f"after {ANALYZER_TRANSPORT_ATTEMPTS} attempts"
                ) from exc
            logger.warning(
                "Analyzer provider returned malformed JSON response; retrying (%d/%d)",
                attempt + 1,
                ANALYZER_TRANSPORT_ATTEMPTS,
            )


ANALYZE_SYSTEM_PROMPT = """You are an AnotherEden team-building expert analyzing graph query results.

Given the database results from a Neo4j character graph and the user's team query,
synthesize the top three legal, source-grounded lineup recommendations.

Output a JSON object with EXACTLY this structure:
{
  "boss_affinity": {
    "weak": ["<element_or_attack_type>", ...],
    "resist": ["<element_or_attack_type>", ...],
    "null": ["<element_or_attack_type>", ...],
    "absorb": ["<element_or_attack_type>", ...]
  },
  "archetype_viability_notes": ["<why an archetype is strong or weaker if relevant>", ...],
  "recommendations": [
    {
      "archetype": "burst",
      "frontline": [
        {
          "name": "<character_name>",
          "role": "<role>",
          "weapon": "<one weapon assumption>",
          "armor": "<one armor assumption>",
          "grastas": ["<grasta_slot_1>", "<grasta_slot_2>", "<grasta_slot_3>"],
          "recommended_skills": ["<skill_name>", ...],
          "recommended_passives": ["<passive_name>", ...],
          "upgrade_assumptions": ["<SA_or_rare_setup_assumption>", ...]
        },
        ...
      ],
      "reserve": [
        {"name": "<character_name>", "role": "<role>", "weapon": "<one weapon assumption>", "armor": "<one armor assumption>", "grastas": ["<grasta_slot_1>", "<grasta_slot_2>", "<grasta_slot_3>"], "recommended_skills": [], "recommended_passives": [], "upgrade_assumptions": []},
        ...
      ],
      "main_sidekick": "<sidekick_name_or_null>",
      "sub_sidekick": "<sidekick_name_or_null>",
      "strategy_summary": "<compact default-view strategy>",
      "key_facts": ["<skill/passive/sidekick fact grounded in graph results>", ...],
      "build_notes": ["<late-game Grasta/Ore/equipment assumption>", ...],
      "boss_counterplay_notes": ["<boss mechanic or affinity counterplay>", ...],
      "sustain_mp_notes": ["<healing, mitigation, MP stability, or sustain note>", ...],
      "risks": ["<missing_or_uncertain_data_and_counterplay_risk>", ...],
      "fit_label": "high|medium|low",
      "confidence_label": "high|medium|low",
      "rubric_summary": {
        "offense": "high|medium|low - weakness coverage and affinity conflicts",
        "defense": "high|medium|low - mitigation, resistance, cleanse, or status handling",
        "synergy": "high|medium|low - role, zone, AF, buff/debuff, and placement fit",
        "sustain": "high|medium|low - healing, recovery, long-fight stability",
        "mp": "high|medium|low - MP sustainability",
        "sidekick": "high|medium|low - main/sub contribution",
        "build_readiness": "high|medium|low - Grasta/Ore/equipment assumptions",
        "upgrade_burden": "high|medium|low - SA or rare setup assumptions"
      },
      "citations": [{"label": "<boss_or_mechanic_fact>", "source_url": "<url>"}],
      "synergy_explanation": "<explanation of grasta, role, and counterplay synergies>"
    },
    {"archetype": "sustain", "...": "..."},
    {"archetype": "hybrid", "...": "..."}
  ]
}

Rules:
- Output EXACTLY 3 recommendation objects in recommendations.
- Prefer one burst, one sustain, and one hybrid lineup. If the boss strongly favors one archetype, output legal variants and explain why the weaker archetypes are weaker in archetype_viability_notes.
- ONLY use characters present in the db_results AND the player's roster
- Do not include not-owned alternative characters or pull-planning suggestions in active recommendations.
- Assign meaningful roles: AF anchor, healer, DPS, support, buffer, debuffer
- Each recommendation frontline MUST contain exactly 4 characters.
- Each recommendation reserve MUST contain exactly 2 characters.
- Do not duplicate heroes between frontline and reserve
- Sidekicks, when present, go only in main_sidekick/sub_sidekick and never in hero slots
- ONLY use sidekicks listed in Player owned sidekicks. If no sidekicks are selected, set main_sidekick and sub_sidekick to null and add a risk that no sidekick ownership was supplied.
- Recommended skills must exist in the database results for that character. Use 3 or 4 skills per character when data supports it; use fewer only when data is incomplete and add a risk.
- Every character MUST include exactly one weapon string, exactly one armor string, and exactly three Grasta strings.
- Treat weapon, armor, and Grasta suggestions as build assumptions even if the player did not enter item ownership.
- Do not assign the same specific weapon or the same specific armor to multiple characters inside the same recommendation lineup. The same item may appear again in a different recommendation lineup.
- Grasta may be reused freely, including repeated copies on one character, when the build calls for it.
- Prefer Grasta that match the character weapon type or listed traits from the database results. If compatibility cannot be verified from graph facts, state that caveat in upgrade_assumptions or build_notes.
- If Pain/Poison Grasta or pain/poison multipliers are part of the damage plan, identify the skill, passive, sidekick, or explicit assumption that applies or enables pain/poison.
- Treat Stellar Awakening-gated skills/passives conservatively and put any upgrade assumption in upgrade_assumptions.
- Explain Grasta/Ore/equipment build notes as late-game-access assumptions, not exact optimizer output.
- Use Superboss mechanics context when present. Boss affinity facts in boss_affinity must match that context.
- Explain offense, defense, synergy, sustain, MP, sidekick, build-readiness, and upgrade-burden tradeoffs where relevant.
- Missing or uncertain data must lower confidence or appear in risks. Do not invent certainty.
- Fit labels are transparent ranking/navigation signals, not success probabilities. Never output numeric win probability.
- Every recommendation must include boss or mechanics citations from the graph/mechanics context.
- Output ONLY the JSON object — no preamble, no markdown fences

MANDATORY SOURCE ATTRIBUTION (per D-13):
For each character in each frontline and reserve, the synergy_explanation MUST cite:
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
      "frontline": [{"name": "...", "role": "...", "weapon": "...", "armor": "...", "grastas": ["...", "...", "..."]}, ...],
      "reserve": [{"name": "...", "role": "...", "weapon": "...", "armor": "...", "grastas": ["...", "...", "..."]}],
      "main_sidekick": null,
      "sub_sidekick": null,
      "fit_label": "medium",
      "confidence_label": "low",
      "rubric_summary": {
        "offense": "low - no graph-backed boss facts",
        "defense": "low - no graph-backed boss facts",
        "synergy": "medium - roster roles are plausible",
        "sustain": "medium - healer or mitigation included",
        "mp": "medium - MP risk should be monitored",
        "sidekick": "low - no sidekick selected",
        "build_readiness": "medium - assumes common late-game Grasta/Ore access",
        "upgrade_burden": "medium - assumptions must be labeled"
      },
      "boss_affinity": {"weak": [], "resist": [], "null": [], "absorb": []},
      "risks": ["No database results were found; confidence is low."],
      "citations": [],
      "synergy_explanation": "..."
    },
    <second alternative>,
    <third alternative>
  ],
  "reason": "Why no database results were found and what the query attempted."
}

Rules:
- Output EXACTLY 3 alternative objects in the alternatives array — no more, no fewer.
- Each alternative must have exactly 4 frontline heroes and exactly 2 reserve heroes.
- Only suggest characters from the player's roster.
- Do not duplicate heroes. Do not place sidekicks in hero slots.
- Only use sidekicks listed in Player owned sidekicks. If none are selected, set both sidekick slots to null.
- Every character MUST include exactly one weapon string, exactly one armor string, and exactly three Grasta strings.
- Do not assign the same specific weapon or armor to multiple characters inside one alternative lineup.
- Grasta may be reused freely, including repeated copies on one character.
- If Pain/Poison Grasta or pain/poison multipliers are part of the damage plan, identify the source or label it as an assumption.
- Include Grasta citations: [CharacterName]: [Grasta name] ([trait]) — [effect].
- Never present numeric win probability.
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
    owned_sidekicks = state.get("owned_sidekicks", [])

    roster_str = ", ".join(roster) if roster else "no characters specified"
    sidekick_str = ", ".join(owned_sidekicks) if owned_sidekicks else "no sidekicks selected"

    # Cap records and nested text to avoid exceeding hosted free-tier context limits.
    MAX_RECORDS = 12
    trimmed = compact_records(
        db_results,
        max_records=MAX_RECORDS,
        max_list_items=4,
        max_string_chars=180,
        max_dict_keys=10,
    )
    trim_note = f" (compacted to {MAX_RECORDS} of {len(db_results)})" if len(db_results) > MAX_RECORDS else " (compacted)"

    human_content = (
        f"User query: {user_query}\n"
        f"Player roster: {roster_str}\n"
        f"Player owned sidekicks: {sidekick_str}\n"
        f"Traversal strategy: {plan_strategy}\n"
        f"Superboss mechanics context: {boss_context or 'none'}\n"
        f"Database results{trim_note}:\n{trimmed}"
    )

    messages = [
        SystemMessage(content=ANALYZE_SYSTEM_PROMPT),
        HumanMessage(content=human_content),
    ]

    response = _invoke_analyzer(llm, messages)
    return {"analysis_result": response.content}


def _generate_alternatives(state: WorkflowState) -> dict:
    """Generate 3 alternative team compositions when db_results is empty.

    Returns {"alternatives": str} — raw LLM JSON string; FORMAT parses this.
    Owned key: alternatives (WorkflowState key added Phase 5).
    """
    llm = get_llm(role="analyzer")
    roster_str = ", ".join(state.get("roster", [])) or "no characters specified"
    sidekick_str = ", ".join(state.get("owned_sidekicks", [])) or "no sidekicks selected"
    user_query = state.get("user_query", "")
    plan_strategy = state.get("plan_strategy", "")
    boss_context = state.get("boss_context", "")

    messages = [
        SystemMessage(content=ALTERNATIVES_SYSTEM_PROMPT),
        HumanMessage(content=(
            f"User query: {user_query}\n"
            f"Player roster: {roster_str}\n"
            f"Player owned sidekicks: {sidekick_str}\n"
            f"Original traversal strategy: {plan_strategy}\n"
            f"Superboss mechanics context: {boss_context or 'none'}\n"
            "No database results were found. Generate EXACTLY 3 alternative team compositions."
        )),
    ]
    response = _invoke_analyzer(llm, messages)
    return {"alternatives": response.content}
