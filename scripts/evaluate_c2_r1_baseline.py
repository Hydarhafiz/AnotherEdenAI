"""Owner-run aggregate-only paired baseline for the frozen C2 cohort.

The required semantic oracle path must be outside this repository. This
command keeps predictions and answers in memory and writes only aggregates.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any, Mapping

from src.etl.c2_scoped_classification import C2_ARTIFACT_VERSION, build_c2_report
from src.etl.c2_semantic_evaluation import (
    adapt_c2_report_to_evaluator,
    evaluate_frozen_cohort,
)


FREEZE_PATH = Path("artifacts/evidence/feature_c2_evaluation_freeze.json")
DEFAULT_OUTPUT = Path("artifacts/evidence/feature_c2_pre_remediation_baseline.json")


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _fresh_witnesses(manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in manifest.get("held_out_witnesses", [])
        if row.get("disposition") in {
            "fresh_replacement_pending_owner_adjudication",
            "fresh_replacement_frozen",
        }
    ]


def evaluate_baseline(owner_oracle_path: Path, *, freeze_path: Path = FREEZE_PATH) -> dict[str, Any]:
    repo_root = Path(__file__).resolve().parents[1]
    resolved_oracle_path = owner_oracle_path.expanduser().resolve()
    if resolved_oracle_path == repo_root or repo_root in resolved_oracle_path.parents:
        raise ValueError("owner semantic oracle must remain outside the repository")
    oracle_bytes = resolved_oracle_path.read_bytes()
    oracle_sha256 = _sha256(oracle_bytes)
    freeze_bytes = freeze_path.read_bytes()
    manifest = json.loads(freeze_bytes)
    expected_oracle_sha = str(manifest.get("oracle_custody", {}).get("sha256") or "")
    if not expected_oracle_sha or oracle_sha256 != expected_oracle_sha:
        raise ValueError("owner oracle digest does not match the committed frozen manifest")
    witnesses = _fresh_witnesses(manifest)
    if not witnesses:
        raise ValueError("frozen manifest has no fresh replacement cohort")

    # A temporary manifest exposes only the fresh cohort to the classifier.
    # Protected legacy identities remain in the committed manifest but are not
    # replayed or emitted by this owner-run baseline.
    temporary_manifest = {
        "known_regressions": [],
        "development_witnesses": witnesses,
        "held_out_witnesses": [],
        "selection_policy": {"known_regressions_are_generalization_evidence": False},
    }
    with tempfile.TemporaryDirectory(prefix="c2-r1-baseline-") as temp_dir:
        temporary_manifest_path = Path(temp_dir) / "fresh_manifest.json"
        temporary_manifest_path.write_text(
            json.dumps(temporary_manifest, ensure_ascii=False, sort_keys=True),
            encoding="utf-8",
        )
        c2_report = build_c2_report(
            manifest_path=temporary_manifest_path,
        )
        evaluator_input = adapt_c2_report_to_evaluator(
            c2_report["comparisons"]["development"],
            witnesses,
        )

    # Parse owner answers only after current C2 predictions are complete.
    # They enter the aggregate evaluator and never the classifier/report path.
    oracle = json.loads(oracle_bytes)
    if oracle.get("cohort") != "fresh_replacement":
        raise ValueError("owner oracle must identify the fresh replacement cohort")
    expected_atom_count = sum(
        len(row.get("atoms", []))
        for row in oracle.get("witnesses", [])
        if isinstance(row.get("atoms", []), list)
    )
    if expected_atom_count == 0:
        raise ValueError("owner oracle contains no atomic expectations; semantic baseline cannot be produced")
    aggregates = evaluate_frozen_cohort(
        evaluator_input["predictions_by_arm"],
        oracle,
        witnesses,
        unresolved_relationships_by_arm=evaluator_input["unresolved_relationships_by_arm"],
    )

    return {
        "artifact_type": "c2_paired_pre_remediation_semantic_baseline",
        "implementation_reference": "b480642",
        "implementation_artifact_version": C2_ARTIFACT_VERSION,
        "evaluator_version": aggregates["evaluator_version"],
        "frozen_manifest_sha256": _sha256(freeze_bytes),
        "semantic_oracle_sha256": oracle_sha256,
        "cohort": "fresh_replacement",
        "witness_count": aggregates["witness_count"],
        "arms": aggregates["arms"],
        "oracle_answers_returned": False,
        "per_witness_results_returned": False,
        "legacy_protected_semantic_baseline": "not produced; historical ordinal counts remain diagnostic only",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the owner-held aggregate-only C2-R1 baseline")
    parser.add_argument("--owner-oracle", type=Path, required=True)
    parser.add_argument("--freeze", type=Path, default=FREEZE_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    output_path = args.output.expanduser().resolve()
    if output_path == args.owner_oracle.expanduser().resolve():
        raise ValueError("aggregate baseline output cannot overwrite the owner semantic oracle")
    if repo_root not in output_path.parents:
        raise ValueError("aggregate baseline output must be a repository evidence artifact")
    baseline = evaluate_baseline(args.owner_oracle, freeze_path=args.freeze)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(baseline, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "artifact_type": baseline["artifact_type"],
                "cohort": baseline["cohort"],
                "witness_count": baseline["witness_count"],
                "arm_names": sorted(baseline["arms"]),
                "evaluator_version": baseline["evaluator_version"],
                "semantic_oracle_sha256": baseline["semantic_oracle_sha256"],
                "output": output_path.relative_to(repo_root).as_posix(),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
