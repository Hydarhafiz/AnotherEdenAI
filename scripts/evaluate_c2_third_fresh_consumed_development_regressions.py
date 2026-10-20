"""Replay the consumed Fresh Test #3 derivative through canonical C2 evaluation."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping

from bs4 import BeautifulSoup

from src.etl.c2_scoped_classification import _classify_unit, _catalog_facts, _load_catalog
from src.etl.c2_semantic_evaluation import adapt_c2_report_to_evaluator, evaluate_frozen_cohort
from src.etl.source_fidelity import PARSED_SIDEKICK_DIR, _source_url_for_character
from src.etl.structural_evidence import (
    SourceIdentity,
    TraversalLimits,
    bind_catalog_facts,
    parse_grid_document,
    validate_source_anchor_identity,
)


ROOT = Path(__file__).resolve().parents[1]
ORACLE_PATH = ROOT / "tests/fixtures/c2/m6_third_fresh_consumed_development_regression_oracle.json"
FROZEN_ORACLE_SHA256 = "93a2a4d48c8d4a6a85bf30a253bf31afb62a654f37a25eadcef31d24a27b1ae5"
FROZEN_REPORT_SHA256 = "49055ca03c1db91f9384b159106c5c35e78fd04adadb3ef0f0d4a68cbf0545e2"
EXPECTED_WITNESSES = (
    ("fresh3-aldo-blaze-sword", "Blaze Sword"),
    ("fresh3-sesta-twinblade-wolf", "Twinblade Wolf"),
    ("fresh3-dewey-as-vapeur-hypnotique", "Vapeur Hypnotique"),
    ("fresh3-shigure-as-type-atk-buff-moves", "Type Atk Buff - Num. of Moves"),
    ("fresh3-gunce-arkouda", "Arkoúda"),
    ("fresh3-lloyd-raining-tiger-blade", "Raining Tiger Blade"),
    ("fresh3-felmina-enhanced-silent-killer", "Silent Killer"),
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


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
    rows = json.loads(path.read_text(encoding="utf-8")).get("rows") or []
    if len(rows) != 1 or str(rows[0].get("name") or "") != entity_name:
        raise ValueError(f"pinned sidekick parse metadata is ambiguous for {entity_name}")
    return str(rows[0].get("source_url") or "")


def _anchors(witness: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    result: list[Mapping[str, Any]] = []
    for atom in witness.get("atoms", []):
        if atom.get("source_anchor"):
            result.append(atom["source_anchor"])
        result.extend(atom.get("supporting_source_anchors", []))
    for gap in witness.get("unsupported_gaps", []):
        if gap.get("source_anchor"):
            result.append(gap["source_anchor"])
        result.extend(gap.get("additional_source_anchors", []))
        owner_anchor = gap.get("owner_source_anchor")
        owner_identity = owner_anchor.get("identity") if isinstance(owner_anchor, Mapping) else None
        if isinstance(owner_identity, Mapping):
            if str(gap.get("source_owner_id") or "") != str(owner_identity.get("anchor_id") or ""):
                raise ValueError(f"unsupported gap owner id does not match its canonical anchor: {gap}")
            result.append(owner_anchor)
    for relationship in witness.get("semantic_relationships", []):
        if relationship.get("source_anchor"):
            result.append(relationship["source_anchor"])
    return result


def _verify_source_anchors(witness: Mapping[str, Any], unit: Any) -> None:
    for anchor in _anchors(witness):
        identity = anchor.get("identity")
        if not isinstance(identity, Mapping):
            raise ValueError(f"canonical source-anchor identity is missing for {witness['witness_id']}")
        blocks = [block for block in unit.blocks if block.location == str(anchor.get("location") or "")]
        if len(blocks) != 1 or not validate_source_anchor_identity(
            identity,
            source_fact_id=str(witness["fact_id"]),
            source_capture_sha256=str(witness["source_capture_sha256"]),
            block=blocks[0],
            diagnostic_quote=str(anchor.get("quote") or ""),
        ):
            raise ValueError(f"source anchor does not match its pinned capture for {witness['witness_id']}: {anchor}")


def load_pinned_inputs() -> tuple[dict[str, Any], list[dict[str, Any]], list[Any], dict[str, Any]]:
    oracle = json.loads(ORACLE_PATH.read_text(encoding="utf-8"))
    promotion = oracle.get("promotion") or {}
    if (
        oracle.get("cohort") != "m6_consumed_development_regression"
        or promotion.get("status") != "consumed_development_regression"
        or promotion.get("source_oracle_sha256") != FROZEN_ORACLE_SHA256
        or promotion.get("source_evaluation_report_sha256") != FROZEN_REPORT_SHA256
        or promotion.get("embedded_html") is not False
    ):
        raise ValueError("Test #3 derivative provenance does not match the frozen official artifacts")
    if tuple(str(row.get("witness_id") or "") for row in oracle.get("witnesses", [])) != tuple(
        row[0] for row in EXPECTED_WITNESSES
    ):
        raise ValueError("consumed Test #3 witness identities or order changed")

    corrections = promotion.get("owner_corrections") or []
    if len(corrections) != 1:
        raise ValueError("Test #3 derivative must contain exactly one approved owner correction")
    correction = corrections[0]
    if (
        correction.get("correction_id") != "C2.1-FELMINA-X5-MULTI-HIT"
        or correction.get("witness_id") != "fresh3-felmina-enhanced-silent-killer"
        or correction.get("added_capability") != "multi_hit_action"
        or correction.get("frozen_oracle_modified") is not False
    ):
        raise ValueError("Felmina's owner-approved multi-hit correction changed")

    catalog = _load_catalog()
    records = _catalog_records(catalog)
    parsed_by_path: dict[str, list[Any]] = {}
    units_by_id: dict[str, Any] = {}
    units_by_witness: dict[str, Any] = {}
    evaluator_witnesses: list[dict[str, Any]] = []

    for witness, (witness_id, expected_title) in zip(
        oracle["witnesses"], EXPECTED_WITNESSES, strict=True
    ):
        source_path = ROOT / str(witness["source_path"])
        raw = source_path.read_bytes()
        capture_sha256 = _sha256(raw)
        if capture_sha256 != str(witness["source_capture_sha256"]):
            raise ValueError(f"pinned capture digest changed for {witness_id}")
        grid_match = re.fullmatch(r"grid\[(\d+)\]/block\[0\]", str(witness["source_location"]))
        if not grid_match:
            raise ValueError(f"unsupported source location for {witness_id}")
        grid_index = int(grid_match.group(1))
        grids = BeautifulSoup(raw, "html.parser").select("div.character-skill-grid-container")
        if grid_index >= len(grids):
            raise ValueError(f"pinned source grid is missing for {witness_id}")
        source_slice_sha256 = _sha256(str(grids[grid_index]).encode("utf-8"))
        if source_slice_sha256 != str(witness["source_slice_sha256"]):
            raise ValueError(f"pinned source-slice digest changed for {witness_id}")

        path_key = source_path.as_posix()
        if path_key not in parsed_by_path:
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
            parsed_by_path[path_key] = parsed
            units_by_id.update({unit.unit_id: unit for unit in parsed})

        expected_location = f"sha256:{capture_sha256}/{witness['source_location']}"
        candidates = [
            unit for unit in parsed_by_path[path_key]
            if unit.blocks
            and unit.blocks[0].location == expected_location
            and unit.record_type == str(witness["record_type"])
            and unit.title == expected_title
        ]
        if witness.get("source_variant_label"):
            candidates = [
                unit for unit in candidates
                if unit.source_variant_label == witness["source_variant_label"]
            ]
        if len(candidates) != 1:
            raise ValueError(f"pinned record is not unique for {witness_id}: {len(candidates)}")
        unit = candidates[0]
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

    return (
        oracle,
        evaluator_witnesses,
        [units_by_id[key] for key in sorted(units_by_id)],
        units_by_witness,
    )


def _explicit_unsupported_gap(row: Mapping[str, Any], witness: Mapping[str, Any]) -> bool:
    span = row.get("source_span") or {}
    prediction_identity = span.get("source_anchor") if isinstance(span, Mapping) else None
    if not isinstance(prediction_identity, Mapping):
        return False
    for gap in witness.get("unsupported_gaps", []):
        for anchor in [gap.get("source_anchor"), *gap.get("additional_source_anchors", [])]:
            if (
                isinstance(anchor, Mapping)
                and str(span.get("location") or "") == str(anchor.get("location") or "")
                and _canonical(prediction_identity) == _canonical(anchor.get("identity"))
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
        "arms": {
            "fidelity_checked": {
                "occurrences": occurrence_rows,
                "relationships": relationship_rows,
            }
        }
    }
    adapted = adapt_c2_report_to_evaluator(comparison, evaluator_witnesses)
    evaluation = evaluate_frozen_cohort(
        adapted["predictions_by_arm"],
        oracle,
        evaluator_witnesses,
        unresolved_relationships_by_arm=adapted["unresolved_relationships_by_arm"],
    )
    unsupported_outputs: list[dict[str, str]] = []
    unlabeled_outputs: list[dict[str, str]] = []
    for witness in oracle["witnesses"]:
        witness_id = str(witness["witness_id"])
        for row in classifier_rows[witness_id]:
            if row.get("occurrence_kind") not in {"effect", "dependency", "gap"}:
                continue
            if row.get("occurrence_kind") != "gap" and (
                row.get("capability_value") or row.get("dependency_value")
            ):
                continue
            target = unsupported_outputs if _explicit_unsupported_gap(row, witness) else unlabeled_outputs
            target.append(
                {
                    "witness_id": witness_id,
                    "source_text": str((row.get("source_span") or {}).get("text") or ""),
                }
            )

    expected_relationships = sum(
        len(row.get("semantic_relationships", [])) for row in oracle["witnesses"]
    )
    attached_relationships = [
        relation
        for rows in adapted["predictions_by_arm"]["fidelity_checked"].values()
        for prediction in rows
        for relation in prediction.get("relationships", [])
    ]
    unresolved_relationships = adapted["unresolved_relationships_by_arm"]["fidelity_checked"]
    arm = evaluation["arms"]["fidelity_checked"]
    felmina_id = "fresh3-felmina-enhanced-silent-killer"
    felmina_rows = classifier_rows[felmina_id]
    felmina_attack = [
        row for row in felmina_rows
        if row.get("occurrence_kind") == "effect"
        and row.get("capability_value") in {"direct_damage", "multi_hit_action"}
    ]
    summary = {
        "artifact_version": "m6-third-fresh-consumed-c2-development-regression-1",
        "cohort": {
            "name": "m6_consumed_development_regression",
            "status": "consumed_development_evidence",
            "witness_count": len(evaluator_witnesses),
            "witness_ids": [row[0] for row in EXPECTED_WITNESSES],
            "held_out": False,
        },
        "oracle_provenance": {
            "original_frozen_oracle_sha256": FROZEN_ORACLE_SHA256,
            "original_frozen_evaluation_report_sha256": FROZEN_REPORT_SHA256,
            "promoted_fixture_sha256": _sha256(ORACLE_PATH.read_bytes()),
            "embedded_html": False,
            "source_capture_and_slice_pins_verified": True,
            "owner_correction_count": 1,
        },
        "metrics": {
            "effects": arm["effect_occurrence_precision_recall"],
            "dependencies": arm["dependency_occurrence_precision_recall"],
            "canonical_labels": arm["capability_label_precision_recall"],
            "field_accuracies": arm["field_correctness"],
            "explicit_unsupported_gaps": arm["explicit_unsupported_gaps"],
            "anchor_diagnostics": arm["diagnostic_only"],
            "relationship_groups": arm["relationship_groups"],
        },
        "classification": {
            "explicit_unsupported_gap_outputs": unsupported_outputs,
            "unlabeled_outputs_without_an_explicit_gap_anchor": unlabeled_outputs,
            "unresolved_relationships": unresolved_relationships,
            "expected_relationship_count": expected_relationships,
            "attached_relationship_count": len(attached_relationships),
            "relationship_group_metrics": arm["relationship_groups"],
            "felmina_x5_owned_occurrences": [
                {
                    "capability_value": row.get("capability_value"),
                    "source_owner_id": row.get("source_owner_id"),
                    "source_anchor": (row.get("source_span") or {}).get("source_anchor"),
                    "hit_count": row.get("hit_count"),
                }
                for row in felmina_attack
            ],
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
    output = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
    print(output, end="")


if __name__ == "__main__":
    main()
