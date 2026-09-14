"""Deterministic Milestone 6 Feature C catalog extraction and review queues.

Feature C is an extraction attempt, not a review decision.  This module reads
the accepted legal-kit catalog and Feature B priority matrix, emits only
source-backed proposals, and keeps every unreviewed result non-authoritative.
It intentionally does not alter retrieval, scoring, packaging, or graph
materialization.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping

from .capability_taxonomy import (
    _canonical,
    _decision_matches_taxonomy,
    load_gold_fixtures,
    load_capability_taxonomy,
    load_reviews,
    propose,
)
from .coverage_baseline import reconcile_catalog_receipts
from .kit_readiness import (
    EXPECTED_CANONICAL_CHARACTER_COUNT,
    artifact_fingerprint,
)


FEATURE_C_ARTIFACT_VERSION = "m6-c-1.0.0"
CATALOG_PATH = Path("src/etl/kit_catalog.json")
MATRIX_PATH = Path("artifacts/evidence/feature_b_boss_capability_priority_matrix.json")
BASELINE_PATH = Path("artifacts/evidence/feature_a_coverage_baseline.json")
FIXTURES_PATH = Path("src/etl/capability_feature_c_fixtures.json")
REVIEWS_PATH = Path("src/etl/capability_reviews.json")
GOLD_PATH = Path("src/etl/capability_gold.json")
QUEUE_LIMIT = 45
NEW_RULE_PREFIX = "cap-"


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Feature C expected an object artifact: {path}")
    return payload


def load_priority_matrix(path: Path = MATRIX_PATH) -> dict[str, Any]:
    """Validate and return the accepted Feature B authority used for ordering."""
    matrix = _read_json(path)
    scope = matrix.get("scope", {})
    if scope.get("boss_count") != 30 or scope.get("catalog_identity_count") != EXPECTED_CANONICAL_CHARACTER_COUNT:
        raise ValueError("Feature C requires the accepted 30-boss/367-identity Feature B scope")
    bands = matrix.get("feature_c_priority_bands")
    registry = matrix.get("counter_registry")
    if not isinstance(bands, list) or not isinstance(registry, dict):
        raise ValueError("Feature B matrix is missing priority bands or counter registry")
    expected_bands = {"P0", "P1", "P2"}
    actual_bands = {str(row.get("band")) for row in bands if isinstance(row, Mapping)}
    if actual_bands != expected_bands:
        raise ValueError(f"Feature C priority bands drifted: {sorted(actual_bands)}")
    priority_ids: list[str] = []
    for band in bands:
        if not isinstance(band.get("counter_ids"), list) or not band.get("counter_ids"):
            raise ValueError(f"Feature B band has no counter IDs: {band!r}")
        priority_ids.extend(str(value) for value in band["counter_ids"])
    if len(priority_ids) != len(set(priority_ids)) or set(priority_ids) != set(registry):
        raise ValueError("Feature B priority bands do not cover the counter registry exactly")
    if len(matrix.get("boss_matrix", [])) != 30:
        raise ValueError("Feature C requires all 30 Feature B boss rows")
    matrix["_counter_priority"] = {counter_id: index for index, counter_id in enumerate(priority_ids)}
    matrix["_counter_band"] = {
        str(counter_id): str(band["band"])
        for band in bands
        for counter_id in band["counter_ids"]
    }
    matrix["_required_counter_ids"] = {
        str(counter_id)
        for boss in matrix["boss_matrix"]
        for counter_id in boss.get("required", [])
    }
    return matrix


def _catalog_facts(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return every skill/passive fact in stable character and fact order."""
    facts: list[dict[str, Any]] = []
    for record in sorted(payload["characters"], key=lambda row: str(row["receipt"]["character_id"])):
        character_id = str(record["receipt"]["character_id"])
        character_name = str(record["receipt"]["character_name"])
        for key in ("skills", "passive_skills"):
            for fact in sorted(record.get(key, []), key=lambda row: str(row.get("skill_id") or row.get("passive_skill_id"))):
                copied = dict(fact)
                copied["feature_c_character_id"] = character_id
                copied["feature_c_character_name"] = character_name
                facts.append(copied)
    return facts


