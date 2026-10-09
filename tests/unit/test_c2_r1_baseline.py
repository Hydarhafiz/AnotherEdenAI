"""Isolation checks for the owner-run C2-R1 baseline."""

import hashlib
import json
from pathlib import Path

import pytest

from scripts import evaluate_c2_r1_baseline as baseline
from scripts.evaluate_c2_r1_baseline import evaluate_baseline


def test_owner_oracle_must_be_outside_repository_before_reading():
    with pytest.raises(ValueError, match="must remain outside the repository"):
        evaluate_baseline(Path("src/etl/source_fidelity_manifest.json"))


def test_owner_answers_reach_only_aggregate_evaluator_after_predictions(tmp_path, monkeypatch):
    witness = {
        "witness_id": "fresh-test-only",
        "source_capture_sha256": "a" * 64,
        "fact_id": "skill:test-only",
        "disposition": "fresh_replacement_frozen",
    }
    oracle = {
        "schema_version": "c2-atomic-oracle-1",
        "cohort": "fresh_replacement",
        "witnesses": [
            {
                "witness_id": witness["witness_id"],
                "source_capture_sha256": witness["source_capture_sha256"],
                "fact_id": witness["fact_id"],
                "atoms": [
                    {
                        "occurrence_kind": "effect",
                        "atomic_capability_id": "test_only_capability",
                        "operation": "apply",
                        "source_anchor": {"location": "sha256:test/grid[0]/block[0]", "quote": "Test-only source"},
                    }
                ],
                "fidelity_dimensions": {"actor": {"status": "passed"}},
            }
        ],
    }
    oracle_path = tmp_path / "owner-oracle.json"
    oracle_bytes = json.dumps(oracle, ensure_ascii=False).encode("utf-8")
    oracle_path.write_bytes(oracle_bytes)
    freeze_path = tmp_path / "freeze.json"
    freeze_path.write_text(
        json.dumps(
            {
                "held_out_witnesses": [witness],
                "oracle_custody": {"sha256": hashlib.sha256(oracle_bytes).hexdigest()},
            }
        ),
        encoding="utf-8",
    )
    events = []

    occurrence = {
        "occurrence_id": "occ:test",
        "occurrence_kind": "effect",
        "operation": "apply",
        "source_fact_id": witness["fact_id"],
        "source_capture_sha256": witness["source_capture_sha256"],
        "source_span": {"location": "sha256:test/grid[0]/block[0]", "text": "Test-only source"},
        "capability_value": "test_only_capability",
    }
    relationship = {
        "relationship_id": "rel:test",
        "source_fact_id": witness["fact_id"],
        "source_occurrence_id": "occ:test",
        "target_kind": "source_fact",
        "target_id": "skill:child",
        "operation": "activates",
    }
    orphan_relationship = {**relationship, "relationship_id": "rel:orphan", "source_occurrence_id": "occ:missing"}

    def fake_build_c2_report(**kwargs):
        events.append("predictions")
        assert kwargs.get("fidelity_oracle") is None
        return {
            "comparisons": {
                "development": {
                    "arms": {
                        "test_arm": {
                            "occurrences": [occurrence],
                            "relationships": [relationship, orphan_relationship],
                        }
                    }
                }
            }
        }

    def fake_evaluate_frozen_cohort(
        predictions,
        actual_oracle,
        witnesses,
        *,
        unresolved_relationships_by_arm,
    ):
        events.append("aggregate_evaluation")
        assert actual_oracle == oracle
        assert list(predictions) == ["test_arm"]
        assert [row["witness_id"] for row in witnesses] == [witness["witness_id"]]
        predicted = predictions["test_arm"][witness["witness_id"]]
        assert predicted[0]["relationships"] == [relationship]
        assert unresolved_relationships_by_arm["test_arm"] == [
            {
                **orphan_relationship,
                "attachment_status": "unresolved",
                "attachment_reason": "source occurrence was not present in the selected report arm",
            }
        ]
        return {"evaluator_version": "test-only", "witness_count": 1, "arms": {"test_arm": {"aggregate": True}}}

    monkeypatch.setattr(baseline, "build_c2_report", fake_build_c2_report)
    monkeypatch.setattr(baseline, "evaluate_frozen_cohort", fake_evaluate_frozen_cohort)
    result = evaluate_baseline(oracle_path, freeze_path=freeze_path)

    assert events == ["predictions", "aggregate_evaluation"]
    assert result["oracle_answers_returned"] is False
    assert result["per_witness_results_returned"] is False
    assert "witnesses" not in result


def test_empty_owner_atom_set_cannot_be_reported_as_a_semantic_baseline(tmp_path, monkeypatch):
    witness = {
        "witness_id": "fresh-test-only",
        "source_capture_sha256": "a" * 64,
        "fact_id": "skill:test-only",
        "disposition": "fresh_replacement_frozen",
    }
    oracle = {
        "schema_version": "c2-atomic-oracle-1",
        "cohort": "fresh_replacement",
        "witnesses": [
            {
                "witness_id": witness["witness_id"],
                "source_capture_sha256": witness["source_capture_sha256"],
                "fact_id": witness["fact_id"],
                "atoms": [],
            }
        ],
    }
    oracle_path = tmp_path / "owner-oracle.json"
    oracle_bytes = json.dumps(oracle).encode("utf-8")
    oracle_path.write_bytes(oracle_bytes)
    freeze_path = tmp_path / "freeze.json"
    freeze_path.write_text(
        json.dumps(
            {
                "held_out_witnesses": [witness],
                "oracle_custody": {"sha256": hashlib.sha256(oracle_bytes).hexdigest()},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        baseline,
        "build_c2_report",
        lambda **kwargs: {"comparisons": {"development": {"arms": {"test_arm": {"occurrences": []}}}}},
    )

    with pytest.raises(ValueError, match="no atomic expectations"):
        evaluate_baseline(oracle_path, freeze_path=freeze_path)
