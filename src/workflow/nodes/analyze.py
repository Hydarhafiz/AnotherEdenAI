"""ANALYZE node — synthesizes query results into a team recommendation via Sonnet 4.6.

Reads db_results, user_query, roster, and plan_strategy from WorkflowState.
Returns only: {"analysis_result": str}

The analysis_result is a raw string from the LLM, intended to be a JSON object
with the team recommendation structure that FORMAT will parse and validate.
"""
import logging
import json
from json import JSONDecodeError

from langchain_core.messages import HumanMessage, SystemMessage

from ..candidates import (
    ARCHETYPES, parse_candidate_response, resolve_candidate_recommendations,
    validate_candidate_response,
)
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
- Use exact graph-backed Grasta display variants; unique/finite copies cannot exceed their account cardinality within a lineup.
- Preserve the complete canonical character name exactly, including style/alias suffixes and commas.
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
- Use exact graph-backed Grasta display variants and respect unique/finite copy limits within each lineup.
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

    if state.get("candidate_bundle"):
        return _analyze_candidate_bundle(state)

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


CANDIDATE_ANALYZE_SYSTEM_PROMPT = """You are selecting Another Eden recommendations from a backend-owned candidate bundle.

Every hard field MUST be a candidate ID copied exactly from the bundle. Never output a display name where an ID is required and never invent an ID.

The bundle uses a shared grastas catalog and grasta_compatibility_groups. A
character's complete compatible Grasta set is global_grasta_ids plus its
group's grasta_ids plus that character's additional_grasta_ids. Select only
from that combined set and resolve details through the shared catalog. Compact
effect_tags summarize skill, passive, and sidekick descriptions.
The schemas object declares the column order for compact catalog rows.

Output JSON with recommendations containing up to three objects, preferably burst, sustain, and hybrid. Each object must contain:
- archetype, strategy_summary, key_facts, build_notes, boss_counterplay_notes, sustain_mp_notes, risks, fit_label, confidence_label, rubric_summary, synergy_explanation
- frontline: exactly four hero objects
- reserve: exactly two hero objects
- main_sidekick_id and sub_sidekick_id (candidate ID or null)
- citation_ids and boss_fact_ids

Each hero object must contain character_id, role, weapon_id, armor_id, exactly three grasta_ids, three or four skill_ids, passive_ids, and upgrade_assumptions.

Use only IDs offered for that exact character. Respect Grasta copy limits. Prefer compatible Pain/Poison Grasta for active damage dealers only when a selected skill, passive, sidekick, or explicit supported assumption applies the status. Prefer distinct Dormant/shareable Grasta on reserve mules. These are preferences, not mandatory rules; explain support, tank, AF, farming, or boss-specific exceptions.

Do not calculate damage, claim exact best-in-slot equipment, substitute outside the bundle, or state numeric win probability. Return only JSON."""


ANALYZER_PROMPT_TEXT_LIMIT_BYTES = 450_000


