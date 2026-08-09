"""Deterministic Feature D hard filters, contextual role scores, and skill packages.

This module deliberately consumes only graph-materialized, reviewed atomic facts.
It is a backend policy boundary: no analyzer-provided role text, IDs, coverage, or
scores participates in filtering, ranking, evidence, or packages.
"""

from __future__ import annotations

import json
from collections import defaultdict
from typing import Any

from .build_packages import DEFAULT_ITEM_POLICY, build_build_package


ROLE_SCORE_POLICY_VERSION = "feature-d-role-score-v1"
ROLE_DIMENSIONS = (
    "primary_damage",
    "offensive_enablement",
    "zone_setup",
    "defense_mitigation",
    "recovery_protection",
    "tank_control",
    "af_support",
    "mp_sustain",
    "boss_counter",
    "reserve_utility",
)
MAX_POOL_SIZE = 8
MAX_COUNTER_EXCEPTIONS = 4
MIN_SHORTLIST_SIZE = 4
MAX_SHORTLIST_SIZE = 6
MIN_PACKAGE_SIZE = 3
MAX_PACKAGE_SIZE = 4


_ROLE_CAPABILITIES = {
    "primary_damage": {"direct_damage", "fixed_damage", "attack_again", "chain_attack", "follow_up_attack"},
    "offensive_enablement": {
        "outgoing_damage_up", "enemy_resistance_down", "physical_resistance_down",
        "magic_resistance_down", "attack_type_resistance_down", "element_resistance_down",
        "power_up", "intelligence_up", "speed_up", "luck_up", "weakness_multiplier_up",
        "physical_critical_rate_up", "magic_critical_rate_up", "physical_critical_damage_up",
        "magic_critical_damage_up", "equipped_weapon_damage_up", "attack_type_damage_up",
        "element_damage_up", "non_type_damage_up", "grant_mental_focus", "grant_singular_focus",
        "grant_eagle_eyes", "grant_overthrow", "grant_physical_overcritical",
        "grant_magic_overcritical", "inflict_pain", "inflict_poison", "inflict_break",
        "apply_kaleido", "grant_link", "grant_copy", "activate_lunatic",
    },
    "zone_setup": {"deploy_zone", "awaken_zone"},
    "defense_mitigation": {"damage_reduction", "damage_reduction_barrier", "shield", "ally_resistance_up", "hold_ground", "dodge"},
    "recovery_protection": {"heal_hp", "regen_hp", "revive", "remove_status_ailment", "remove_debuff", "grant_status_immunity", "knockback_immunity"},
    "tank_control": {"taunt", "cover", "guard", "stalk", "hold_ground", "dodge"},
    "af_support": {"af_gauge_restore", "af_gauge_gain_up", "af_combo_gain_up", "af_damage_up"},
    "mp_sustain": {"recover_mp"},
    "boss_counter": {
        "remove_status_ailment", "remove_debuff", "grant_status_immunity", "knockback_immunity",
        "damage_reduction", "damage_reduction_barrier", "shield", "ally_resistance_up",
        "recover_mp", "barrier_pierce", "ignore_target_defense", "invert_weakness_resistance",
    },
    "reserve_utility": {"recover_mp", "af_gauge_restore", "af_gauge_gain_up", "grant_status_immunity", "heal_hp", "regen_hp"},
}


