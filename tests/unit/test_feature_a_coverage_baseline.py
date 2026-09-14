"""Feature A offline catalog coverage and semantic-state regressions."""

import json
from pathlib import Path

import pytest

from src.etl.coverage_baseline import (
    FEATURE_A_METRIC_CONTRACT_VERSION,
    build_accepted_baseline,
    build_catalog_coverage_report,
    load_catalog_report,
    metric_contract,
    summarize_historical_diversity,
)


CATALOG = Path("src/etl/kit_catalog.json")


def test_offline_catalog_report_reconciles_exact_corpus_and_records_current_distribution():
    report = load_catalog_report(CATALOG)

    assert report["metric_contract_version"] == FEATURE_A_METRIC_CONTRACT_VERSION
    assert report["identity_reconciliation"]["ready"] is True
    assert report["identity_reconciliation"]["canonical_identity_count"] == 367
    assert report["identity_reconciliation"]["receipt_count"] == 367
    assert report["identity_reconciliation"]["complete_receipt_count"] == 367
    assert report["metrics"]["catalog_characters"] == 367
    assert report["metrics"]["legal_kit_complete"] == 367
    assert report["metrics"]["high_value_capability_attempted"] == 367
    assert report["metrics"]["facts_ambiguous"] == 0
    assert report["metrics"]["facts_rejected"] == 22
    assert report["thresholds"] == {
        "status": "not_set",
        "values": {},
        "reason": "Feature A records the current distribution; Features D-G thresholds require the planned human checkpoint.",
    }


def test_catalog_identity_drift_fails_visibly_before_baseline_is_emitted():
    payload = json.loads(CATALOG.read_text(encoding="utf-8"))
    payload["characters"][0]["receipt"]["character_id"] = "character:drifted"

    with pytest.raises(ValueError, match="Feature A A-01.*identity drift"):
        build_catalog_coverage_report(payload)


def test_metric_contract_names_sources_denominators_and_unknown_policies():
    required = {
        "catalog_characters",
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
        "facts_proven",
        "facts_unknown",
        "facts_ambiguous",
        "facts_rejected",
        "user_roster_count",
        "f2p_augmented_count",
        "distinct_available_count",
        "data_complete_count",
        "boss_eligible_count",
        "role_pool_union_count",
        "candidate_count",
        "unique_character_set_count",
        "unique_frontline_set_count",
        "unique_archetype_count",
    }
    contract = metric_contract()

    assert required <= contract.keys()
    assert all(
        definition["definition"] and definition["source"]
        and definition["denominator"] and definition["unknown_data_policy"]
        for definition in contract.values()
    )


def test_semantic_states_keep_unknown_ambiguous_rejected_untagged_and_absence_distinct():
    states = load_catalog_report(CATALOG)["semantic_states"]

    assert states["unknown"] > 0
    assert states["ambiguous"] == 0
    assert states["rejected"] == 22
    assert states["untagged_facts"] > 0
    assert states["proven_absent"] == 0
    baseline = json.loads(Path("artifacts/evidence/feature_a_coverage_baseline.json").read_text(encoding="utf-8"))
    assert baseline["semantic_states"]["unknown"] == 5103
    assert baseline["semantic_states"]["untagged_facts"] == 2208
    assert baseline["semantic_states"]["proven_absent"] == 0


def test_historical_request_diversity_is_reproducible_and_surfaces_collapsed_sets():
    payload = json.loads(Path("llm-output-review/anothereden-feature-h1.json").read_text(encoding="utf-8"))
    report = summarize_historical_diversity(payload["scenarios"])

    assert report["scenario_count"] == 8
    assert report["distributions"]["unique_character_set_count"]["values"] == [1, 1, 1, 1, 6, 6, 6, 1]
    assert report["distributions"]["unique_frontline_set_count"]["values"] == [3, 2, 2, 3, 3, 4, 5, 2]
    assert report["permutation_only_or_same_set_scenario_count"] == 5
    assert report["identical_total_score_scenario_count"] == 6


def test_accepted_baseline_is_concise_and_keeps_thresholds_unset():
    report = load_catalog_report(CATALOG)
    baseline = build_accepted_baseline(report)

    assert set(baseline) == {
        "artifact_type", "artifact_version", "captured_on", "metric_contract_version",
        "source", "identity_reconciliation", "metrics", "semantic_states", "thresholds",
    }
    assert baseline["thresholds"]["status"] == "not_set"
