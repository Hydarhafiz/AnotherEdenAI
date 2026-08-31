"""Deterministic capability-template lineup generation for Feature F.

The production retrieval and role-scoring layers provide the authoritative
entities consumed here.  This module deliberately does not inspect user prose,
invent capabilities, or call an analyzer.  It turns reviewed role evidence,
selected skill packages, and validated build packages into a bounded set of
legal, scored backend candidates.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from typing import Any, Iterable

from .build_packages import resolve_lineup_allocation


LINEUP_GENERATION_POLICY_VERSION = "feature-f-lineup-v1"
BEAM_WIDTH = 50
MAX_CANDIDATES = 10
MAX_BRANCHING = 12
FRONTLINE_SIZE = 4
RESERVE_SIZE = 2
LINEUP_SIZE = FRONTLINE_SIZE + RESERVE_SIZE

SURVIVAL_ROLES = ("defense_mitigation", "recovery_protection", "tank_control")

CAPABILITY_TEMPLATES: dict[str, dict[str, Any]] = {
    "burst": {
        "mandatory": (
            {"id": "primary_damage", "roles": ("primary_damage",), "label": "credible primary damage"},
            {"id": "offensive_enablement", "roles": ("offensive_enablement",), "label": "damage enablement"},
            {"id": "survival", "roles": SURVIVAL_ROLES, "label": "survival or protection"},
        ),
        "optional": ("af_support", "zone_setup", "boss_counter", "reserve_utility"),
        "slot_roles": ("primary_damage", "offensive_enablement", "zone_setup", "boss_counter", "reserve_utility", "reserve_utility"),
    },
    "sustain": {
        "mandatory": (
            {"id": "primary_damage", "roles": ("primary_damage",), "label": "credible primary damage"},
            {"id": "offensive_enablement", "roles": ("offensive_enablement",), "label": "damage enablement"},
            {"id": "stability", "roles": SURVIVAL_ROLES, "label": "defensive or recovery stability"},
        ),
        "optional": ("mp_sustain", "af_support", "zone_setup", "boss_counter", "reserve_utility"),
        "slot_roles": ("primary_damage", "defense_mitigation", "recovery_protection", "offensive_enablement", "mp_sustain", "reserve_utility"),
    },
    "hybrid": {
        "mandatory": (
            {"id": "primary_damage", "roles": ("primary_damage",), "label": "credible primary damage"},
            {"id": "setup", "roles": ("zone_setup", "offensive_enablement"), "label": "setup or enablement"},
            {"id": "offensive_enablement", "roles": ("offensive_enablement",), "label": "support or damage enablement"},
            {"id": "defensive_reliability", "roles": SURVIVAL_ROLES, "label": "defensive reliability"},
        ),
        "optional": ("af_support", "mp_sustain", "boss_counter", "reserve_utility"),
        "slot_roles": ("primary_damage", "zone_setup", "offensive_enablement", "defense_mitigation", "recovery_protection", "reserve_utility"),
    },
}

SCORING_POLICY: dict[str, Any] = {
    "version": LINEUP_GENERATION_POLICY_VERSION,
    "weights": {
        "coverage": 100,
        "boss_matchup": 18,
        "setup_completeness": 16,
        "synergy": 12,
        "sustain_mitigation": 12,
        "skill_package_readiness": 10,
        "sidekick_contribution": 8,
        "reserve_utility": 8,
        "role_overlap": -2,
        "item_assumption_burden": -2,
        "missing_setup": -20,
        "uncertainty": -4,
    },
    "beam_width": BEAM_WIDTH,
    "max_candidates": MAX_CANDIDATES,
}


def generate_lineup_candidates(
    *,
    characters: list[dict[str, Any]] | None = None,
    sidekicks: list[dict[str, Any]] | None = None,
    boss: dict[str, Any] | None = None,
    role_scores: dict[str, Any] | None = None,
    coverage: dict[str, Any] | None = None,
    max_candidates: int = MAX_CANDIDATES,
    beam_width: int = BEAM_WIDTH,
) -> dict[str, Any]:
    """Generate up to ten legal, diverse lineups with bounded beam search.

    ``role_scores`` is the Feature D backend contract.  ``characters`` and
    ``sidekicks`` are accepted separately so tests and offline evaluation can
    provide a compact fixture without constructing a Pydantic retrieval model.
    """
    role_scores = role_scores or {}
    boss = boss or {}
    characters = characters or []
    sidekicks = sidekicks or []
    beam_width = max(1, min(int(beam_width), BEAM_WIDTH))
    max_candidates = max(1, min(int(max_candidates), MAX_CANDIDATES))

    character_entities = _character_entities(characters, role_scores)
    sidekick_entities = _sidekick_entities(sidekicks, role_scores)
    eligible = {
        entity_id: entity
        for entity_id, entity in character_entities.items()
        if entity.get("eligible", True) and not entity.get("rejection_reasons")
    }
    diagnostics: dict[str, Any] = {
        "policy_version": LINEUP_GENERATION_POLICY_VERSION,
        "beam_width": beam_width,
        "max_candidates": max_candidates,
        "eligible_character_count": len(eligible),
        "requested_character_count": int((coverage or {}).get("requested_character_count", len(characters))),
        "beam_trace": [],
        "pruning_reasons": [],
        "rejection_counts": {},
        "zero_candidate_causes": [],
    }

    if len(eligible) < LINEUP_SIZE:
        diagnostics["zero_candidate_causes"] = ["insufficient_roster"]
        return _result([], diagnostics, status="zero", missing_archetypes=list(CAPABILITY_TEMPLATES))

    if not any(_has_role(entity, "primary_damage") for entity in eligible.values()):
        diagnostics["zero_candidate_causes"] = ["no_usable_primary_damage"]
        return _result([], diagnostics, status="zero", missing_archetypes=list(CAPABILITY_TEMPLATES))

    role_pools = _normalise_role_pools(role_scores, eligible)
    candidates: list[dict[str, Any]] = []
    rejection_counts: Counter[str] = Counter()
    for archetype, template in CAPABILITY_TEMPLATES.items():
        partials = _beam_expand(
            archetype,
            template,
            eligible,
            role_pools,
            beam_width=beam_width,
            trace=diagnostics["beam_trace"],
        )
        for partial in partials:
            sidekick_options = _sidekick_options(sidekick_entities)
            for sidekick_pair in sidekick_options:
                candidate, reasons = _evaluate_candidate(
                    archetype=archetype,
                    character_ids=partial,
                    sidekick_pair=sidekick_pair,
                    template=template,
                    entities=eligible,
                    sidekick_entities=sidekick_entities,
                    role_scores=role_scores,
                    boss=boss,
                )
                if candidate is None:
                    for reason in reasons:
                        rejection_counts[reason] += 1
                    continue
                candidates.append(candidate)

    diagnostics["rejection_counts"] = dict(sorted(rejection_counts.items()))
    if not candidates:
        causes = _dominant_causes(rejection_counts)
        diagnostics["zero_candidate_causes"] = causes or ["missing_mandatory_coverage"]
        diagnostics["pruning_reasons"] = [
            {"reason": cause, "count": rejection_counts[cause]}
            for cause in diagnostics["zero_candidate_causes"]
        ]
        return _result([], diagnostics, status="zero", missing_archetypes=list(CAPABILITY_TEMPLATES))

    deduplicated = _deduplicate_candidates(candidates)
    selected = _select_diverse(deduplicated, max_candidates=max_candidates)
    present_archetypes = {candidate["archetype"] for candidate in selected}
    missing_archetypes = [value for value in CAPABILITY_TEMPLATES if value not in present_archetypes]
    status = "success" if len(selected) >= 3 and not missing_archetypes else "partial"
    diagnostics["pruning_reasons"] = [
        {"reason": "exact_or_near_duplicate", "count": len(candidates) - len(deduplicated)},
        {"reason": "diversity_cap", "count": max(0, len(deduplicated) - len(selected))},
    ]
    return _result(selected, diagnostics, status=status, missing_archetypes=missing_archetypes)


# Verb-first aliases keep the backend contract easy to discover for offline
# evaluation callers without creating a second implementation surface.
generate_candidates = generate_lineup_candidates
generate_backend_candidates = generate_lineup_candidates


def build_capability_templates(
    *,
    boss: dict[str, Any] | None = None,
    role_scores: dict[str, Any] | None = None,
    characters: list[dict[str, Any]] | None = None,
) -> dict[str, dict[str, Any]]:
    """Return the immutable template contract plus context-sensitive gates."""
    boss = boss or {}
    role_scores = role_scores or {}
    entities = _character_entities(characters or [], role_scores)
    dependencies = _lineup_dependencies(entities.values())
    required_counters = _required_counters(boss, role_scores)
    required_setup = _required_setup_roles(boss, dependencies)
    result = {}
    for name, template in CAPABILITY_TEMPLATES.items():
        value = json.loads(json.dumps(template))
        value["required_counters"] = required_counters
        value["required_setup_roles"] = required_setup
        value["requires_mp_sustain"] = _requires_mp_sustain(boss, role_scores)
        result[name] = value
    return result


def score_lineup_candidate(
    candidate: dict[str, Any],
    *,
    entities: dict[str, dict[str, Any]],
    sidekick_entities: dict[str, dict[str, Any]] | None = None,
    boss: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Recompute the public score breakdown for an already-built candidate."""
    sidekick_entities = sidekick_entities or {}
    boss = boss or {}
    character_ids = list(candidate.get("character_ids") or [])
    sidekick_pair = (
        candidate.get("main_sidekick_entity_id"),
        candidate.get("sub_sidekick_entity_id"),
    )
    template = CAPABILITY_TEMPLATES.get(str(candidate.get("archetype")), CAPABILITY_TEMPLATES["hybrid"])
    return _score_candidate(
        character_ids,
        sidekick_pair,
        template,
        entities,
        sidekick_entities,
        boss,
        candidate.get("coverage", {}),
        selected_packages=candidate.get("build_packages") or {},
    )