def derive_contextual_role_scores(
    *,
    boss: dict[str, Any],
    characters: list[dict[str, Any]],
    skills: list[dict[str, Any]],
    passives: list[dict[str, Any]],
    sidekicks: list[dict[str, Any]],
    stellar_awakened: dict[str, Any],
    mechanics: list[dict[str, Any]] | None = None,
    grastas: list[dict[str, Any]] | None = None,
    equipment: list[dict[str, Any]] | None = None,
    ores: list[dict[str, Any]] | None = None,
    item_policy: str = DEFAULT_ITEM_POLICY,
    policy_version: str = ROLE_SCORE_POLICY_VERSION,
) -> dict[str, Any]:
    """Build reproducible Feature D score/output records from typed retrieval facts."""
    facts_by_owner: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for fact in [*skills, *passives]:
        owner = str(fact.get("character_name") or "")
        if owner:
            facts_by_owner[owner].append(fact)

    counters = _required_boss_counters(boss, mechanics or [])
    entities: list[dict[str, Any]] = []
    for character in sorted(characters, key=_entity_key):
        name = str(character.get("name") or "")
        entity_id = str(character.get("id") or name)
        if not name or not entity_id:
            continue
        state = _sa_state(stellar_awakened.get(name, stellar_awakened.get(entity_id, "unknown")))
        entities.append(_character_entity(
            entity_id=entity_id,
            name=name,
            character=character,
            facts=facts_by_owner.get(name, []),
            boss=boss,
            sa_state=state,
            required_counters=counters,
            policy_version=policy_version,
            grastas=grastas or [],
            equipment=equipment or [],
            ores=ores or [],
            item_policy=item_policy,
        ))
    for sidekick in sorted(sidekicks, key=_entity_key):
        entities.extend(_sidekick_entities(sidekick, boss, counters, policy_version))

    pools = _role_pools(entities, counters)
    artifact_versions = sorted({
        str(version) for entity in entities for version in entity.get("artifact_versions", []) if version
    })
    return {
        "policy_version": policy_version,
        "role_dimensions": list(ROLE_DIMENSIONS),
        "artifact_versions": artifact_versions,
        "affinity_state": _affinity_state(boss),
        "required_boss_counters": counters,
        "entities": sorted(entities, key=lambda value: value["id"]),
        "role_pools": pools,
        "build_packages": {
            entity["id"]: entity["build_package"]
            for entity in entities
            if entity.get("entity_type") == "character" and entity.get("build_package")
        },
    }


def _character_entity(*, entity_id: str, name: str, character: dict[str, Any], facts: list[dict[str, Any]], boss: dict[str, Any], sa_state: str, required_counters: list[str], policy_version: str, grastas: list[dict[str, Any]], equipment: list[dict[str, Any]], ores: list[dict[str, Any]], item_policy: str) -> dict[str, Any]:
    executable = [fact for fact in facts if _is_skill(fact) and _available(fact, sa_state)]
    passive = [fact for fact in facts if not _is_skill(fact) and _available(fact, sa_state)]
    shortlist_by_role = _shortlists(executable, boss, required_counters)
    package = _default_package(shortlist_by_role)
    selected_ids = set(package["skill_ids"])
    selected_facts = [fact for fact in executable if _fact_id(fact) in selected_ids]
    scores, evidence = _scores_and_evidence(
        [*selected_facts, *passive], boss, required_counters, placement="frontline"
    )
    rejection_reasons = _character_rejections(executable, boss)
    if character.get("eligible") is False or character.get("ownership_valid") is False or character.get("item_legal") is False:
        rejection_reasons = ["character.ownership_or_item_illegal", *rejection_reasons]
    eligible = not rejection_reasons
    role_ids = _role_ids(scores) if eligible else []
    entity = {
        "id": entity_id,
        "name": name,
        "entity_type": "character",
        "placement": "frontline",
        "sa_state": sa_state,
        "eligible": eligible,
        "rejection_reasons": rejection_reasons,
        "role_scores": scores,
        "role_ids": role_ids,
        "primary_role_id": role_ids[0] if role_ids else None,
        "secondary_role_ids": role_ids[1:3],
        "evidence": evidence,
        "skill_shortlists": shortlist_by_role,
        "default_package": package,
        "artifact_versions": _artifact_versions([*executable, *passive]),
        "policy_version": policy_version,
        "source_character_id": character.get("id"),
    }
    entity["build_package"] = build_build_package(
        character,
        role_entity=entity,
        grastas=grastas,
        equipment=equipment,
        ores=ores,
        selected_facts=[*selected_facts, *passive],
        item_policy=item_policy,
    )
    return entity


