"""Acceptance coverage for the Milestone 6 C2 comparison gate."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.etl.capability_taxonomy import load_capability_taxonomy
from src.etl.c2_scoped_classification import (
    OCCURRENCE_KINDS,
    PRIMARY_OCCURRENCE_KINDS,
    build_c2_report,
    evaluate_c2_oracle,
)
from src.etl.c2_semantic_evaluation import (
    FIDELITY_DIMENSIONS as EVALUATOR_FIDELITY_DIMENSIONS,
    ORACLE_SCHEMA_VERSION,
    adapt_c2_report_to_evaluator,
    evaluate_frozen_cohort,
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
    freeze = json.loads(FROZEN_MANIFEST.read_text(encoding="utf-8"))
    assert replay["manifest"]["known_regression_count"] == 7
    assert replay["manifest"]["development_witness_count"] == freeze["development_witness_count"]
    assert replay["manifest"]["held_out_witness_count"] == freeze["held_out_witness_count"]
    for cohort in ("development",):
        covered = set(replay["comparisons"][cohort]["archetype_coverage"])
        assert covered
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


def test_development_report_uses_canonical_classifier_to_evaluator_contract(report: dict):
    comparison = report["comparisons"]["development"]
    contract = report["comparison_contract"]
    assert contract["occurrence_operation_is_explicit"] is True
    assert contract["unmapped_semantics_are_explicit_taxonomy_gaps"] is True
    assert contract["relationship_contract"]["report_adapter_owner_key"] == "source_occurrence_id"
    assert contract["relationship_contract"]["unattached_rows_are_retained_as_unresolved"] is True
    taxonomy = load_capability_taxonomy()
    capability_ids = set(taxonomy["capabilities"])
    dependency_ids = set(taxonomy["dependencies"])

    for arm in comparison["arms"].values():
        for occurrence in arm["occurrences"]:
            assert occurrence["operation"]
            if occurrence["occurrence_kind"] == "effect":
                if occurrence["capability_value"]:
                    assert occurrence["capability_value"] in capability_ids
                else:
                    assert occurrence["capability_gap"] is True
            elif occurrence["occurrence_kind"] == "dependency":
                if occurrence["dependency_value"]:
                    assert occurrence["dependency_value"] in dependency_ids
                else:
                    assert occurrence["dependency_gap"] is True

    source_capture_by_fact = {
        occurrence["source_fact_id"]: occurrence["source_capture_sha256"]
        for occurrence in comparison["arms"]["structural_only"]["occurrences"]
    }
    development_witnesses = [
        {
            "witness_id": row["witness_id"],
            "fact_id": row["fact_id"],
            "source_capture_sha256": source_capture_by_fact[row["fact_id"]],
        }
        for row in comparison["witnesses"]
        if row["fact_id"] in source_capture_by_fact
    ]
    full_adapter = adapt_c2_report_to_evaluator(comparison, development_witnesses)
    attached_relationship_count = 0
    for arm_name, arm in comparison["arms"].items():
        adapted_occurrences = [
            occurrence
            for rows in full_adapter["predictions_by_arm"][arm_name].values()
            for occurrence in rows
        ]
        attached_relationship_count += sum(
            len(occurrence["relationships"]) for occurrence in adapted_occurrences
        )
        selected_facts = {row["fact_id"] for row in development_witnesses}
        reported_relationship_count = sum(
            str(relationship.get("source_fact_id") or "") in selected_facts
            for relationship in arm["relationships"]
        )
        unresolved_count = len(full_adapter["unresolved_relationships_by_arm"][arm_name])
        assert reported_relationship_count == sum(
            len(occurrence["relationships"]) for occurrence in adapted_occurrences
        ) + unresolved_count
    assert attached_relationship_count > 0

    witness_row = next(
        row for row in comparison["witnesses"]
        if row["witness_id"] == "development-aisha-mp-restore"
    )
    effect = next(
        row for row in comparison["arms"]["structural_only"]["occurrences"]
        if row["source_fact_id"] == witness_row["fact_id"]
        and row["occurrence_kind"] == "effect"
        and row["source_text"].casefold().startswith("restore all party members' mp")
    )
    witness = {
        "witness_id": witness_row["witness_id"],
        "fact_id": witness_row["fact_id"],
        "source_capture_sha256": effect["source_capture_sha256"],
    }
    adapted = adapt_c2_report_to_evaluator(comparison, [witness])
    evaluator_row = next(
        row for row in adapted["predictions_by_arm"]["structural_only"][witness["witness_id"]]
        if row["occurrence_id"] == effect["occurrence_id"]
    )
    assert evaluator_row["atomic_capability_id"] == "recover_mp"
    assert evaluator_row["operation"] == "restore"
    assert evaluator_row["source_capture_sha256"] == effect["source_capture_sha256"]
    assert evaluator_row["source_span"] == effect["source_span"]

    oracle = {
        "schema_version": ORACLE_SCHEMA_VERSION,
        "cohort": "development_contract_smoke",
        "witnesses": [
            {
                **witness,
                "atoms": [
                    {
                        "occurrence_kind": "effect",
                        "atomic_capability_id": "recover_mp",
                        "operation": "restore",
                        "source_anchor": {
                            "location": effect["source_span"]["location"],
                            "quote": "Restore all party members",
                        },
                        "fields": {
                            "recipient": {"status": "adjudicated", "value": "party"},
                            "relationships": {"status": "not_applicable"},
                        },
                    }
                ],
                "fidelity_dimensions": {
                    name: {"status": "unknown"} for name in EVALUATOR_FIDELITY_DIMENSIONS
                },
            }
        ],
    }
    evaluated = evaluate_frozen_cohort(
        adapted["predictions_by_arm"],
        oracle,
        [witness],
        unresolved_relationships_by_arm=adapted["unresolved_relationships_by_arm"],
    )

    structural = evaluated["arms"]["structural_only"]
    assert structural["effect_occurrence_precision_recall"]["true_positive_count"] == 1
    assert structural["capability_label_precision_recall"]["true_positive_count"] == 1
    assert structural["field_correctness"]["recipient"]["correct_count"] == 1
    assert evaluated["oracle_answers_returned"] is False
    assert evaluated["per_witness_results_returned"] is False


def test_committed_freeze_contains_non_answer_metadata_only():
    freeze = json.loads(FROZEN_MANIFEST.read_text(encoding="utf-8"))
    assert freeze["known_regression_count"] == 7
    assert freeze["development_witness_count"] == len(freeze["development_witnesses"])
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
