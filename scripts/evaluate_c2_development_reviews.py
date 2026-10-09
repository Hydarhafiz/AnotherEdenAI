"""Run the real C2 report, shared adapter, and evaluator on seven reviewed rows."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import tempfile
import unicodedata
from pathlib import Path
from typing import Any, Mapping

from src.etl.c2_scoped_classification import build_c2_report
from src.etl.c2_semantic_evaluation import (
    EVALUATOR_VERSION,
    adapt_c2_report_to_evaluator,
    evaluate_frozen_cohort,
)
import src.etl.source_fidelity as source_fidelity
from src.etl.structural_evidence import SourceIdentity, parse_grid_document


ROOT = Path(__file__).resolve().parents[1]
ORACLE_PATH = ROOT / "tests/fixtures/c2/recovery_phase2_development_oracle.json"
SOURCE_MANIFEST_PATH = ROOT / "src/etl/source_fidelity_manifest.json"
SOURCE_SLICE_PATH = ROOT / "tests/fixtures/source_fidelity/source_slice_manifest.json"
FIDELITY_ORACLE_PATH = ROOT / "tests/fixtures/source_fidelity/c2_development_oracle.json"
TAXONOMY_PATH = ROOT / "src/etl/capability_taxonomy.json"
DEFAULT_OUTPUT = ROOT / "artifacts/evidence/feature_c2_recovery_phase2_development_evaluation.json"

EXPECTED_IDS = (
    "known-darunis-hunters-fangs-conflict",
    "known-alma-refraction-counter",
    "known-anabel-prayer-child",
    "known-tetra-ruincarnation",
    "development-hameow-aura",
    "development-aldo-starwyrm-slash",
    "development-claude-es-another-zone",
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _normal_text(value: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value or "")).strip().casefold()


def _verify_source_anchors(
    answers: Mapping[str, Any],
    selected_manifest_rows: Mapping[str, Mapping[str, Any]],
) -> None:
    """Verify answer anchors from pinned source HTML, without classifier output."""
    for answer in answers["witnesses"]:
        witness_id = str(answer["witness_id"])
        row = selected_manifest_rows[witness_id]
        source_kind = str(row["source_kind"])
        bucket = "characters" if source_kind == "character" else "sidekicks"
        slug = re.sub(r"[^A-Za-z0-9]+", "_", str(row["entity_name"]).strip()).strip("_").lower() or "unknown"
        path = ROOT / "data/raw" / bucket / f"{slug}.html"
        raw = path.read_bytes()
        capture_sha256 = _sha256(raw)
        if capture_sha256 != str(answer["source_capture_sha256"]):
            raise ValueError(f"pinned raw capture drift for {witness_id}")
        source = SourceIdentity(
            source_kind=source_kind,
            source_url=f"https://anothereden.wiki/w/{slug}",
            capture_sha256=capture_sha256,
            capture_path=path.relative_to(ROOT).as_posix(),
        )
        units, _diagnostics = parse_grid_document(
            raw.decode("utf-8"),
            source=source,
            entity_kind=source_kind,
            entity_name=str(row["entity_name"]),
        )
        candidates = [
            unit for unit in units
            if unit.record_type == str(row["record_type"])
            and _normal_text(unit.title) == _normal_text(str(row["fact_name"]))
        ]
        variant = answer.get("source_variant_label")
        if variant:
            candidates = [unit for unit in candidates if unit.source_variant_label == variant]
        if len(candidates) != 1:
            raise ValueError(f"reviewed source row is not unique in pinned capture: {witness_id}")
        unit = candidates[0]
        for atom in answer.get("atoms", []):
            anchor = atom["source_anchor"]
            quote = _normal_text(str(anchor["quote"]))
            matching_blocks = [
                block for block in unit.blocks
                if quote and quote in _normal_text(" ".join(token.text for token in block.tokens))
            ]
            if len(matching_blocks) != 1 or matching_blocks[0].location != anchor["location"]:
                raise ValueError(f"answer anchor does not uniquely match pinned source for {witness_id}: {anchor}")


def _selected_inputs() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    answers = _read_json(ORACLE_PATH)
    answer_rows = answers.get("witnesses", [])
    if tuple(row.get("witness_id") for row in answer_rows) != EXPECTED_IDS:
        raise ValueError("the semantic answer set must contain exactly the seven requested identities in order")
    taxonomy = _read_json(TAXONOMY_PATH)
    for answer in answer_rows:
        for atom in answer.get("atoms", []):
            allowed = taxonomy["capabilities"] if atom["occurrence_kind"] == "effect" else taxonomy["dependencies"]
            if atom["atomic_capability_id"] not in allowed:
                raise ValueError(f"non-canonical expected label in {answer['witness_id']}: {atom['atomic_capability_id']}")

    source_manifest = _read_json(SOURCE_MANIFEST_PATH)
    source_slices = _read_json(SOURCE_SLICE_PATH)
    slice_by_id = {
        str(row["witness_id"]): row
        for row in source_slices.get("records", [])
        if str(row.get("witness_id") or "") in EXPECTED_IDS
    }
    if set(slice_by_id) != set(EXPECTED_IDS):
        raise ValueError("a selected answer is missing its pinned source slice")

    selected_manifest_rows: dict[str, dict[str, Any]] = {}
    cohort_groups: dict[str, list[dict[str, Any]]] = {
        "known_regressions": [],
        "development_witnesses": [],
        "held_out_witnesses": [],
    }
    source_cohorts = (
        ("known_regressions", "known_regressions"),
        ("development_witnesses", "development_witnesses"),
    )
    for source_key, output_key in source_cohorts:
        for row in source_manifest.get(source_key, []):
            witness_id = str(row.get("witness_id") or "")
            if witness_id not in EXPECTED_IDS:
                continue
            if witness_id in selected_manifest_rows:
                raise ValueError(f"duplicate selected source identity: {witness_id}")
            selected_manifest_rows[witness_id] = dict(row)
            cohort_groups[output_key].append(dict(row))

    answer_by_id = {str(row["witness_id"]): row for row in answer_rows}
    if set(selected_manifest_rows) != set(EXPECTED_IDS):
        raise ValueError("the source manifest does not place all seven requested identities in known/development")
    for witness_id in EXPECTED_IDS:
        expected_cohort = answer_by_id[witness_id]["cohort_kind"]
        actual_cohort = "known_regression" if witness_id in {
            row["witness_id"] for row in cohort_groups["known_regressions"]
        } else "development"
        if expected_cohort != actual_cohort:
            raise ValueError(f"source cohort mismatch for {witness_id}")
        source_row = selected_manifest_rows[witness_id]
        source_slice = slice_by_id[witness_id]
        if (
            str(source_row.get("fact_id") or "") != str(answer_by_id[witness_id]["fact_id"])
            or str(source_row.get("source_capture_sha256") or "") != str(answer_by_id[witness_id]["source_capture_sha256"])
            or str(source_slice.get("record_id") or "") != str(answer_by_id[witness_id]["fact_id"])
            or str(source_slice.get("capture_sha256") or "") != str(answer_by_id[witness_id]["source_capture_sha256"])
            or str(source_slice.get("source_location") or "") != str(answer_by_id[witness_id]["source_location"])
            or str(source_slice.get("source_slice_sha256") or "") != str(answer_by_id[witness_id]["source_slice_sha256"])
        ):
            raise ValueError(f"source identity or source slice drift for {witness_id}")

    _verify_source_anchors(answers, selected_manifest_rows)

    selected_slice_fixture = {
        "authority": source_slices.get("authority"),
        "extraction_method": source_slices.get("extraction_method"),
        "fixture_version": source_slices.get("fixture_version"),
        "records": [slice_by_id[witness_id] for witness_id in EXPECTED_IDS],
    }

    fidelity_oracle = _read_json(FIDELITY_ORACLE_PATH)
    fidelity_rows = [
        row for row in fidelity_oracle.get("witnesses", [])
        if str(row.get("witness_id") or "") in EXPECTED_IDS
    ]
    if {str(row.get("witness_id") or "") for row in fidelity_rows} != set(EXPECTED_IDS):
        raise ValueError("the approved C1.1 development oracle does not cover exactly the selected identities")
    selected_fidelity_oracle = {
        "oracle_version": fidelity_oracle.get("oracle_version"),
        "sealed": False,
        "authority": "Filtered selected rows from the approved development-only C1.1 oracle.",
        "isolation": {"cohorts": "selected known regressions and development only"},
        "default_dimensions": fidelity_oracle.get("default_dimensions", {}),
        "witnesses": fidelity_rows,
    }

    return answers, selected_slice_fixture, selected_fidelity_oracle, [
        *cohort_groups["known_regressions"],
        *cohort_groups["development_witnesses"],
    ]


def _one_selected_comparison(report: Mapping[str, Any]) -> dict[str, Any]:
    known = report["comparisons"]["known_regressions"]
    development = report["comparisons"]["development"]
    arm_names = set(known.get("arms", {})) | set(development.get("arms", {}))
    arms: dict[str, Any] = {}
    for arm_name in sorted(arm_names):
        known_arm = known.get("arms", {}).get(arm_name, {})
        development_arm = development.get("arms", {}).get(arm_name, {})
        arms[arm_name] = {
            "occurrences": [
                *known_arm.get("occurrences", []),
                *development_arm.get("occurrences", []),
            ],
            "relationships": [
                *known_arm.get("relationships", []),
                *development_arm.get("relationships", []),
            ],
        }
    return {"arms": arms}


def run(output_path: Path) -> dict[str, Any]:
    answers, selected_slice_fixture, fidelity_oracle, manifest_rows = _selected_inputs()
    output_path = output_path.resolve()
    if output_path == ORACLE_PATH or output_path.is_relative_to(ROOT / "tests/fixtures"):
        raise ValueError("evaluation output must not overwrite a fixture")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="c2-recovery-phase2-") as temporary:
        scratch = Path(temporary)
        manifest_path = scratch / "selected-manifest.json"
        source_slice_path = scratch / "selected-source-slices.json"
        _write_json(
            manifest_path,
            {
                "selection_policy": "Exactly the four requested known regressions and three requested development witnesses.",
                "known_regressions": [row for row in manifest_rows if row["witness_id"] in EXPECTED_IDS[:4]],
                "development_witnesses": [row for row in manifest_rows if row["witness_id"] in EXPECTED_IDS[4:]],
                "held_out_witnesses": [],
            },
        )
        _write_json(source_slice_path, selected_slice_fixture)

        # Restrict source-fidelity replay output and C2 evidence to the same seven rows.
        source_fidelity.SOURCE_SLICE_FIXTURE_PATH = source_slice_path
        report = build_c2_report(
            fidelity_oracle=fidelity_oracle,
            manifest_path=manifest_path,
        )

    answer_by_id = {str(row["witness_id"]): row for row in answers["witnesses"]}
    selected_manifest = [
        {
            "witness_id": row["witness_id"],
            "fact_id": row["fact_id"],
            "source_capture_sha256": row["source_capture_sha256"],
            "source_location": answer_by_id[row["witness_id"]]["source_location"],
            "source_slice_sha256": answer_by_id[row["witness_id"]]["source_slice_sha256"],
        }
        for row in manifest_rows
    ]
    comparison = _one_selected_comparison(report)
    adapted = adapt_c2_report_to_evaluator(comparison, selected_manifest)
    evaluation = evaluate_frozen_cohort(
        adapted["predictions_by_arm"],
        answers,
        selected_manifest,
        unresolved_relationships_by_arm=adapted["unresolved_relationships_by_arm"],
    )

    per_witness: list[dict[str, Any]] = []
    for answer in answers["witnesses"]:
        witness_id = str(answer["witness_id"])
        witness_input = [row for row in selected_manifest if row["witness_id"] == witness_id]
        single_answer = {**answers, "witnesses": [answer]}
        per_witness_evaluation = evaluate_frozen_cohort(
            {
                arm: {witness_id: rows.get(witness_id, [])}
                for arm, rows in adapted["predictions_by_arm"].items()
            },
            single_answer,
            witness_input,
            unresolved_relationships_by_arm={
                arm: [
                    row for row in rows
                    if str(row.get("source_fact_id") or "") == str(answer["fact_id"])
                ]
                for arm, rows in adapted["unresolved_relationships_by_arm"].items()
            },
        )
        per_arm: dict[str, Any] = {}
        for arm, predictions_by_witness in adapted["predictions_by_arm"].items():
            predictions = list(predictions_by_witness.get(witness_id, []))
            relation_rows = [
                relation
                for prediction in predictions
                for relation in prediction.get("relationships", [])
            ]
            per_arm[arm] = {
                "evaluation": per_witness_evaluation["arms"][arm],
                "predictions": predictions,
                "attached_relationships": relation_rows,
                "unresolved_relationships": [
                    row for row in adapted["unresolved_relationships_by_arm"].get(arm, [])
                    if str(row.get("source_fact_id") or "") == str(answer["fact_id"])
                ],
            }
        per_witness.append(
            {
                "witness_id": witness_id,
                "fact_id": answer["fact_id"],
                "source_capture_sha256": answer["source_capture_sha256"],
                "source_location": answer["source_location"],
                "source_slice_sha256": answer["source_slice_sha256"],
                "review_reference": answer["review_reference"],
                "source_identity_note": answer.get("source_identity_note"),
                "expected_scored_atoms": answer["atoms"],
                "reviewed_relationships": answer.get("reviewed_relationships", []),
                "reviewed_unscored_mechanics": answer.get("reviewed_unscored_mechanics", []),
                "arms": per_arm,
            }
        )

    result = {
        "artifact_version": "c2-recovery-phase2-development-evaluation-1",
        "scope": {
            "kind": "selected_known_regressions_and_development_only",
            "witness_count": len(per_witness),
            "witness_ids": list(EXPECTED_IDS),
            "held_out_witnesses": 0,
            "classifier_rules_modified": False,
            "feature_d_started": False,
        },
        "provenance": {
            "semantic_answer_set": ORACLE_PATH.relative_to(ROOT).as_posix(),
            "semantic_answer_set_sha256": _sha256(ORACLE_PATH.read_bytes()),
            "source_identity_manifest": SOURCE_MANIFEST_PATH.relative_to(ROOT).as_posix(),
            "source_slice_fixture": SOURCE_SLICE_PATH.relative_to(ROOT).as_posix(),
            "approved_c1_1_development_oracle": FIDELITY_ORACLE_PATH.relative_to(ROOT).as_posix(),
            "source_fidelity_artifact_version": source_fidelity.SOURCE_FIDELITY_VERSION,
            "classifier_artifact_version": report["artifact_version"],
            "semantic_evaluator_version": EVALUATOR_VERSION,
            "report_comparison_digest": report["deterministic_replay"]["comparison_digest"],
            "source_fidelity_digest": report["deterministic_replay"]["source_fidelity_digest"],
            "input_filter": "Temporary manifest, C1.1 oracle, and source-slice fixture each contain only the seven named identities.",
        },
        "relationship_scoring_limit": (
            "Reviewed relationship expectations are reported beside adapter output. The semantic evaluator's typed relationship field uses prediction-generated occurrence and relationship IDs, so source-only expected rows cannot independently supply exact IDs."
        ),
        "aggregate_evaluation": evaluation,
        "per_witness": per_witness,
    }
    _write_json(output_path, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate the real C2 pipeline on seven reviewed development/regression examples"
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = run(args.output)
    print(f"C2 classifier artifact: {result['provenance']['classifier_artifact_version']}")
    print(f"semantic evaluator: {result['provenance']['semantic_evaluator_version']}")
    print(f"witnesses: {result['scope']['witness_count']} ({', '.join(result['scope']['witness_ids'])})")
    for arm, metrics in result["aggregate_evaluation"]["arms"].items():
        effect = metrics["effect_occurrence_precision_recall"]
        dependency = metrics["dependency_occurrence_precision_recall"]
        capabilities = metrics["capability_label_precision_recall"]
        print(
            f"{arm}: effects TP/FP/FN={effect['true_positive_count']}/{effect['false_positive_count']}/{effect['false_negative_count']}; "
            f"dependencies TP/FP/FN={dependency['true_positive_count']}/{dependency['false_positive_count']}/{dependency['false_negative_count']}; "
            f"canonical labels TP/FP/FN={capabilities['true_positive_count']}/{capabilities['false_positive_count']}/{capabilities['false_negative_count']}"
        )
    print(f"evidence: {args.output}")


if __name__ == "__main__":
    main()