def evaluate_backend_lineup(
    *,
    archetype: str,
    character_ids: list[str],
    sidekick_pair: tuple[str | None, str | None] = (None, None),
    entities: dict[str, dict[str, Any]],
    sidekick_entities: dict[str, dict[str, Any]] | None = None,
    role_scores: dict[str, Any] | None = None,
    boss: dict[str, Any] | None = None,
) -> tuple[dict[str, Any] | None, list[str]]:
    """Re-run complete backend legality and scoring gates for one lineup."""
    role_scores = role_scores or {}
    sidekick_entities = sidekick_entities or {}
    boss = boss or {}
    template = CAPABILITY_TEMPLATES.get(archetype)
    if template is None:
        return None, ["archetype.invalid"]
    return _evaluate_candidate(
        archetype=archetype,
        character_ids=list(character_ids),
        sidekick_pair=sidekick_pair,
        template=template,
        entities=entities,
        sidekick_entities=sidekick_entities,
        role_scores=role_scores,
        boss=boss,
    )


def _result(candidates, diagnostics, *, status, missing_archetypes):
    return {
        "policy_version": LINEUP_GENERATION_POLICY_VERSION,
        "scoring_policy": SCORING_POLICY,
        "templates": {
            name: {
                "mandatory": list(template["mandatory"]),
                "optional": list(template["optional"]),
                "slot_roles": list(template["slot_roles"]),
            }
            for name, template in CAPABILITY_TEMPLATES.items()
        },
        "status": status,
        "candidates": candidates,
        "candidate_count": len(candidates),
        "missing_archetypes": missing_archetypes,
        "diagnostics": diagnostics,
    }


