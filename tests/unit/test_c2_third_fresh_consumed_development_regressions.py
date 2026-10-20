"""Provenance checks for the consumed Fresh Test #3 regression derivative."""

from __future__ import annotations

from scripts.evaluate_c2_third_fresh_consumed_development_regressions import (
    EXPECTED_WITNESSES,
    FROZEN_ORACLE_SHA256,
    FROZEN_REPORT_SHA256,
    evaluate,
    load_pinned_inputs,
)


def test_test3_derivative_preserves_frozen_provenance_and_approved_felmina_fix():
    oracle, witnesses, _units, units_by_witness = load_pinned_inputs()
    promotion = oracle["promotion"]

    assert promotion["status"] == "consumed_development_regression"
    assert promotion["embedded_html"] is False
    assert promotion["source_oracle_sha256"] == FROZEN_ORACLE_SHA256
    assert promotion["source_evaluation_report_sha256"] == FROZEN_REPORT_SHA256
    assert tuple(row["witness_id"] for row in witnesses) == tuple(
        witness_id for witness_id, _title in EXPECTED_WITNESSES
    )
    assert len(witnesses) == len(units_by_witness) == 7

    corrections = promotion["owner_corrections"]
    assert len(corrections) == 1
    assert corrections[0]["correction_id"] == "C2.1-FELMINA-X5-MULTI-HIT"
    assert corrections[0]["added_capability"] == "multi_hit_action"
    assert corrections[0]["frozen_oracle_modified"] is False

    felmina = next(
        row for row in oracle["witnesses"]
        if row["witness_id"] == "fresh3-felmina-enhanced-silent-killer"
    )
    damage = next(row for row in felmina["atoms"] if row["atomic_capability_id"] == "direct_damage")
    multi_hit = next(row for row in felmina["atoms"] if row["atomic_capability_id"] == "multi_hit_action")
    assert damage["source_anchor"] == multi_hit["source_anchor"]
    assert damage["fields"]["magnitude"]["value"]["hit_count"] == 5
    assert multi_hit["fields"]["magnitude"]["value"]["hit_count"] == 5


def test_lloyd_parent_activation_keeps_children_without_inherited_conditions():
    report, details = evaluate()
    lloyd = next(
        row for row in details["oracle"]["witnesses"]
        if row["witness_id"] == "fresh3-lloyd-raining-tiger-blade"
    )
    relationship = next(
        row for row in lloyd["semantic_relationships"]
        if row.get("relationship_id") == "lloyd-resonant-raid-activation"
    )

    assert relationship["operation"] == "activates"
    assert relationship["trigger"] == "on_skill_use"
    assert "condition" not in relationship
    assert {target["name"] for target in relationship["targets"]} == {
        "Raining Tiger Claw",
        "Raining Tiger Fire",
    }

    relationship_metrics = report["metrics"]["relationship_groups"]
    assert relationship_metrics["expected_groups"] == 3
    assert relationship_metrics["emitted_groups"] == 3
    assert relationship_metrics["exact_correct_groups"] == 3
    assert relationship_metrics["extra_groups"] == 0
    assert relationship_metrics["unresolved_groups"] == 0

    assert report["classification"]["unlabeled_outputs_without_an_explicit_gap_anchor"] == []
    gap_metrics = report["metrics"]["explicit_unsupported_gaps"]
    assert gap_metrics["expected_count"] == 6
    assert gap_metrics["matched_count"] == 6
    assert gap_metrics["unexpected_count"] == 0
    assert gap_metrics["unmatched_expected_count"] == 0
    assert gap_metrics["unsupported_outputs_without_gap_anchor_count"] == 0
