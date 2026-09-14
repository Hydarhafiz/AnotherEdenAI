"""Deterministic Feature A catalog coverage accounting.

This module reports the current state of the authoritative legal-kit and
capability artifacts.  It intentionally does not turn an unreviewed proposal,
an untagged fact, or a missing relationship into capability proof.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from statistics import median
from typing import Any, Iterable, Mapping, TypedDict

from .capability_taxonomy import materialize_atomic, propose
from .kit_readiness import (
    EXPECTED_CANONICAL_CHARACTER_COUNT,
    artifact_fingerprint,
    validate_catalog_payload,
)


FEATURE_A_METRIC_CONTRACT_VERSION = "feature-a-metric-contract-v1"
FEATURE_A_BASELINE_VERSION = "feature-a-baseline-v1"
CATALOG_SOURCE = "src/etl/kit_catalog.json"
CAPABILITY_SOURCE = "src/etl/capability_taxonomy.json + src/etl/capability_reviews.json"

# These groups are the bounded Feature A measurement vocabulary.  They are
# deliberately broader than the currently reviewed evidence so that the
# baseline measures extraction attempts separately from proof.
HIGH_VALUE_CAPABILITY_FAMILIES: dict[str, frozenset[str]] = {
    "primary_damage": frozenset({
        "direct_damage", "fixed_damage", "attack_again", "chain_attack", "follow_up_attack",
    }),
    "offensive_enablement": frozenset({
        "outgoing_damage_up", "enemy_resistance_down", "physical_resistance_down",
        "magic_resistance_down", "attack_type_resistance_down", "element_resistance_down",
        "power_up", "intelligence_up", "speed_up", "luck_up", "weakness_multiplier_up",
        "physical_critical_rate_up", "magic_critical_rate_up", "physical_critical_damage_up",
        "magic_critical_damage_up", "equipped_weapon_damage_up", "attack_type_damage_up",
        "element_damage_up", "non_type_damage_up", "grant_mental_focus", "grant_singular_focus",
        "grant_eagle_eyes", "grant_overthrow", "grant_physical_overcritical",
        "grant_magic_overcritical", "inflict_pain", "inflict_poison", "inflict_break",
        "apply_kaleido", "grant_link", "grant_copy", "activate_lunatic",
    }),
    "zone_setup": frozenset({"deploy_zone", "awaken_zone"}),
    "mitigation": frozenset({
        "damage_reduction", "damage_reduction_barrier", "shield", "ally_resistance_up",
        "hold_ground", "dodge", "guard", "cover", "taunt", "stalk",
    }),
    "recovery": frozenset({
        "heal_hp", "regen_hp", "revive", "remove_status_ailment", "remove_debuff",
        "grant_status_immunity", "knockback_immunity",
    }),
    "status_counterplay": frozenset({
        "remove_status_ailment", "remove_debuff", "grant_status_immunity", "knockback_immunity",
    }),
    "af_support": frozenset({
        "af_gauge_restore", "af_gauge_gain_up", "af_combo_gain_up", "af_damage_up",
    }),
    "pain_poison_setup": frozenset({"inflict_pain", "inflict_poison"}),
    # This is a corpus-independent counter vocabulary.  Boss-specific required
    # counters remain a Feature B responsibility and are not inferred here.
    "boss_counter_evidence": frozenset({
        "remove_status_ailment", "remove_debuff", "grant_status_immunity",
        "knockback_immunity", "damage_reduction", "damage_reduction_barrier",
        "shield", "ally_resistance_up", "recover_mp", "barrier_pierce",
        "ignore_target_defense", "invert_weakness_resistance",
    }),
}

_HIGH_VALUE_UNION = frozenset().union(*HIGH_VALUE_CAPABILITY_FAMILIES.values())
_CHARACTER_METRICS = (
    "legal_kit_complete",
    "high_value_capability_attempted",
    "characters_with_proven_primary_damage",
    "characters_with_offensive_enablement",
    "characters_with_zone_setup",
    "characters_with_mitigation",
    "characters_with_recovery",
    "characters_with_status_counterplay",
    "characters_with_af_support",
    "characters_with_pain_poison_setup",
    "characters_with_boss_counter_evidence",
)
_FACT_METRICS = ("facts_proven", "facts_unknown", "facts_ambiguous", "facts_rejected")
class MetricDefinition(TypedDict):
    definition: str
    source: str
    denominator: str
    unknown_data_policy: str


class CoverageBaselineError(ValueError):
    """Raised when Feature A cannot establish an accountable baseline."""


def metric_contract() -> dict[str, MetricDefinition]:
    """Return the versioned definitions shared by offline and request reports."""
    catalog_character_denominator = "canonical catalog identities"
    proposal_denominator = "all proposed atomic capability assertions"
    return {
        "catalog_characters": {
            "definition": "Count of distinct canonical character identities in the legal-kit catalog.",
            "source": f"{CATALOG_SOURCE}#characters[].character.character_id",
            "denominator": "none; cardinality metric",
            "unknown_data_policy": "A missing, duplicate, or malformed identity fails the report; it is never counted as unknown.",
        },
        "legal_kit_complete": {
            "definition": "Canonical identities whose receipt has overall_state=complete and passes receipt recomputation.",
            "source": f"{CATALOG_SOURCE}#characters[].receipt.overall_state",
            "denominator": catalog_character_denominator,
            "unknown_data_policy": "Failed or ambiguous receipts are excluded from the numerator and remain visible in reconciliation diagnostics.",
        },
        "high_value_capability_attempted": {
            "definition": "Canonical identities with at least one deterministic proposal in the bounded high-value capability family set.",
            "source": f"{CATALOG_SOURCE}#characters[].skills[] and passive_skills[]; {CAPABILITY_SOURCE}",
            "denominator": catalog_character_denominator,
            "unknown_data_policy": "Candidate, rejected, ambiguous, and untagged outcomes still count as an attempt, but never as proven coverage.",
        },
        "characters_with_proven_primary_damage": {
            "definition": "Canonical identities with reviewed, source-backed proof of at least one primary-damage capability.",
            "source": f"{CATALOG_SOURCE}#characters[].skills[].capability_evidence_json and passive_skills[].capability_evidence_json",
            "denominator": catalog_character_denominator,
            "unknown_data_policy": "Only reviewed approve/correct/proven evidence counts; missing, candidate, rejected, ambiguous, or untagged facts do not prove absence.",
        },
        "characters_with_offensive_enablement": {
            "definition": "Canonical identities with reviewed proof of at least one offensive-enablement capability.",
            "source": f"{CATALOG_SOURCE}#characters[].skills[]/passive_skills[].capabilities",
            "denominator": catalog_character_denominator,
            "unknown_data_policy": "Unproven capability proposals remain non-authoritative and do not count.",
        },
        "characters_with_zone_setup": {
            "definition": "Canonical identities with reviewed proof of deploy_zone or awaken_zone.",
            "source": f"{CATALOG_SOURCE}#characters[].skills[]/passive_skills[].capability_evidence_json",
            "denominator": catalog_character_denominator,
            "unknown_data_policy": "No zone proof is not proven absence; unresolved facts remain in semantic-state diagnostics.",
        },
        "characters_with_mitigation": {
            "definition": "Canonical identities with reviewed proof of at least one bounded mitigation capability.",
            "source": f"{CATALOG_SOURCE}#characters[].skills[]/passive_skills[].capabilities",
            "denominator": catalog_character_denominator,
            "unknown_data_policy": "Only reviewed proof counts; untagged facts and rejected proposals remain distinct diagnostics.",
        },
        "characters_with_recovery": {
            "definition": "Canonical identities with reviewed proof of healing, recovery, revival, or recovery-oriented protection.",
            "source": f"{CATALOG_SOURCE}#characters[].skills[]/passive_skills[].capabilities",
            "denominator": catalog_character_denominator,
            "unknown_data_policy": "Unknown or ambiguous recovery evidence is not converted to absence.",
        },
        "characters_with_status_counterplay": {
            "definition": "Canonical identities with reviewed proof of status/debuff removal or status/knockback immunity.",
            "source": f"{CATALOG_SOURCE}#characters[].skills[]/passive_skills[].capabilities",
            "denominator": catalog_character_denominator,
            "unknown_data_policy": "Unresolved status evidence is excluded from the numerator without asserting absence.",
        },
        "characters_with_af_support": {
            "definition": "Canonical identities with reviewed proof of AF gauge, combo, or AF-damage support.",
            "source": f"{CATALOG_SOURCE}#characters[].skills[]/passive_skills[].capabilities",
            "denominator": catalog_character_denominator,
            "unknown_data_policy": "The absence of a reviewed AF fact is not evidence that the character lacks AF support.",
        },
        "characters_with_pain_poison_setup": {
            "definition": "Canonical identities with reviewed proof of inflicting Pain or Poison.",
            "source": f"{CATALOG_SOURCE}#characters[].skills[]/passive_skills[].capabilities",
            "denominator": catalog_character_denominator,
            "unknown_data_policy": "Candidate or untagged status text is not counted as setup proof and does not prove absence.",
        },
        "characters_with_boss_counter_evidence": {
            "definition": "Canonical identities with reviewed proof of at least one generic boss-counter capability; boss-specific requirements are not inferred.",
            "source": f"{CATALOG_SOURCE}#characters[].skills[]/passive_skills[].capabilities; {CAPABILITY_SOURCE}",
            "denominator": catalog_character_denominator,
            "unknown_data_policy": "This baseline records generic counter evidence only; boss-specific unknowns remain unresolved for Feature B.",
        },
        "facts_proven": {
            "definition": "Atomic capability proposal instances resolved to reviewed proven evidence.",
            "source": f"{CATALOG_SOURCE}#characters[].skills[]/passive_skills[].capability_diagnostics_json",
            "denominator": proposal_denominator,
            "unknown_data_policy": "Only approve/correct/proven review outcomes are proven; no proposal is treated as absent merely because it is unresolved.",
        },
        "facts_unknown": {
            "definition": "Atomic proposal instances with no current authoritative review decision (candidate state).",
            "source": f"{CATALOG_SOURCE}#characters[].skills[]/passive_skills[].capability_diagnostics_json",
            "denominator": proposal_denominator,
            "unknown_data_policy": "Unknown proposals remain non-authoritative and are distinct from explicit ambiguity, rejection, and untagged source facts.",
        },
        "facts_ambiguous": {
            "definition": "Atomic proposal instances with an explicit ambiguous review decision.",
            "source": f"{CATALOG_SOURCE}#characters[].skills[]/passive_skills[].capability_diagnostics_json",
            "denominator": proposal_denominator,
            "unknown_data_policy": "Ambiguous is retained as its own state and never downgraded to absence or promoted to proof.",
        },
        "facts_rejected": {
            "definition": "Atomic proposal instances with an explicit rejected review decision.",
            "source": f"{CATALOG_SOURCE}#characters[].skills[]/passive_skills[].capability_diagnostics_json",
            "denominator": proposal_denominator,
            "unknown_data_policy": "Rejection disproves that proposal only; it does not prove character-level capability absence.",
        },
        "user_roster_count": {
            "definition": "Distinct canonical character identities supplied by the user before permanent F2P augmentation.",
            "source": "ProductionRecommendationRequest.roster after exact normalization",
            "denominator": "none; cardinality metric",
            "unknown_data_policy": "Unresolved or ambiguous user names fail typed retrieval before a report is emitted.",
        },
        "f2p_augmented_count": {
            "definition": "Distinct canonical character identities newly added by permanent F2P augmentation.",
            "source": "RosterInput.available_characters / augment_with_f2p",
            "denominator": "distinct_available_count",
            "unknown_data_policy": "Only canonical identities present after augmentation but absent from the normalized user roster count; no unsupported subset is substituted.",
        },
        "distinct_available_count": {
            "definition": "Distinct character identities available to the request after roster normalization and F2P augmentation.",
            "source": "ProductionRetrieval.request.roster",
            "denominator": "none; cardinality metric",
            "unknown_data_policy": "Duplicates collapse deterministically; unresolved identities are request errors rather than unknown available characters.",
        },
        "data_complete_count": {
            "definition": "Available characters with a structurally ready legal skill-package frontier at request time.",
            "source": "ProductionRetrieval.role_scores.entities[].package_ready",
            "denominator": "distinct_available_count",
            "unknown_data_policy": "Missing readiness markers are reported as unknown and excluded; incomplete kits are not treated as strategically absent.",
        },
        "boss_eligible_count": {
            "definition": "Available character entities passing deterministic ownership, item, setup, and boss-affinity eligibility filters.",
            "source": "ProductionRetrieval.role_scores.entities[].eligible and rejection_reasons",
            "denominator": "distinct_available_count",
            "unknown_data_policy": "Unknown boss affinity remains eligible only where existing policy permits it; missing or rejected evidence is visible in entity diagnostics.",
        },
        "role_pool_union_count": {
            "definition": "Distinct available character identities present in at least one deterministic role pool.",
            "source": "ProductionRetrieval.role_scores.role_pools",
            "denominator": "distinct_available_count",
            "unknown_data_policy": "Characters with no proven role evidence are not in the union, but remain available legal-kit candidates when structurally complete.",
        },
        "candidate_count": {
            "definition": "Number of deterministic backend lineup candidates returned after legality, setup, allocation, and bounded diversity pruning.",
            "source": "ProductionRetrieval.lineup_candidates.candidates",
            "denominator": "none; bounded output cardinality",
            "unknown_data_policy": "Zero is a valid result; no candidate is manufactured to satisfy a target count.",
        },
        "unique_character_set_count": {
            "definition": "Number of distinct unordered six-character sets across returned backend candidates.",
            "source": "ProductionRetrieval.lineup_candidates.candidates[].character_ids",
            "denominator": "candidate_count",
            "unknown_data_policy": "Missing candidate IDs make the diversity observation unknown and are not silently repaired.",
        },
        "unique_frontline_set_count": {
            "definition": "Number of distinct unordered frontline character sets across returned backend candidates.",
            "source": "ProductionRetrieval.lineup_candidates.candidates[].frontline_character_ids or first four character_ids",
            "denominator": "candidate_count",
            "unknown_data_policy": "A candidate without a determinable frontline is excluded from this numerator and flagged unknown.",
        },
        "unique_archetype_count": {
            "definition": "Number of distinct backend archetype labels across returned candidates; strategic differentiation is audited separately.",
            "source": "ProductionRetrieval.lineup_candidates.candidates[].archetype",
            "denominator": "candidate_count",
            "unknown_data_policy": "Missing labels are represented as unknown, not assigned an inferred archetype.",
        },
    }


def reconcile_catalog_receipts(
    payload: Mapping[str, Any],
    *,
    expected_count: int = EXPECTED_CANONICAL_CHARACTER_COUNT,
) -> dict[str, Any]:
    """Reconcile canonical catalog identities and receipts before measuring."""
    records = payload.get("characters")
    if not isinstance(records, list):
        raise CoverageBaselineError("Feature A A-01 identity drift: catalog characters is not a list")

    canonical_ids: list[str] = []
    receipt_ids: list[str] = []
    complete_ids: list[str] = []
    malformed_records: list[int] = []
    for index, record in enumerate(records):
        character = record.get("character") if isinstance(record, Mapping) else None
        receipt = record.get("receipt") if isinstance(record, Mapping) else None
        character_id = character.get("character_id") if isinstance(character, Mapping) else None
        receipt_id = receipt.get("character_id") if isinstance(receipt, Mapping) else None
        if not character_id or not receipt_id:
            malformed_records.append(index)
            continue
        canonical_ids.append(str(character_id))
        receipt_ids.append(str(receipt_id))
        if receipt.get("overall_state") == "complete":
            complete_ids.append(str(receipt_id))

    canonical_set = set(canonical_ids)
    receipt_set = set(receipt_ids)
    duplicate_canonical_ids = sorted({value for value in canonical_ids if canonical_ids.count(value) > 1})
    duplicate_receipt_ids = sorted({value for value in receipt_ids if receipt_ids.count(value) > 1})
    missing_receipt_ids = sorted(canonical_set - receipt_set)
    extra_receipt_ids = sorted(receipt_set - canonical_set)
    mismatched_identity_rows = [
        index for index, record in enumerate(records)
        if isinstance(record, Mapping)
        and isinstance(record.get("character"), Mapping)
        and isinstance(record.get("receipt"), Mapping)
        and record["character"].get("character_id") != record["receipt"].get("character_id")
    ]
    report = {
        "expected_canonical_count": expected_count,
        "canonical_identity_count": len(canonical_set),
        "receipt_count": len(receipt_ids),
        "complete_receipt_count": len(complete_ids),
        "missing_receipt_ids": missing_receipt_ids,
        "extra_receipt_ids": extra_receipt_ids,
        "duplicate_canonical_ids": duplicate_canonical_ids,
        "duplicate_receipt_ids": duplicate_receipt_ids,
        "mismatched_identity_rows": mismatched_identity_rows,
        "malformed_record_indexes": malformed_records,
    }
    report["ready"] = (
        len(records) == expected_count
        and len(canonical_ids) == expected_count
        and len(canonical_set) == expected_count
        and len(receipt_ids) == expected_count
        and len(receipt_set) == expected_count
        and len(complete_ids) == expected_count
        and not any(report[key] for key in (
            "missing_receipt_ids", "extra_receipt_ids", "duplicate_canonical_ids",
            "duplicate_receipt_ids", "mismatched_identity_rows", "malformed_record_indexes",
        ))
    )
    if not report["ready"]:
        raise CoverageBaselineError(
            "Feature A A-01 catalog/receipt identity drift: "
            f"canonical={report['canonical_identity_count']}/{expected_count}, "
            f"receipts={report['receipt_count']}/{expected_count}, "
            f"complete={report['complete_receipt_count']}/{expected_count}, "
            f"missing={report['missing_receipt_ids'][:5]}, "
            f"extra={report['extra_receipt_ids'][:5]}, "
            f"mismatched_rows={report['mismatched_identity_rows'][:5]}"
        )
    return report


def _iter_catalog_facts(payload: Mapping[str, Any]) -> Iterable[tuple[str, dict[str, Any]]]:
    for record in sorted(payload["characters"], key=lambda value: str(value["receipt"]["character_id"])):
        character_id = str(record["receipt"]["character_id"])
        for key in ("skills", "passive_skills"):
            for fact in record.get(key, []):
                if isinstance(fact, Mapping):
                    yield character_id, dict(fact)


def _proven_capabilities(fact: Mapping[str, Any]) -> set[str]:
    capabilities, _, evidence, _, _ = materialize_atomic(dict(fact))
    proven_evidence = {
        str(row.get("value"))
        for row in evidence
        if row.get("kind") == "capability"
        and str(row.get("review_decision", "")).casefold() in {"approve", "correct", "proven"}
    }
    return set(capabilities) & proven_evidence


def build_catalog_coverage_report(
    payload: Mapping[str, Any],
    *,
    source_path: str = CATALOG_SOURCE,
    expected_count: int = EXPECTED_CANONICAL_CHARACTER_COUNT,
) -> dict[str, Any]:
    """Build the reproducible offline catalog report or fail on identity drift."""
    reconciliation = reconcile_catalog_receipts(payload, expected_count=expected_count)
    validation = validate_catalog_payload(dict(payload), expected_count=expected_count)
    facts = list(_iter_catalog_facts(payload))
    proven_by_character: dict[str, set[str]] = {}
    proposal_totals: Counter[str] = Counter()
    fact_states: Counter[str] = Counter()
    attempted_characters: set[str] = set()
    untagged_fact_count = 0
    for character_id, fact in facts:
        proposals = propose(fact)
        high_value_proposals = {
            proposal["proposed_value"] for proposal in proposals
            if proposal["proposed_value"] in _HIGH_VALUE_UNION
        }
        if high_value_proposals:
            attempted_characters.add(character_id)
        _, _, _, _, diagnostics = materialize_atomic(fact)
        proposal_totals.update({key: int(diagnostics.get(key, 0)) for key in ("proven", "candidate", "ambiguous", "rejected")})
        if not proposals:
            untagged_fact_count += 1
            continue
        proven = _proven_capabilities(fact)
        if proven:
            fact_states["proven"] += 1
            proven_by_character.setdefault(character_id, set()).update(proven)
        elif diagnostics.get("ambiguous"):
            fact_states["ambiguous"] += 1
        elif diagnostics.get("rejected") and not diagnostics.get("candidate"):
            fact_states["rejected"] += 1
        else:
            fact_states["unknown"] += 1

    character_groups = {
        metric_name: len({
            character_id
            for character_id, capabilities in proven_by_character.items()
            if capabilities & HIGH_VALUE_CAPABILITY_FAMILIES[group_name]
        })
        for metric_name, group_name in (
            ("characters_with_proven_primary_damage", "primary_damage"),
            ("characters_with_offensive_enablement", "offensive_enablement"),
            ("characters_with_zone_setup", "zone_setup"),
            ("characters_with_mitigation", "mitigation"),
            ("characters_with_recovery", "recovery"),
            ("characters_with_status_counterplay", "status_counterplay"),
            ("characters_with_af_support", "af_support"),
            ("characters_with_pain_poison_setup", "pain_poison_setup"),
            ("characters_with_boss_counter_evidence", "boss_counter_evidence"),
        )
    }
    values = {
        "catalog_characters": reconciliation["canonical_identity_count"],
        "legal_kit_complete": reconciliation["complete_receipt_count"],
        "high_value_capability_attempted": len(attempted_characters),
        **character_groups,
        "facts_proven": proposal_totals["proven"],
        "facts_unknown": proposal_totals["candidate"],
        "facts_ambiguous": proposal_totals["ambiguous"],
        "facts_rejected": proposal_totals["rejected"],
    }
    definitions = metric_contract()
    denominator_values = {
        "catalog_characters": None,
        **{metric: values["catalog_characters"] for metric in _CHARACTER_METRICS},
        **{metric: sum(proposal_totals.values()) for metric in _FACT_METRICS},
    }
    metric_details = {
        name: {
            **definitions[name],
            "value": values[name],
            "denominator_value": denominator_values[name],
        }
        for name in (*("catalog_characters",), *_CHARACTER_METRICS, *_FACT_METRICS)
    }
    state_distribution = {
        "proven_present": proposal_totals["proven"],
        "unknown": proposal_totals["candidate"],
        "ambiguous": proposal_totals["ambiguous"],
        "rejected": proposal_totals["rejected"],
        "untagged_facts": untagged_fact_count,
        "proven_absent": 0,
        "proven_fact_count": fact_states["proven"],
        "unknown_fact_count": fact_states["unknown"],
        "ambiguous_fact_count": fact_states["ambiguous"],
        "rejected_only_fact_count": fact_states["rejected"],
        "total_source_facts": len(facts),
        "total_proposal_instances": sum(proposal_totals.values()),
    }
    report = {
        "report_type": "feature_a_offline_catalog_coverage",
        "report_version": FEATURE_A_BASELINE_VERSION,
        "metric_contract_version": FEATURE_A_METRIC_CONTRACT_VERSION,
        "source": {
            "catalog_path": source_path,
            "catalog_fingerprint": artifact_fingerprint(dict(payload)),
            "artifact_version": payload.get("artifact_version"),
            "parser_version": payload.get("parser_version"),
            "schema_version": payload.get("schema_version"),
            "capability_source": CAPABILITY_SOURCE,
        },
        "identity_reconciliation": reconciliation,
        "catalog_validation": validation,
        "metric_contract": definitions,
        "metrics": values,
        "metric_details": metric_details,
        "semantic_states": state_distribution,
        "high_value_capability_families": {
            group: sorted(values) for group, values in HIGH_VALUE_CAPABILITY_FAMILIES.items()
        },
        "thresholds": {
            "status": "not_set",
            "values": {},
            "reason": "Feature A records the current distribution; Features D-G thresholds require the planned human checkpoint.",
        },
    }
    # Flat values make command-line inspection and downstream logging easy while
    # ``metrics`` and ``metric_details`` remain the canonical structured forms.
    report.update(values)
    return report


def load_catalog_report(
    catalog_path: str | Path = CATALOG_SOURCE,
    *,
    expected_count: int = EXPECTED_CANONICAL_CHARACTER_COUNT,
) -> dict[str, Any]:
    path = Path(catalog_path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CoverageBaselineError(f"Unable to load Feature A catalog {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise CoverageBaselineError(f"Feature A catalog {path} must contain a JSON object")
    return build_catalog_coverage_report(payload, source_path=path.as_posix(), expected_count=expected_count)


def summarize_historical_diversity(scenarios: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Summarize sanitized historical candidate sets without making provider calls."""
    rows = []
    for scenario in scenarios:
        candidates = scenario.get("backend_candidate_ranking")
        if isinstance(candidates, list):
            rows.append({"scenario_id": scenario.get("scenario_id"), "candidates": candidates})

    distributions: dict[str, list[int | float]] = {
        "candidate_count": [],
        "unique_character_set_count": [],
        "unique_frontline_set_count": [],
        "unique_archetype_count": [],
        "jaccard_min": [],
        "jaccard_median": [],
        "jaccard_max": [],
    }
    identical_total_scores = 0
    identical_component_vectors = 0
    permutation_only = 0
    scenario_reports = []
    for row in rows:
        candidate_rows = row["candidates"]
        report = _candidate_diversity(candidate_rows)
        scenario_reports.append({"scenario_id": row["scenario_id"], **report})
        for name in ("candidate_count", "unique_character_set_count", "unique_frontline_set_count", "unique_archetype_count"):
            if report[name] is not None:
                distributions[name].append(report[name])
        jaccard = report["character_set_jaccard"]
        if jaccard:
            distributions["jaccard_min"].append(min(jaccard))
            distributions["jaccard_median"].append(float(median(jaccard)))
            distributions["jaccard_max"].append(max(jaccard))
        identical_total_scores += int(report["identical_total_scores"])
        identical_component_vectors += int(report["identical_component_score_vectors"])
        permutation_only += int(report["ordering_only_or_same_set"])

    def distribution(values: list[int | float]) -> dict[str, Any]:
        if not values:
            return {"values": [], "min": None, "median": None, "max": None}
        return {
            "values": values,
            "min": min(values),
            "median": float(median(values)),
            "max": max(values),
        }

    return {
        "scenario_count": len(rows),
        "distributions": {name: distribution(values) for name, values in distributions.items()},
        "identical_total_score_scenario_count": identical_total_scores,
        "identical_component_score_vector_scenario_count": identical_component_vectors,
        "permutation_only_or_same_set_scenario_count": permutation_only,
        "scenarios": scenario_reports,
    }


