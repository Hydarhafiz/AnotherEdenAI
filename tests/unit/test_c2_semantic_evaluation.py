"""Synthetic tests for aggregate-only, one-to-one C2 semantic matching."""

from __future__ import annotations

import json

import pytest

from src.etl.c2_semantic_evaluation import (
    EVALUATOR_VERSION,
    FIDELITY_DIMENSIONS,
    ORACLE_SCHEMA_VERSION,
    adapt_c2_report_to_evaluator,
    evaluate_frozen_cohort,
    _normalise_field,
)


CAPTURE = "a" * 64
FACT_ID = "skill:synthetic"
LOCATION = f"sha256:{CAPTURE}/grid[0]/block[0]"


def _witness() -> dict:
    return {
        "witness_id": "fresh-test-only",
        "source_capture_sha256": CAPTURE,
        "fact_id": FACT_ID,
    }


def _atom(capability: str = "direct_damage") -> dict:
    return {
        "occurrence_kind": "effect",
        "atomic_capability_id": capability,
        "operation": "damage",
        "source_anchor": {"location": LOCATION, "quote": "Deal damage"},
        "fields": {
            "recipient": {"status": "adjudicated", "value": "single_enemy"},
            "condition": {"status": "unknown"},
            "relationships": {"status": "not_applicable"},
        },
    }


def _prediction(capability: str = "direct_damage") -> dict:
    return {
        "occurrence_kind": "effect",
        "source_fact_id": FACT_ID,
        "source_capture_sha256": CAPTURE,
        "source_span": {"location": LOCATION, "text": "Deal damage to a single enemy."},
        "source_text": "Deal damage to a single enemy.",
        "operation": "damage",
        "capability_value": capability,
        "recipient": "single_enemy",
        "condition": "",
    }


def _oracle(atom: dict | None = None) -> dict:
    return {
        "schema_version": ORACLE_SCHEMA_VERSION,
        "cohort": "fresh_replacement",
        "witnesses": [
            {
                **_witness(),
                "atoms": [atom or _atom()],
                "fidelity_dimensions": {
                    name: {"status": "unknown"} for name in FIDELITY_DIMENSIONS
                },
            }
        ],
    }


def test_exact_semantics_match_once_and_return_aggregates_only():
    report = evaluate_frozen_cohort(
        {"structural_only": {"fresh-test-only": [_prediction()]}},
        _oracle(),
        [_witness()],
    )
    arm = report["arms"]["structural_only"]
    assert report["evaluator_version"] == EVALUATOR_VERSION
    assert report["witness_count"] == 1
    assert arm["effect_occurrence_precision_recall"]["true_positive_count"] == 1
    assert arm["capability_label_precision_recall"]["true_positive_count"] == 1
    assert arm["field_correctness"]["recipient"]["correct_count"] == 1
    assert arm["field_correctness"]["condition"]["unknown_count"] == 1
    assert arm["field_correctness"]["relationships"]["not_applicable_count"] == 1
    assert arm["c1_1_fidelity_dimensions"]["actor"]["unknown_or_unresolved_count"] == 1
    assert report["oracle_answers_returned"] is False
    assert report["per_witness_results_returned"] is False
    serialized = json.dumps(report, ensure_ascii=False)
    assert "fresh-test-only" not in serialized
    assert "direct_damage" not in serialized
    assert "Deal damage" not in serialized


def test_non_taxonomy_label_counts_as_occurrence_but_not_as_a_capability():
    report = evaluate_frozen_cohort(
        {"structural_only": {"fresh-test-only": [_prediction("scoped_effect")]}},
        _oracle(),
        [_witness()],
    )
    arm = report["arms"]["structural_only"]
    assert arm["effect_occurrence_precision_recall"]["true_positive_count"] == 1
    capability = arm["capability_label_precision_recall"]
    assert capability["true_positive_count"] == 0
    assert capability["predicted_count"] == 0
    assert capability["false_positive_count"] == 0
    assert capability["false_negative_count"] == 1


def test_duplicate_predictions_cannot_match_one_expected_atom_more_than_once():
    report = evaluate_frozen_cohort(
        {"structural_only": {"fresh-test-only": [_prediction(), _prediction()]}},
        _oracle(),
        [_witness()],
    )
    arm = report["arms"]["structural_only"]
    assert arm["effect_occurrence_precision_recall"]["true_positive_count"] == 1
    assert arm["effect_occurrence_precision_recall"]["false_positive_count"] == 1
    assert arm["capability_label_precision_recall"]["true_positive_count"] == 1
    assert arm["capability_label_precision_recall"]["false_positive_count"] == 1