def _character_entities(characters, role_scores):
    score_entities = {
        str(entity.get("id")): dict(entity)
        for entity in role_scores.get("entities", [])
        if isinstance(entity, dict)
        and entity.get("entity_type", "character") == "character"
        and entity.get("id")
    }
    result = {}
    for character in characters:
        if not isinstance(character, dict):
            continue
        entity_id = str(character.get("id") or character.get("character_id") or "")
        if not entity_id:
            continue
        merged = {**character, **score_entities.get(entity_id, {})}
        merged["id"] = entity_id
        result[entity_id] = merged
    for entity_id, entity in score_entities.items():
        result.setdefault(entity_id, entity)
    return result


def _sidekick_entities(sidekicks, role_scores):
    result = {
        str(entity.get("id")): dict(entity)
        for entity in role_scores.get("entities", [])
        if isinstance(entity, dict)
        and entity.get("entity_type") == "sidekick"
        and entity.get("id")
    }
    by_base = {str(item.get("id")): item for item in sidekicks if isinstance(item, dict) and item.get("id")}
    for entity_id, entity in list(result.items()):
        base_id = entity_id.rsplit(":", 1)[0]
        if base_id in by_base:
            result[entity_id] = {**by_base[base_id], **entity}
    return result


def _normalise_role_pools(role_scores, eligible):
    pools = {}
    raw = role_scores.get("role_pools", {}) if isinstance(role_scores, dict) else {}
    for role in _all_roles():
        values = []
        for item in raw.get(role, []) if isinstance(raw, dict) else []:
            entity_id = str(item.get("entity_id") or "") if isinstance(item, dict) else str(item)
            if entity_id in eligible and entity_id not in values:
                values.append(entity_id)
        if not values:
            values = [entity_id for entity_id in sorted(eligible) if _has_role(eligible[entity_id], role)]
        pools[role] = values[:8]
    return pools


