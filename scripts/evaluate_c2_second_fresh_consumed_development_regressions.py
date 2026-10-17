"""Evaluate consumed Fresh Test #2 as source-pinned C2 regression evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from pathlib import Path
from typing import Any, Mapping

from bs4 import BeautifulSoup

from src.etl.c2_scoped_classification import (
    _classify_unit,
    _catalog_facts,
    _load_catalog,
    _render_fragment_tokens,
)
from src.etl.c2_semantic_evaluation import adapt_c2_report_to_evaluator, evaluate_frozen_cohort
from src.etl.source_fidelity import PARSED_SIDEKICK_DIR, _source_url_for_character
from src.etl.structural_evidence import (
    SourceIdentity,
    TraversalLimits,
    bind_catalog_facts,
    parse_grid_document,
)


ROOT = Path(__file__).resolve().parents[1]
ORACLE_PATH = ROOT / "tests/fixtures/c2/m6_second_fresh_consumed_development_regression_oracle.json"
EXPECTED_SOURCE_ORACLE_SHA256 = "89d932f00c972762668b305ba2f0d61c1851230894d6b377d1d76b5b3c3d2267"
EXPECTED_SOURCE_REPORT_SHA256 = "5a292625654835252f127253b8b2401840c013ae65a1a5a23e1c7771cf98e8b6"
EXPECTED_WITNESSES = (
    ("fresh2-benedict-large-slash", "Large Slash"),
    ("fresh2-ewan-as-roaring-bash", "Sign: Roaring Bash"),
    ("fresh2-ewella-saevus-furorem", "Saevus Furorem"),
    ("fresh2-iridian-heal-arcus-irus", "Arcus Irus"),
    ("fresh2-philo-as-store-power", "Store Power"),
    ("fresh2-radias-turn-end-buff", "Radias turn end buff"),
    ("fresh2-riica-elimination-ray", "Elimination Ray"),
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _normal_text(value: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value or "")).strip().casefold()


def _catalog_records(catalog: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {
        str(record["receipt"].get("character_name") or ""): record
        for record in catalog.get("characters", [])
    }


def _sidekick_source_url(entity_name: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", entity_name.strip()).strip("_").lower()
    path = PARSED_SIDEKICK_DIR / f"{slug}.json"
    if not path.exists():
        raise ValueError(f"pinned sidekick parse metadata is missing for {entity_name}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("rows") or []
    if len(rows) != 1 or str(rows[0].get("name") or "") != entity_name:
        raise ValueError(f"pinned sidekick parse metadata is ambiguous for {entity_name}")
    return str(rows[0].get("source_url") or "")


def _verify_source_anchors(witness: Mapping[str, Any], unit: Any) -> None:
    anchors: list[Mapping[str, Any]] = []
    for atom in witness.get("atoms", []):
        if atom.get("source_anchor"):
            anchors.append(atom["source_anchor"])
        anchors.extend(atom.get("supporting_source_anchors", []))
    for relationship in witness.get("semantic_relationships", []):
        if relationship.get("source_anchor"):
            anchors.append(relationship["source_anchor"])
    for gap in witness.get("unsupported_gaps", []):
        if gap.get("source_anchor"):
            anchors.append(gap["source_anchor"])
        anchors.extend(gap.get("additional_source_anchors", []))

    for anchor in anchors:
        expected_location = str(anchor.get("location") or "")
        quote = _normal_text(str(anchor.get("quote") or ""))
        matches = [
            block
            for block in unit.blocks
            if block.location == expected_location
            and quote
            and quote in _normal_text(_render_fragment_tokens(block.tokens)[0])
        ]
        if len(matches) != 1:
            raise ValueError(f"source anchor no longer matches the pinned packet: {anchor}")


def load_pinned_inputs() -> tuple[dict[str, Any], list[dict[str, Any]], list[Any], dict[str, Any]]:
    oracle = json.loads(ORACLE_PATH.read_text(encoding="utf-8"))
    if oracle.get("cohort") != "m6_consumed_development_regression":
        raise ValueError("Test #2 must be marked as consumed development evidence")
    promotion = oracle.get("promotion") or {}
    if (
        promotion.get("status") != "consumed_development_regression"
        or promotion.get("source_oracle_sha256") != EXPECTED_SOURCE_ORACLE_SHA256
        or promotion.get("source_evaluation_report_sha256") != EXPECTED_SOURCE_REPORT_SHA256
        or promotion.get("embedded_html") is not False
    ):
        raise ValueError("promoted fixture provenance does not match the frozen Test #2 artifacts")
    witnesses = oracle.get("witnesses") or []
    if tuple(str(row.get("witness_id") or "") for row in witnesses) != tuple(row[0] for row in EXPECTED_WITNESSES):
        raise ValueError("the consumed regression cohort identities or order changed")

    catalog = _load_catalog()
    records = _catalog_records(catalog)
    units_by_capture: dict[str, list[Any]] = {}
    units_by_witness: dict[str, Any] = {}
    evaluator_witnesses: list[dict[str, Any]] = []

    for witness, (witness_id, expected_title) in zip(witnesses, EXPECTED_WITNESSES, strict=True):
        source_path = ROOT / str(witness["source_path"])
        raw = source_path.read_bytes()
        capture_sha256 = _sha256(raw)
        if capture_sha256 != str(witness["source_capture_sha256"]):
            raise ValueError(f"pinned capture digest changed for {witness_id}")

        location_match = re.search(r"(grid\[(\d+)\]/block\[0\])$", str(witness["source_location"]))
        if not location_match:
            raise ValueError(f"unsupported pinned location for {witness_id}")
        grid_index = int(location_match.group(2))
        grids = BeautifulSoup(raw, "html.parser").select("div.character-skill-grid-container")
        if grid_index >= len(grids):
            raise ValueError(f"pinned grid is missing for {witness_id}")
        source_slice_sha256 = _sha256(str(grids[grid_index]).encode("utf-8"))
        if source_slice_sha256 != str(witness["source_slice_sha256"]):
            raise ValueError(f"pinned source-slice digest changed for {witness_id}")

        capture_key = source_path.as_posix()
        if capture_key not in units_by_capture:
            sidekick = str(witness["source_kind"]) == "sidekick"
            source_kind = "sidekick" if sidekick else "character"
            source_url = (
                _sidekick_source_url(str(witness["entity_name"]))
                if sidekick
                else _source_url_for_character(records[str(witness["entity_name"])])
            )
            source = SourceIdentity(
                source_kind=source_kind,
                source_url=source_url,
                capture_sha256=capture_sha256,
                capture_path=source_path.relative_to(ROOT).as_posix(),
            )
            parsed, diagnostics = parse_grid_document(
                raw.decode("utf-8"),
                source=source,
                entity_kind=source_kind,
                entity_name=str(witness["entity_name"]),
            )
            if diagnostics:
                raise ValueError(f"pinned source parser diagnostics for {witness_id}: {diagnostics}")
            if not sidekick:
                bind_catalog_facts(parsed, _catalog_facts(records[str(witness["entity_name"])]))
            units_by_capture[capture_key] = parsed

        expected_location = f"sha256:{capture_sha256}/{location_match.group(1)}"
        matches = [
            unit
            for unit in units_by_capture[capture_key]
            if unit.blocks and unit.blocks[0].location == expected_location
        ]
        if len(matches) != 1:
            raise ValueError(f"pinned record is not unique for {witness_id}")
        unit = matches[0]
        if unit.title != expected_title or unit.entity_name != witness["entity_name"]:
            raise ValueError(f"pinned record title or source owner changed for {witness_id}")
        if unit.source_fact_id and unit.source_fact_id != str(witness["fact_id"]):
            raise ValueError(f"catalog fact binding changed for {witness_id}")
        unit.source_fact_id = str(witness["fact_id"])
        _verify_source_anchors(witness, unit)
        units_by_witness[witness_id] = unit
        evaluator_witnesses.append(
            {
                "witness_id": witness_id,
                "fact_id": str(witness["fact_id"]),
                "source_capture_sha256": capture_sha256,
                "source_location": str(witness["source_location"]),
                "source_slice_sha256": source_slice_sha256,
            }
        )

    all_units = [unit for key in sorted(units_by_capture) for unit in units_by_capture[key]]
    return oracle, evaluator_witnesses, all_units, units_by_witness


def _explicit_unsupported_gap(row: Mapping[str, Any], witness: Mapping[str, Any]) -> bool:
    span = row.get("source_span") or {}
    location = str(span.get("location") or "")
    source_text = _normal_text(str(span.get("text") or row.get("source_text") or ""))
    for gap in witness.get("unsupported_gaps", []):
        anchors = [gap.get("source_anchor"), *gap.get("additional_source_anchors", [])]
        for anchor in anchors:
            if not isinstance(anchor, Mapping):
                continue
            quote = _normal_text(str(anchor.get("quote") or ""))
            comparable_quote = quote.rstrip(" .;,:\\")
            if (
                location == str(anchor.get("location") or "")
                and comparable_quote
                and comparable_quote in source_text
            ):
                return True
    return False


def evaluate() -> tuple[dict[str, Any], dict[str, Any]]:
    oracle, evaluator_witnesses, all_units, unit_by_witness = load_pinned_inputs()
    oracle_by_id = {str(row["witness_id"]): row for row in oracle["witnesses"]}
    occurrence_rows: list[dict[str, Any]] = []
    relationship_rows: list[dict[str, Any]] = []
    classifier_rows: dict[str, list[dict[str, Any]]] = {}

    for witness_id, unit in unit_by_witness.items():
        witness = oracle_by_id[witness_id]
        classified = _classify_unit(
            {
                **witness,
                "record_id": str(witness["fact_id"]),
                "record_type": unit.record_type,
                "source_identity_status": "passed",
                "source_record_selection_status": "passed",
                "source_fixture_status": "passed",
            },
            unit,
            all_units,
            TraversalLimits(max_depth=1, max_pages_per_root=2),
            arm="fidelity_checked",
            fidelity_passed=True,
        )
        classifier_rows[witness_id] = [row.as_dict() for row in classified.occurrences]
        occurrence_rows.extend(classifier_rows[witness_id])
        relationship_rows.extend(row.as_dict() for row in classified.relationships)

    comparison = {
        "arms": {"fidelity_checked": {"occurrences": occurrence_rows, "relationships": relationship_rows}}
    }
    adapted = adapt_c2_report_to_evaluator(comparison, evaluator_witnesses)
    evaluation = evaluate_frozen_cohort(
        adapted["predictions_by_arm"],
        oracle,
        evaluator_witnesses,
        unresolved_relationships_by_arm=adapted["unresolved_relationships_by_arm"],
    )
    arm = evaluation["arms"]["fidelity_checked"]

    unsupported_outputs = []
    unlabeled_outputs = []
    for witness in oracle["witnesses"]:
        witness_id = str(witness["witness_id"])
        for row in classifier_rows[witness_id]:
            if row.get("occurrence_kind") not in {"effect", "dependency"}:
                continue
            label = str(row.get("capability_value") or row.get("dependency_value") or "")
            if label:
                continue
            if _explicit_unsupported_gap(row, witness):
                unsupported_outputs.append({"witness_id": witness_id, "source_text": row.get("source_span", {}).get("text", "")})
            else:
                unlabeled_outputs.append({"witness_id": witness_id, "source_text": row.get("source_span", {}).get("text", "")})

    summary = {
        "artifact_version": "m6-second-fresh-consumed-c2-development-regression-1",
        "cohort": {
            "name": "m6_consumed_development_regression",
            "status": "consumed_development_evidence",
            "witness_count": len(evaluator_witnesses),
            "witness_ids": [row[0] for row in EXPECTED_WITNESSES],
            "held_out": False,
        },
        "oracle_provenance": {
            "original_frozen_oracle_sha256": EXPECTED_SOURCE_ORACLE_SHA256,
            "original_frozen_evaluation_report_sha256": EXPECTED_SOURCE_REPORT_SHA256,
            "promoted_fixture_sha256": _sha256(ORACLE_PATH.read_bytes()),
            "embedded_html": False,
            "source_capture_and_slice_pins_verified": True,
        },
        "metrics": {
            "effects": arm["effect_occurrence_precision_recall"],
            "dependencies": arm["dependency_occurrence_precision_recall"],
            "canonical_labels": arm["capability_label_precision_recall"],
            "field_accuracies": arm["field_correctness"],
        },
        "classification": {
            "explicit_unsupported_gap_outputs": unsupported_outputs,
            "unlabeled_outputs_without_an_explicit_gap_anchor": unlabeled_outputs,
            "unresolved_relationships": adapted["unresolved_relationships_by_arm"]["fidelity_checked"],
            "c1_1_dimension_status_counts": arm["c1_1_fidelity_dimensions"],
        },
        "per_witness": [
            {
                "witness_id": witness_id,
                "title": title,
                "effect_labels": sorted({
                    str(row.get("capability_value"))
                    for row in classifier_rows[witness_id]
                    if row.get("occurrence_kind") == "effect" and row.get("capability_value")
                }),
                "dependency_labels": sorted({
                    str(row.get("dependency_value"))
                    for row in classifier_rows[witness_id]
                    if row.get("occurrence_kind") == "dependency" and row.get("dependency_value")
                }),
            }
            for witness_id, title in EXPECTED_WITNESSES
        ],
        "evaluator_invocations": 1,
        "classifier_invocations": len(evaluator_witnesses),
        "shared_adapter_invocations": 1,
    }
    return summary, {
        "oracle": oracle,
        "witnesses": evaluator_witnesses,
        "predictions_by_arm": adapted["predictions_by_arm"],
        "unresolved_relationships_by_arm": adapted["unresolved_relationships_by_arm"],
        "relationships": relationship_rows,
        "classifier_rows": classifier_rows,
        "evaluation": evaluation,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report, _details = evaluate()
    text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")


if __name__ == "__main__":
    main()
