"""Aggregate-only semantic evaluation for the frozen C2 replacement cohort.

The semantic oracle is supplied by its human owner at runtime. This module
never performs file IO and never returns witness-level predictions or answers.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from typing import Any, Mapping, Sequence


EVALUATOR_VERSION = "c2-atomic-eval-1.0.0"
ORACLE_SCHEMA_VERSION = "c2-atomic-oracle-1"
FIDELITY_DIMENSIONS = (
    "source_record_selection",
    "source_identity",
    "effect_completeness",
    "effect_order",
    "parent_child_condition_attachment",
    "actor",
    "recipient",
    "trigger",
    "result",
    "magnitude_parameter",
    "duration_activation",
    "element",
    "attack_type",
    "mechanic_resource_reference",
    "child_definition_resolution",
)
FIELD_NAMES = (
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
    "relationships",
)
OCCURRENCE_KINDS = ("effect", "dependency")

_SPACE = re.compile(r"\s+")
_OPERATION_PATTERNS = (
    ("damage", re.compile(r"\b(?:attack|attacks|deal(?:s)?|fixed damage)\b", re.I)),
    ("restore", re.compile(r"\b(?:heal|restore|recover)\b", re.I)),
    ("apply", re.compile(r"\b(?:apply|inflict|give|grant)\b", re.I)),
    ("increase", re.compile(r"\b(?:increase|raise|up)\b|\+\s*\d", re.I)),
    ("decrease", re.compile(r"\b(?:decrease|reduce|lower|down)\b|-\s*\d", re.I)),
    ("remove", re.compile(r"\b(?:remove|clear|dispel)\b", re.I)),
    ("activate", re.compile(r"\b(?:activate|deploy|awaken)\b", re.I)),
    ("consume", re.compile(r"\bconsume(?:s|d)?\b", re.I)),
    ("require", re.compile(r"\b(?:requires?|needs?)\b", re.I)),
)


def _normal_text(value: Any) -> str:
    return _SPACE.sub(" ", unicodedata.normalize("NFKC", str(value or ""))).strip().casefold()


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _operation(row: Mapping[str, Any], *, occurrence_kind: str) -> str:
    explicit = _normal_text(row.get("operation"))
    if explicit:
        return explicit
    text = " ".join(
        str(value or "")
        for value in (
            row.get("source_text"),
            (row.get("source_span") or {}).get("text") if isinstance(row.get("source_span"), Mapping) else "",
            row.get("result"),
        )
    )
    if occurrence_kind == "dependency":
        if re.search(r"\bconsume(?:s|d)?\b", text, re.I):
            return "consume"
        if re.search(r"\b(?:requires?|needs?)\b", text, re.I):
            return "require"
        if re.search(r"\b(?:if|when|unless|only when|after|before|during)\b", text, re.I):
            return "conditional"
    for operation, pattern in _OPERATION_PATTERNS:
        if pattern.search(text):
            return operation
    if occurrence_kind == "dependency" and re.search(r"\b(?:if|when|unless|only when|after|before|during)\b", text, re.I):
        return "conditional"
    return "unknown"


def _prediction_capability(row: Mapping[str, Any]) -> str:
    value = row.get("atomic_capability_id") or row.get(
        "dependency_value" if row.get("occurrence_kind") == "dependency" else "capability_value"
    ) or ""
    return _normal_text(value)


def _prediction_anchor(row: Mapping[str, Any]) -> tuple[str, str]:
    span = row.get("source_span")
    if isinstance(span, Mapping):
        location = str(span.get("location") or "")
        text = str(span.get("text") or row.get("source_text") or "")
    else:
        location = str(row.get("source_location") or "")
        text = str(row.get("source_text") or "")
    return location, _normal_text(text)


def _expected_anchor(atom: Mapping[str, Any]) -> tuple[str, str]:
    anchor = atom.get("source_anchor") or {}
    if not isinstance(anchor, Mapping):
        return "", ""
    return str(anchor.get("location") or ""), _normal_text(anchor.get("quote"))


def _identity_matches(prediction: Mapping[str, Any], witness: Mapping[str, Any]) -> bool:
    return (
        str(prediction.get("source_capture_sha256") or "") == str(witness.get("source_capture_sha256") or "")
        and str(prediction.get("source_fact_id") or prediction.get("fact_id") or "")
        == str(witness.get("fact_id") or "")
    )


def _anchor_matches(prediction: Mapping[str, Any], atom: Mapping[str, Any]) -> bool:
    predicted_location, predicted_text = _prediction_anchor(prediction)
    expected_location, expected_quote = _expected_anchor(atom)
    return bool(
        predicted_location
        and expected_location
        and predicted_location == expected_location
        and expected_quote
        and expected_quote in predicted_text
    )


def _base_matches(
    prediction: Mapping[str, Any],
    atom: Mapping[str, Any],
    witness: Mapping[str, Any],
) -> bool:
    kind = str(atom.get("occurrence_kind") or "")
    return (
        _identity_matches(prediction, witness)
        and str(prediction.get("occurrence_kind") or "") == kind
        and kind in OCCURRENCE_KINDS
        and _operation(prediction, occurrence_kind=kind) == _normal_text(atom.get("operation"))
        and _anchor_matches(prediction, atom)
    )


def _maximum_one_to_one(edges: Sequence[Sequence[int]]) -> dict[int, int]:
    """Return a deterministic maximum matching from prediction to expected atom."""
    expected_owner: dict[int, int] = {}

    def place(predicted_index: int, visited: set[int]) -> bool:
        for expected_index in edges[predicted_index]:
            if expected_index in visited:
                continue
            visited.add(expected_index)
            previous = expected_owner.get(expected_index)
            if previous is None or place(previous, visited):
                expected_owner[expected_index] = predicted_index
                return True
        return False

    for predicted_index in range(len(edges)):
        place(predicted_index, set())
    return {predicted_index: expected_index for expected_index, predicted_index in expected_owner.items()}


def _metrics(predicted_count: int, expected_count: int, true_positive: int) -> dict[str, Any]:
    false_positive = predicted_count - true_positive
    false_negative = expected_count - true_positive
    return {
        "predicted_count": predicted_count,
        "expected_count": expected_count,
        "true_positive_count": true_positive,
        "false_positive_count": false_positive,
        "false_negative_count": false_negative,
        "precision": true_positive / predicted_count if predicted_count else 0.0,
        "recall": true_positive / expected_count if expected_count else 1.0 if not predicted_count else 0.0,
    }


def _field_status(value: Any) -> tuple[str, Any]:
    if isinstance(value, Mapping) and "status" in value:
        status = str(value.get("status") or "unknown")
        return status, value.get("value")
    if value is None or _normal_text(value) in {"", "unknown", "unresolved"}:
        return "unknown", None
    return "adjudicated", value


def _field_metrics(
    predictions: Sequence[Mapping[str, Any]],
    atoms: Sequence[Mapping[str, Any]],
    matching: Mapping[int, int],
) -> dict[str, Any]:
    expected_by_prediction = {predicted: expected for predicted, expected in matching.items()}
    result: dict[str, Any] = {}
    for field in FIELD_NAMES:
        counts = Counter()
        for atom_index, atom in enumerate(atoms):
            counts["denominator_count"] += 1
            status, expected_value = _field_status((atom.get("fields") or {}).get(field))
            if status == "not_applicable":
                counts["not_applicable_count"] += 1
                continue
            if status != "adjudicated":
                counts["unknown_count"] += 1
                continue
            counts["adjudicated_count"] += 1
            predicted_index = next(
                (index for index, expected_index in expected_by_prediction.items() if expected_index == atom_index),
                None,
            )
            if predicted_index is None:
                counts["incorrect_count"] += 1
                continue
            actual_value = predictions[predicted_index].get(field)
            if _canonical(actual_value) == _canonical(expected_value):
                counts["correct_count"] += 1
            else:
                counts["incorrect_count"] += 1
        result[field] = {
            **dict(counts),
            "accuracy": counts["correct_count"] / counts["adjudicated_count"] if counts["adjudicated_count"] else None,
        }
    return result


def _validate_inputs(
    predictions_by_arm: Mapping[str, Mapping[str, Sequence[Mapping[str, Any]]]],
    oracle: Mapping[str, Any],
    witnesses: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Mapping[str, Any]], dict[str, Mapping[str, Any]]]:
    if oracle.get("schema_version") != ORACLE_SCHEMA_VERSION:
        raise ValueError("unsupported semantic oracle schema")
    witness_by_id = {str(row.get("witness_id") or ""): row for row in witnesses}
    if not witness_by_id or "" in witness_by_id:
        raise ValueError("evaluation cohort requires stable witness identities")
    raw_oracle_rows = oracle.get("witnesses")
    if not isinstance(raw_oracle_rows, list):
        raise ValueError("semantic oracle witnesses must be a list")
    oracle_by_id = {str(row.get("witness_id") or ""): row for row in raw_oracle_rows}
    if set(oracle_by_id) != set(witness_by_id) or "" in oracle_by_id:
        raise ValueError("semantic oracle identities must equal the frozen cohort")
    for witness_id, witness in witness_by_id.items():
        adjudication = oracle_by_id[witness_id]
        if (
            str(adjudication.get("source_capture_sha256") or "") != str(witness.get("source_capture_sha256") or "")
            or str(adjudication.get("fact_id") or "") != str(witness.get("fact_id") or "")
        ):
            raise ValueError("semantic oracle source identity does not match the frozen manifest")
        for atom in adjudication.get("atoms", []):
            kind = str(atom.get("occurrence_kind") or "")
            location, quote = _expected_anchor(atom)
            if (
                kind not in OCCURRENCE_KINDS
                or not str(atom.get("atomic_capability_id") or "").strip()
                or not str(atom.get("operation") or "").strip()
                or not location
                or not quote
            ):
                raise ValueError("semantic oracle atom is missing its capability, operation, kind, or source anchor")
    for arm, per_witness in predictions_by_arm.items():
        extra_ids = set(per_witness) - set(witness_by_id)
        if extra_ids:
            raise ValueError(f"prediction arm {arm!r} contains identities outside the frozen cohort")
    return witness_by_id, oracle_by_id


def _arm_aggregate(
    per_witness: Mapping[str, Sequence[Mapping[str, Any]]],
    witness_by_id: Mapping[str, Mapping[str, Any]],
    oracle_by_id: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    occurrence_counts = {kind: Counter() for kind in OCCURRENCE_KINDS}
    capability_counts = Counter()
    field_totals = {kind: defaultdict(Counter) for kind in OCCURRENCE_KINDS}
    field_correctness: dict[str, Counter] = defaultdict(Counter)
    dimension_counts: dict[str, Counter] = {name: Counter() for name in FIDELITY_DIMENSIONS}
    witness_denominator = len(witness_by_id)

    for witness_id, witness in witness_by_id.items():
        expected_atoms = list(oracle_by_id[witness_id].get("atoms", []))
        predictions = [
            row
            for row in per_witness.get(witness_id, [])
            if str(row.get("occurrence_kind") or "") in OCCURRENCE_KINDS
        ]
        base_edges: list[list[int]] = []
        capability_edges: list[list[int]] = []
        for prediction in predictions:
            base_edges.append(
                [index for index, atom in enumerate(expected_atoms) if _base_matches(prediction, atom, witness)]
            )
            prediction_capability = _prediction_capability(prediction)
            capability_edges.append(
                [
                    index
                    for index in base_edges[-1]
                    if prediction_capability
                    and prediction_capability not in {"scoped_effect", "scoped_condition"}
                    and prediction_capability == _normal_text(expected_atoms[index].get("atomic_capability_id"))
                ]
            )
        base_matching = _maximum_one_to_one(base_edges)
        capability_matching = _maximum_one_to_one(capability_edges)
        for kind in OCCURRENCE_KINDS:
            predicted_indices = [i for i, row in enumerate(predictions) if row.get("occurrence_kind") == kind]
            expected_indices = [i for i, row in enumerate(expected_atoms) if row.get("occurrence_kind") == kind]
            tp = sum(1 for pred_index in base_matching if predictions[pred_index].get("occurrence_kind") == kind)
            occurrence_counts[kind].update(
                {
                    "predicted_count": len(predicted_indices),
                    "expected_count": len(expected_indices),
                    "true_positive_count": tp,
                }
            )
        capability_counts["predicted_count"] += sum(bool(_prediction_capability(row)) for row in predictions)
        capability_counts["expected_count"] += len(expected_atoms)
        capability_counts["true_positive_count"] += len(capability_matching)
        fields = _field_metrics(predictions, expected_atoms, base_matching)
        for field, metrics in fields.items():
            field_correctness[field].update(
                {key: value for key, value in metrics.items() if key != "accuracy" and isinstance(value, int)}
            )

        for dimension in FIDELITY_DIMENSIONS:
            value = (oracle_by_id[witness_id].get("fidelity_dimensions") or {}).get(dimension)
            status = str(value.get("status") or "unknown") if isinstance(value, Mapping) else "unknown"
            if status not in {"passed", "failed", "unknown", "not_applicable"}:
                status = "unknown"
            dimension_counts[dimension][status] += 1

    per_kind = {
        kind: _metrics(
            counts["predicted_count"],
            counts["expected_count"],
            counts["true_positive_count"],
        )
        for kind, counts in occurrence_counts.items()
    }
    effect_counts = occurrence_counts["effect"]
    dependency_counts = occurrence_counts["dependency"]
    return {
        "witness_denominator": witness_denominator,
        "capability_label_precision_recall": _metrics(
            capability_counts["predicted_count"],
            capability_counts["expected_count"],
            capability_counts["true_positive_count"],
        ),
        "effect_occurrence_precision_recall": per_kind["effect"],
        "dependency_occurrence_precision_recall": per_kind["dependency"],
        "primary_occurrence_precision_recall": _metrics(
            effect_counts["predicted_count"] + dependency_counts["predicted_count"],
            effect_counts["expected_count"] + dependency_counts["expected_count"],
            effect_counts["true_positive_count"] + dependency_counts["true_positive_count"],
        ),
        "field_correctness": {
            name: {
                **dict(counts),
                "accuracy": counts["correct_count"] / counts["adjudicated_count"] if counts["adjudicated_count"] else None,
            }
            for name, counts in sorted(field_correctness.items())
        },
        "condition_attachment": {
            **dict(field_correctness.get("condition", {})),
            "accuracy": (
                field_correctness["condition"]["correct_count"] / field_correctness["condition"]["adjudicated_count"]
                if field_correctness.get("condition", {}).get("adjudicated_count")
                else None
            ),
        },
        "typed_relationship_correctness": {
            **dict(field_correctness.get("relationships", {})),
            "accuracy": (
                field_correctness["relationships"]["correct_count"] / field_correctness["relationships"]["adjudicated_count"]
                if field_correctness.get("relationships", {}).get("adjudicated_count")
                else None
            ),
        },
        "c1_1_fidelity_dimensions": {
            name: {
                "denominator_count": witness_denominator,
                "status_counts": dict(sorted(dimension_counts[name].items())),
                "known_applicable_count": dimension_counts[name]["passed"] + dimension_counts[name]["failed"],
                "unknown_or_unresolved_count": dimension_counts[name]["unknown"],
                "not_applicable_count": dimension_counts[name]["not_applicable"],
            }
            for name in FIDELITY_DIMENSIONS
        },
    }


def evaluate_frozen_cohort(
    predictions_by_arm: Mapping[str, Mapping[str, Sequence[Mapping[str, Any]]]],
    oracle: Mapping[str, Any],
    witnesses: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Return cohort/arm aggregates only; never include a witness-level row."""
    witness_by_id, oracle_by_id = _validate_inputs(predictions_by_arm, oracle, witnesses)
    return {
        "evaluator_version": EVALUATOR_VERSION,
        "cohort": str(oracle.get("cohort") or "fresh_replacement"),
        "witness_count": len(witness_by_id),
        "arms": {
            str(arm): _arm_aggregate(per_witness, witness_by_id, oracle_by_id)
            for arm, per_witness in sorted(predictions_by_arm.items())
        },
        "oracle_answers_returned": False,
        "per_witness_results_returned": False,
    }