def _beam_expand(archetype, template, entities, role_pools, *, beam_width, trace):
    states: list[tuple[str, ...]] = [()]
    all_ids = sorted(entities)
    for step, role in enumerate(template["slot_roles"], start=1):
        pool = list(role_pools.get(role, []))
        pool.extend(entity_id for entity_id in all_ids if entity_id not in pool)
        pool = pool[:MAX_BRANCHING]
        expanded: set[tuple[str, ...]] = set()
        for state in states:
            for entity_id in pool:
                if entity_id in state:
                    continue
                expanded.add((*state, entity_id))
        ordered = sorted(
            expanded,
            key=lambda value: _partial_sort_key(value, role, entities),
        )
        states = ordered[:beam_width]
        trace.append({
            "archetype": archetype,
            "step": step,
            "role": role,
            "expanded": len(expanded),
            "retained": len(states),
            "beam_width": beam_width,
        })
        if not states:
            break
    return states


def _partial_sort_key(state, next_role, entities):
    role_score = sum(_role_score(entities[entity_id], next_role) for entity_id in state)
    covered = len({role for entity_id in state for role in _role_ids(entities[entity_id])})
    total = sum(sum(_role_score(entities[entity_id], role) for role in _all_roles()) for entity_id in state)
    return (-role_score, -covered, -total, state)


def _sidekick_options(sidekick_entities):
    if not sidekick_entities:
        return [(None, None)]
    mains = sorted(
        (entity_id, entity)
        for entity_id, entity in sidekick_entities.items()
        if str(entity.get("placement")) == "main"
    )
    subs = sorted(
        (entity_id, entity)
        for entity_id, entity in sidekick_entities.items()
        if str(entity.get("placement")) == "sub"
    )
    options: list[tuple[str | None, str | None]] = [(None, None)]
    options.extend((entity_id, None) for entity_id, _ in mains)
    options.extend((None, entity_id) for entity_id, _ in subs)
    options.extend(
        (main_id, sub_id)
        for main_id, main in mains
        for sub_id, sub in subs
        if _sidekick_base(main_id) != _sidekick_base(sub_id)
    )
    return options[: max(1, MAX_BRANCHING)]


