"""Evaluate the consumed Milestone 6 cohort as development regression evidence."""

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
)
from src.etl.c2_semantic_evaluation import (
    adapt_c2_report_to_evaluator,
    evaluate_frozen_cohort,
)
from src.etl.source_fidelity import (
    PARSED_SIDEKICK_DIR,
    _source_url_for_character,
)
from src.etl.structural_evidence import (
    SourceIdentity,
    TraversalLimits,
    bind_catalog_facts,
    parse_grid_document,
    validate_source_anchor_identity,
)


ROOT = Path(__file__).resolve().parents[1]
ORACLE_PATH = ROOT / "tests/fixtures/c2/m6_consumed_development_regression_oracle.json"
EXPECTED_SOURCE_ORACLE_SHA256 = "3e57be52fd7576fab6d058f263966b851d0779f28b186937e9212f15276b2310"
EXPECTED_WITNESSES = (
    ("m6-heldout-aisha-waters-nocturne", "Water's Nocturne"),
    ("m6-heldout-otoha-as-surging-scratch", "Surging Scratch"),
    ("m6-heldout-nona-as-castigo", "Castigo"),
    ("m6-heldout-claude-es-another-zone-heal", "Another Zone turn-end Heal"),
    ("m6-heldout-jilya-invasion-glow", "Invasion Glow"),
    ("m6-heldout-harle-lunairetic", "Lunairetic"),
    ("m6-heldout-melissa-hornet-hail-enhanced", "Hornet Hail"),
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
        owner_anchor = gap.get("owner_source_anchor")
        owner_identity = owner_anchor.get("identity") if isinstance(owner_anchor, Mapping) else None
        if not isinstance(owner_identity, Mapping) or str(gap.get("source_owner_id") or "") != str(
            owner_identity.get("anchor_id") or ""
        ):
            raise ValueError(f"unsupported gap is missing its canonical owner anchor: {gap}")
        anchors.append(owner_anchor)

    for anchor in anchors:
        expected_location = str(anchor.get("location") or "")
        matching_blocks = [block for block in unit.blocks if block.location == expected_location]
        if len(matching_blocks) != 1:
            raise ValueError(
                f"source anchor no longer matches the pinned packet for {witness['witness_id']}: {anchor}"
            )
        identity = anchor.get("identity")
        if not isinstance(identity, Mapping) or not validate_source_anchor_identity(
            identity,
            source_fact_id=str(witness["fact_id"]),
            source_capture_sha256=str(witness["source_capture_sha256"]),
            block=matching_blocks[0],
            diagnostic_quote=str(anchor.get("quote") or ""),
        ):
            raise ValueError(
                f"canonical source anchor identity changed for {witness['witness_id']}: {anchor}"
            )


def load_pinned_inputs() -> tuple[dict[str, Any], list[dict[str, Any]], list[Any], dict[str, Any]]:
    oracle_bytes = ORACLE_PATH.read_bytes()
    oracle = json.loads(oracle_bytes)
    if oracle.get("cohort") != "m6_consumed_development_regression":
        raise ValueError("the promoted oracle must be marked as consumed development evidence")
    promotion = oracle.get("promotion") or {}
    if promotion.get("source_oracle_sha256") != EXPECTED_SOURCE_ORACLE_SHA256:
        raise ValueError("promoted oracle source digest does not match the approved frozen oracle")
    if promotion.get("embedded_html") is not False:
        raise ValueError("the regression oracle must not embed complete HTML descriptions")
    witnesses = oracle.get("witnesses") or []
    actual_ids = tuple(str(row.get("witness_id") or "") for row in witnesses)
    if actual_ids != tuple(item[0] for item in EXPECTED_WITNESSES):
        raise ValueError("the consumed regression cohort identities or order changed")

    catalog = _load_catalog()
    records = _catalog_records(catalog)
    parsed_by_path: dict[str, list[Any]] = {}
    raw_by_path: dict[str, bytes] = {}
    units_by_id: dict[str, Any] = {}
    evaluator_witnesses: list[dict[str, Any]] = []

    for witness, (_witness_id, expected_title) in zip(witnesses, EXPECTED_WITNESSES, strict=True):
        source_path = ROOT / str(witness["source_path"])
        raw = raw_by_path.setdefault(source_path.as_posix(), source_path.read_bytes())
        capture_sha256 = _sha256(raw)
        if capture_sha256 != str(witness["source_capture_sha256"]):
            raise ValueError(f"pinned capture digest changed for {witness['witness_id']}")

        match = re.fullmatch(r"grid\[(\d+)\]/block\[0\]", str(witness["source_location"]))
        if not match:
            raise ValueError(f"unsupported pinned location for {witness['witness_id']}")
        grid_index = int(match.group(1))
        soup = BeautifulSoup(raw, "html.parser")
        grids = soup.select("div.character-skill-grid-container")
        if grid_index >= len(grids):
            raise ValueError(f"pinned grid is missing for {witness['witness_id']}")
        source_slice_sha256 = _sha256(str(grids[grid_index]).encode("utf-8"))
        if source_slice_sha256 != str(witness["source_slice_sha256"]):
            raise ValueError(f"pinned source-slice digest changed for {witness['witness_id']}")

        source_path_key = source_path.as_posix()
        if source_path_key not in parsed_by_path:
            sidekick = str(witness["fact_id"]).startswith("sidekick_")
            entity_kind = "sidekick" if sidekick else "character"
            source_url = (
                _sidekick_source_url(str(witness["entity_name"]))
                if sidekick
                else _source_url_for_character(records[str(witness["entity_name"])])
            )
            source = SourceIdentity(
                source_kind=entity_kind,
                source_url=source_url,
                capture_sha256=capture_sha256,
                capture_path=source_path.relative_to(ROOT).as_posix(),
            )
            units, diagnostics = parse_grid_document(
                raw.decode("utf-8"),
                source=source,
                entity_kind=entity_kind,
                entity_name=str(witness["entity_name"]),
            )
            if diagnostics:
                raise ValueError(f"pinned source parser diagnostics for {witness['witness_id']}: {diagnostics}")
            if not sidekick:
                record = records[str(witness["entity_name"])]
                bind_catalog_facts(units, _catalog_facts(record))
            parsed_by_path[source_path_key] = units
            raw_by_path[source_path_key] = raw
            units_by_id.update({unit.unit_id: unit for unit in units})

        expected_location = f"sha256:{capture_sha256}/{witness['source_location']}"
        matches = [
            unit
            for unit in parsed_by_path[source_path_key]
            if unit.blocks and unit.blocks[0].location == expected_location
        ]
        if len(matches) != 1:
            raise ValueError(f"pinned record is not unique for {witness['witness_id']}")
        unit = matches[0]
        if unit.title != expected_title or unit.entity_name != witness["entity_name"]:
            raise ValueError(f"pinned record title or source owner changed for {witness['witness_id']}")
        if witness.get("source_variant_label") and unit.source_variant_label != witness["source_variant_label"]:
            raise ValueError(f"pinned source variant changed for {witness['witness_id']}")
        if unit.source_fact_id and unit.source_fact_id != witness["fact_id"]:
            raise ValueError(f"catalog fact binding changed for {witness['witness_id']}")
        unit.source_fact_id = str(witness["fact_id"])
        _verify_source_anchors(witness, unit)
        evaluator_witnesses.append(
            {
                "witness_id": str(witness["witness_id"]),
                "fact_id": str(witness["fact_id"]),
                "source_capture_sha256": capture_sha256,
                "source_location": str(witness["source_location"]),
                "source_slice_sha256": source_slice_sha256,
            }
        )

    return oracle, evaluator_witnesses, [units_by_id[key] for key in sorted(units_by_id)], {
        row["witness_id"]: unit
        for row, unit in zip(witnesses, (next(
            candidate for candidate in parsed_by_path[str(ROOT / str(row["source_path"]))]
            if candidate.blocks and candidate.blocks[0].location == f"sha256:{row['source_capture_sha256']}/{row['source_location']}"
        ) for row in witnesses), strict=True)
    }


def evaluate() -> tuple[dict[str, Any], dict[str, Any]]:
    oracle, evaluator_witnesses, all_units, unit_by_witness = load_pinned_inputs()
    occurrence_rows: list[dict[str, Any]] = []
    relationship_rows: list[dict[str, Any]] = []
    classifier_rows: dict[str, list[dict[str, Any]]] = {}

    oracle_by_id = {str(row["witness_id"]): row for row in oracle["witnesses"]}
    for witness_id, unit in unit_by_witness.items():
        witness = oracle_by_id[witness_id]
        classifier_input = {
            **witness,
            "record_id": str(witness["fact_id"]),
            "record_type": unit.record_type,
            "source_identity_status": "passed",
            "source_record_selection_status": "passed",
            "source_fixture_status": "passed",
        }
        classified = _classify_unit(
            classifier_input,
            unit,
            all_units,
            TraversalLimits(max_depth=1, max_pages_per_root=2),
            arm="fidelity_checked",
            fidelity_passed=True,
        )
        occurrences = [row.as_dict() for row in classified.occurrences]
        relationships = [row.as_dict() for row in classified.relationships]
        classifier_rows[witness_id] = occurrences
        occurrence_rows.extend(occurrences)
        relationship_rows.extend(relationships)

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

    expected_relationship_count = sum(
        len(row.get("semantic_relationships", [])) for row in oracle["witnesses"]
    )
    attached_relationships = [
        relationship
        for rows in adapted["predictions_by_arm"]["fidelity_checked"].values()
        for prediction in rows
        for relationship in prediction.get("relationships", [])
    ]
    unresolved_relationships = adapted["unresolved_relationships_by_arm"]["fidelity_checked"]
    melissa_id = EXPECTED_WITNESSES[-1][0]
    melissa_relations = [
        *[
            relationship
            for prediction in adapted["predictions_by_arm"]["fidelity_checked"][melissa_id]
            for relationship in prediction.get("relationships", [])
        ],
        *[
            relationship
            for relationship in unresolved_relationships
            if str(relationship.get("source_fact_id") or "") == str(oracle_by_id[melissa_id]["fact_id"])
        ],
    ]

    arm = evaluation["arms"]["fidelity_checked"]
    summary = {
        "artifact_version": "m6-consumed-c2-development-regression-1",
        "cohort": {
            "name": "m6_consumed_development_regression",
            "status": "consumed_development_evidence",
            "witness_count": len(evaluator_witnesses),
            "witness_ids": [row[0] for row in EXPECTED_WITNESSES],
            "held_out": False,
        },
        "oracle_provenance": {
            "original_frozen_oracle_sha256": EXPECTED_SOURCE_ORACLE_SHA256,
            "promoted_fixture_sha256": _sha256(ORACLE_PATH.read_bytes()),
            "embedded_html": False,
            "source_capture_and_slice_pins_verified": True,
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
        "relationships": {
            "expected_count": expected_relationship_count,
            "attached_count": len(attached_relationships),
            "unresolved_count": len(unresolved_relationships),
            "groups": arm["relationship_groups"],
            "melissa": melissa_relations,
        },
        "unsupported_gaps": [
            {
                "witness_id": row["witness_id"],
                "gap_ids": [str(gap["gap_id"]) for gap in row.get("unsupported_gaps", [])],
            }
            for row in oracle["witnesses"]
        ],
        "per_witness": [
            {
                "witness_id": row[0],
                "title": row[1],
                "effect_count": sum(item.get("occurrence_kind") == "effect" for item in classifier_rows[row[0]]),
                "dependency_count": sum(item.get("occurrence_kind") == "dependency" for item in classifier_rows[row[0]]),
                "canonical_effect_ids": sorted({str(item.get("capability_value") or "") for item in classifier_rows[row[0]] if item.get("occurrence_kind") == "effect" and item.get("capability_value")}),
                "canonical_dependency_ids": sorted({str(item.get("dependency_value") or "") for item in classifier_rows[row[0]] if item.get("occurrence_kind") == "dependency" and item.get("dependency_value")}),
            }
            for row in EXPECTED_WITNESSES
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