def _sidekick_entities(sidekick: dict[str, Any], boss: dict[str, Any], required_counters: list[str], policy_version: str) -> list[dict[str, Any]]:
    name = str(sidekick.get("name") or "")
    base_id = str(sidekick.get("id") or name)
    if not name or not base_id:
        return []
    skills = [fact for fact in sidekick.get("skills", []) if isinstance(fact, dict)]
    auras = [fact for fact in sidekick.get("auras", []) if isinstance(fact, dict)]
    results = []
    for placement in ("main", "sub"):
        placement_facts = [
            fact for fact in [*skills, *auras]
            if _sidekick_fact_available(fact, placement)
        ]
        scores, evidence = _scores_and_evidence(placement_facts, boss, required_counters, placement=placement)
        role_ids = _role_ids(scores)
        results.append({
            "id": f"{base_id}:{placement}",
            "name": name,
            "entity_type": "sidekick",
            "placement": placement,
            "sa_state": "not_applicable",
            "eligible": True,
            "rejection_reasons": [],
            "role_scores": scores,
            "role_ids": role_ids,
            "primary_role_id": role_ids[0] if role_ids else None,
            "secondary_role_ids": role_ids[1:3],
            "evidence": evidence,
            "skill_shortlists": {},
            "default_package": {"skill_ids": [], "package_size": 0, "role_id": None},
            "artifact_versions": _artifact_versions(placement_facts),
            "policy_version": policy_version,
            "source_sidekick_id": sidekick.get("id"),
        })
    return results


def _shortlists(skills: list[dict[str, Any]], boss: dict[str, Any], required_counters: list[str]) -> dict[str, list[dict[str, Any]]]:
    shortlists: dict[str, list[dict[str, Any]]] = {}
    for role in ROLE_DIMENSIONS:
        choices = []
        for fact in skills:
            capabilities = _proven_capabilities(fact)
            score = len(capabilities & _ROLE_CAPABILITIES[role])
            if role == "primary_damage" and _usable_primary(fact, boss):
                score += 2
            if role == "boss_counter":
                score += 2 * len(capabilities & set(required_counters))
            if score:
                choices.append({
                    "skill_id": _fact_id(fact), "score": score,
                    "evidence_ids": _evidence_ids(fact, capabilities & _ROLE_CAPABILITIES[role]),
                })
        choices.sort(key=lambda value: (-value["score"], value["skill_id"]))
        if choices:
            shortlists[role] = choices[:MAX_SHORTLIST_SIZE]
    return shortlists