def _evaluate_candidate(*, archetype, character_ids, sidekick_pair, template, entities, sidekick_entities, role_scores, boss):
    reasons: list[str] = []
    if len(character_ids) != LINEUP_SIZE or len(set(character_ids)) != LINEUP_SIZE:
        return None, ["lineup.shape"]
    if any(entity_id not in entities for entity_id in character_ids):
        return None, ["character.unavailable"]
    if any(not entities[entity_id].get("eligible", True) for entity_id in character_ids):
        return None, ["character.ineligible"]

    package_options = {
        entity_id: _build_package_options(entities[entity_id])
        for entity_id in character_ids
        if _build_package_options(entities[entity_id])
    }
    if len(package_options) != LINEUP_SIZE:
        reasons.append("build_package.missing")
        allocation = {
            "valid": False,
            "selected_packages": {},
            "selected_package_ids": {},
            "allocation": {"scope": "lineup", "items": []},
            "search": {"states_explored": 0, "max_states": 0, "bounded": True},
        }
    else:
        allocation = resolve_lineup_allocation(package_options, character_ids=list(character_ids))
        if not allocation.get("valid"):
            reasons.append("build_incompatibility")

    selected_packages = allocation.get("selected_packages") or {
        entity_id: entities[entity_id].get("build_package")
        for entity_id in character_ids
        if entities[entity_id].get("build_package")
    }
    coverage = _coverage(
        character_ids,
        sidekick_pair,
        template,
        entities,
        sidekick_entities,
        boss,
        role_scores,
        selected_packages=selected_packages,
    )
    reasons.extend(coverage["missing"])

    for entity_id in character_ids:
        if not _package_ready(entities[entity_id]):
            reasons.append("skill_package.missing_or_unbounded")
    if reasons:
        return None, sorted(set(reasons))

    score = _score_candidate(
        character_ids,
        sidekick_pair,
        template,
        entities,
        sidekick_entities,
        boss,
        coverage,
        selected_packages=selected_packages,
    )
    main_sidekick_id = _public_sidekick_id(sidekick_pair[0], sidekick_entities)
    sub_sidekick_id = _public_sidekick_id(sidekick_pair[1], sidekick_entities)
    package_ids = {
        entity_id: str(selected_packages.get(entity_id, {}).get("id") or entity_id)
        for entity_id in character_ids
    }
    skills = {
        entity_id: list(_default_package(entities[entity_id]).get("skill_ids") or [])
        for entity_id in character_ids
    }
    candidate = {
        "id": _stable_id(
            "lineup",
            archetype,
            *character_ids,
            *package_ids.values(),
            sidekick_pair[0],
            sidekick_pair[1],
        ),
        "archetype": archetype,
        "character_ids": list(character_ids),
        "frontline_character_ids": list(character_ids[:FRONTLINE_SIZE]),
        "reserve_character_ids": list(character_ids[FRONTLINE_SIZE:]),
        "role_assignments": {
            entity_id: list(_role_ids(entities[entity_id]))
            for entity_id in character_ids
        },
        "main_sidekick_entity_id": sidekick_pair[0],
        "sub_sidekick_entity_id": sidekick_pair[1],
        "main_sidekick_id": main_sidekick_id,
        "sub_sidekick_id": sub_sidekick_id,
        "skill_package_ids": skills,
        "build_package_ids": package_ids,
        "build_packages": selected_packages,
        "build_allocation": allocation.get("allocation", {"scope": "lineup", "items": []}),
        "allocation_search": allocation.get("search", {}),
        "coverage": coverage,
        "score": score["score"],
        "component_scores": score["component_scores"],
        "penalties": score["penalties"],
        "assumptions": score["assumptions"],
        "uncertainty": score["uncertainty"],
        "validation": {
            "valid": True,
            "character_count": LINEUP_SIZE,
            "build_allocation": "validated",
            "build_package_ids": package_ids,
            "reason": "survived bounded beam expansion and full-lineup legality gates",
        },
        "pruning_survival_reason": f"{archetype} template coverage-valid candidate retained by deterministic score",
    }
    return candidate, []


