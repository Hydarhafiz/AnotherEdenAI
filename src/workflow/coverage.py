"""Deterministic request-time coverage and candidate-diversity diagnostics."""

from __future__ import annotations

import json
from itertools import combinations
from typing import Any, Iterable, Mapping

from src.etl.coverage_baseline import (
    FEATURE_A_METRIC_CONTRACT_VERSION,
    metric_contract,
)


def build_request_coverage_report(
    *,
    user_roster: Iterable[str],
    f2p_augmented_roster: Iterable[str],
    characters: Iterable[Mapping[str, Any]],
    role_scores: Mapping[str, Any],
    candidate_generation: Mapping[str, Any],
) -> dict[str, Any]:
    """Account for each request stage without conflating catalog and candidates."""
    user_names = _distinct_strings(user_roster)
    available_names = _distinct_strings(f2p_augmented_roster)
    user_name_set = set(user_names)
    f2p_added_names = {name for name in available_names if name not in user_name_set}
    character_rows = [character for character in characters if isinstance(character, Mapping)]
    retrieved_names = {
        str(character.get("name"))
        for character in character_rows
        if character.get("name")
    }
    available_ids = {
        str(character.get("id") or character.get("character_id") or character.get("name"))
        for character in character_rows
        if character.get("id") or character.get("character_id") or character.get("name")
    }
    entities = {
        str(entity.get("id")): entity
        for entity in role_scores.get("entities", [])
        if isinstance(entity, Mapping)
        and entity.get("entity_type", "character") == "character"
        and entity.get("id")
    }
    entity_ids = available_ids & set(entities)
    data_complete = {
        entity_id for entity_id in entity_ids
        if entities[entity_id].get("package_ready") is True
    }
    boss_eligible = {
        entity_id for entity_id in entity_ids
        if entities[entity_id].get("eligible") is True
        and not entities[entity_id].get("rejection_reasons")
    }
    role_pool_union = _role_pool_union(role_scores.get("role_pools", {}), entity_ids)
    candidates = [
        candidate for candidate in candidate_generation.get("candidates", [])
        if isinstance(candidate, Mapping)
    ]
    values = {
        "user_roster_count": len(user_names),
        "f2p_augmented_count": len(f2p_added_names),
        "distinct_available_count": len(available_names),
        "data_complete_count": len(data_complete),
        "boss_eligible_count": len(boss_eligible),
        "role_pool_union_count": len(role_pool_union),
        "candidate_count": len(candidates),
    }
    diversity = candidate_diversity_report(candidates)
    values.update({
        "unique_character_set_count": diversity["unique_character_set_count"],
        "unique_frontline_set_count": diversity["unique_frontline_set_count"],
        "unique_archetype_count": diversity["unique_archetype_count"],
    })
    definitions = metric_contract()
    denominator_values = {
        "user_roster_count": None,
        "f2p_augmented_count": values["distinct_available_count"],
        "distinct_available_count": None,
        "data_complete_count": values["distinct_available_count"],
        "boss_eligible_count": values["distinct_available_count"],
        "role_pool_union_count": values["distinct_available_count"],
        "candidate_count": None,
        "unique_character_set_count": values["candidate_count"],
        "unique_frontline_set_count": values["candidate_count"],
        "unique_archetype_count": values["candidate_count"],
    }
    metric_details = {
        name: {
            **definitions[name],
            "value": values[name],
            "denominator_value": denominator_values[name],
        }
        for name in values
    }
    report = {
        "report_type": "feature_a_request_coverage",
        "metric_contract_version": FEATURE_A_METRIC_CONTRACT_VERSION,
        "metric_contract": {name: definitions[name] for name in values},
        "metrics": values,
        "metric_details": metric_details,
        "diversity": diversity,
        "stage_ids": {
            "available_character_ids": sorted(available_ids),
            "data_complete_character_ids": sorted(data_complete),
            "boss_eligible_character_ids": sorted(boss_eligible),
            "role_pool_union_character_ids": sorted(role_pool_union),
        },
        "unknown_data": {
            "available_characters_not_retrieved": len(set(available_names) - retrieved_names),
            "retrieved_characters_without_role_scores": len(available_ids - entity_ids),
            "readiness_markers_unknown": sum(
                1 for entity_id in entity_ids if "package_ready" not in entities[entity_id]
            ),
            "character_sets_unknown": diversity["character_sets_unknown"],
            "frontline_sets_unknown": diversity["frontline_sets_unknown"],
            "total_scores_unknown": diversity["total_scores_unknown"],
            "component_score_vectors_unknown": diversity["component_score_vectors_unknown"],
        },
    }
    report.update(values)
    return report