def _candidate_diversity(candidates: list[Mapping[str, Any]]) -> dict[str, Any]:
    character_sets = [frozenset(str(value) for value in candidate.get("character_ids", []) if value) for candidate in candidates]
    frontline_sets = []
    character_orders = []
    archetypes = set()
    totals = []
    components = []
    for candidate, character_set in zip(candidates, character_sets):
        character_ids = [str(value) for value in candidate.get("character_ids", []) if value]
        character_orders.append(tuple(character_ids))
        frontline = candidate.get("frontline_character_ids")
        if not isinstance(frontline, list):
            frontline = character_ids[:4]
        if frontline:
            frontline_sets.append(frozenset(str(value) for value in frontline if value))
        archetypes.add(str(candidate.get("archetype") or "unknown"))
        totals.append(candidate.get("score"))
        components.append(json.dumps(candidate.get("component_scores") or {}, sort_keys=True, ensure_ascii=False))
    jaccard = [
        round(len(left & right) / len(left | right), 3) if left | right else 1.0
        for index, left in enumerate(character_sets)
        for right in character_sets[index + 1:]
    ]
    same_sets = len(set(character_sets)) <= 1 if character_sets else False
    same_orders = len(set(character_orders)) <= 1 if character_orders else False
    same_total_scores = len(set(json.dumps(value, sort_keys=True) for value in totals)) <= 1 if totals else False
    same_components = len(set(components)) <= 1 if components else False
    ordering_only = same_sets and not same_orders and len(character_sets) > 1
    return {
        "candidate_count": len(candidates),
        "unique_character_set_count": len(set(character_sets)) if character_sets else 0,
        "unique_frontline_set_count": len(set(frontline_sets)) if frontline_sets else None,
        "unique_archetype_count": len(archetypes) if archetypes else 0,
        "identical_total_scores": same_total_scores,
        "identical_component_score_vectors": same_components,
        "character_set_jaccard": jaccard,
        "ordering_only_or_same_set": ordering_only,
        "archetype_differentiation": "unproven" if len(archetypes) > 1 and same_sets and same_components else "not_flagged",
    }


def build_accepted_baseline(
    report: Mapping[str, Any],
    *,
    historical_diversity: Mapping[str, Any] | None = None,
    captured_on: str = "2026-09-14",
) -> dict[str, Any]:
    """Select the small durable baseline from a full generated report."""
    baseline = {
        "artifact_type": "feature_a_accepted_coverage_baseline",
        "artifact_version": FEATURE_A_BASELINE_VERSION,
        "captured_on": captured_on,
        "metric_contract_version": report["metric_contract_version"],
        "source": report["source"],
        "identity_reconciliation": report["identity_reconciliation"],
        "metrics": report["metrics"],
        "semantic_states": report["semantic_states"],
        "thresholds": report["thresholds"],
    }
    if historical_diversity is not None:
        baseline["historical_request_diversity"] = {
            key: value for key, value in historical_diversity.items() if key != "scenarios"
        }
    return baseline