def _candidate_prompt_bundle(bundle: dict) -> dict:
    """Normalize repeated candidates into a compact analyzer-only view.

    The full bundle remains the deterministic validation authority. This view
    preserves every hard-field ID while storing shared Grasta metadata once and
    deduplicating common compatibility lists by weapon group.
    """
    grasta_catalog: dict[str, list] = {}
    character_rows = []
    for character in bundle.get("characters", []):
        grasta_ids = []
        seen_grasta_ids = set()
        for grasta in character.get("grastas", []):
            grasta_id = grasta.get("id")
            if not grasta_id:
                continue
            if grasta_id not in seen_grasta_ids:
                grasta_ids.append(grasta_id)
                seen_grasta_ids.add(grasta_id)
            prompt_grasta = [
                grasta.get("id"),
                grasta.get("display_name"),
                grasta.get("category"),
                grasta.get("tier"),
                grasta.get("personality_req"),
                grasta.get("required_trait"),
                grasta.get("acquisition_class"),
                grasta.get("max_theoretical_copies"),
                grasta.get("ranking_tags") or [],
            ]
            grasta_catalog.setdefault(grasta_id, prompt_grasta)
        character_rows.append({
            **_prompt_fields(
                character,
                "id", "display_name", "weapon", "traits",
                "has_stellar_awakening",
            ),
            "skills": [
                _prompt_skill_row(skill)
                for skill in character.get("skills", [])
            ],
            "passives": [
                _prompt_passive_row(passive)
                for passive in character.get("passives", [])
            ],
            "weapon_options": [
                _prompt_fields(option, "id", "display_name", "generic")
                for option in character.get("weapon_options", [])
            ],
            "armor_options": [
                _prompt_fields(option, "id", "display_name", "generic")
                for option in character.get("armor_options", [])
            ],
            "_allowed_grasta_ids": grasta_ids,
        })

    all_sets = [
        set(character["_allowed_grasta_ids"])
        for character in character_rows
    ]
    global_common_ids = set.intersection(*all_sets) if all_sets else set()
    global_grasta_ids = [
        grasta_id
        for grasta_id in character_rows[0]["_allowed_grasta_ids"]
        if grasta_id in global_common_ids
    ] if character_rows else []

    compatibility_groups = []
    members_by_weapon: dict[str, list[dict]] = {}
    for character in character_rows:
        members_by_weapon.setdefault(
            str(character.get("weapon") or "unknown"), []
        ).append(character)
    for weapon, members in members_by_weapon.items():
        member_sets = [set(member["_allowed_grasta_ids"]) for member in members]
        weapon_common_ids = set.intersection(*member_sets) if member_sets else set()
        group_common_ids = weapon_common_ids - global_common_ids
        ordered_common = [
            grasta_id
            for grasta_id in members[0]["_allowed_grasta_ids"]
            if grasta_id in group_common_ids
        ]
        group_id = f"grasta-compatibility:{len(compatibility_groups)}"
        compatibility_groups.append({
            "id": group_id,
            "weapon": weapon,
            "grasta_ids": ordered_common,
        })
        for character in members:
            allowed_ids = character.pop("_allowed_grasta_ids")
            character["grasta_compatibility_group_id"] = group_id
            character["additional_grasta_ids"] = [
                grasta_id
                for grasta_id in allowed_ids
                if grasta_id not in global_common_ids | group_common_ids
            ]

    return {
        "version": bundle.get("version"),
        "schemas": {
            "grasta": ["id", "name", "category", "tier", "personality", "trait", "acquisition", "max_copies", "ranking_tags"],
            "skill": ["id", "name", "element", "requires_sa", "effect_tags"],
            "passive": ["id", "name", "type", "requires_sa", "effect_tags"],
            "sidekick_effect": ["name", "effect_tags"],
        },
        "characters": character_rows,
        "grastas": list(grasta_catalog.values()),
        "global_grasta_ids": global_grasta_ids,
        "grasta_compatibility_groups": compatibility_groups,
        "sidekicks": [
            _prompt_sidekick(item)
            for item in bundle.get("sidekicks", [])
        ],
        "stellar_awakened": bundle.get("stellar_awakened", {}),
        "boss": bundle.get("boss", {}),
        "coverage": bundle.get("coverage", {}),
        "ranking_policy": bundle.get("ranking_policy", {}),
    }


def _prompt_fields(item: dict, *keys: str) -> dict:
    """Keep selected prompt fields, including meaningful false/zero values."""
    return {
        key: item.get(key)
        for key in keys
        if item.get(key) not in (None, "", [], {})
    }


def _prompt_skill_row(item: dict) -> list:
    return [
        item.get("id"),
        item.get("name"),
        item.get("element"),
        bool(item.get("requires_stellar_awakened")),
        _prompt_effect_tags(item.get("description")),
    ]


def _prompt_passive_row(item: dict) -> list:
    return [
        item.get("id"),
        item.get("name"),
        item.get("passive_type"),
        bool(item.get("requires_stellar_awakened")),
        _prompt_effect_tags(item.get("description")),
    ]


def _prompt_sidekick(item: dict) -> dict:
    sidekick = _prompt_fields(item, "id", "name")
    sidekick["skills"] = [
        [choice.get("name"), _prompt_effect_tags(choice.get("description"))]
        for choice in item.get("skills", [])
    ]
    sidekick["auras"] = [
        [choice.get("name"), _prompt_effect_tags(choice.get("description"))]
        for choice in item.get("auras", [])
    ]
    return sidekick