def _default_package(shortlists: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    ordered: list[tuple[int, str, str]] = []
    for role, choices in shortlists.items():
        for choice in choices:
            ordered.append((-choice["score"], choice["skill_id"], role))
    ordered.sort()
    selected: list[str] = []
    role_id = None
    for _, skill_id, role in ordered:
        if skill_id not in selected:
            selected.append(skill_id)
            role_id = role_id or role
        if len(selected) == MAX_PACKAGE_SIZE:
            break
    return {"skill_ids": selected[:MAX_PACKAGE_SIZE], "package_size": len(selected), "role_id": role_id}


def _character_rejections(skills: list[dict[str, Any]], boss: dict[str, Any]) -> list[str]:
    damaging = [fact for fact in skills if "direct_damage" in _proven_capabilities(fact)]
    if not damaging:
        # A pure healer, tank, or enabler is still a viable contextual candidate;
        # it simply cannot enter the primary-damage pool.
        return []
    usable = [fact for fact in damaging if _usable_primary(fact, boss)]
    if usable:
        return []
    blocked = [fact for fact in damaging if _affinity(fact) in _blocked_affinities(boss)]
    if blocked:
        return ["primary_damage.null_or_absorb"]
    return ["primary_damage.no_neutral_or_better"]


def _scores_and_evidence(facts: list[dict[str, Any]], boss: dict[str, Any], required_counters: list[str], *, placement: str) -> tuple[dict[str, int], dict[str, list[dict[str, str]]]]:
    scores = {role: 0 for role in ROLE_DIMENSIONS}
    evidence = {role: [] for role in ROLE_DIMENSIONS}
    required = set(required_counters)
    for fact in facts:
        capabilities = _proven_capabilities(fact)
        for role, accepted in _ROLE_CAPABILITIES.items():
            matched = capabilities & accepted
            if matched:
                scores[role] += len(matched)
                evidence[role].extend(_evidence(fact, matched, placement))
        if "direct_damage" in capabilities and _usable_primary(fact, boss):
            scores["primary_damage"] += 2
        matched_counters = capabilities & required
        if matched_counters:
            scores["boss_counter"] += 2 * len(matched_counters)
            evidence["boss_counter"].extend(_evidence(fact, matched_counters, placement))
    for role in ROLE_DIMENSIONS:
        evidence[role].sort(key=lambda value: (value["fact_id"], value["capability"], value["evidence_id"]))
    return scores, evidence


def _role_pools(entities: list[dict[str, Any]], required_counters: list[str]) -> dict[str, list[dict[str, Any]]]:
    pools = {}
    for role in ROLE_DIMENSIONS:
        eligible = [entity for entity in entities if entity["eligible"] and entity["role_scores"][role] > 0]
        eligible.sort(key=lambda entity: (-entity["role_scores"][role], entity["id"]))
        normal = eligible[:MAX_POOL_SIZE]
        if role == "boss_counter" and required_counters:
            exceptions = [
                entity for entity in eligible[MAX_POOL_SIZE:]
                if _covers_required_counter(entity, required_counters)
            ][:MAX_COUNTER_EXCEPTIONS]
            normal.extend(exceptions)
        pools[role] = [
            {
                "entity_id": entity["id"],
                "score": entity["role_scores"][role],
                "counter_exception": entity in normal[MAX_POOL_SIZE:],
                "evidence": entity["evidence"][role],
            }
            for entity in normal
        ]
    return pools


def _covers_required_counter(entity: dict[str, Any], required_counters: list[str]) -> bool:
    provided = {row["capability"] for row in entity["evidence"]["boss_counter"]}
    return bool(provided & set(required_counters))


def _proven_capabilities(fact: dict[str, Any]) -> set[str]:
    state = str(fact.get("review_state") or fact.get("capability_review_state") or "").casefold()
    if state in {"candidate", "rejected", "dependency-only", "ambiguous", "untagged", "missing"}:
        return set()
    diagnostics = _as_mapping(fact.get("capability_diagnostics_json", fact.get("capability_diagnostics", {})))
    if any(diagnostics.get(key) for key in ("candidate", "rejected", "ambiguous", "untagged")) and not diagnostics.get("proven"):
        return set()
    evidence = _as_list(fact.get("capability_evidence_json", fact.get("capability_evidence", [])))
    evidence_capabilities = {
        str(row.get("value")) for row in evidence
        if isinstance(row, dict) and row.get("kind") == "capability"
        and str(row.get("review_decision", "")).casefold() in {"approve", "correct", "proven"}
    }
    capabilities = {str(value) for value in fact.get("capabilities", []) if value}
    return capabilities & evidence_capabilities if evidence else capabilities


def _evidence(fact: dict[str, Any], capabilities: set[str], placement: str) -> list[dict[str, str]]:
    fact_id = _fact_id(fact)
    raw = _as_list(fact.get("capability_evidence_json", fact.get("capability_evidence", [])))
    entries = []
    for capability in sorted(capabilities):
        matched = [row for row in raw if isinstance(row, dict) and row.get("kind") == "capability" and row.get("value") == capability]
        if matched:
            for row in matched:
                entries.append({"fact_id": fact_id, "capability": capability, "evidence_id": str(row.get("source_id") or row.get("source_fact_id") or fact_id), "placement": placement})
        else:
            entries.append({"fact_id": fact_id, "capability": capability, "evidence_id": fact_id, "placement": placement})
    return entries


def _evidence_ids(fact: dict[str, Any], capabilities: set[str]) -> list[str]:
    return sorted({row["evidence_id"] for row in _evidence(fact, capabilities, "frontline")})


def _required_boss_counters(boss: dict[str, Any], mechanics: list[dict[str, Any]]) -> list[str]:
    values = list(boss.get("required_counters", [])) + list(boss.get("required_capabilities", []))
    for mechanic in mechanics:
        values.extend(mechanic.get("required_counters", []) if isinstance(mechanic, dict) else [])
        values.extend(mechanic.get("required_capabilities", []) if isinstance(mechanic, dict) else [])
    tags = {str(tag).casefold() for tag in boss.get("mechanic_tags", [])}
    if tags & {"status", "ailment"}:
        values.append("grant_status_immunity")
    if "mp" in tags:
        values.append("recover_mp")
    return sorted({str(value) for value in values if str(value) in _ROLE_CAPABILITIES["boss_counter"]})


def _usable_primary(fact: dict[str, Any], boss: dict[str, Any]) -> bool:
    affinity = _affinity(fact)
    unfavorable = _blocked_affinities(boss) | _resisted_affinities(boss)
    return "direct_damage" in _proven_capabilities(fact) and bool(affinity) and affinity not in unfavorable


def _blocked_affinities(boss: dict[str, Any]) -> set[str]:
    return {_normalize_affinity(value) for value in [*boss.get("null", []), *boss.get("absorb", [])]}


def _resisted_affinities(boss: dict[str, Any]) -> set[str]:
    return {_normalize_affinity(value) for value in boss.get("resist", [])}


def _affinity(fact: dict[str, Any]) -> str:
    return _normalize_affinity(fact.get("element") or fact.get("affinity"))


def _normalize_affinity(value: Any) -> str:
    return str(value or "").strip().casefold()


def _affinity_state(boss: dict[str, Any]) -> str:
    if boss.get("affinity_complete") is False:
        return "incomplete"
    if boss.get("weakness_known") is False:
        return "unknown"
    if boss.get("weak"):
        return "weakness_available"
    return "confirmed_no_weakness"


def _is_skill(fact: dict[str, Any]) -> bool:
    return bool(fact.get("skill_id") or str(fact.get("id", "")).startswith("skill:"))


def _available(fact: dict[str, Any], sa_state: str) -> bool:
    if fact.get("available") is False or fact.get("legal") is False or fact.get("item_legal") is False:
        return False
    if fact.get("setup_satisfied") is False or fact.get("dependencies_satisfied") is False:
        return False
    return not fact.get("requires_stellar_awakened") or sa_state == "awakened"


def _sidekick_fact_available(fact: dict[str, Any], placement: str) -> bool:
    availability = str(fact.get("availability") or fact.get("sidekick_availability") or "")
    if not availability:
        evidence = _as_list(fact.get("capability_evidence_json", fact.get("capability_evidence", [])))
        availability = next((str(row.get("availability")) for row in evidence if isinstance(row, dict) and row.get("availability")), "main_or_sub")
    return availability == "main_or_sub" or (availability == "main_only" and placement == "main")


def _role_ids(scores: dict[str, int]) -> list[str]:
    return [role for role, score in sorted(scores.items(), key=lambda pair: (-pair[1], pair[0])) if score > 0]


def _artifact_versions(facts: list[dict[str, Any]]) -> list[str]:
    return sorted({str(fact.get("capability_artifact_version") or fact.get("artifact_version") or "") for fact in facts if fact.get("capability_artifact_version") or fact.get("artifact_version")})


def _fact_id(fact: dict[str, Any]) -> str:
    return str(fact.get("id") or fact.get("skill_id") or fact.get("passive_skill_id") or fact.get("sidekick_skill_id") or fact.get("sidekick_aura_id") or fact.get("name") or "unknown")


def _entity_key(value: dict[str, Any]) -> tuple[str, str]:
    return str(value.get("id") or ""), str(value.get("name") or "")


def _sa_state(value: Any) -> str:
    if value is True or value == "awakened":
        return "awakened"
    if value is False or value == "not_awakened":
        return "not_awakened"
    return "unknown"


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return []
        return parsed if isinstance(parsed, list) else []
    return []


def _as_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}
