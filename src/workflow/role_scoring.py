"""Deterministic Feature D hard filters, contextual role scores, and skill packages.

This module deliberately consumes only graph-materialized, reviewed atomic facts.
It is a backend policy boundary: no analyzer-provided role text, IDs, coverage, or
scores participates in filtering, ranking, evidence, or packages.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from itertools import combinations
from typing import Any

from .build_packages import DEFAULT_ITEM_POLICY, build_build_package


ROLE_SCORE_POLICY_VERSION = "feature-d-role-score-v1"
SKILL_PACKAGE_POLICY_VERSION = "feature-d2-skill-package-v1"
LIGHT_SHADOW_FOUR_SKILL_THRESHOLD = 80
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
MAX_PACKAGE_OPTIONS = 3

_PACKAGE_PROFILES = {
    "balanced": {
        "primary_damage": 4,
        "offensive_enablement": 3,
        "zone_setup": 2,
        "defense_mitigation": 2,
        "recovery_protection": 2,
        "tank_control": 1,
        "af_support": 2,
        "mp_sustain": 2,
        "boss_counter": 5,
        "reserve_utility": 1,
    },
    "offensive": {
        "primary_damage": 7,
        "offensive_enablement": 6,
        "zone_setup": 3,
        "af_support": 3,
        "boss_counter": 4,
        "defense_mitigation": 1,
        "recovery_protection": 1,
    },
    "sustain": {
        "primary_damage": 3,
        "offensive_enablement": 2,
        "defense_mitigation": 6,
        "recovery_protection": 6,
        "tank_control": 4,
        "mp_sustain": 5,
        "boss_counter": 5,
    },
    "counter": {
        "primary_damage": 2,
        "offensive_enablement": 2,
        "zone_setup": 4,
        "defense_mitigation": 4,
        "recovery_protection": 4,
        "tank_control": 3,
        "af_support": 2,
        "mp_sustain": 3,
        "boss_counter": 12,
    },
}
_PROFILE_ORDER = tuple(_PACKAGE_PROFILES)


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
    light_shadow_points: dict[str, Any] | None = None,
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
    light_shadow_points = light_shadow_points or {}
    entities: list[dict[str, Any]] = []
    for character in sorted(characters, key=_entity_key):
        name = str(character.get("name") or "")
        entity_id = str(character.get("id") or name)
        if not name or not entity_id:
            continue
        state = _sa_state(stellar_awakened.get(name, stellar_awakened.get(entity_id, "unknown")))
        points = _light_shadow_value(light_shadow_points, name, entity_id)
        entities.append(_character_entity(
            entity_id=entity_id,
            name=name,
            character=character,
            facts=facts_by_owner.get(name, []),
            boss=boss,
            sa_state=state,
            light_shadow_points=points,
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
        "skill_package_policy_version": SKILL_PACKAGE_POLICY_VERSION,
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


def _character_entity(*, entity_id: str, name: str, character: dict[str, Any], facts: list[dict[str, Any]], boss: dict[str, Any], sa_state: str, light_shadow_points: int | None, required_counters: list[str], policy_version: str, grastas: list[dict[str, Any]], equipment: list[dict[str, Any]], ores: list[dict[str, Any]], item_policy: str) -> dict[str, Any]:
    executable = [
        fact for fact in facts
        if _is_skill(fact) and _available(fact, sa_state, character, require_equipable=True)
    ]
    passive = [fact for fact in facts if not _is_skill(fact) and _available(fact, sa_state, character)]
    shortlist_by_role = _shortlists(executable, boss, required_counters)
    package_frontier = _skill_package_frontier(
        character=character,
        skills=executable,
        passives=passive,
        boss=boss,
        sa_state=sa_state,
        light_shadow_points=light_shadow_points,
        required_counters=required_counters,
    )
    package_options = package_frontier["options"]
    package = package_options[0] if package_options else _empty_skill_package(
        character=character,
        light_shadow_points=light_shadow_points,
        reason=package_frontier["rejection_reasons"][0] if package_frontier["rejection_reasons"] else "skill_package.unavailable",
    )
    selected_ids = set(package["skill_ids"])
    selected_facts = [fact for fact in executable if _fact_id(fact) in selected_ids]
    score_facts = selected_facts if package_options else executable
    scores, evidence = _scores_and_evidence(
        [*score_facts, *passive], boss, required_counters, placement="frontline"
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
        "light_shadow_points": light_shadow_points,
        "skill_slot_limit": package_frontier["slot_limit"],
        "package_ready": package_frontier["package_ready"],
        "eligible": eligible,
        "rejection_reasons": rejection_reasons,
        "role_scores": scores,
        "role_ids": role_ids,
        "primary_role_id": role_ids[0] if role_ids else None,
        "secondary_role_ids": role_ids[1:3],
        "evidence": evidence,
        "skill_shortlists": shortlist_by_role,
        "skill_package_frontier": package_frontier,
        "skill_packages": package_options,
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


def _skill_package_frontier(
    *,
    character: dict[str, Any],
    skills: list[dict[str, Any]],
    passives: list[dict[str, Any]],
    boss: dict[str, Any],
    sa_state: str,
    light_shadow_points: int | None,
    required_counters: list[str],
) -> dict[str, Any]:
    """Build the bounded, legal skill-package frontier for one character.

    Legal skill families are selected independently of capability proof.  A
    skill without reviewed capabilities can therefore fill a slot, while only
    proven facts contribute to the package's contextual scores and evidence.
    """
    slot_limit = _skill_slot_limit(light_shadow_points)
    family_rows: dict[str, dict[str, Any]] = {}
    for fact in skills:
        family_id = _skill_family_id(fact)
        current = family_rows.get(family_id)
        if current is None or _skill_choice_key(fact) < _skill_choice_key(current):
            family_rows[family_id] = fact
    families = sorted(family_rows.items(), key=lambda item: (item[0], _fact_id(item[1])))
    if len(families) < MIN_PACKAGE_SIZE:
        return {
            "policy_version": SKILL_PACKAGE_POLICY_VERSION,
            "slot_limit": slot_limit,
            "legal_skill_count": len(skills),
            "legal_family_count": len(families),
            "package_ready": False,
            "rejection_reasons": ["skill_package.fewer_than_three_families"],
            "options": [],
        }

    package_size = min(slot_limit, len(families))
    package_pool = _package_combination_pool(
        families=families,
        package_size=package_size,
        passives=passives,
        boss=boss,
        required_counters=required_counters,
    )
    candidates = []
    for profile in _PROFILE_ORDER:
        if not package_pool:
            continue
        selected = max(
            package_pool,
            key=lambda combo: (
                _profile_package_score(combo, passives, boss, required_counters, profile),
                _package_family_key(combo),
            ),
        )
        candidates.append(_make_skill_package(
            character=character,
            selected=selected,
            passives=passives,
            boss=boss,
            required_counters=required_counters,
            slot_limit=slot_limit,
            profile=profile,
        ))

    # Keep one representative for each contextual result before Pareto
    # filtering. Different legal families with identical contextual behavior
    # are equivalent package variants, not three artificial recommendations.
    unique: dict[tuple[Any, ...], dict[str, Any]] = {}
    for package in candidates:
        signature = (
            tuple(package["role_scores"].get(role, 0) for role in ROLE_DIMENSIONS),
            package["contextual_score"],
            tuple(package["proven_capabilities"]),
            tuple(package["dependency_ids"]),
        )
        current = unique.get(signature)
        if current is None or _package_sort_key(package) < _package_sort_key(current):
            unique[signature] = package
    candidates = list(unique.values())
    candidates = [
        package for package in candidates
        if not any(
            other is not package and _package_dominates(other, package)
            for other in candidates
        )
    ]
    candidates.sort(key=_package_sort_key)
    candidates = candidates[:MAX_PACKAGE_OPTIONS]
    return {
        "policy_version": SKILL_PACKAGE_POLICY_VERSION,
        "slot_limit": slot_limit,
        "legal_skill_count": len(skills),
        "legal_family_count": len(families),
        "package_ready": bool(candidates),
        "rejection_reasons": [],
        "options": candidates,
    }


def _package_combination_pool(*, families, package_size, passives, boss, required_counters):
    """Return a bounded deterministic set of family combinations."""
    if len(families) <= 12:
        return [list(combo) for combo in combinations(families, package_size)]
    # Large or malformed legacy kits are bounded without discarding a rare
    # counter: retain the best complete family combination under every profile.
    selected: dict[tuple[str, ...], list[tuple[str, dict[str, Any]]]] = {}
    for profile in _PROFILE_ORDER:
        available = list(families)
        combo = []
        while available and len(combo) < package_size:
            choice = max(
                available,
                key=lambda item: (
                    _profile_package_score([*combo, item], passives, boss, required_counters, profile),
                    tuple(item[0:1]),
                ),
            )
            combo.append(choice)
            available.remove(choice)
        selected[_package_family_key(combo)] = combo
    return list(selected.values())


def _profile_package_score(combo, passives, boss, required_counters, profile):
    facts = [fact for _, fact in combo]
    scores, _ = _scores_and_evidence([*facts, *passives], boss, required_counters, placement="frontline")
    weights = _PACKAGE_PROFILES[profile]
    return sum(scores.get(role, 0) * weight for role, weight in weights.items())


def _make_skill_package(*, character, selected, passives, boss, required_counters, slot_limit, profile):
    facts = [fact for _, fact in selected]
    scores, evidence = _scores_and_evidence(
        [*facts, *passives], boss, required_counters, placement="frontline"
    )
    skill_ids = [_fact_id(fact) for fact in facts]
    family_ids = [family_id for family_id, _ in selected]
    untagged = [
        _fact_id(fact) for fact in facts
        if not _proven_capabilities(fact)
    ]
    proven_capabilities = sorted({
        capability
        for fact in [*facts, *passives]
        for capability in _proven_capabilities(fact)
    })
    dependencies = _package_dependencies(facts)
    contextual_score = _contextual_package_score(scores)
    role_ids = _role_ids(scores)
    package_id = _stable_package_id(
        character.get("id") or character.get("name"),
        family_ids,
        skill_ids,
        slot_limit,
    )
    return {
        "id": package_id,
        "policy_version": SKILL_PACKAGE_POLICY_VERSION,
        "character_id": str(character.get("id") or character.get("name") or ""),
        "character_name": str(character.get("name") or ""),
        "profile": profile,
        "skill_ids": skill_ids,
        "skill_family_ids": family_ids,
        "package_size": len(skill_ids),
        "slot_limit": slot_limit,
        "role_id": role_ids[0] if role_ids else None,
        "role_ids": role_ids,
        "role_scores": scores,
        "contextual_score": contextual_score,
        "evidence": evidence,
        "proven_capabilities": proven_capabilities,
        "untagged_skill_ids": untagged,
        "setup_dependency_ids": dependencies,
        "dependency_ids": dependencies,
        "legal": True,
    }


def _package_dominates(left: dict[str, Any], right: dict[str, Any]) -> bool:
    left_scores = left.get("role_scores", {})
    right_scores = right.get("role_scores", {})
    at_least = all(
        left_scores.get(role, 0) >= right_scores.get(role, 0)
        for role in ROLE_DIMENSIONS
    ) and left.get("contextual_score", 0) >= right.get("contextual_score", 0)
    strictly = (
        left.get("contextual_score", 0) > right.get("contextual_score", 0)
        or any(left_scores.get(role, 0) > right_scores.get(role, 0) for role in ROLE_DIMENSIONS)
    )
    return at_least and strictly


def _package_sort_key(package: dict[str, Any]) -> tuple[Any, ...]:
    scores = package.get("role_scores", {})
    return (
        -int(package.get("contextual_score", 0)),
        -int(scores.get("boss_counter", 0)),
        -int(scores.get("primary_damage", 0)),
        _PROFILE_ORDER.index(package.get("profile")) if package.get("profile") in _PROFILE_ORDER else len(_PROFILE_ORDER),
        tuple(package.get("skill_family_ids", [])),
        str(package.get("id", "")),
    )


def _contextual_package_score(scores: dict[str, int]) -> int:
    weights = {
        "primary_damage": 5,
        "offensive_enablement": 4,
        "zone_setup": 3,
        "defense_mitigation": 3,
        "recovery_protection": 3,
        "tank_control": 2,
        "af_support": 3,
        "mp_sustain": 3,
        "boss_counter": 8,
        "reserve_utility": 1,
    }
    return sum(scores.get(role, 0) * weight for role, weight in weights.items())


def _package_family_key(combo) -> tuple[str, ...]:
    return tuple(sorted(str(family_id) for family_id, _ in combo))


def _package_dependencies(facts: list[dict[str, Any]]) -> list[str]:
    values = set()
    for fact in facts:
        raw = fact.get("dependencies", [])
        if isinstance(raw, str):
            raw = [raw]
        if isinstance(raw, list):
            values.update(str(value) for value in raw if value)
        for key in ("requires_manifest", "requires_equipment"):
            if fact.get(key):
                values.add(_dependency_id(key, fact[key]))
        if fact.get("replaces_skill_id"):
            values.add(_dependency_id("replaces_skill_id", fact["replaces_skill_id"]))
    return sorted(values)


def _dependency_id(prefix: str, value: Any) -> str:
    normalized = "_".join(str(value).casefold().split())
    return f"requires_{prefix.removeprefix('requires_')}:{normalized}"


def _stable_package_id(character_id: Any, family_ids: list[str], skill_ids: list[str], slot_limit: int) -> str:
    raw = "\x1f".join([
        str(character_id), SKILL_PACKAGE_POLICY_VERSION, str(slot_limit),
        *sorted(str(value) for value in family_ids),
        *sorted(str(value) for value in skill_ids),
    ])
    return f"skill-package:{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:20]}"


def _empty_skill_package(*, character: dict[str, Any], light_shadow_points: int | None, reason: str) -> dict[str, Any]:
    slot_limit = _skill_slot_limit(light_shadow_points)
    return {
        "id": None,
        "policy_version": SKILL_PACKAGE_POLICY_VERSION,
        "character_id": str(character.get("id") or character.get("name") or ""),
        "character_name": str(character.get("name") or ""),
        "profile": None,
        "skill_ids": [],
        "skill_family_ids": [],
        "package_size": 0,
        "slot_limit": slot_limit,
        "role_id": None,
        "role_ids": [],
        "role_scores": {role: 0 for role in ROLE_DIMENSIONS},
        "contextual_score": 0,
        "evidence": {role: [] for role in ROLE_DIMENSIONS},
        "proven_capabilities": [],
        "untagged_skill_ids": [],
        "setup_dependency_ids": [],
        "dependency_ids": [],
        "legal": False,
        "rejection_reason": reason,
    }


def _skill_slot_limit(light_shadow_points: int | None) -> int:
    return 4 if light_shadow_points is not None and light_shadow_points >= LIGHT_SHADOW_FOUR_SKILL_THRESHOLD else 3


def _light_shadow_value(values: dict[str, Any], name: str, entity_id: str) -> int | None:
    raw = values.get(name, values.get(entity_id))
    if isinstance(raw, dict):
        raw = raw.get("points", raw.get("light_shadow_points"))
    try:
        value = int(raw) if raw is not None else None
    except (TypeError, ValueError):
        return None
    return value if value is not None and value >= 0 else None


def _skill_choice_key(fact: dict[str, Any]) -> tuple[Any, ...]:
    try:
        rank = int(fact.get("upgrade_rank") or 0)
    except (TypeError, ValueError):
        rank = 0
    return (-rank, -len(_proven_capabilities(fact)), _fact_id(fact))


def _skill_family_id(fact: dict[str, Any]) -> str:
    explicit = fact.get("skill_family_id")
    if explicit:
        return str(explicit)
    name = " ".join(str(fact.get("name") or "").casefold().split())
    name = name.removesuffix(" +").removesuffix(" (sa)")
    owner = str(fact.get("character_name") or "").casefold()
    raw = f"{owner}\x1f{name}"
    return f"skill-family:{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:20]}"


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
                    "skill_id": _fact_id(fact),
                    "skill_family_id": _skill_family_id(fact),
                    "slot_eligibility": _skill_slot_eligibility(fact),
                    "score": score,
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
    evidence_key = "capability_evidence_json" if "capability_evidence_json" in fact else "capability_evidence"
    has_evidence = evidence_key in fact
    evidence = _as_list(fact.get(evidence_key, []))
    evidence_capabilities = {
        str(row.get("value")) for row in evidence
        if isinstance(row, dict) and row.get("kind") == "capability"
        and str(row.get("review_decision", "")).casefold() in {"approve", "correct", "proven"}
    }
    capabilities = {str(value) for value in fact.get("capabilities", []) if value}
    return capabilities & evidence_capabilities if has_evidence else capabilities


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


def _available(
    fact: dict[str, Any],
    sa_state: str,
    character: dict[str, Any] | None = None,
    *,
    require_equipable: bool = False,
) -> bool:
    if fact.get("available") is False or fact.get("legal") is False or fact.get("item_legal") is False:
        return False
    if fact.get("setup_satisfied") is False or fact.get("dependencies_satisfied") is False:
        return False
    if require_equipable and _skill_slot_eligibility(fact) not in {
        "active_equipable", "basic_attack_replacement"
    }:
        return False
    if fact.get("requires_stellar_awakened") and sa_state != "awakened":
        return False
    character = character or {}
    if fact.get("manifest_available") is False or fact.get("equipment_available") is False:
        return False
    if not _named_dependency_available(fact.get("requires_manifest"), character, (
        "available_manifests", "manifest_ids", "unlocked_manifests", "manifest_weapons"
    )):
        return False
    if not _named_dependency_available(fact.get("requires_equipment"), character, (
        "available_equipment", "equipment_ids", "equipped_equipment"
    )):
        return False
    return True


def _skill_slot_eligibility(fact: dict[str, Any]) -> str:
    return str(fact.get("slot_eligibility") or "active_equipable").casefold()


def _named_dependency_available(value: Any, character: dict[str, Any], keys: tuple[str, ...]) -> bool:
    if not value:
        return True
    required = str(value).casefold()
    for key in keys:
        if key not in character:
            continue
        values = character.get(key)
        if not isinstance(values, (list, tuple, set)):
            values = [values]
        normalized = {str(item).casefold() for item in values if item is not None}
        return required in normalized
    return True


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
