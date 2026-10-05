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


FIDELITY_ORACLE = Path("tests/fixtures/source_fidelity/c2_development_oracle.json")
FROZEN_MANIFEST = Path("artifacts/evidence/feature_c2_evaluation_freeze.json")


@pytest.fixture(scope="module")
def report() -> dict:
    if not Path("data/raw/characters").exists():
        pytest.skip("accepted raw captures are required for C2 replay")
    fidelity_oracle = json.loads(FIDELITY_ORACLE.read_text(encoding="utf-8"))
    return build_c2_report(fidelity_oracle=fidelity_oracle)


def test_routine_report_has_development_arms_only(report: dict):
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


def test_only_fidelity_passed_rows_are_fully_supported(report: dict):
    for comparison in report["comparisons"].values():
        for occurrence in comparison["arms"]["fidelity_checked"]["occurrences"]:
            if occurrence["semantic_state"] != "fully_supported_input":
                assert occurrence["authority"] == "unknown_non_authoritative"
        assert comparison["arms"]["fidelity_checked"]["fully_supported_occurrence_count"] <= comparison["arms"]["fidelity_checked"]["occurrence_count"]


def test_shared_mechanic_references_stay_parent_scoped_and_non_authoritative(report: dict):
    contract = report["shared_mechanic_contract"]
    assert contract["resolution_is_non_authoritative"] is True
    assert contract["local_payload_owner"] == "parent source fact"
    assert contract["unavailable_definition_never_becomes_semantics"] is True
    assert contract["registry_deduplicates_by_mechanic_id"] is True
    assert contract["graph_labels_added"] is False

    claude = next(
        row
        for row in report["comparisons"]["development"]["witnesses"]
        if row["witness_id"] == "development-claude-es-another-zone"
    )
    zone_rows = [
        row
        for row in claude["shared_mechanic_resolutions"]
        if row["mechanic_id"] == "shared:another-zone"
    ]
    assert zone_rows
    assert all(row["parent_source_fact_id"] == claude["fact_id"] for row in zone_rows)
    assert all(row["parent_owner_name"] == claude["entity_name"] for row in zone_rows)
    assert all("capability" not in row and "authority" not in row for row in zone_rows)

    for comparison in report["comparisons"].values():
        for witness in comparison["witnesses"]:
            for resolution in witness["shared_mechanic_resolutions"]:
                assert resolution["parent_source_fact_id"] == witness["fact_id"]
                assert resolution["parent_owner_name"] == witness["entity_name"]
                assert resolution["resolution_status"] in {"resolved", "ambiguous", "unresolved"}


def test_manifest_and_catalog_diagnostics_remain_stratified_and_complete(report: dict):
    replay = report
    assert replay["manifest"]["known_regression_count"] == 7
    assert replay["manifest"]["development_witness_count"] == 57
    assert replay["manifest"]["held_out_witness_count"] == 7
    for cohort in ("development",):
        covered = set(replay["comparisons"][cohort]["archetype_coverage"])
        assert covered
    freeze = json.loads(FROZEN_MANIFEST.read_text(encoding="utf-8"))
    assert set(freeze["coverage_contract"]["required_strata"]) == {
        "simple_skill",
        "complex_multi_effect_skill",
        "passive",
        "stellar_or_state_driven_variant",
        "sidekick_auto",
        "sidekick_charge",
        "sidekick_aura",
        "shared_mechanic",
        "parent_child_relation",
        "condition_or_state_heavy_mechanic",
    }
    assert all(freeze["coverage_contract"]["current_metadata_candidates"].values())
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


def test_committed_freeze_contains_non_answer_metadata_only():
    freeze = json.loads(FROZEN_MANIFEST.read_text(encoding="utf-8"))
    assert freeze["known_regression_count"] == 7
    assert freeze["development_witness_count"] == 57
    assert freeze["held_out_witness_count"] == 7
    assert len(freeze["r5_reserved_post_fix_human_sample"]) == 7
    assert {
        row["witness_id"] for row in freeze["held_out_witnesses"]
    } == set(freeze["r5_reserved_post_fix_human_sample"])
    def keys(value):
        if isinstance(value, dict):
            for key, child in value.items():
                yield key
                yield from keys(child)
        elif isinstance(value, list):
            for child in value:
                yield from keys(child)

    assert not {
        "atomic_capability_id",
        "source_anchor",
        "fidelity_dimensions",
        "atoms",
    }.intersection(keys(freeze))
    assert freeze["oracle_custody"]["sha256"] is None or len(freeze["oracle_custody"]["sha256"]) == 64


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


def test_routine_report_does_not_expose_protected_rows(report: dict):
    freeze = json.loads(FROZEN_MANIFEST.read_text(encoding="utf-8"))
    protected_ids = {
        row["witness_id"]
        for row in freeze["held_out_witnesses"]
        if row.get("disposition") in {"protected_validation", "fresh_replacement_pending_owner_adjudication"}
    }
    serialized = json.dumps(report, ensure_ascii=False)
    assert not protected_ids.intersection(serialized.split('"'))
    assert "held_out" not in report["comparisons"]
    assert "character_rows" not in report["full_catalog_diagnostics"]["full_catalog_replay"]
    assert "rows" not in report["full_catalog_diagnostics"]["sidekick_replay"]
    assert "mapping_diagnostics" not in report["full_catalog_diagnostics"]["full_catalog_replay"]["structural_parse_coverage"]
    assert "witnesses" not in report["witness_replay"]
    assert "oracle_evaluation" not in report


def test_historical_ordinal_evaluator_refuses_protected_cohort_access():
    with pytest.raises(ValueError, match="disabled for protected validation"):
        evaluate_c2_oracle({"comparisons": {}}, {"sealed": True, "witnesses": {}}, include_held_out=True)
    with pytest.raises(ValueError, match="outside known/development"):
        evaluate_c2_oracle(
            {"comparisons": {"development": {"witnesses": []}}},
            {"witnesses": [{"witness_id": "fresh-minimander-auto"}]},
        )


def test_fidelity_dimensions_are_explicit(report: dict):
    replay = report
    assert replay["fidelity_dimensions"]["dimensions"] == list(FIDELITY_DIMENSIONS)
    assert replay["fidelity_dimensions"]["unresolved_state"] == "unknown_non_authoritative"
    assert replay["fidelity_dimensions"]["inapplicable_state"] == "not_applicable"
    assert replay["fidelity_dimensions"]["failed_state"] == "failed_non_authoritative"
    for comparison in replay["comparisons"].values():
        for witness in comparison["witnesses"]:
            if witness["c1_fidelity_status"] == "passed":
                assert set(witness["c1_fidelity_dimensions"]) == set(FIDELITY_DIMENSIONS)
