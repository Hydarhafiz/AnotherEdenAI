"""Feature C backend-owned recommendation candidates and hard-field validation."""

from __future__ import annotations

import hashlib
import json
import re
import logging
from collections import Counter
from typing import Any

from .state import WorkflowState

logger = logging.getLogger(__name__)


ARCHETYPES = ("burst", "sustain", "hybrid")


def _candidate_id(prefix: str, *parts: object) -> str:
    normalized = "\x1f".join(str(part or "").strip().casefold() for part in parts)
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:20]
    return f"{prefix}:{digest}"


async def _query(driver, cypher: str, **parameters) -> list[dict]:
    records, _, _ = await driver.execute_query(cypher, database_="neo4j", **parameters)
    return [dict(record) for record in records]


async def prepare_candidates_node(state: WorkflowState, driver) -> dict:
    """Build the complete roster candidate boundary after retrieval succeeds."""
    roster = list(dict.fromkeys(state.get("roster", [])))
    owned_sidekicks = list(dict.fromkeys(state.get("owned_sidekicks", [])))

    characters = await _query(
        driver,
        """
MATCH (c:Character)
WHERE c.name IN $roster
RETURN c.character_id AS id, c.name AS name,
       coalesce(c.display_name, c.name) AS display_name,
       coalesce(c.aliases, []) AS aliases,
       c.weapon AS weapon, coalesce(c.is_SA, false) AS has_stellar_awakening
ORDER BY c.name
""",
        roster=roster,
    )
    traits = await _query(
        driver,
        """
MATCH (c:Character)-[:HAS_TRAIT]->(t:Trait)
WHERE c.name IN $roster
RETURN c.name AS character_name, collect(DISTINCT t.name) AS traits
""",
        roster=roster,
    )
    skills = await _query(
        driver,
        """
MATCH (c:Character)-[:HAS_SKILL]->(s:Skill)
WHERE c.name IN $roster
RETURN c.name AS character_name, s.name AS name, s.description AS description,
       s.element AS element, s.skill_type AS skill_type,
       coalesce(s.requires_stellar_awakened, false) AS requires_stellar_awakened,
       s.source_url AS source_url
ORDER BY c.name, s.name
""",
        roster=roster,
    )
    passives = await _query(
        driver,
        """
MATCH (c:Character)-[:HAS_PASSIVE_SKILL]->(p:PassiveSkill)
WHERE c.name IN $roster
RETURN c.name AS character_name, p.name AS name, p.description AS description,
       p.passive_type AS passive_type,
       coalesce(p.requires_stellar_awakened, false) AS requires_stellar_awakened,
       p.source_url AS source_url
ORDER BY c.name, p.name
""",
        roster=roster,
    )
    sidekicks = await _query(
        driver,
        """
MATCH (s:Sidekick)
WHERE s.name IN $owned_sidekicks
OPTIONAL MATCH (s)-[:HAS_AUTO_SKILL|HAS_CHARGE_SKILL]->(skill:SidekickSkill)
OPTIONAL MATCH (s)-[:HAS_AURA]->(aura:SidekickAura)
RETURN s.name AS name, s.source_url AS source_url,
       collect(DISTINCT {name: skill.name, description: skill.description}) AS skills,
       collect(DISTINCT {name: aura.name, description: aura.effect_text}) AS auras
ORDER BY s.name
""",
        owned_sidekicks=owned_sidekicks,
    )
    grastas = await _query(
        driver,
        """
MATCH (g:Grasta)
OPTIONAL MATCH (g)-[:REQUIRES_TRAIT]->(t:Trait)
RETURN g.grasta_id AS id, g.name AS name,
       coalesce(g.display_name, g.name) AS display_name,
       g.category AS category, g.tier AS tier, g.stats AS stats,
       g.effect_text AS effect_text, g.personality_req AS personality_req,
       t.name AS required_trait, g.weapon_req AS weapon_req,
       coalesce(g.weapon_group, []) AS weapon_group,
       coalesce(g.is_shareable, false) AS is_shareable,
       coalesce(g.acquisition_class, 'unknown') AS acquisition_class,
       g.max_theoretical_copies AS max_theoretical_copies,
       g.source_url AS source_url, coalesce(g.effect_tags, []) AS effect_tags
ORDER BY g.display_name
""",
    )

    traits_by_character = {
        row["character_name"]: [value for value in row.get("traits", []) if value]
        for row in traits
    }
    skills_by_character: dict[str, list[dict]] = {}
    for row in skills:
        owner = row.pop("character_name")
        row["id"] = _candidate_id("skill", owner, row.get("name"))
        row["description"] = _compact_text(row.get("description"))
        skills_by_character.setdefault(owner, []).append(row)
    passives_by_character: dict[str, list[dict]] = {}
    for row in passives:
        owner = row.pop("character_name")
        row["id"] = _candidate_id("passive", owner, row.get("name"))
        row["description"] = _compact_text(row.get("description"))
        passives_by_character.setdefault(owner, []).append(row)

    valid_grastas = [row for row in grastas if row.get("id") and row.get("display_name")]
    character_candidates = []
    for character in characters:
        name = character["name"]
        character["id"] = character.get("id") or _candidate_id("character", name)
        character_traits = traits_by_character.get(name, [])
        weapon = character.get("weapon") or ""
        compatible_grastas = [
            _compact_grasta(row)
            for row in valid_grastas
            if _grasta_is_compatible(row, character_traits, weapon)
        ]
        character_candidates.append(
            {
                **character,
                "traits": character_traits,
                "skills": skills_by_character.get(name, []),
                "passives": passives_by_character.get(name, []),
                "weapon_options": [
                    {
                        "id": _candidate_id("equipment", "weapon", weapon or "available"),
                        "display_name": weapon or "available weapon",
                        "generic": True,
                    }
                ],
                "armor_options": [
                    {
                        "id": _candidate_id("equipment", "armor", "available"),
                        "display_name": "available armor",
                        "generic": True,
                    }
                ],
                "grastas": compatible_grastas,
            }
        )

    sidekick_candidates = []
    for sidekick in sidekicks:
        sidekick["skills"] = [{**item, "description": _compact_text(item.get("description"))} for item in sidekick.get("skills", []) if item.get("name")]
        sidekick["auras"] = [{**item, "description": _compact_text(item.get("description"))} for item in sidekick.get("auras", []) if item.get("name")]
        sidekick_candidates.append(
            {
                **sidekick,
                "id": _candidate_id("sidekick", sidekick.get("name")),
            }
        )

    boss = _boss_candidates(state.get("boss_context", ""))
    citation_urls = {item["source_url"] for item in boss["citations"]}
    for character in character_candidates:
        source_choices = [
            *character.get("skills", []),
            *character.get("passives", []),
            *character.get("grastas", []),
        ]
        for choice in source_choices:
            source_url = choice.get("source_url")
            if not source_url or source_url in citation_urls:
                continue
            citation_urls.add(source_url)
            boss["citations"].append({
                "id": _candidate_id("citation", character["name"], source_url),
                "label": f"{character['display_name']} graph source",
                "source_url": source_url,
            })
    graph_names = {character["name"] for character in character_candidates}
    missing = [name for name in roster if name not in graph_names]
    coverage = {
        "eligible_roster_count": len(roster),
        "candidate_character_count": len(character_candidates),
        "missing_character_names": missing,
        "complete": not missing,
    }
    warnings = []
    if missing:
        warnings.append(
            "Candidate coverage omitted eligible roster entries: " + ", ".join(missing)
        )

    bundle = {
        "version": "feature-c-v1",
        "characters": character_candidates,
        "sidekicks": sidekick_candidates,
        "stellar_awakened": state.get("stellar_awakened", {}),
        "boss": boss,
        "coverage": coverage,
        "ranking_policy": {
            "frontline": "Prefer compatible Pain/Poison Grasta when a selected source applies the status.",
            "reserve": "Prefer distinct shareable or Dormant-oriented Grasta for reserve mules.",
            "exceptions": "Support, tank, AF, farming, and boss-specific exceptions are allowed with explanation.",
        },
    }
    logger.info("Prepared candidate bundle: characters=%d sidekicks=%d complete=%s", len(character_candidates), len(sidekick_candidates), coverage["complete"])
    return {"candidate_bundle": bundle, "candidate_warnings": warnings}