def _coverage(character_ids, sidekick_pair, template, entities, sidekick_entities, boss, role_scores, *, selected_packages=None):
    selected_packages = selected_packages or {}
    selected = [entities[entity_id] for entity_id in character_ids]
    selected_sidekicks = [sidekick_entities[entity_id] for entity_id in sidekick_pair if entity_id and entity_id in sidekick_entities]
    all_entities = [*selected, *selected_sidekicks]
    covered_roles = {role for entity in all_entities for role in _role_ids(entity)}
    evidence_by_role: dict[str, list[dict[str, Any]]] = {role: [] for role in _all_roles()}
    capabilities: set[str] = set()
    for entity in all_entities:
        evidence = entity.get("evidence", {})
        for role, rows in evidence.items() if isinstance(evidence, dict) else []:
            if not isinstance(rows, list):
                continue
            evidence_by_role.setdefault(role, []).extend(rows)
            capabilities.update(
                str(row.get("capability"))
                for row in rows
                if isinstance(row, dict) and row.get("capability")
            )

    missing: list[str] = []
    groups = list(template["mandatory"])
    for group in groups:
        if not any(role in covered_roles for role in group["roles"]):
            missing.append(f"mandatory.{group['id']}")

    required_counters = _required_counters(boss, role_scores)
    for required in required_counters:
        if required not in capabilities:
            missing.append(f"mandatory.counter.{required}")

    dependencies = _lineup_dependencies(
        selected_packages.get(entity_id, entity.get("build_package") or {})
        for entity_id, entity in zip(character_ids, selected)
    )
    required_setup_roles = _required_setup_roles(boss, dependencies)
    for required_role in required_setup_roles:
        if required_role not in covered_roles:
            missing.append(f"mandatory.setup.{required_role}")

    if _requires_mp_sustain(boss, role_scores) and "mp_sustain" not in covered_roles:
        if template is CAPABILITY_TEMPLATES["sustain"]:
            missing.append("mandatory.mp_sustain")

    mandatory_ids = [group["id"] for group in groups]
    optional = [role for role in template["optional"] if role in covered_roles]
    return {
        "mandatory": mandatory_ids,
        "optional": optional,
        "covered_roles": sorted(covered_roles),
        "missing": sorted(set(missing)),
        "required_boss_counters": required_counters,
        "provided_capabilities": sorted(capabilities),
        "evidence": {
            role: sorted(rows, key=lambda row: json.dumps(row, sort_keys=True, ensure_ascii=False))
            for role, rows in evidence_by_role.items()
            if rows
        },
        "setup_dependencies": sorted(dependencies),
    }


def _score_candidate(character_ids, sidekick_pair, template, entities, sidekick_entities, boss, coverage, *, selected_packages=None):
    selected_packages = selected_packages or {}
    selected = [entities[entity_id] for entity_id in character_ids]
    frontline = selected[:FRONTLINE_SIZE]
    reserve = selected[FRONTLINE_SIZE:]
    sidekicks = [sidekick_entities[entity_id] for entity_id in sidekick_pair if entity_id and entity_id in sidekick_entities]
    all_entities = [*selected, *sidekicks]
    mandatory_count = len(coverage.get("mandatory", []))
    missing_count = len(coverage.get("missing", []))
    covered_count = mandatory_count - missing_count
    primary = sum(_role_score(entity, "primary_damage") for entity in selected)
    matchup = primary + (primary if boss.get("weak") else 0)
    setup = max(0, len(coverage.get("setup_dependencies", [])) - len([item for item in coverage.get("missing", []) if ".setup." in item]))
    synergy = sum(max(0, len(_role_ids(entity)) - 1) for entity in selected)
    sustain = sum(_role_score(entity, role) for entity in selected for role in SURVIVAL_ROLES + ("mp_sustain",))
    package_ready = sum(1 for entity in selected if _package_ready(entity))
    sidekick_score = sum(sum(_role_score(entity, role) for role in _all_roles()) for entity in sidekicks)
    reserve_utility = sum(_role_score(entity, "reserve_utility") + _role_score(entity, "mp_sustain") for entity in reserve)
    role_counts = Counter(role for entity in frontline for role in _role_ids(entity))
    overlap = sum(max(0, count - 2) for count in role_counts.values())
    assumption_count = sum(
        len((selected_packages.get(entity_id, entity.get("build_package") or {}).get("assumptions") or []))
        + int(selected_packages.get(entity_id, entity.get("build_package") or {}).get("generic_placeholder_count") or 0)
        for entity_id, entity in zip(character_ids, selected)
    )
    uncertainty_count = sum(
        1 for entity in all_entities
        if entity.get("sa_state") == "unknown" or not entity.get("evidence")
    )
    component_scores = {
        "coverage": max(0, covered_count) / max(1, mandatory_count) * 100,
        "boss_matchup": matchup,
        "setup_completeness": setup,
        "synergy": synergy,
        "sustain_mitigation": sustain,
        "skill_package_readiness": package_ready,
        "sidekick_contribution": sidekick_score,
        "reserve_utility": reserve_utility,
        "role_overlap": overlap,
        "item_assumption_burden": assumption_count,
        "missing_setup": sum(1 for item in coverage.get("missing", []) if ".setup." in item),
        "uncertainty": uncertainty_count,
    }
    weights = SCORING_POLICY["weights"]
    score = sum(component_scores[key] * weights[key] for key in component_scores)
    penalties = []
    if assumption_count:
        penalties.append({"code": "item_assumption_burden", "amount": assumption_count, "message": "Build package contains unverified late-game assumptions."})
    if overlap:
        penalties.append({"code": "role_overlap", "amount": overlap, "message": "Frontline roles have redundant coverage."})
    if coverage.get("missing"):
        penalties.append({"code": "missing_setup", "amount": missing_count, "message": "Mandatory coverage or setup is missing."})
    if uncertainty_count:
        penalties.append({"code": "uncertainty", "amount": uncertainty_count, "message": "One or more selected facts have unknown evidence or state."})
    assumptions = sorted({
        assumption
        for entity_id, entity in zip(character_ids, selected)
        for assumption in (selected_packages.get(entity_id, entity.get("build_package") or {}).get("assumptions", []))
    })
    return {
        "score": round(float(score), 4),
        "component_scores": component_scores,
        "penalties": penalties,
        "assumptions": assumptions,
        "uncertainty": {
            "count": uncertainty_count,
            "boss_affinity_state": role_scores_affinity_state(boss),
        },
    }