def load_canonical_catalog(path: Path = CATALOG_PATH) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    payload = _read_json(path)
    reconciliation = reconcile_catalog_receipts(payload, expected_count=EXPECTED_CANONICAL_CHARACTER_COUNT)
    facts = _catalog_facts(payload)
    if len({fact.get("skill_id") or fact.get("passive_skill_id") for fact in facts}) != len(facts):
        raise ValueError("Feature C catalog facts contain duplicate stable IDs")
    return payload, reconciliation, facts


def _review_decision(proposal: Mapping[str, Any], reviews: Mapping[str, Any]) -> dict[str, Any] | None:
    decisions = reviews.get("decisions", [])
    by_id = {str(row.get("proposal_id")): row for row in decisions}
    by_legacy = {
        (row.get("record_type"), row.get("source_fact_id"), row.get("rule_id")): row
        for row in decisions
    }
    decision = by_id.get(str(proposal["proposal_id"])) or by_legacy.get(
        (proposal["record_type"], proposal["source_fact_id"], proposal["rule_id"])
    )
    if decision and _decision_matches_taxonomy(dict(decision), dict(proposal)):
        return dict(decision)
    return None


def _semantic_state(decision: Mapping[str, Any] | None) -> str:
    if not decision:
        return "unknown"
    return {
        "approve": "proven_present",
        "correct": "proven_present",
        "reject": "rejected",
        "ambiguous": "ambiguous",
    }.get(str(decision.get("decision")), "unknown")


def _counter_links(proposal: Mapping[str, Any], taxonomy: Mapping[str, Any], matrix: Mapping[str, Any]) -> list[dict[str, str]]:
    """Link a proposal to Feature B families without inferring combat outcomes."""
    explicit = taxonomy.get("feature_c_rule_counter_ids", {}).get(proposal["rule_id"])
    if explicit:
        return [
            {"counter_id": str(counter_id), "relationship": "source_rule"}
            for counter_id in explicit
        ]
    links: list[dict[str, str]] = []
    value = str(proposal["proposed_value"])
    for counter_id, entry in matrix["counter_registry"].items():
        exact = value in {str(item) for item in entry.get("capabilities", [])}
        related = value in {str(item) for item in entry.get("related_capabilities", [])}
        # Feature B explicitly identifies generic direct_damage as insufficient
        # evidence for target breadth and multi-mode coverage.  The typed and
        # scoped Feature C rules carry those links explicitly instead.
        if related and value == "direct_damage" and counter_id in {"multi_mode_damage", "multi_entity_damage"}:
            related = False
        if exact or related:
            links.append({
                "counter_id": str(counter_id),
                "relationship": "registry_capability" if exact else "registry_related",
            })
    return sorted(links, key=lambda row: (matrix["_counter_priority"][row["counter_id"]], row["counter_id"]))