def candidate_diversity_report(candidates: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Return stable uniqueness, warning, score-vector, and overlap diagnostics."""
    rows = [candidate for candidate in candidates if isinstance(candidate, Mapping)]
    character_sets: list[frozenset[str]] = []
    frontline_sets: list[frozenset[str]] = []
    character_orders: list[tuple[str, ...]] = []
    archetypes: set[str] = set()
    total_scores: list[Any] = []
    component_vectors: list[str] = []
    character_sets_unknown = 0
    frontline_sets_unknown = 0
    total_scores_unknown = 0
    component_score_vectors_unknown = 0
    for candidate in rows:
        character_ids = tuple(str(value) for value in candidate.get("character_ids", []) if value)
        character_set_known = len(character_ids) == 6 and len(set(character_ids)) == 6
        if character_set_known:
            character_orders.append(character_ids)
            character_sets.append(frozenset(character_ids))
        else:
            character_sets_unknown += 1
        frontline = candidate.get("frontline_character_ids")
        if not isinstance(frontline, list):
            frontline = list(character_ids[:4]) if character_set_known else []
        frontline_ids = tuple(str(value) for value in frontline if value)
        if len(frontline_ids) == 4 and len(set(frontline_ids)) == 4:
            frontline_sets.append(frozenset(frontline_ids))
        else:
            frontline_sets_unknown += 1
        archetypes.add(str(candidate.get("archetype") or "unknown"))
        if candidate.get("score") is None:
            total_scores_unknown += 1
        else:
            total_scores.append(candidate["score"])
        component_scores = candidate.get("component_scores")
        if not isinstance(component_scores, Mapping):
            component_score_vectors_unknown += 1
        else:
            component_vectors.append(json.dumps(component_scores, sort_keys=True, ensure_ascii=False))

    pairwise_jaccard = [
        round(len(left & right) / len(left | right), 3) if left | right else 1.0
        for left, right in combinations(character_sets, 2)
    ]
    same_character_sets = bool(character_sets) and len(set(character_sets)) == 1
    same_character_order = bool(character_orders) and len(set(character_orders)) == 1
    identical_total_scores = (
        len(total_scores) == len(rows) and bool(rows)
        and len({_stable_json(value) for value in total_scores}) == 1
    )
    identical_component_vectors = (
        len(component_vectors) == len(rows) and bool(rows)
        and len(set(component_vectors)) == 1
    )
    permutation_only = same_character_sets and not same_character_order and len(rows) > 1
    warnings: list[str] = []
    if character_sets_unknown:
        warnings.append("candidate_character_sets_unknown")
    if frontline_sets_unknown:
        warnings.append("candidate_frontline_sets_unknown")
    if total_scores_unknown:
        warnings.append("candidate_total_scores_unknown")
    if component_score_vectors_unknown:
        warnings.append("candidate_component_score_vectors_unknown")
    if same_character_sets and len(rows) > 1:
        warnings.append("permutation_only_or_same_character_set")
    if identical_total_scores and len(rows) > 1:
        warnings.append("identical_total_score_vector")
    if identical_component_vectors and len(rows) > 1:
        warnings.append("identical_component_score_vector")
    if len(archetypes) > 1 and same_character_sets and identical_component_vectors:
        warnings.append("archetype_labels_not_strategically_differentiated")
    return {
        "candidate_count": len(rows),
        "unique_character_set_count": (
            len(set(character_sets)) if character_sets else (None if rows else 0)
        ),
        "unique_frontline_set_count": (
            len(set(frontline_sets)) if frontline_sets else (None if rows else 0)
        ),
        "unique_archetype_count": len(archetypes) if archetypes else 0,
        "archetypes": sorted(archetypes),
        "identical_total_scores": identical_total_scores,
        "identical_component_score_vectors": identical_component_vectors,
        "character_set_jaccard": pairwise_jaccard,
        "permutation_only_or_same_set": permutation_only,
        "warnings": warnings,
        "character_sets_unknown": character_sets_unknown,
        "frontline_sets_unknown": frontline_sets_unknown,
        "total_scores_unknown": total_scores_unknown,
        "component_score_vectors_unknown": component_score_vectors_unknown,
        "status": "REVIEW" if warnings else "PASS",
    }


def _role_pool_union(role_pools: Any, character_ids: set[str]) -> set[str]:
    union: set[str] = set()
    if not isinstance(role_pools, Mapping):
        return union
    for pool in role_pools.values():
        if not isinstance(pool, list):
            continue
        for row in pool:
            identifier = row.get("entity_id") if isinstance(row, Mapping) else row
            if identifier is not None and str(identifier) in character_ids:
                union.add(str(identifier))
    return union


def _distinct_strings(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(str(value).strip() for value in values if str(value).strip()))


def _stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