def test_capture_fact_or_anchor_mismatch_cannot_match():
    wrong = _prediction()
    wrong["source_capture_sha256"] = "b" * 64
    report = evaluate_frozen_cohort(
        {"structural_only": {"fresh-test-only": [wrong]}},
        _oracle(),
        [_witness()],
    )
    assert report["arms"]["structural_only"]["effect_occurrence_precision_recall"]["true_positive_count"] == 0
    assert report["arms"]["structural_only"]["capability_label_precision_recall"]["false_negative_count"] == 1


def test_evaluator_requires_classifier_operation_instead_of_guessing_from_prose():
    prediction = _prediction()
    prediction.pop("operation")

    with pytest.raises(ValueError, match="without an explicit operation"):
        evaluate_frozen_cohort(
            {"structural_only": {"fresh-test-only": [prediction]}},
            _oracle(),
            [_witness()],
        )


def test_equivalent_enum_and_structured_fields_match_after_normalization():
    prediction = _prediction()
    prediction.update(
        {
            "recipient": "Single Enemy",
            "element": "FIRE",
            "magnitude": {"unit": "Percent", "value": "25.0"},
            "duration_activation": {"turns": 1},
        }
    )
    atom = _atom()
    atom["fields"].update(
        {
            "recipient": {"status": "adjudicated", "value": "single_enemy"},
            "element": {"status": "adjudicated", "value": "fire"},
            "magnitude": {"status": "adjudicated", "value": {"value": 25, "unit": "percent"}},
            "duration_activation": {"status": "adjudicated", "value": {"turns": "1.0"}},
        }
    )

    report = evaluate_frozen_cohort(
        {"structural_only": {"fresh-test-only": [prediction]}},
        _oracle(atom),
        [_witness()],
    )

    fields = report["arms"]["structural_only"]["field_correctness"]
    for field in ("recipient", "element", "magnitude", "duration_activation"):
        assert fields[field]["correct_count"] == 1


def test_unknown_field_spellings_have_one_evaluator_value():
    assert _normalise_field("condition", None) == "unknown"
    assert _normalise_field("condition", "") == "unknown"
    assert _normalise_field("condition", "UNRESOLVED") == "unknown"


def test_report_adapter_attaches_typed_edges_and_reports_orphans():
    occurrence = {
        **_prediction(),
        "occurrence_id": "occ:owner",
        "source_span": {"location": LOCATION, "text": "Deal damage to a single enemy."},
    }
    relationship = {
        "relationship_id": "rel:attached",
        "source_fact_id": FACT_ID,
        "source_occurrence_id": "occ:owner",
        "target_kind": "source_fact",
        "target_id": "skill:child",
        "operation": "activates",
        "condition": "when used",
        "timing": "turn_end",
        "resolution_status": "resolved",
    }
    orphan = {**relationship, "relationship_id": "rel:orphan", "source_occurrence_id": "occ:missing"}
    comparison = {
        "arms": {
            "structural_only": {
                "occurrences": [occurrence],
                "relationships": [relationship, orphan],
            }
        }
    }

    adapted = adapt_c2_report_to_evaluator(comparison, [_witness()])
    predictions = adapted["predictions_by_arm"]["structural_only"]["fresh-test-only"]
    assert predictions[0]["source_capture_sha256"] == CAPTURE
    assert predictions[0]["source_span"] == occurrence["source_span"]
    assert predictions[0]["atomic_capability_id"] == "direct_damage"
    assert predictions[0]["relationships"] == [relationship]
    assert adapted["unresolved_relationships_by_arm"]["structural_only"] == [
        {
            **orphan,
            "attachment_status": "unresolved",
            "attachment_reason": "source occurrence was not present in the selected report arm",
        }
    ]

    atom = _atom()
    atom["fields"]["relationships"] = {"status": "adjudicated", "value": [relationship]}
    report = evaluate_frozen_cohort(
        adapted["predictions_by_arm"],
        _oracle(atom),
        [_witness()],
        unresolved_relationships_by_arm=adapted["unresolved_relationships_by_arm"],
    )
    arm = report["arms"]["structural_only"]
    assert arm["field_correctness"]["relationships"]["correct_count"] == 1
    assert arm["unresolved_relationship_count"] == 1
    serialized = json.dumps(report, ensure_ascii=False)
    assert "rel:orphan" not in serialized
    assert "fresh-test-only" not in serialized


def test_source_span_is_required_even_when_capture_and_fact_match():
    prediction = _prediction()
    prediction["source_span"] = None
    report = evaluate_frozen_cohort(
        {"structural_only": {"fresh-test-only": [prediction]}},
        _oracle(),
        [_witness()],
    )
    assert report["arms"]["structural_only"]["effect_occurrence_precision_recall"]["true_positive_count"] == 0
