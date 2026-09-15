"""Acceptance coverage for the Milestone 6 C2 comparison gate."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.etl.c2_scoped_classification import (
    OCCURRENCE_KINDS,
    PRIMARY_OCCURRENCE_KINDS,
    build_c2_report,
    evaluate_c2_oracle,
)
from src.etl.source_fidelity import FIDELITY_DIMENSIONS, REQUIRED_ARCHETYPES


FIDELITY_ORACLE = Path("src/etl/source_fidelity_oracle.json")
OCCURRENCE_ORACLE = Path("tests/fixtures/c2/occurrence_oracle.json")


@pytest.fixture(scope="module")
def report() -> dict:
    if not Path("data/raw/characters").exists():
        pytest.skip("accepted raw captures are required for C2 replay")
    return build_c2_report()


@pytest.fixture(scope="module")
def evaluated() -> tuple[dict, dict]:
    if not Path("data/raw/characters").exists():
        pytest.skip("accepted raw captures are required for C2 evaluation")
    fidelity_oracle = json.loads(FIDELITY_ORACLE.read_text(encoding="utf-8"))
    occurrence_oracle = json.loads(OCCURRENCE_ORACLE.read_text(encoding="utf-8"))
    replay = build_c2_report(fidelity_oracle=fidelity_oracle, include_held_out=True)
    return replay, evaluate_c2_oracle(replay, occurrence_oracle, include_held_out=True)


def test_default_report_has_three_arms_and_is_oracle_free(report: dict):
    assert "oracle_evaluation" not in report
    assert set(report["comparisons"]) == {"known_regressions", "development"}
    assert report["comparison_contract"]["occurrence_kinds"] == list(OCCURRENCE_KINDS)
    assert report["comparison_contract"]["primary_occurrence_kinds"] == list(PRIMARY_OCCURRENCE_KINDS)
    for comparison in report["comparisons"].values():
        assert set(comparison["arms"]) == {"legacy_flattened", "structural_only", "fidelity_checked"}
        assert comparison["witness_count"] > 0


def test_c2_witnesses_preserve_real_fact_identity_and_source_spans(report: dict):
    for comparison in report["comparisons"].values():
        fact_ids = {str(row["fact_id"]) for row in comparison["witnesses"]}
        assert fact_ids
        for occurrence in comparison["arms"]["structural_only"]["occurrences"]:
            assert occurrence["source_fact_id"] in fact_ids
            assert occurrence["source_capture_sha256"]
            assert occurrence["source_span"] is not None
            assert occurrence["source_span"]["location"].startswith("sha256:")
            for field in (
                "actor",
                "direction",
                "recipient",
                "target_cardinality",
                "condition",
                "trigger",
                "result",
                "magnitude",
                "duration_activation",
                "element",
                "attack_type",
                "state_reference",
                "definition_support",
                "semantic_state",
                "authority",
            ):
                assert field in occurrence
        assert all(
            occurrence["source_span"] is None
            for occurrence in comparison["arms"]["legacy_flattened"]["occurrences"]
        )


def test_only_fidelity_passed_rows_are_fully_supported_and_known_failures_stay_unknown(evaluated: tuple[dict, dict]):
    replay, _ = evaluated
    known = {row["witness_id"]: row for row in replay["comparisons"]["known_regressions"]["witnesses"]}
    assert known["known-iphi-blood-ritual"]["c1_fidelity_dimensions"]["child_definition_resolution"]["status"] == "unknown"
    assert known["known-alma-refraction-counter"]["c1_fidelity_dimensions"]["parent_child_condition_attachment"]["status"] == "failed"
    assert known["known-darunis-hunters-fangs-conflict"]["c1_fidelity_dimensions"]["attack_type"]["status"] == "failed"
    assert known["known-anabel-prayer-child"]["c1_fidelity_dimensions"]["child_definition_resolution"]["status"] == "unknown"
    for comparison in replay["comparisons"].values():
        for occurrence in comparison["arms"]["fidelity_checked"]["occurrences"]:
            if occurrence["semantic_state"] != "fully_supported_input":
                assert occurrence["authority"] == "unknown_non_authoritative"
        assert comparison["arms"]["fidelity_checked"]["fully_supported_occurrence_count"] <= comparison["arms"]["fidelity_checked"]["occurrence_count"]


def test_manifest_and_catalog_diagnostics_remain_stratified_and_complete(evaluated: tuple[dict, dict]):
    replay, _ = evaluated
    assert replay["manifest"]["known_regression_count"] == 7
    assert replay["manifest"]["development_witness_count"] == 26
    assert replay["manifest"]["held_out_witness_count"] == 21
    for cohort in ("development", "held_out"):
        covered = set(replay["comparisons"][cohort]["archetype_coverage"])
        assert set(REQUIRED_ARCHETYPES) <= covered
    diagnostics = replay["full_catalog_diagnostics"]
    assert diagnostics["legal_kit"] == {
        "canonical_identity_count": 367,
        "complete_receipt_count": 367,
        "ready": True,
        "identity_or_receipt_drift": False,
    }
    assert diagnostics["full_catalog_replay"]["character_identity_denominator"] == 367
    assert diagnostics["full_catalog_replay"]["structural_parse_coverage"]["identities_with_structural_parse"] == 367
    kinds = diagnostics["sidekick_replay"]["record_kind_coverage"]
    assert all(kinds[kind]["structurally_parsed_record_count"] > 0 for kind in ("sidekick_auto", "sidekick_charge", "sidekick_aura"))


def test_damage_events_are_authoritative_once_with_derived_multi_target_projection(report: dict):
    for comparison in report["comparisons"].values():
        effects = [
            row
            for row in comparison["arms"]["fidelity_checked"]["occurrences"]
            if row["occurrence_kind"] == "effect" and row["capability_value"] == "direct_damage"
        ]
        locations = [(row["source_fact_id"], row["source_span"]["location"]) for row in effects]
        assert len(locations) == len(set(locations))
        assert all(
            row["derived_projection"] in ("", "multi_entity_damage")
            for row in effects
        )
        assert comparison["arms"]["fidelity_checked"]["authority_counts"].get("reviewed_proven", 0) == 0
    assert "multi_entity_damage" not in report["comparison_contract"]["occurrence_kinds"]
    assert "multi_entity_damage" in report["comparison_contract"]["one_direct_damage_event_rule"]


def test_compatibility_mapping_never_silently_fans_out_legacy_review_ids(report: dict):
    for comparison in report["comparisons"].values():
        for witness in comparison["compatibility"]:
            mapping = witness["mapping"]
            assert mapping["silent_fanout"] is False
            assert mapping["review_authority_unchanged"] is True
            assert mapping["carried_forward_count"] + mapping["split_requires_review_count"] + mapping["review_required_count"] == len(mapping["mappings"])
            for item in mapping["mappings"]:
                if item["status"] == "carried_forward":
                    assert len(item["candidate_occurrence_ids"]) == 1
                if item["status"] == "split_requires_review":
                    assert len(item["candidate_occurrence_ids"]) > 1


def test_evaluation_keeps_cohorts_counts_arms_and_review_gap_separate(evaluated: tuple[dict, dict]):
    replay, evaluation = evaluated
    assert set(replay["comparisons"]) == {"known_regressions", "development", "held_out"}
    assert evaluation["sealed"] is True
    assert evaluation["known_regressions_excluded_from_generalization"] is True
    assert evaluation["cohorts"]["known_regressions"]["generalization_evidence"] is False
    assert evaluation["cohorts"]["development"]["generalization_evidence"] is True
    assert evaluation["cohorts"]["held_out"]["generalization_evidence"] is True
    assert evaluation["cohorts"]["development"]["witness_count"] == 26
    assert evaluation["cohorts"]["held_out"]["witness_count"] == 21
    assert evaluation["cohorts"]["development"]["independently_adjudicated_effect_occurrence_count"] == 40
    assert evaluation["cohorts"]["development"]["independently_adjudicated_dependency_occurrence_count"] == 23
    assert evaluation["cohorts"]["held_out"]["independently_adjudicated_effect_occurrence_count"] == 30
    assert evaluation["cohorts"]["held_out"]["independently_adjudicated_dependency_occurrence_count"] == 16
    for cohort in evaluation["cohorts"].values():
        assert set(cohort["arm_evaluations"]) == {"legacy_flattened", "structural_only", "fidelity_checked"}
        assert cohort["oracle_missing_witness_ids"] == []
        assert set(cohort["arm_evaluations"]["fidelity_checked"]["occurrence_precision_recall"]) >= {
            "precision",
            "recall",
            "true_positive_count",
            "false_positive_count",
            "false_negative_count",
        }
        assert cohort["review_time"]["measured_accepted_occurrence_count"] == 0
        assert cohort["review_time"]["status_counts"] == {"not_measured": cohort["witness_count"]}
    assert evaluation["benefit"]["status"] == "not_measured"
    assert evaluation["benefit"]["review_reduction_claim"] is False


def test_held_out_evaluation_requires_a_sealed_oracle(report: dict):
    with pytest.raises(ValueError, match="sealed"):
        evaluate_c2_oracle(report, {"sealed": False, "witnesses": {}}, include_held_out=True)


def test_fidelity_dimensions_are_explicit(evaluated: tuple[dict, dict]):
    replay, evaluation = evaluated
    assert replay["fidelity_dimensions"]["dimensions"] == list(FIDELITY_DIMENSIONS)
    assert replay["fidelity_dimensions"]["unresolved_state"] == "unknown_non_authoritative"
    assert replay["fidelity_dimensions"]["inapplicable_state"] == "not_applicable"
    assert replay["fidelity_dimensions"]["failed_state"] == "failed_non_authoritative"
    for comparison in replay["comparisons"].values():
        for witness in comparison["witnesses"]:
            if witness["c1_fidelity_status"] == "passed":
                assert set(witness["c1_fidelity_dimensions"]) == set(FIDELITY_DIMENSIONS)
    assert evaluation["cohorts"]["held_out"]["d_floor_effort"]["status"] == "reported_by_oracle"