def _deduplicate_candidates(candidates):
    exact: dict[tuple, dict[str, Any]] = {}
    for candidate in sorted(candidates, key=_candidate_sort_key):
        key = (
            candidate["archetype"],
            tuple(sorted(candidate["character_ids"])),
            candidate.get("main_sidekick_id"),
            candidate.get("sub_sidekick_id"),
            tuple(
                sorted(
                    (entity_id, tuple(skill_ids))
                    for entity_id, skill_ids in candidate.get("skill_package_ids", {}).items()
                )
            ),
            tuple(sorted(candidate.get("build_package_ids", {}).items())),
        )
        exact.setdefault(key, candidate)
    unique = list(exact.values())
    retained: list[dict[str, Any]] = []
    for candidate in sorted(unique, key=_candidate_sort_key):
        if any(
            candidate["archetype"] == existing["archetype"]
            and _jaccard(candidate["character_ids"], existing["character_ids"]) >= 5 / 6
            and candidate.get("coverage", {}).get("covered_roles") == existing.get("coverage", {}).get("covered_roles")
            for existing in retained
        ):
            continue
        retained.append(candidate)
    return retained


def _select_diverse(candidates, *, max_candidates):
    ordered = sorted(candidates, key=_candidate_sort_key)
    selected: list[dict[str, Any]] = []
    for archetype in CAPABILITY_TEMPLATES:
        candidate = next((item for item in ordered if item["archetype"] == archetype), None)
        if candidate and candidate not in selected:
            selected.append(candidate)
    for candidate in ordered:
        if len(selected) >= max_candidates:
            break
        if candidate in selected:
            continue
        if any(_jaccard(candidate["character_ids"], item["character_ids"]) >= 5 / 6 for item in selected):
            continue
        selected.append(candidate)
    return sorted(selected, key=_candidate_sort_key)


def _candidate_sort_key(candidate):
    return (-float(candidate.get("score", 0)), str(candidate.get("archetype", "")), str(candidate.get("id", "")))


def _jaccard(left: Iterable[str], right: Iterable[str]) -> float:
    left_set, right_set = set(left), set(right)
    return len(left_set & right_set) / max(1, len(left_set | right_set))


def _dominant_causes(counts):
    if not counts:
        return []
    grouped = Counter()
    for reason, count in counts.items():
        if reason.startswith("mandatory.counter."):
            grouped["missing_mandatory_counter"] += count
        elif reason.startswith("mandatory.setup."):
            grouped["missing_mandatory_setup"] += count
        elif reason.startswith("mandatory."):
            grouped["missing_mandatory_coverage"] += count
        else:
            grouped[reason] += count
    return [reason for reason, _ in sorted(grouped.items(), key=lambda item: (-item[1], item[0]))[:3]]