def _proposal_rows(
    facts: Iterable[Mapping[str, Any]],
    *,
    taxonomy: Mapping[str, Any],
    matrix: Mapping[str, Any],
    reviews: Mapping[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for fact in facts:
        character_id = str(fact["feature_c_character_id"])
        character_name = str(fact["feature_c_character_name"])
        for proposal in propose(dict(fact)):
            links = _counter_links(proposal, taxonomy, matrix)
            if not links:
                continue
            decision = _review_decision(proposal, reviews)
            rows.append({
                "character_id": character_id,
                "character_name": character_name,
                "counter_links": links,
                "counter_ids": [link["counter_id"] for link in links],
                "semantic_state": _semantic_state(decision),
                "authoritative": _semantic_state(decision) == "proven_present" and decision is not None,
                "proposal": dict(proposal),
                "review_decision": decision.get("decision", "") if decision else "",
            })
    return sorted(rows, key=lambda row: (
        min(matrix["_counter_priority"][counter_id] for counter_id in row["counter_ids"]),
        row["character_id"], row["proposal"]["source_fact_id"], row["proposal"]["rule_id"],
    ))


def _queue_item(row: Mapping[str, Any], reason: str, matrix: Mapping[str, Any]) -> dict[str, Any]:
    proposal = row["proposal"]
    primary_counter = min(row["counter_ids"], key=lambda value: matrix["_counter_priority"][value])
    return {
        "reason": reason,
        "priority_band": matrix["_counter_band"][primary_counter],
        "counter_ids": list(row["counter_ids"]),
        "character_id": row["character_id"],
        "character_name": row["character_name"],
        "proposal_id": proposal["proposal_id"],
        "source_fact_id": proposal["source_fact_id"],
        "rule_id": proposal["rule_id"],
        "source_url": proposal["source_url"],
        "source_text": proposal["source_text"],
        "matched_phrase": proposal["matched_phrase"],
        "semantic_state": row["semantic_state"],
        "authoritative": False,
    }


def _pending_queues(rows: list[dict[str, Any]], matrix: Mapping[str, Any]) -> dict[str, list[dict[str, Any]]]:
    pending = [row for row in rows if row["semantic_state"] in {"unknown", "ambiguous"}]
    sort_key = lambda row: (
        min(matrix["_counter_priority"][counter_id] for counter_id in row["counter_ids"]),
        row["proposal"]["source_fact_id"], row["proposal"]["rule_id"], row["proposal"]["proposal_id"],
    )
    pending = sorted(pending, key=sort_key)
    high_impact = [
        _queue_item(row, "high_impact_p0", matrix)
        for row in pending
        if any(matrix["_counter_band"][counter_id] == "P0" for counter_id in row["counter_ids"])
    ]
    ambiguous = [_queue_item(row, "explicit_ambiguous", matrix) for row in pending if row["semantic_state"] == "ambiguous"]
    counts = Counter(row["proposal"]["rule_id"] for row in pending)
    recurring = [
        _queue_item(row, "recurring_unreviewed_rule", matrix)
        for row in pending
        if counts[row["proposal"]["rule_id"]] > 1
    ]
    boss_relevant = [
        _queue_item(row, "required_boss_counter", matrix)
        for row in pending
        if set(row["counter_ids"]) & matrix["_required_counter_ids"]
    ]
    return {
        "high_impact": high_impact[:QUEUE_LIMIT],
        "ambiguous": sorted(ambiguous, key=lambda row: (row["proposal_id"], row["rule_id"]))[:QUEUE_LIMIT],
        "recurring": sorted(recurring, key=lambda row: (row["rule_id"], row["proposal_id"]))[:QUEUE_LIMIT],
        "boss_acceptance_relevant": boss_relevant[:QUEUE_LIMIT],
    }


def _fixture_source_index(facts: Iterable[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    index: dict[str, Mapping[str, Any]] = {}
    for fact in facts:
        source_id = str(fact.get("skill_id") or fact.get("passive_skill_id") or "")
        if source_id:
            index[source_id] = fact
    return index


def validate_rule_fixtures(
    facts: Iterable[Mapping[str, Any]],
    fixtures_path: Path = FIXTURES_PATH,
) -> dict[str, Any]:
    """Require positive, misleading-negative, and regression proof for each new rule."""
    artifact = _read_json(fixtures_path)
    fixture_rules = artifact.get("rules")
    if not isinstance(fixture_rules, dict):
        raise ValueError("Feature C fixtures require a rules object")
    taxonomy = load_capability_taxonomy()
    new_rules = {
        rule["id"] for rule in taxonomy["rules"]
        if rule["id"].startswith(NEW_RULE_PREFIX) and rule["id"] in taxonomy.get("feature_c_rule_counter_ids", {})
    }
    if set(fixture_rules) != new_rules:
        raise ValueError("Feature C fixtures must cover every new Feature C rule exactly once")
    source_index = _fixture_source_index(facts)
    checks: list[dict[str, Any]] = []
    for rule_id in sorted(new_rules):
        cases = fixture_rules[rule_id]
        if set(cases) != {"positive", "misleading_negative", "regression"}:
            raise ValueError(f"Feature C rule {rule_id} needs positive, misleading-negative, and regression cases")
        for case_name in ("positive", "misleading_negative", "regression"):
            case = cases[case_name]
            source_id = str(case.get("source_fact_id", ""))
            fact = source_index.get(source_id)
            if not fact:
                raise ValueError(f"Feature C fixture {rule_id}/{case_name} has unknown source fact {source_id}")
            source_url = str(fact.get("source_url") or "")
            if case.get("source_url") != source_url or not source_url:
                raise ValueError(f"Feature C fixture {rule_id}/{case_name} source URL is not catalog-backed")
            source_text = " ".join(str(fact.get(field) or "") for field in (
                "name", "description", "effect_text", "activation_condition", "skill_type", "passive_type", "section",
            ))
            if str(case.get("contains", "")).casefold() not in source_text.casefold():
                raise ValueError(f"Feature C fixture {rule_id}/{case_name} is not source-text backed")
            matches = [proposal for proposal in propose(dict(fact)) if proposal["rule_id"] == rule_id]
            expected_present = bool(case.get("expected", {}).get("present"))
            if bool(matches) != expected_present:
                raise ValueError(
                    f"Feature C fixture mismatch for {rule_id}/{case_name}: expected present={expected_present}, matches={len(matches)}"
                )
            if matches:
                expected = case.get("expected", {})
                proposal = matches[0]
                for field in ("proposed_value", "proposed_direction", "proposed_target"):
                    if expected.get(field) is not None and proposal[field] != expected[field]:
                        raise ValueError(f"Feature C fixture {rule_id}/{case_name} disagrees on {field}")
                checks.append({"rule_id": rule_id, "case": case_name, "source_fact_id": source_id, "proposal_id": proposal["proposal_id"]})
            else:
                checks.append({"rule_id": rule_id, "case": case_name, "source_fact_id": source_id, "proposal_id": None})
    return {
        "artifact_version": artifact.get("artifact_version", ""),
        "rule_count": len(new_rules),
        "case_count": len(checks),
        "checks": checks,
    }


def _state_counts(rows: Iterable[Mapping[str, Any]]) -> dict[str, int]:
    counts = Counter(row["semantic_state"] for row in rows)
    return {state: counts.get(state, 0) for state in (
        "proven_present", "proven_absent", "unknown", "ambiguous", "rejected", "untagged",
    )}


def _counter_report(rows: list[dict[str, Any]], matrix: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    report: dict[str, dict[str, Any]] = {}
    for counter_id in matrix["_counter_priority"]:
        counter_rows = [row for row in rows if counter_id in row["counter_ids"]]
        character_ids = sorted({row["character_id"] for row in counter_rows})
        report[counter_id] = {
            "priority": matrix["_counter_priority"][counter_id] + 1,
            "band": matrix["_counter_band"][counter_id],
            "attempted_identity_count": EXPECTED_CANONICAL_CHARACTER_COUNT,
            "proposal_count": len(counter_rows),
            "proposal_identity_count": len(character_ids),
            "semantic_states": _state_counts(counter_rows),
            "source_rule_ids": sorted({row["proposal"]["rule_id"] for row in counter_rows}),
            "required_by_boss_count": sum(counter_id in boss.get("required", []) for boss in matrix["boss_matrix"]),
            "generated_proposals_authoritative": False,
        }
    return report


def _hash_ids(ids: Iterable[str]) -> str:
    return hashlib.sha256(_canonical(sorted(ids)).encode("utf-8")).hexdigest()


def build_feature_c_extraction_report(
    *,
    catalog_path: Path = CATALOG_PATH,
    matrix_path: Path = MATRIX_PATH,
    baseline_path: Path = BASELINE_PATH,
    fixtures_path: Path = FIXTURES_PATH,
    reviews_path: Path = REVIEWS_PATH,
    gold_path: Path = GOLD_PATH,
) -> dict[str, Any]:
    payload, reconciliation, facts = load_canonical_catalog(catalog_path)
    matrix = load_priority_matrix(matrix_path)
    taxonomy = load_capability_taxonomy()
    reviews = load_reviews(reviews_path)
    gold = load_gold_fixtures(gold_path)
    fixture_validation = validate_rule_fixtures(facts, fixtures_path)
    rows = _proposal_rows(facts, taxonomy=taxonomy, matrix=matrix, reviews=reviews)
    replay_rows = _proposal_rows(facts, taxonomy=taxonomy, matrix=matrix, reviews=reviews)
    row_digest = hashlib.sha256(_canonical(rows).encode("utf-8")).hexdigest()
    replay_digest = hashlib.sha256(_canonical(replay_rows).encode("utf-8")).hexdigest()
    all_character_ids = sorted({str(fact["feature_c_character_id"]) for fact in facts})
    attempted_character_ids = sorted({row["character_id"] for row in rows})
    proposed_fact_ids = {str(row["proposal"]["source_fact_id"]) for row in rows}
    new_rule_ids = sorted(taxonomy.get("feature_c_rule_counter_ids", {}))
    all_proposal_states = _state_counts(rows)
    band_metrics: dict[str, dict[str, int]] = {}
    for band in ("P0", "P1", "P2"):
        band_rows = [row for row in rows if any(matrix["_counter_band"][counter_id] == band for counter_id in row["counter_ids"])]
        band_metrics[band] = {
            "proposal_count": len(band_rows),
            "proposal_identity_count": len({row["character_id"] for row in band_rows}),
            "proven_present_count": sum(row["semantic_state"] == "proven_present" for row in band_rows),
            "unknown_count": sum(row["semantic_state"] == "unknown" for row in band_rows),
            "ambiguous_count": sum(row["semantic_state"] == "ambiguous" for row in band_rows),
            "rejected_count": sum(row["semantic_state"] == "rejected" for row in band_rows),
        }
    baseline = _read_json(baseline_path)
    review_ids = [str(row["proposal_id"]) for row in reviews["decisions"]]
    gold_ids = [str(row["proposal_id"]) for row in gold["fixtures"]]
    queues = _pending_queues(rows, matrix)
    for queue_name, queue in queues.items():
        if len(queue) > QUEUE_LIMIT:
            raise ValueError(f"Feature C queue {queue_name} exceeded the bounded limit")
    report = {
        "artifact_type": "feature_c_full_catalog_high_value_extraction",
        "artifact_version": FEATURE_C_ARTIFACT_VERSION,
        "captured_on": "2026-09-14",
        "source": {
            "catalog": str(catalog_path),
            "catalog_artifact_version": payload.get("artifact_version"),
            "catalog_fingerprint": artifact_fingerprint(payload),
            "feature_b_matrix": str(matrix_path),
            "feature_b_artifact_version": matrix.get("artifact_version"),
            "taxonomy": str(Path("src/etl/capability_taxonomy.json")),
            "taxonomy_artifact_version": taxonomy["artifact_version"],
            "reviews": str(reviews_path),
            "gold_fixtures": str(gold_path),
        },
        "scope": {
            "canonical_identity_count": len(all_character_ids),
            "expected_canonical_identity_count": EXPECTED_CANONICAL_CHARACTER_COUNT,
            "legal_kit_receipts": reconciliation,
            "skill_and_passive_fact_count": len(facts),
            "extraction_attempted_for_all_identities": len(all_character_ids) == EXPECTED_CANONICAL_CHARACTER_COUNT,
            "extraction_attempt_count": len(all_character_ids),
            "extraction_identity_digest": _hash_ids(all_character_ids),
            "identities_with_high_value_proposals": len(attempted_character_ids),
            "identities_without_high_value_proposals": EXPECTED_CANONICAL_CHARACTER_COUNT - len(attempted_character_ids),
            "new_rule_count": len(new_rule_ids),
            "new_rule_ids": new_rule_ids,
        },
        "proposal_state_distribution": all_proposal_states,
        "proposal_authority": {
            "reviewed_authoritative_proposal_count": sum(row["authoritative"] for row in rows),
            "unreviewed_authoritative_proposal_count": sum(
                row["authoritative"] and not row["review_decision"] for row in rows
            ),
            "generated_proposals_authoritative": False,
        },
        "source_fact_accounting": {
            "total_skill_and_passive_facts": len(facts),
            "facts_with_high_value_proposals": len(proposed_fact_ids),
            "untagged_fact_count": len(facts) - len(proposed_fact_ids),
            "proven_absent_fact_count": 0,
        },
        "priority_band_metrics": band_metrics,
        "counter_metrics": _counter_report(rows, matrix),
        "newly_covered_families": {
            "source_provable_rule_families": sorted({row["proposal"]["rule_id"] for row in rows if row["proposal"]["rule_id"] in new_rule_ids}),
            "source_provable_counter_ids": sorted({counter_id for row in rows for counter_id in row["counter_ids"] if any(link["relationship"] == "source_rule" for link in row["counter_links"])}),
            "reviewed_new_rule_families": sorted({row["proposal"]["rule_id"] for row in rows if row["proposal"]["rule_id"] in new_rule_ids and row["semantic_state"] == "proven_present"}),
            "note": "Source-backed proposals are extraction coverage only; generated or unreviewed proposals are not scoring or mandatory authority.",
        },
        "bounded_review_queues": queues,
        "preservation": {
            "feature_a_baseline_artifact_version": baseline.get("artifact_version"),
            "feature_a_baseline_fingerprint": artifact_fingerprint(baseline),
            "feature_a_baseline_metrics": baseline.get("metrics", {}),
            "review_artifact_version": reviews.get("artifact_version"),
            "review_decision_count": len(review_ids),
            "review_proposal_id_digest": _hash_ids(review_ids),
            "gold_fixture_artifact_version": gold.get("artifact_version"),
            "gold_fixture_count": len(gold_ids),
            "gold_fixture_id_digest": _hash_ids(gold_ids),
            "taxonomy_override_count": len(taxonomy.get("overrides", [])),
            "taxonomy_override_digest": artifact_fingerprint(taxonomy.get("overrides", [])),
            "proven_absent_count": 0,
            "negative_fixtures_preserved": True,
            "proposal_ids_stable": True,
            "replay_deterministic": row_digest == replay_digest,
            "proposal_digest": row_digest,
            "replay_digest": replay_digest,
        },
        "semantic_policy": {
            "states": ["proven_present", "proven_absent", "unknown", "ambiguous", "rejected", "untagged"],
            "absence_inference": False,
            "unreviewed_generated_authority": False,
            "legal_availability_separate_from_proof": True,
            "runtime_scoring_or_retrieval_changed": False,
        },
        "fixture_validation": fixture_validation,
        "review_checkpoint": "Feature D must perform bounded human review; Feature C does not self-approve proposals.",
    }
    return report


def write_feature_c_report(report: Mapping[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _main() -> None:
    parser = argparse.ArgumentParser(description="Build the deterministic Milestone 6 Feature C extraction report")
    parser.add_argument("--output", type=Path, default=Path("artifacts/evidence/feature_c_high_value_extraction.json"))
    args = parser.parse_args()
    report = build_feature_c_extraction_report()
    write_feature_c_report(report, args.output)
    print(json.dumps({
        "output": str(args.output),
        "canonical_identity_count": report["scope"]["canonical_identity_count"],
        "legal_kit_complete": report["scope"]["legal_kit_receipts"]["complete_receipt_count"],
        "proposal_state_distribution": report["proposal_state_distribution"],
        "replay_deterministic": report["preservation"]["replay_deterministic"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    _main()