def _prompt_effect_tags(value: object) -> list[str]:
    text = str(value or "").casefold()
    keywords = (
        "pain", "poison", "zone", "heal", "restore", "regen",
        "buff", "debuff", "resist", "barrier", "shield", "cleanse",
        "break", "weakness", "status", "mp", "critical", "awaken",
        "fire", "water", "wind", "earth", "thunder", "shade", "crystal",
    )
    return [keyword for keyword in keywords if keyword in text]


def _invoke_candidate_analyzer(llm, messages):
    """Return one analyzer response plus provider-envelope retry count."""
    retries = 0
    for attempt in range(1, ANALYZER_TRANSPORT_ATTEMPTS + 1):
        try:
            return llm.invoke(messages), retries
        except JSONDecodeError as exc:
            if attempt >= ANALYZER_TRANSPORT_ATTEMPTS:
                raise RuntimeError(
                    "Analyzer provider returned malformed JSON responses "
                    f"after {ANALYZER_TRANSPORT_ATTEMPTS} attempts"
                ) from exc
            retries += 1
            logger.warning(
                "Analyzer provider transport retry (%d/%d)",
                attempt + 1,
                ANALYZER_TRANSPORT_ATTEMPTS,
            )


def _analyze_candidate_bundle(state: WorkflowState) -> dict:
    """Run initial selection plus at most two batched correction rounds."""
    bundle = state["candidate_bundle"]
    coverage = bundle.get("coverage", {})
    if not coverage.get("complete", False):
        return {
            "analysis_failure": {
                "type": "candidate_coverage_failure",
                "message": "Eligible roster coverage is incomplete.",
                "details": coverage,
            },
            "cypher_retry_count": state.get("retry_count", 0),
            "analyzer_call_count": 0,
            "analyzer_correction_rounds": 0,
            "provider_transport_retries": 0,
            "structured_output_errors": [],
            "candidate_validation_errors": [],
        }
    if len(bundle.get("characters", [])) < 6:
        return {
            "analysis_failure": {
                "type": "insufficient_candidate_roster",
                "message": "Fewer than six legal character candidates are available.",
            },
            "cypher_retry_count": state.get("retry_count", 0),
            "analyzer_call_count": 0,
            "analyzer_correction_rounds": 0,
            "provider_transport_retries": 0,
            "structured_output_errors": [],
            "candidate_validation_errors": [],
        }

    prompt_bundle = _candidate_prompt_bundle(bundle)
    prompt_bundle_json = json.dumps(
        prompt_bundle,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    prompt_bytes = len(prompt_bundle_json.encode("utf-8"))
    logger.info("Analyzer candidate prompt payload: %d bytes", prompt_bytes)
    if prompt_bytes > ANALYZER_PROMPT_TEXT_LIMIT_BYTES:
        return {
            "analysis_failure": {
                "type": "candidate_payload_too_large",
                "message": "Compacted candidate payload exceeds the provider-safe text limit.",
                "details": {"payload_bytes": prompt_bytes, "limit_bytes": ANALYZER_PROMPT_TEXT_LIMIT_BYTES},
            },
            "cypher_retry_count": state.get("retry_count", 0),
            "analyzer_call_count": 0,
            "analyzer_correction_rounds": 0,
            "provider_transport_retries": 0,
            "structured_output_errors": [],
            "candidate_validation_errors": [],
        }

    llm = get_llm(role="analyzer")
    frozen: list[dict] = []
    frozen_archetypes: set[str] = set()
    frozen_signatures: set[str] = set()
    structured_errors: list[dict] = []
    candidate_errors: list[dict] = []
    rejection_warnings: list[str] = list(state.get("candidate_warnings", []))
    call_count = 0
    correction_rounds = 0
    transport_retries = 0
    viability_notes: list[str] = []

    messages = [
        SystemMessage(content=CANDIDATE_ANALYZE_SYSTEM_PROMPT),
        HumanMessage(
            content=(
                f"User query: {state.get('user_query', '')}\n"
                f"Traversal strategy: {state.get('plan_strategy', '')}\n"
                "Candidate bundle (the sole authority for hard fields):\n"
                + prompt_bundle_json
            )
        ),
    ]

    pending_invalid: list[dict] = []
    for round_index in range(3):
        response, provider_retries = _invoke_candidate_analyzer(llm, messages)
        call_count += 1
        transport_retries += provider_retries
        try:
            payload = parse_candidate_response(response.content)
        except (ValueError, json.JSONDecodeError) as exc:
            error = {
                "code": "structured_output.invalid_json",
                "path": "response",
                "message": str(exc),
                "allowed_ids": [],
            }
            structured_errors.append(error)
            pending_invalid = [{"index": 0, "proposal": {}, "errors": [error]}]
            payload = {}
        else:
            notes = payload.get("archetype_viability_notes", [])
            if isinstance(notes, list):
                viability_notes = [str(note) for note in notes]
            valid, pending_invalid = validate_candidate_response(payload, bundle)
            candidate_errors.extend(error for invalid in pending_invalid for error in invalid.get("errors", []))
            for proposal in valid:
                # Different archetypes may intentionally use the same six heroes.
                # Only suppress an exact repeated proposal, not a shared roster.
                signature = json.dumps(proposal, sort_keys=True, ensure_ascii=False)
                if signature in frozen_signatures:
                    continue
                frozen.append(proposal)
                frozen_signatures.add(signature)
                archetype = str(proposal.get("archetype", "")).casefold()
                if archetype:
                    frozen_archetypes.add(archetype)
                if len(frozen) >= 3:
                    break
        if not pending_invalid or len(frozen) >= 3 or round_index >= 2:
            break

        correction_rounds += 1
        logger.info("Analyzer correction round %d: frozen=%d invalid=%d", correction_rounds, len(frozen), len(pending_invalid))
        rejected_codes = sorted({
            error["code"]
            for invalid in pending_invalid
            for error in invalid.get("errors", [])
        })
        rejection_warnings.append(
            f"Analyzer correction round {correction_rounds} rejected: "
            + ", ".join(rejected_codes)
        )
        missing_archetypes = [value for value in ARCHETYPES if value not in frozen_archetypes]
        correction_request = {
            "instruction": "Correct all invalid lineups together. Do not repeat or modify frozen valid lineups.",
            "frozen_valid_archetypes": sorted(frozen_archetypes),
            "required_archetypes": missing_archetypes,
            "invalid_lineups": pending_invalid,
            "frozen_valid_lineups": [{"archetype": item.get("archetype"), "character_ids": [hero.get("character_id") for hero in item.get("frontline", []) + item.get("reserve", [])]} for item in frozen],
            "candidate_bundle": prompt_bundle,
        }
        messages = [
            SystemMessage(content=CANDIDATE_ANALYZE_SYSTEM_PROMPT),
            HumanMessage(content=json.dumps(correction_request, ensure_ascii=False)),
        ]

    if not frozen:
        diagnostics = [
            error
            for invalid in pending_invalid
            for error in invalid.get("errors", [])
        ]
        return {
            "analysis_failure": {
                "type": "analyzer_correction_exhausted",
                "message": "No fully valid lineup remained after the correction cap.",
                "diagnostics": diagnostics,
            },
            "cypher_retry_count": state.get("retry_count", 0),
            "analyzer_call_count": call_count,
            "analyzer_correction_rounds": correction_rounds,
            "provider_transport_retries": transport_retries,
            "structured_output_errors": structured_errors,
            "candidate_validation_errors": candidate_errors,
        }

    if pending_invalid:
        rejection_warnings.append(
            f"Discarded {len(pending_invalid)} invalid lineup proposal(s) after correction cap."
        )
    resolved = resolve_candidate_recommendations(frozen[:3], bundle, rejection_warnings)
    resolved["archetype_viability_notes"] = viability_notes
    return {
        "analysis_result": json.dumps(resolved, ensure_ascii=False),
        "cypher_retry_count": state.get("retry_count", 0),
        "analyzer_call_count": call_count,
        "analyzer_correction_rounds": correction_rounds,
        "provider_transport_retries": transport_retries,
        "structured_output_errors": structured_errors,
        "candidate_validation_errors": candidate_errors,
        "analysis_failure": {},
    }