def _required_counters(boss, role_scores):
    values = [
        *_values(boss.get("required_counters")),
        *_values(boss.get("required_capabilities")),
        *_values(role_scores.get("required_boss_counters")),
    ]
    return sorted({str(value) for value in values if value})


def _required_setup_roles(boss, dependencies):
    values = [*_values(boss.get("required_setup_roles"))]
    if boss.get("requires_zone") or "zone" in {str(tag).casefold() for tag in _values(boss.get("mechanic_tags"))}:
        values.append("zone_setup")
    mapping = {
        "requires_zone": "zone_setup",
        "requires_zone_setup": "zone_setup",
        "requires_status_immunity": "recovery_protection",
        "requires_cleanse": "recovery_protection",
        "requires_mp": "mp_sustain",
        "requires_mp_sustain": "mp_sustain",
    }
    values.extend(mapping[value] for value in dependencies if value in mapping)
    return sorted(set(values))


def _lineup_dependencies(entities):
    dependencies = set()
    for entity in entities:
        if not isinstance(entity, dict):
            continue
        package = entity.get("build_package") if isinstance(entity.get("build_package"), dict) else {}
        for value in [
            *_values(entity.get("setup_dependencies")),
            *_values(entity.get("dependencies")),
            *_values(package.get("setup_dependencies")),
            *_values(package.get("dependencies")),
        ]:
            normalized = str(value).casefold().replace(" ", "_")
            if normalized and not normalized.startswith("requires_"):
                normalized = "requires_" + normalized
            if normalized:
                dependencies.add(normalized)
    return dependencies


def _requires_mp_sustain(boss, role_scores):
    tags = {str(value).casefold() for value in _values(boss.get("mechanic_tags"))}
    return bool(
        "recover_mp" in _required_counters(boss, role_scores)
        or tags & {"mp", "long_fight", "attrition", "sustain"}
        or boss.get("requires_mp_sustain")
    )


def _has_role(entity, role):
    return role in _role_ids(entity) or _role_score(entity, role) > 0


def _role_ids(entity):
    values = set(str(value) for value in _values(entity.get("role_ids")) if value)
    values.update(role for role, score in (entity.get("role_scores") or {}).items() if _numeric(score) > 0)
    return sorted(values)


def _all_roles():
    return (
        "primary_damage", "offensive_enablement", "zone_setup", "defense_mitigation",
        "recovery_protection", "tank_control", "af_support", "mp_sustain",
        "boss_counter", "reserve_utility",
    )


def _role_score(entity, role):
    return _numeric((entity.get("role_scores") or {}).get(role))


def _numeric(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _values(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return list(value)
    return [value]


def _default_package(entity):
    package = entity.get("default_package")
    return package if isinstance(package, dict) else {}


def _build_package_options(entity):
    options = entity.get("build_package_options")
    if isinstance(options, list):
        valid = [option for option in options if isinstance(option, dict) and option.get("id")]
        if valid:
            return valid
    package = entity.get("build_package")
    if isinstance(package, dict) and package.get("id"):
        alternatives = package.get("alternatives") or package.get("options") or []
        return [package, *[option for option in alternatives if isinstance(option, dict) and option.get("id")]]
    return []


def _package_ready(entity):
    package = _default_package(entity)
    skill_ids = package.get("skill_ids")
    return isinstance(skill_ids, list) and 3 <= len(skill_ids) <= 4


def _sidekick_base(entity_id):
    return str(entity_id or "").rsplit(":", 1)[0]


def _public_sidekick_id(entity_id, entities):
    if not entity_id:
        return None
    entity = entities.get(entity_id, {})
    return str(entity.get("source_sidekick_id") or _sidekick_base(entity_id))


def role_scores_affinity_state(boss):
    if boss.get("affinity_complete") is False:
        return "incomplete"
    if boss.get("weakness_known") is False:
        return "unknown"
    if boss.get("weak"):
        return "weakness_available"
    return "confirmed_no_weakness"


def _stable_id(prefix, *parts):
    normalized = "\x1f".join(str(part or "").strip().casefold() for part in parts)
    return f"{prefix}:{hashlib.sha256(normalized.encode('utf-8')).hexdigest()[:20]}"