def _compact_text(value: object, limit: int = 240) -> str:
    text = " ".join(str(value or "").split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _compact_grasta(row: dict) -> dict:
    text = " ".join(
        str(row.get(key) or "")
        for key in ("name", "display_name", "effect_text", "stats")
    ).lower()
    tags = list(row.get("effect_tags", []))
    if "pain" in text or "poison" in text:
        tags.append("preference:active-damage-status")
    if row.get("is_shareable") or "dormant" in text:
        tags.append("preference:reserve-share")
    row = {**row, "effect_text": _compact_text(row.get("effect_text")), "stats": _compact_text(row.get("stats"), 120)}
    return {
        key: row.get(key)
        for key in (
            "id", "display_name", "category", "tier", "stats", "effect_text",
            "personality_req", "required_trait", "weapon_req", "weapon_group",
            "is_shareable", "acquisition_class", "max_theoretical_copies", "source_url",
        )
    } | {"ranking_tags": list(dict.fromkeys(tags))}


def _grasta_is_compatible(grasta: dict, traits: list[str], weapon: str) -> bool:
    required_trait = grasta.get("required_trait") or grasta.get("personality_req")
    if required_trait and required_trait not in traits:
        return False
    weapon_req = grasta.get("weapon_req")
    weapon_group = set(grasta.get("weapon_group") or [])
    if weapon_req and weapon_req.casefold() != weapon.casefold():
        return False
    if weapon_group and weapon not in weapon_group:
        return False
    return True


def _boss_candidates(raw_context: str) -> dict:
    try:
        context = json.loads(raw_context) if raw_context else {}
    except (TypeError, json.JSONDecodeError):
        context = {}
    boss = context.get("boss") if isinstance(context.get("boss"), dict) else {}
    affinities = {
        key: list(boss.get(key, [])) if isinstance(boss.get(key), list) else []
        for key in ("weak", "resist", "null", "absorb")
    }
    facts = []
    if boss:
        facts.append(
            {
                "id": _candidate_id("boss-fact", boss.get("name"), "affinities"),
                "kind": "affinities",
                "value": affinities,
            }
        )
        mechanics = boss.get("mechanics_text") or boss.get("characteristics")
        if mechanics:
            facts.append(
                {
                    "id": _candidate_id("boss-fact", boss.get("name"), "mechanics"),
                    "kind": "mechanics",
                    "value": mechanics,
                }
            )
    citations = []
    raw_citations = context.get("citations", []) if isinstance(context, dict) else []
    if boss.get("source_url"):
        raw_citations = [
            *raw_citations,
            {"label": boss.get("name", "Boss source"), "source_url": boss["source_url"]},
        ]
    seen_urls = set()
    for citation in raw_citations:
        if not isinstance(citation, dict):
            continue
        url = citation.get("source_url")
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        citations.append(
            {
                "id": _candidate_id("citation", citation.get("label"), url),
                "label": citation.get("label") or "Source",
                "source_url": url,
            }
        )
    return {
        "name": boss.get("name"),
        "affinities": affinities,
        "facts": facts,
        "citations": citations,
    }


def parse_candidate_response(text: str) -> dict:
    """Parse an analyzer JSON object without accepting prose as hard fields."""
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
        if not match:
            raise ValueError("analyzer did not return a valid JSON object")
        value = json.loads(match.group(1))
    if not isinstance(value, dict):
        raise ValueError("analyzer response must be a JSON object")
    return value


def validate_candidate_response(payload: dict, bundle: dict) -> tuple[list[dict], list[dict]]:
    """Validate each proposed lineup independently against allowed hard-field IDs."""
    proposals = payload.get("recommendations", [])
    if isinstance(proposals, list) and not proposals:
        return [], [{"index": 0, "proposal": {}, "errors": [_diagnostic("shape.empty", "recommendations", "At least one lineup proposal is required", [])]}]
    if not isinstance(proposals, list):
        return [], [_diagnostic("shape.recommendations", "recommendations", "Expected a list", [])]
    valid = []
    invalid = []
    for index, proposal in enumerate(proposals[:3]):
        errors = _validate_candidate_lineup(proposal, bundle, index)
        if errors:
            invalid.append({"index": index, "proposal": proposal, "errors": errors})
        else:
            valid.append(proposal)
    if len(proposals) > 3:
        invalid.append(
            {
                "index": 3,
                "proposal": {},
                "errors": [_diagnostic("shape.too_many", "recommendations", "At most three lineups are allowed", [])],
            }
        )
    return valid, invalid


def _validate_candidate_lineup(lineup: Any, bundle: dict, index: int) -> list[dict]:
    path = f"recommendations.{index}"
    if not isinstance(lineup, dict):
        return [_diagnostic("shape.lineup", path, "Lineup must be an object", [])]
    characters = {item["id"]: item for item in bundle.get("characters", [])}
    sidekicks = {item["id"]: item for item in bundle.get("sidekicks", [])}
    citations = {item["id"]: item for item in bundle.get("boss", {}).get("citations", [])}
    boss_facts = {item["id"] for item in bundle.get("boss", {}).get("facts", [])}
    errors: list[dict] = []
    frontline = lineup.get("frontline")
    reserve = lineup.get("reserve")
    if not isinstance(frontline, list) or len(frontline) != 4:
        errors.append(_diagnostic("shape.frontline", f"{path}.frontline", "Exactly four frontline entries are required", list(characters)))
        frontline = frontline if isinstance(frontline, list) else []
    if not isinstance(reserve, list) or len(reserve) != 2:
        errors.append(_diagnostic("shape.reserve", f"{path}.reserve", "Exactly two reserve entries are required", list(characters)))
        reserve = reserve if isinstance(reserve, list) else []

    selected_characters = []
    allocated_grastas: Counter[str] = Counter()
    allocated_specific_equipment: Counter[str] = Counter()
    status_dependent = False
    status_source = False
    for slot_name, entries in (("frontline", frontline), ("reserve", reserve)):
        for slot_index, entry in enumerate(entries):
            slot_path = f"{path}.{slot_name}.{slot_index}"
            if not isinstance(entry, dict):
                errors.append(_diagnostic("shape.hero", slot_path, "Hero entry must be an object", list(characters)))
                continue
            character_id = entry.get("character_id")
            character = characters.get(character_id)
            if not character:
                errors.append(_diagnostic("id.character", f"{slot_path}.character_id", "Unknown character candidate ID", list(characters)))
                continue
            selected_characters.append(character_id)
            errors.extend(_validate_equipment_ids(entry, character, slot_path))
            for key, option_key in (("weapon_id", "weapon_options"), ("armor_id", "armor_options")):
                options = {item["id"]: item for item in character.get(option_key, [])}
                selected_option = options.get(entry.get(key))
                if selected_option and not selected_option.get("generic", False):
                    allocated_specific_equipment[selected_option["id"]] += 1
            assumption_text = " ".join(entry.get("upgrade_assumptions", []) if isinstance(entry.get("upgrade_assumptions", []), list) else []).lower()

            skill_options = {choice["id"]: choice for choice in character.get("skills", [])}
            passive_options = {choice["id"]: choice for choice in character.get("passives", [])}
            for key, options, code in (
                ("skill_ids", skill_options, "id.skill"),
                ("passive_ids", passive_options, "id.passive"),
            ):
                selected = entry.get(key, [])
                if key == "skill_ids" and isinstance(selected, list) and len(selected) not in {3, 4}:
                    errors.append(_diagnostic("shape.skills", f"{slot_path}.{key}", "Select exactly three or four skill candidate IDs", list(options)))
                if not isinstance(selected, list):
                    errors.append(_diagnostic(code, f"{slot_path}.{key}", "Expected a list of candidate IDs", list(options)))
                    continue
                for choice_id in selected:
                    choice = options.get(choice_id)
                    if not choice:
                        errors.append(_diagnostic(code, f"{slot_path}.{key}", f"Unknown {key[:-4]} candidate ID", list(options)))
                        continue
                    choice_text = f"{choice.get('name', '')} {choice.get('description', '')}".lower()
                    status_source = status_source or "pain" in choice_text or "poison" in choice_text
                    if choice.get("requires_stellar_awakened"):
                        sa_state = bundle.get("stellar_awakened", {}).get(character["name"], "unknown")
                        if sa_state is False or sa_state == "not_awakened":
                            errors.append(_diagnostic("stellar.unavailable", f"{slot_path}.{key}", "Selected Stellar Awakening choice is unavailable", list(options)))
                        elif sa_state not in (True, "awakened") and choice.get("name", "").casefold() not in assumption_text:
                            errors.append(_diagnostic("stellar.assumption_missing", f"{slot_path}.{key}", "Unknown Stellar Awakening state requires an explicit upgrade assumption", list(options)))

            grasta_options = {choice["id"]: choice for choice in character.get("grastas", [])}
            selected_grastas = entry.get("grasta_ids")
            if not isinstance(selected_grastas, list) or len(selected_grastas) != 3:
                errors.append(_diagnostic("shape.grasta", f"{slot_path}.grasta_ids", "Exactly three Grasta candidate IDs are required", list(grasta_options)))
            else:
                for grasta_id in selected_grastas:
                    grasta = grasta_options.get(grasta_id)
                    if not grasta:
                        errors.append(_diagnostic("id.grasta", f"{slot_path}.grasta_ids", "Unknown or incompatible Grasta candidate ID", list(grasta_options)))
                        continue
                    allocated_grastas[grasta_id] += 1
                    text = f"{grasta.get('display_name', '')} {grasta.get('effect_text', '')}".lower()
                    status_dependent = status_dependent or "pain" in text or "poison" in text

            assumption_text = " ".join(entry.get("upgrade_assumptions", []) if isinstance(entry.get("upgrade_assumptions", []), list) else []).lower()
            status_source = status_source or (
                ("apply" in assumption_text or "inflict" in assumption_text)
                and ("pain" in assumption_text or "poison" in assumption_text)
            )

    duplicates = [value for value, count in Counter(selected_characters).items() if count > 1]
    if duplicates:
        errors.append(_diagnostic("lineup.duplicate_character", path, "Character candidate IDs cannot repeat", list(characters)))

    for equipment_id, assigned in allocated_specific_equipment.items():
        if assigned > 1:
            errors.append(_diagnostic("lineup.duplicate_equipment", path, f"Specific equipment {equipment_id} cannot repeat within one lineup", []))

    all_grastas = {
        choice["id"]: choice
        for character in bundle.get("characters", [])
        for choice in character.get("grastas", [])
    }
    for grasta_id, assigned in allocated_grastas.items():
        grasta = all_grastas.get(grasta_id, {})
        if grasta.get("acquisition_class") == "repeatable":
            continue
        limit = grasta.get("max_theoretical_copies")
        if limit is not None and assigned > limit:
            replacements = sorted({choice["id"] for character_id in selected_characters for choice in characters[character_id].get("grastas", []) if choice["id"] != grasta_id})
            errors.append(_diagnostic("cardinality.grasta", path, f"{grasta_id} assigned {assigned} times but maximum is {limit}", replacements))

    for key in ("main_sidekick_id", "sub_sidekick_id"):
        value = lineup.get(key)
        if value is not None and value not in sidekicks:
            errors.append(_diagnostic("id.sidekick", f"{path}.{key}", "Unknown or unowned sidekick candidate ID", list(sidekicks)))
    if lineup.get("main_sidekick_id") and lineup.get("main_sidekick_id") == lineup.get("sub_sidekick_id"):
        errors.append(_diagnostic("lineup.duplicate_sidekick", path, "Main and sub sidekick IDs must differ", list(sidekicks)))
    sidekick_text = " ".join(
        json.dumps(sidekicks.get(lineup.get(key), {}), ensure_ascii=False)
        for key in ("main_sidekick_id", "sub_sidekick_id")
        if lineup.get(key)
    ).lower()
    status_source = status_source or "pain" in sidekick_text or "poison" in sidekick_text
    if status_dependent and not status_source:
        errors.append(_diagnostic("status.source_missing", path, "Pain/Poison Grasta requires a selected or explicit supported status source", []))

    citation_ids = lineup.get("citation_ids", [])
    if not isinstance(citation_ids, list) or (citations and not citation_ids):
        errors.append(_diagnostic("citation.missing", f"{path}.citation_ids", "At least one graph-backed citation ID is required", list(citations)))
    elif any(citation_id not in citations for citation_id in citation_ids):
        errors.append(_diagnostic("id.citation", f"{path}.citation_ids", "Unknown citation candidate ID", list(citations)))
    fact_ids = lineup.get("boss_fact_ids", [])
    if not isinstance(fact_ids, list) or (boss_facts and not fact_ids) or any(fact_id not in boss_facts for fact_id in fact_ids):
        errors.append(_diagnostic("id.boss_fact", f"{path}.boss_fact_ids", "Unknown boss-fact candidate ID", list(boss_facts)))
    if str(lineup.get("archetype", "")).casefold() not in ARCHETYPES:
        errors.append(_diagnostic("dynamic.archetype", f"{path}.archetype", "Archetype must be burst, sustain, or hybrid", list(ARCHETYPES)))
    for key in ("strategy_summary", "synergy_explanation"):
        if not isinstance(lineup.get(key), str) or not lineup[key].strip():
            errors.append(_diagnostic("dynamic.required_text", f"{path}.{key}", f"{key} is required", []))
    for key in ("build_notes", "boss_counterplay_notes", "sustain_mp_notes", "risks"):
        if not isinstance(lineup.get(key), list) or not lineup[key]:
            errors.append(_diagnostic("dynamic.required_list", f"{path}.{key}", f"{key} must contain at least one entry", []))
    for key in ("fit_label", "confidence_label"):
        if lineup.get(key) not in {"high", "medium", "low"}:
            errors.append(_diagnostic("dynamic.label", f"{path}.{key}", f"{key} must be high, medium, or low", ["high", "medium", "low"]))
    if not isinstance(lineup.get("rubric_summary"), dict) or not lineup["rubric_summary"]:
        errors.append(_diagnostic("dynamic.rubric", f"{path}.rubric_summary", "rubric_summary is required", []))
    return errors


def _validate_equipment_ids(entry: dict, character: dict, path: str) -> list[dict]:
    errors = []
    for key, option_key in (("weapon_id", "weapon_options"), ("armor_id", "armor_options")):
        allowed = [item["id"] for item in character.get(option_key, [])]
        if entry.get(key) not in allowed:
            errors.append(_diagnostic(f"id.{key[:-3]}", f"{path}.{key}", f"Unknown {key[:-3]} candidate ID", allowed))
    return errors


def _diagnostic(code: str, path: str, message: str, allowed_ids: list[str]) -> dict:
    return {"code": code, "path": path, "message": message, "allowed_ids": allowed_ids}


def resolve_candidate_recommendations(proposals: list[dict], bundle: dict, warnings: list[str]) -> dict:
    """Resolve validated IDs to display fields only after deterministic validation."""
    characters = {item["id"]: item for item in bundle.get("characters", [])}
    sidekicks = {item["id"]: item for item in bundle.get("sidekicks", [])}
    citations = {item["id"]: item for item in bundle.get("boss", {}).get("citations", [])}
    resolved = []
    for proposal in proposals:
        lineup = {key: value for key, value in proposal.items() if key not in {
            "frontline", "reserve", "main_sidekick_id", "sub_sidekick_id",
            "citation_ids", "boss_fact_ids",
        }}
        lineup["frontline"] = [_resolve_hero(entry, characters) for entry in proposal["frontline"]]
        lineup["reserve"] = [_resolve_hero(entry, characters) for entry in proposal["reserve"]]
        lineup["main_sidekick"] = sidekicks.get(proposal.get("main_sidekick_id"), {}).get("name")
        lineup["sub_sidekick"] = sidekicks.get(proposal.get("sub_sidekick_id"), {}).get("name")
        lineup["citations"] = [
            {"label": citations[value]["label"], "source_url": citations[value]["source_url"]}
            for value in proposal.get("citation_ids", [])
            if value in citations
        ]
        resolved.append(lineup)
    present = {str(item.get("archetype", "")).casefold() for item in resolved}
    missing = [archetype for archetype in ARCHETYPES if archetype not in present]
    all_warnings = list(warnings)
    if missing:
        all_warnings.append("Missing valid archetypes after correction cap: " + ", ".join(missing))
    return {
        "recommendations": resolved,
        "boss_affinity": bundle.get("boss", {}).get("affinities", {}),
        "archetype_viability_notes": [],
        "warnings": all_warnings,
    }


def _resolve_hero(entry: dict, characters: dict[str, dict]) -> dict:
    character = characters[entry["character_id"]]
    skills = {item["id"]: item for item in character.get("skills", [])}
    passives = {item["id"]: item for item in character.get("passives", [])}
    grastas = {item["id"]: item for item in character.get("grastas", [])}
    weapons = {item["id"]: item for item in character.get("weapon_options", [])}
    armors = {item["id"]: item for item in character.get("armor_options", [])}
    return {
        "name": character["display_name"],
        "role": entry.get("role", "unspecified role"),
        "weapon": weapons[entry["weapon_id"]]["display_name"],
        "armor": armors[entry["armor_id"]]["display_name"],
        "grastas": [grastas[value]["display_name"] for value in entry["grasta_ids"]],
        "recommended_skills": [skills[value]["name"] for value in entry.get("skill_ids", [])],
        "recommended_passives": [passives[value]["name"] for value in entry.get("passive_ids", [])],
        "upgrade_assumptions": entry.get("upgrade_assumptions", []),
    }
