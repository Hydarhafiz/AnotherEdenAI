"""Synthetic tests for aggregate-only, one-to-one C2 semantic matching."""

from __future__ import annotations

import json

from src.etl.c2_semantic_evaluation import (
    EVALUATOR_VERSION,
    FIDELITY_DIMENSIONS,
    ORACLE_SCHEMA_VERSION,
    evaluate_frozen_cohort,
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


def test_generic_scoped_effect_counts_as_occurrence_but_not_capability():
    report = evaluate_frozen_cohort(
        {"structural_only": {"fresh-test-only": [_prediction("scoped_effect")]}},
        _oracle(),
        [_witness()],
    )
    arm = report["arms"]["structural_only"]
    assert arm["effect_occurrence_precision_recall"]["true_positive_count"] == 1
    capability = arm["capability_label_precision_recall"]
    assert capability["true_positive_count"] == 0
    assert capability["false_positive_count"] == 1
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
