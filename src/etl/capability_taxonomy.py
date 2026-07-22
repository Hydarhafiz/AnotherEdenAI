"""Reviewed atomic capability materialization and repository-native review tooling."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import random
import re
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

TAXONOMY_PATH = Path(__file__).with_name("capability_taxonomy.json")
REVIEWS_PATH = Path(__file__).with_name("capability_reviews.json")
GOLD_PATH = Path(__file__).with_name("capability_gold.json")
BATCH_SIZE = 45
PHASES = {"defensive_setup", "offensive_support", "dependencies_conditions"}
SUPERSEDED_BATCHES = {
    "c2_defensive_setup_batch_2.csv",
    "c3_offensive_support_batch_1.csv",
}
MIGRATED_RULES = {
    "cap-barrier": {"cap-damage-reduction-barrier", "cap-shield"},
    "cap-cleanse": {"cap-remove-status-ailment", "cap-remove-debuff"},
}
IMMUTABLE_COLUMNS = (
    "proposal_id", "record_type", "source_fact_id", "character_name", "fact_name",
    "source_text", "source_url", "rule_id", "proposed_kind", "proposed_value",
    "proposed_direction", "proposed_target", "proposed_availability",
    "proposed_magnitude_value", "proposed_magnitude_unit",
    "proposed_activation_count", "proposed_duration_turns", "proposed_trigger",
    "proposed_stacking_behavior", "proposed_max_stacks", "proposed_qualifiers_json",
    "matched_phrase", "artifact_version",
)
REVIEW_COLUMNS = (
    "decision", "corrected_kind", "corrected_value", "corrected_direction",
    "corrected_target", "corrected_availability", "corrected_magnitude_value",
    "corrected_magnitude_unit", "corrected_activation_count",
    "corrected_duration_turns", "corrected_trigger", "corrected_stacking_behavior",
    "corrected_max_stacks", "corrected_qualifiers_json", "reviewer", "reviewer_notes",
)

RECORD_TYPES = {"skill", "passive", "sidekick_skill", "sidekick_aura"}
C3_RESERVED_CAPABILITIES = {
    "af_gauge_gain_up", "invert_weakness_resistance", "grant_copy", "follow_up_attack",
}


def _read_review_csv(path: Path) -> list[dict[str, str]]:
    """Read human-edited review CSVs from common spreadsheet encodings."""
    payload = path.read_bytes()
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = payload.decode("utf-8-sig", errors="surrogateescape")
        text = "".join(
            bytes([ord(char) - 0xDC00]).decode("cp1252")
            if "\udc80" <= char <= "\udc9f"
            else char
            for char in text
        )
    return list(csv.DictReader(io.StringIO(text), dialect="excel"))


def _normalize_corrected_fields(row: dict[str, str]) -> dict[str, str]:
    """Normalize safe spreadsheet-review aliases into constrained importer values."""
    normalized = dict(row)
    for key in REVIEW_COLUMNS:
        normalized[key] = normalized.get(key, "").strip()
    trigger_aliases = {
        "stellar_burst": "on_stellar_burst",
        "stellar burst": "on_stellar_burst",
        "in duel only(feature in 1 of another eden episode": "none",
        "velette in frontline": "battle_activation",
        "time breakup environmental effect": "battle_activation",
        "any ally used fire attack": "ally_action",
        "own_ability": "own_action",
        "user_into_frontline": "battle_activation",
        "any)type_effect_active": "battle_activation",
    }
    unit_aliases = {
        "hp": "flat_hp",
        "percent of user max hp": "percent",
        "percent of max hp": "percent",
        "stack": "stacks",
    }
    target_aliases = {
        "user, left_and_right_of_the_user": "self_and_adjacent_allies",
        "user, left and right of the user": "self_and_adjacent_allies",
        "single_ally": "one_ally",
        "all thunder element allies": "party",
        "all katana weapon allies": "party",
    }
    for key, aliases in (
        ("corrected_trigger", trigger_aliases),
        ("corrected_magnitude_unit", unit_aliases),
        ("corrected_target", target_aliases),
    ):
        value = normalized.get(key, "")
        normalized[key] = aliases.get(value.lower(), value)
    if normalized.get("corrected_max_stacks", "").lower() == "reject":
        normalized["corrected_max_stacks"] = ""
    kaleido_qualifier = re.fullmatch(
        r"\{\s*kaleido_type\s*:\s*(fire|water|wind|earth|thunder|shade|crystal|non-type)\s*\}",
        normalized.get("corrected_qualifiers_json", ""),
        re.IGNORECASE,
    )
    if kaleido_qualifier:
        element = kaleido_qualifier.group(1)
        normalized["corrected_qualifiers_json"] = _canonical({
            "element": ["non-type" if element.lower() == "non-type" else element.title()],
        })
    if normalized.get("decision") != "correct" and normalized.get("corrected_qualifiers_json") == "{}":
        normalized["corrected_qualifiers_json"] = ""
    return normalized


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


@lru_cache(maxsize=1)
def load_capability_taxonomy() -> dict[str, Any]:
    artifact = json.loads(TAXONOMY_PATH.read_text(encoding="utf-8"))
    required = (
        "artifact_version", "review_schema_version", "capabilities", "dependencies",
        "directions", "targets", "availability", "magnitude_units", "triggers",
        "stacking_behaviors", "qualifier_domains", "review_states", "reserved_capabilities",
    )
    if any(not artifact.get(key) for key in required):
        raise ValueError("Capability taxonomy is missing required vocabulary or version fields")
    vocabulary_keys = (
        "capabilities", "dependencies", "directions", "targets", "availability",
        "magnitude_units", "triggers", "stacking_behaviors", "review_states",
    )
    for key in vocabulary_keys:
        if len(artifact[key]) != len(set(artifact[key])):
            raise ValueError(f"Capability taxonomy has duplicate {key}")
    if set(artifact["reserved_capabilities"]) != C3_RESERVED_CAPABILITIES:
        raise ValueError("Capability taxonomy must retain exactly the four deferred C3 capabilities as reserved")
    ids: set[str] = set()
    vocab = {"capability": set(artifact["capabilities"]), "dependency": set(artifact["dependencies"])}
    for rule in artifact.get("rules", []):
        if (
            not rule.get("id") or rule["id"] in ids or rule.get("phase") not in PHASES
            or rule.get("kind") not in vocab or rule.get("value") not in vocab.get(rule.get("kind"), set())
            or rule.get("direction") not in artifact["directions"] or rule.get("target") not in artifact["targets"]
            or not set(rule.get("record_types", ())).issubset(RECORD_TYPES)
            or not rule.get("record_types") or not rule.get("pattern")
        ):
            raise ValueError(f"Invalid atomic capability rule: {rule!r}")
        ids.add(rule["id"])
        if rule["phase"] == "offensive_support" and rule["value"] in C3_RESERVED_CAPABILITIES:
            raise ValueError("Reserved C3 capabilities cannot have active rules")
        re.compile(rule["pattern"], re.IGNORECASE)
        for pattern in rule.get("negative_patterns", []):
            re.compile(pattern, re.IGNORECASE)
    for override in artifact.get("overrides", []):
        kind = override.get("kind")
        vocabulary = {"capability": artifact["capabilities"], "dependency": artifact["dependencies"]}
        if (
            not override.get("id") or override["id"] in ids or not override.get("record_id")
            or override.get("record_type") not in RECORD_TYPES or kind not in vocabulary
            or override.get("value") not in vocabulary.get(kind, [])
            or override.get("direction") not in artifact["directions"]
            or override.get("target") not in artifact["targets"]
            or override.get("phase") not in PHASES
        ):
            raise ValueError(f"Invalid atomic capability override: {override!r}")
        ids.add(override["id"])
    return artifact


def active_capabilities(*, phase: str | None = None) -> list[str]:
    """Return capability values which can be proposed in the requested review phase."""
    taxonomy = load_capability_taxonomy()
    values = {
        rule["value"] for rule in taxonomy["rules"]
        if rule["kind"] == "capability" and (phase is None or rule["phase"] == phase)
    }
    return sorted(values)


def load_reviews(path: Path = REVIEWS_PATH) -> dict[str, Any]:
    if not path.exists():
        return {"artifact_version": "1.0.0", "decisions": []}
    artifact = json.loads(path.read_text(encoding="utf-8"))
    if not artifact.get("artifact_version") or not isinstance(artifact.get("decisions"), list):
        raise ValueError("Review artifact requires artifact_version and a decisions list")
    ids = [row.get("proposal_id") for row in artifact["decisions"]]
    if None in ids or len(ids) != len(set(ids)):
        raise ValueError("Review artifact contains missing or duplicate proposal IDs")
    return artifact


def _decision_matches_taxonomy(decision: dict[str, Any], proposal: dict[str, Any]) -> bool:
    """Never promote a decision whose reviewed semantics predate the current proposal."""
    if decision.get("artifact_version") == proposal["artifact_version"]:
        return True
    if decision.get("decision") == "correct":
        kind = decision.get("corrected_kind")
        value = decision.get("corrected_value")
        direction = decision.get("corrected_direction")
        target = decision.get("corrected_target")
    else:
        kind = decision.get("proposed_kind")
        value = decision.get("proposed_value")
        direction = decision.get("proposed_direction")
        target = decision.get("proposed_target")
    return (kind, value, direction, target) == (
        proposal["proposed_kind"], proposal["proposed_value"],
        proposal["proposed_direction"], proposal["proposed_target"],
    )


def load_gold_fixtures(path: Path = GOLD_PATH) -> dict[str, Any]:
    artifact = json.loads(path.read_text(encoding="utf-8"))
    if not artifact.get("artifact_version") or not isinstance(artifact.get("fixtures"), list):
        raise ValueError("Gold artifact requires artifact_version and a fixtures list")
    ids = [row.get("proposal_id") for row in artifact["fixtures"]]
    if None in ids or len(ids) != len(set(ids)):
        raise ValueError("Gold artifact contains missing or duplicate proposal IDs")
    return artifact


def _source(record: dict[str, Any]) -> tuple[str, str]:
    candidates = (
        ("skill", record.get("skill_id")),
        ("passive", record.get("passive_skill_id")),
        ("sidekick_skill", record.get("sidekick_skill_id")),
        ("sidekick_aura", record.get("sidekick_aura_id")),
    )
    record_type, raw_id = next(((kind, value) for kind, value in candidates if value), ("", ""))
    source_id = str(raw_id or "")
    if not source_id:
        raise ValueError("Atomic capability records require a stable source fact ID")
    return record_type, source_id


def _rule_record_type(record_type: str) -> str:
    """Let sidekick facts reuse objective rules without losing their own identity."""
    return {"sidekick_skill": "skill", "sidekick_aura": "passive"}.get(record_type, record_type)


def _qualifiers(text: str, taxonomy: dict[str, Any]) -> dict[str, str]:
    percent = re.search(r"(?<!\w)(\d+(?:\.\d+)?)\s*%", text)
    turns = re.search(r"\bfor\s+(\d+)\s+turns?\b", text, re.IGNORECASE)
    activations = re.search(r"\b(\d+)\s+(?:times?|activations?|uses?)\b", text, re.IGNORECASE)
    trigger = next((value for value in taxonomy["triggers"] if value != "none" and re.search(rf"\b{re.escape(value.replace('_', ' '))}\b", text, re.IGNORECASE)), "none")
    max_stacks = re.search(r"\bmax(?:imum)?\s+(\d+)\s+stacks?\b|\bup to\s+(\d+)\s+stacks?\b", text, re.IGNORECASE)
    stacking_behavior = (
        "overwrites" if re.search(r"\b(?:overwrite|replaces?)\b", text, re.IGNORECASE)
        else "stackable" if re.search(r"\bstacks?\b", text, re.IGNORECASE)
        else "not_applicable"
    )
    qualifiers: dict[str, list[str]] = {}
    for domain, values in taxonomy["qualifier_domains"].items():
        matched = [value for value in values if re.search(rf"\b{re.escape(value)}\b", text, re.IGNORECASE)]
        if matched:
            qualifiers[domain] = matched
    return {
        "proposed_magnitude_value": percent.group(1) if percent else "",
        "proposed_magnitude_unit": "percent" if percent else "",
        "proposed_activation_count": activations.group(1) if activations else "",
        "proposed_duration_turns": turns.group(1) if turns else "",
        "proposed_trigger": trigger,
        "proposed_stacking_behavior": stacking_behavior,
        "proposed_max_stacks": next((value for value in (max_stacks.groups() if max_stacks else ()) if value), ""),
        "proposed_qualifiers_json": _canonical(qualifiers),
    }


def propose(record: dict[str, Any], *, phase: str | None = None) -> list[dict[str, str]]:
    taxonomy = load_capability_taxonomy()
    record_type, source_id = _source(record)
    source_text = " ".join(str(record.get(field) or "") for field in (
        "name", "description", "effect_text", "activation_condition", "skill_type",
        "passive_type", "section",
    ))
    proposals: list[dict[str, str]] = []
    for rule in taxonomy["rules"]:
        if phase and rule["phase"] != phase:
            continue
        if record_type not in rule["record_types"] and _rule_record_type(record_type) not in rule["record_types"]:
            continue
        match = re.search(rule["pattern"], source_text, re.IGNORECASE)
        if not match or any(re.search(p, source_text, re.IGNORECASE) for p in rule.get("negative_patterns", [])):
            continue
        identity = f"{record_type}|{source_id}|{rule['id']}"
        availability = "main_only" if record_type == "sidekick_skill" else "main_or_sub" if record_type == "sidekick_aura" else "not_applicable"
        proposals.append({
            "proposal_id": hashlib.sha256(identity.encode()).hexdigest()[:24],
            "record_type": record_type, "source_fact_id": source_id,
            "character_name": str(record.get("character_name") or record.get("sidekick_name") or ""),
            "fact_name": str(record.get("name") or ""), "source_text": source_text.strip(),
            "source_url": str(record.get("source_url") or ""), "rule_id": rule["id"],
            "phase": rule["phase"], "proposed_kind": rule["kind"], "proposed_value": rule["value"],
            "proposed_direction": rule["direction"], "proposed_target": rule["target"],
            # C3 qualifiers must be attributable to this atomic match, rather than
            # borrowing percentages or durations from another clause in a compound fact.
            "proposed_availability": availability, **_qualifiers(
                match.group(0) if rule["phase"] == "offensive_support" else source_text,
                taxonomy,
            ),
            "matched_phrase": match.group(0), "artifact_version": taxonomy["artifact_version"],
            "proposal_origin": "rule",
        })
    for override in taxonomy.get("overrides", []):
        if override["record_type"] != record_type or override["record_id"] != source_id or (phase and override["phase"] != phase):
            continue
        identity = f"{record_type}|{source_id}|{override['id']}"
        availability = "main_only" if record_type == "sidekick_skill" else "main_or_sub" if record_type == "sidekick_aura" else "not_applicable"
        matched_phrase = str(override.get("matched_phrase") or source_text).strip()
        proposals.append({
            "proposal_id": hashlib.sha256(identity.encode()).hexdigest()[:24],
            "record_type": record_type, "source_fact_id": source_id,
            "character_name": str(record.get("character_name") or record.get("sidekick_name") or ""),
            "fact_name": str(record.get("name") or ""), "source_text": source_text.strip(),
            "source_url": str(record.get("source_url") or ""), "rule_id": override["id"],
            "phase": override["phase"], "proposed_kind": override["kind"], "proposed_value": override["value"],
            "proposed_direction": override["direction"], "proposed_target": override["target"],
            "proposed_availability": override.get("availability", availability),
            **_qualifiers(matched_phrase, taxonomy),
            "matched_phrase": matched_phrase,
            "artifact_version": taxonomy["artifact_version"], "proposal_origin": "override",
        })
    return sorted(proposals, key=lambda row: (row["proposed_value"], row["source_fact_id"], row["rule_id"]))


def materialize_atomic(record: dict[str, Any], reviews_path: Path = REVIEWS_PATH) -> tuple[list[str], list[str], list[dict[str, str]], str, dict[str, int]]:
    taxonomy = load_capability_taxonomy()
    review_rows = load_reviews(reviews_path)["decisions"]
    decisions = {row["proposal_id"]: row for row in review_rows}
    legacy_decisions = {(row.get("record_type"), row.get("source_fact_id"), row.get("rule_id")): row for row in review_rows}
    all_proposals = propose(record)
    states = Counter()
    evidence: list[dict[str, str]] = []
    for proposal in all_proposals:
        decision = decisions.get(proposal["proposal_id"]) or legacy_decisions.get((proposal["record_type"], proposal["source_fact_id"], proposal["rule_id"]))
        if decision and not _decision_matches_taxonomy(decision, proposal):
            decision = None
        state = decision.get("decision") if decision else "candidate"
        states["proposed"] += 1
        states["reviewed"] += int(decision is not None)
        states[{"approve": "proven", "correct": "proven", "reject": "rejected"}.get(state, state)] += 1
        if state not in {"approve", "correct"}:
            continue
        kind = decision.get("corrected_kind") if state == "correct" else proposal["proposed_kind"]
        value = decision.get("corrected_value") if state == "correct" else proposal["proposed_value"]
        direction = decision.get("corrected_direction") if state == "correct" else proposal["proposed_direction"]
        target = decision.get("corrected_target") if state == "correct" else proposal["proposed_target"]
        def reviewed(field: str) -> str:
            corrected = decision.get(f"corrected_{field}") if state == "correct" else None
            return str(corrected if corrected not in (None, "") else proposal.get(f"proposed_{field}", ""))
        evidence_row = {
            "kind": kind, "value": value, "direction": direction, "target": target,
            "availability": reviewed("availability"),
            "magnitude_value": reviewed("magnitude_value"),
            "magnitude_unit": reviewed("magnitude_unit"),
            "activation_count": reviewed("activation_count"),
            "duration_turns": reviewed("duration_turns"), "trigger": reviewed("trigger"),
            "matched_phrase": proposal["matched_phrase"], "source": f"reviewed_{proposal.get('proposal_origin', 'rule')}",
            "source_id": proposal["rule_id"], "source_fact_id": proposal["source_fact_id"],
            "review_decision": state, "reviewer": str(decision.get("reviewer") or ""),
            "reviewer_notes": str(decision.get("reviewer_notes") or ""),
            "artifact_version": taxonomy["artifact_version"],
            "review_artifact_version": load_reviews(reviews_path)["artifact_version"],
        }
        if proposal["phase"] == "offensive_support":
            evidence_row.update({
                "stacking_behavior": reviewed("stacking_behavior"),
                "max_stacks": reviewed("max_stacks"),
                "qualifiers": json.loads(reviewed("qualifiers_json") or "{}"),
            })
        evidence.append(evidence_row)
    evidence.sort(key=lambda row: (row["kind"], row["value"], row["source_id"]))
    capabilities = sorted({row["value"] for row in evidence if row["kind"] == "capability"})
    dependencies = sorted({row["value"] for row in evidence if row["kind"] == "dependency"})
    diagnostics = {key: states.get(key, 0) for key in ("proposed", "proven", "candidate", "rejected", "ambiguous", "reviewed")}
    diagnostics["untagged"] = int(not all_proposals)
    return capabilities, dependencies, evidence, taxonomy["artifact_version"], diagnostics


def _iter_records(paths: Iterable[Path]) -> Iterable[dict[str, Any]]:
    """Yield canonical capability records, deriving stable IDs from parsed rows."""
    # Imported lazily: models use this module for capability materialization.
    from .models import PassiveSkillRow, SidekickAuraRow, SidekickSkillRow, SkillRow

    for path in sorted(paths, key=str):
        payload = json.loads(path.read_text(encoding="utf-8"))
        for row in payload.get("rows", []):
            if row.get("character_name") and row.get("name") and "description" in row:
                yield SkillRow.model_validate(row).model_dump()
        for row in payload.get("passive_rows", []):
            if row.get("character_name") and row.get("name"):
                yield PassiveSkillRow.model_validate(row).model_dump()
        for sidekick in payload.get("rows", []):
            sidekick_name = sidekick.get("name")
            for row in (*sidekick.get("auto_skills", []), *sidekick.get("charge_skills", [])):
                if sidekick_name and row.get("name"):
                    yield SidekickSkillRow.model_validate(row).model_dump()
            for row in sidekick.get("auras", []):
                if sidekick_name and row.get("name"):
                    yield SidekickAuraRow.model_validate(row).model_dump()


def generate_review_batch(records: Iterable[dict[str, Any]], *, phase: str, batch_number: int, seed: int, output: Path, reviews_path: Path = REVIEWS_PATH) -> list[dict[str, str]]:
    if phase not in PHASES or batch_number < 1:
        raise ValueError("A valid phase and positive batch number are required")
    review_rows = load_reviews(reviews_path)["decisions"]
    reviewed = {row["proposal_id"] for row in review_rows}
    reviewed_semantics = {(row.get("record_type"), row.get("source_fact_id"), row.get("rule_id")) for row in review_rows}
    unique = {
        row["proposal_id"]: row
        for record in records
        for row in propose(record, phase=phase)
        if row["proposal_id"] not in reviewed
        and (row["record_type"], row["source_fact_id"], row["rule_id"]) not in reviewed_semantics
    }
    buckets: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in unique.values():
        buckets[row["proposed_value"]].append(row)
    rng = random.Random(f"{load_capability_taxonomy()['artifact_version']}:{phase}:{batch_number}:{seed}")
    for rows in buckets.values():
        rows.sort(key=lambda row: row["proposal_id"])
        rng.shuffle(rows)
    chosen: list[dict[str, str]] = []
    while buckets and len(chosen) < BATCH_SIZE:
        for key in sorted(tuple(buckets)):
            if buckets[key] and len(chosen) < BATCH_SIZE:
                chosen.append(buckets[key].pop())
            if not buckets[key]:
                del buckets[key]
    if len(chosen) != BATCH_SIZE:
        raise ValueError(f"Phase {phase} has only {len(chosen)} unreviewed proposals; exactly {BATCH_SIZE} are required")
    chosen.sort(key=lambda row: (row["proposed_value"], row["source_fact_id"], row["rule_id"]))
    output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(IMMUTABLE_COLUMNS) + list(REVIEW_COLUMNS)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in chosen:
            writer.writerow({**row, **{key: "" for key in REVIEW_COLUMNS}})
    reference_path = output.with_name(f"{output.stem}.reference.json")
    allowed_values = {
        "decision": taxonomy["review_states"] if (taxonomy := load_capability_taxonomy()) else [],
        "kind": ["capability", "dependency"],
        "capability": taxonomy["capabilities"], "dependency": taxonomy["dependencies"],
        "direction": taxonomy["directions"], "target": taxonomy["targets"],
        "availability": taxonomy["availability"],
        "magnitude_unit": taxonomy["magnitude_units"], "trigger": taxonomy["triggers"],
    }
    if phase == "offensive_support":
        allowed_values.update({
            "stacking_behavior": taxonomy["stacking_behaviors"],
            "qualifier_domains": taxonomy["qualifier_domains"],
        })
    reference_path.write_text(json.dumps({
        "allowed_values": {
            **allowed_values,
        },
        "field_guidance": {
            "approve": "Accept the proposed atomic fact and its direction/target semantics.",
            "reject": "The source text does not prove the proposed atomic fact.",
            "correct": "Supply corrected kind/value/direction/target and any changed placement or qualifier fields.",
            "ambiguous": "Evidence is insufficient; this remains non-authoritative.",
            "immutable": list(IMMUTABLE_COLUMNS),
            "source_url": "Consult the linked source only when captured source_text is unclear."
        },
        "artifact_version": taxonomy["artifact_version"], "phase": phase,
        "batch_number": batch_number, "sampling_seed": seed,
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return chosen


def c3_seed_coverage(records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Diagnose source-backed seed candidates without treating a general mechanic page as evidence.

    A usable candidate is an atomic proposal from a parsed character or sidekick fact with
    a stable fact ID and its captured canonical wiki URL.  Reserved vocabulary is excluded
    completely: it remains a future extension rather than an unreviewed coverage hole.
    """
    active = active_capabilities(phase="offensive_support")
    proposals = [
        proposal for record in records for proposal in propose(record, phase="offensive_support")
        if proposal["proposed_value"] in active and proposal["source_url"]
    ]
    by_value: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)
    for proposal in proposals:
        # The parsed corpus can contain repeated renderings of the same stable fact.
        # One stable proposal is one seed candidate, regardless of duplicate payload rows.
        by_value[proposal["proposed_value"]].setdefault(proposal["proposal_id"], proposal)
    normalized: dict[str, list[dict[str, str]]] = {}
    for value, rows_by_id in by_value.items():
        rows = list(rows_by_id.values())
        rows.sort(key=lambda row: (row["source_fact_id"], row["rule_id"], row["proposal_id"]))
        normalized[value] = rows
    missing = [value for value in active if not normalized.get(value)]
    return {
        "artifact_version": load_capability_taxonomy()["artifact_version"],
        "active_capabilities": active,
        "reserved_capabilities": sorted(C3_RESERVED_CAPABILITIES),
        "coverage": {value: [row["proposal_id"] for row in normalized.get(value, [])] for value in active},
        "missing": missing,
        "proposals": normalized,
    }


def generate_c3_seed_review(records: Iterable[dict[str, Any]], *, output: Path) -> list[dict[str, str]]:
    """Export deterministic source-backed positive/cross-family C3 seed fixtures.

    This intentionally writes only review artifacts.  It neither imports decisions nor
    invokes ETL/Neo4j materialization; Feature C5 remains the graph replay boundary.
    """
    report = c3_seed_coverage(records)
    if report["missing"]:
        raise ValueError(
            "C3 seed coverage gap: " + ", ".join(report["missing"])
            + ". Supply a canonical character or sidekick fact; mechanics pages cannot fill this gap."
        )
    all_rows = [row for value in report["active_capabilities"] for row in report["proposals"][value]]
    selected: list[dict[str, str]] = []
    for value in report["active_capabilities"]:
        positive = report["proposals"][value][0]
        # A different active family is an explicit cross-family regression fixture.
        cross = next(row for row in all_rows if row["proposed_value"] != value)
        selected.append({
            **positive, "fixture_role": "positive_with_cross_family", "fixture_capability": value,
            "cross_family_proposal_id": cross["proposal_id"],
            "cross_family_value": cross["proposed_value"],
        })
    rows = sorted(selected, key=lambda row: (row["fixture_capability"], row["proposal_id"]))
    output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [*IMMUTABLE_COLUMNS, "fixture_role", "fixture_capability", "cross_family_proposal_id", "cross_family_value", *REVIEW_COLUMNS]
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({**row, **{key: "" for key in REVIEW_COLUMNS}})
    taxonomy = load_capability_taxonomy()
    output.with_name(f"{output.stem}.reference.json").write_text(json.dumps({
        "artifact_type": "targeted_c3_seed_review", "artifact_version": taxonomy["artifact_version"],
        "review_schema_version": taxonomy["review_schema_version"], "row_count": len(rows),
        "active_capabilities": report["active_capabilities"],
        "reserved_capabilities": sorted(C3_RESERVED_CAPABILITIES),
        "coverage": report["coverage"],
        "field_guidance": {
            "positive_with_cross_family": "Review the positive assertion; the named cross-family source is a permanent non-substitution regression.",
            "immutable": list(IMMUTABLE_COLUMNS),
        },
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rows


def generate_c3_recovery_batch(records: Iterable[dict[str, Any]], *, reviewed_batch: Path, output: Path, seed_proposal_ids: Iterable[str] = ()) -> list[dict[str, str]]:
    """Preserve reviewed replacement rows and deterministically refill seed overlaps to 45."""
    preserved = _read_review_csv(reviewed_batch)
    if len(preserved) != BATCH_SIZE or any(row.get("decision", "") not in load_capability_taxonomy()["review_states"] for row in preserved):
        raise ValueError("Reviewed C3 replacement batch must contain exactly 45 explicit decisions")
    active = set(active_capabilities(phase="offensive_support"))
    preserved = [row for row in preserved if row.get("proposed_value") in active]
    seed_ids = set(seed_proposal_ids)
    overlap = [row for row in preserved if row["proposal_id"] in seed_ids]
    # Overlapping decisions remain in the seed artifact/regression history.  They are
    # deliberately removed from the clean batch and replaced one-for-one below.
    preserved = [row for row in preserved if row["proposal_id"] not in seed_ids]
    # A seed overlap is already preserved as seed evidence.  Do not silently add the
    # same proposal back as an unreviewed refill row.
    used = {row["proposal_id"] for row in preserved} | seed_ids
    candidates = sorted({
        proposal["proposal_id"]: proposal
        for record in records for proposal in propose(record, phase="offensive_support")
        if proposal["proposed_value"] in active and proposal["proposal_id"] not in used
    }.values(), key=lambda row: (row["proposed_value"], row["source_fact_id"], row["rule_id"]))
    needed = BATCH_SIZE - len(preserved)
    if len(candidates) < needed:
        raise ValueError(f"C3 replacement recovery needs {needed} new proposals but found {len(candidates)}")
    rows = [*preserved, *({**row, **{key: "" for key in REVIEW_COLUMNS}} for row in candidates[:needed])]
    rows.sort(key=lambda row: (row["proposed_value"], row["source_fact_id"], row["rule_id"]))
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=[*IMMUTABLE_COLUMNS, *REVIEW_COLUMNS], extrasaction="ignore")
        writer.writeheader(); writer.writerows(rows)
    output.with_name(f"{output.stem}.reference.json").write_text(json.dumps({
        "artifact_type": "c3_recovery_batch", "artifact_version": load_capability_taxonomy()["artifact_version"],
        "phase": "offensive_support", "row_count": BATCH_SIZE,
        "preserved_proposal_ids": sorted(row["proposal_id"] for row in overlap),
        "new_proposal_count": needed, "active_capabilities": sorted(active),
        "reserved_capabilities": sorted(C3_RESERVED_CAPABILITIES),
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rows


def generate_migration_review(*, output: Path, reviews_path: Path = REVIEWS_PATH) -> list[dict[str, str]]:
    """Export changed legacy decisions for explicit review under the current vocabulary."""
    taxonomy = load_capability_taxonomy()
    changed = _migration_review_rows(reviews_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=[*IMMUTABLE_COLUMNS, *REVIEW_COLUMNS], extrasaction="ignore")
        writer.writeheader()
        for row in changed:
            writer.writerow({**row, **{key: "" for key in REVIEW_COLUMNS}})
    output.with_name(f"{output.stem}.reference.json").write_text(json.dumps({
        "artifact_type": "targeted_migration_review", "artifact_version": taxonomy["artifact_version"],
        "review_schema_version": taxonomy["review_schema_version"], "row_count": len(changed),
        "allowed_values": {"decision": taxonomy["review_states"], "capability": taxonomy["capabilities"],
                           "dependency": taxonomy["dependencies"], "direction": taxonomy["directions"],
                           "target": taxonomy["targets"], "availability": taxonomy["availability"],
                           "magnitude_unit": taxonomy["magnitude_units"], "trigger": taxonomy["triggers"],
                           "stacking_behavior": taxonomy["stacking_behaviors"],
                           "qualifier_domains": taxonomy["qualifier_domains"]},
        "field_guidance": {"migration": "Re-review every changed atomic fact; no prior approval is carried forward.",
                           "immutable": list(IMMUTABLE_COLUMNS)},
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return changed


def _migration_review_rows(reviews_path: Path = REVIEWS_PATH) -> list[dict[str, str]]:
    """Rebuild the targeted migration proposal set from existing legacy decisions."""
    changed: list[dict[str, str]] = []
    for decision in load_reviews(reviews_path)["decisions"]:
        record = {
            {"skill": "skill_id", "passive": "passive_skill_id", "sidekick_skill": "sidekick_skill_id", "sidekick_aura": "sidekick_aura_id"}[decision["record_type"]]: decision["source_fact_id"],
            "character_name": decision.get("character_name", ""), "name": decision.get("fact_name", ""),
            "description": decision.get("source_text", ""), "source_url": decision.get("source_url", ""),
        }
        proposals = propose(record, phase="defensive_setup")
        current = {row["rule_id"]: row for row in proposals}.get(decision["rule_id"])
        if current and not _decision_matches_taxonomy(decision, current):
            changed.append(current)
        for row in proposals:
            if row["rule_id"] in MIGRATED_RULES.get(decision["rule_id"], set()):
                changed.append(row)
    if not changed:
        raise ValueError("No changed decisions require migration review")
    changed = list({row["proposal_id"]: row for row in changed}.values())
    changed.sort(key=lambda row: (row["proposed_value"], row["source_fact_id"], row["rule_id"]))
    return changed


def import_review_batch(csv_path: Path, records: Iterable[dict[str, Any]], *, reviews_path: Path = REVIEWS_PATH) -> dict[str, Any]:
    if csv_path.name in SUPERSEDED_BATCHES:
        raise ValueError(f"Superseded review batch cannot be imported: {csv_path.name}")
    taxonomy = load_capability_taxonomy()
    reference_path = csv_path.with_name(f"{csv_path.stem}.reference.json")
    reference = json.loads(reference_path.read_text(encoding="utf-8")) if reference_path.exists() else {}
    proposals = {
        row["proposal_id"]: row
        for row in (
            _migration_review_rows(reviews_path)
            if reference.get("artifact_type") == "targeted_migration_review"
            else [proposal for record in records for proposal in propose(record)]
        )
    }
    rows = [_normalize_corrected_fields(row) for row in _read_review_csv(csv_path)]
    expected_rows = reference.get("row_count", BATCH_SIZE)
    if len(rows) != expected_rows:
        raise ValueError(f"Review import requires exactly {expected_rows} rows")
    seen: set[str] = set()
    for row in rows:
        proposal = proposals.get(row.get("proposal_id", ""))
        if not proposal or row["proposal_id"] in seen:
            raise ValueError("Review import contains source-ID drift or duplicate proposal IDs")
        seen.add(row["proposal_id"])
        for key in IMMUTABLE_COLUMNS:
            if row.get(key, "") != proposal.get(key, ""):
                if key in {"source_fact_id", "record_type"}:
                    raise ValueError(f"Review import contains source-ID drift: {row['proposal_id']} {key}")
                raise ValueError(f"Immutable review evidence was edited: {row['proposal_id']} {key}")
        decision = row.get("decision", "").strip()
        if decision not in taxonomy["review_states"]:
            raise ValueError(f"Blank or invalid decision for {row['proposal_id']}")
        if decision == "correct":
            kind = row.get("corrected_kind", "").strip()
            value = row.get("corrected_value", "").strip()
            if kind not in {"capability", "dependency"}:
                raise ValueError(f"Malformed correction for {row['proposal_id']}")
            vocabulary_key = "capabilities" if kind == "capability" else "dependencies"
            if value not in taxonomy[vocabulary_key]:
                raise ValueError(f"Malformed correction for {row['proposal_id']}")
            if row.get("corrected_direction") not in taxonomy["directions"] or row.get("corrected_target") not in taxonomy["targets"]:
                raise ValueError(f"Invalid correction semantics for {row['proposal_id']}")
            if row.get("corrected_availability") and row["corrected_availability"] not in taxonomy["availability"]:
                raise ValueError(f"Invalid corrected availability for {row['proposal_id']}")
            if row.get("corrected_magnitude_unit") and row["corrected_magnitude_unit"] not in taxonomy["magnitude_units"]:
                raise ValueError(f"Invalid corrected magnitude unit for {row['proposal_id']}")
            if row.get("corrected_trigger") and row["corrected_trigger"] not in taxonomy["triggers"]:
                raise ValueError(f"Invalid corrected trigger for {row['proposal_id']}")
            if row.get("corrected_stacking_behavior") and row["corrected_stacking_behavior"] not in taxonomy["stacking_behaviors"]:
                raise ValueError(f"Invalid corrected stacking behavior for {row['proposal_id']}")
            for field in ("corrected_magnitude_value", "corrected_activation_count", "corrected_duration_turns", "corrected_max_stacks"):
                if row.get(field) and not re.fullmatch(r"\d+(?:\.\d+)?", row[field]):
                    raise ValueError(f"Invalid numeric qualifier for {row['proposal_id']}")
            if row.get("corrected_qualifiers_json"):
                try:
                    qualifiers = json.loads(row["corrected_qualifiers_json"])
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Invalid corrected qualifiers for {row['proposal_id']}") from exc
                if not isinstance(qualifiers, dict) or any(
                    domain not in taxonomy["qualifier_domains"] or not isinstance(values, list)
                    or any(value not in taxonomy["qualifier_domains"][domain] for value in values)
                    for domain, values in qualifiers.items()
                ):
                    raise ValueError(f"Invalid corrected qualifiers for {row['proposal_id']}")
        elif any(row.get(key, "").strip() for key in REVIEW_COLUMNS if key.startswith("corrected_")):
            raise ValueError(f"Correction fields require decision=correct for {row['proposal_id']}")
    artifact = load_reviews(reviews_path)
    artifact["artifact_version"] = taxonomy["review_schema_version"]
    existing = {row["proposal_id"]: row for row in artifact["decisions"]}
    for row in rows:
        existing[row["proposal_id"]] = {key: row.get(key, "") for key in (*IMMUTABLE_COLUMNS, *REVIEW_COLUMNS)}
    artifact["decisions"] = sorted(existing.values(), key=lambda row: row["proposal_id"])
    reviews_path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return artifact


def diagnostics(records: Iterable[dict[str, Any]], reviews_path: Path = REVIEWS_PATH) -> dict[str, Any]:
    totals: Counter = Counter()
    per_value: dict[str, Counter] = defaultdict(Counter)
    decisions = {row["proposal_id"]: row for row in load_reviews(reviews_path)["decisions"]}
    for record in records:
        _, _, _, _, counts = materialize_atomic(record, reviews_path)
        totals.update(counts)
        for proposal in propose(record):
            decision = decisions.get(proposal["proposal_id"], {}).get("decision")
            state = {"approve": "proven", "correct": "proven", "reject": "rejected"}.get(decision, decision or "candidate")
            per_value[proposal["proposed_value"]]["proposed"] += 1
            per_value[proposal["proposed_value"]][state] += 1
            per_value[proposal["proposed_value"]]["reviewed"] += int(decision is not None)
    return {"totals": dict(sorted(totals.items())), "per_value": {key: dict(sorted(value.items())) for key, value in sorted(per_value.items())}}


async def assert_capability_materialization(driver, skills: list[Any], passives: list[Any], sidekicks: list[Any] | None = None) -> None:
    expected = {row.skill_id: (row.capabilities, row.dependencies, row.capability_evidence_json, row.capability_artifact_version, row.capability_diagnostics_json, row.schema_version) for row in skills}
    expected.update({row.passive_skill_id: (row.capabilities, row.dependencies, row.capability_evidence_json, row.capability_artifact_version, row.capability_diagnostics_json, row.schema_version) for row in passives})
    for sidekick in sidekicks or []:
        expected.update({row.sidekick_skill_id: (row.capabilities, row.dependencies, row.capability_evidence_json, row.capability_artifact_version, row.capability_diagnostics_json, row.schema_version) for row in [*sidekick.auto_skills, *sidekick.charge_skills]})
        expected.update({row.sidekick_aura_id: (row.capabilities, row.dependencies, row.capability_evidence_json, row.capability_artifact_version, row.capability_diagnostics_json, row.schema_version) for row in sidekick.auras})
    if not expected:
        return
    query = """MATCH (n) WHERE (n:Skill OR n:PassiveSkill OR n:SidekickSkill OR n:SidekickAura) AND coalesce(n.skill_id,n.passive_skill_id,n.sidekick_skill_id,n.sidekick_aura_id) IN $ids
RETURN coalesce(n.skill_id,n.passive_skill_id,n.sidekick_skill_id,n.sidekick_aura_id) AS id, n.capabilities AS capabilities,
n.dependencies AS dependencies, n.capability_evidence_json AS evidence,
n.capability_artifact_version AS version, n.capability_diagnostics_json AS diagnostics,
n.schema_version AS schema_version"""
    async with driver.session() as session:
        result = await session.run(query, ids=list(expected))
        actual = {row["id"]: (row["capabilities"] or [], row["dependencies"] or [], row["evidence"] or "", row["version"], row["diagnostics"] or "", row["schema_version"]) async for row in result}
    drift = sorted(key for key, value in expected.items() if actual.get(key) != value)
    if drift:
        raise RuntimeError(f"Atomic capability graph drift detected for {len(drift)} records: {drift[:10]}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate/import deterministic atomic capability review batches")
    parser.add_argument("command", choices=("generate", "generate-migration", "generate-c3-seed", "recover-c3-batch", "import", "diagnostics"))
    parser.add_argument("--reviewed-batch", type=Path)
    parser.add_argument("--seed-csv", type=Path)
    parser.add_argument("--parsed-dir", type=Path)
    parser.add_argument("--csv", type=Path)
    parser.add_argument("--phase", choices=sorted(PHASES))
    parser.add_argument("--batch-number", type=int, default=1)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--reviews", type=Path, default=REVIEWS_PATH)
    args = parser.parse_args()
    if args.command != "generate-migration" and not args.parsed_dir:
        parser.error(f"{args.command} requires --parsed-dir")
    paths = list(args.parsed_dir.rglob("*.json")) if args.parsed_dir else []
    records = list(_iter_records(paths))
    if args.command == "generate":
        if not args.csv or not args.phase:
            parser.error("generate requires --csv and --phase")
        generate_review_batch(records, phase=args.phase, batch_number=args.batch_number, seed=args.seed, output=args.csv, reviews_path=args.reviews)
        print(f"Awaiting human review: {args.csv}")
    elif args.command == "generate-migration":
        if not args.csv:
            parser.error("generate-migration requires --csv")
        generate_migration_review(output=args.csv, reviews_path=args.reviews)
        print(f"Awaiting human review: {args.csv}")
    elif args.command == "generate-c3-seed":
        if not args.csv:
            parser.error("generate-c3-seed requires --csv")
        generate_c3_seed_review(records, output=args.csv)
        print(f"Awaiting human review: {args.csv}")
    elif args.command == "recover-c3-batch":
        if not args.csv or not args.reviewed_batch:
            parser.error("recover-c3-batch requires --csv and --reviewed-batch")
        seed_ids: list[str] = []
        if args.seed_csv:
            seed_ids = [row["proposal_id"] for row in _read_review_csv(args.seed_csv)]
        generate_c3_recovery_batch(records, reviewed_batch=args.reviewed_batch, output=args.csv, seed_proposal_ids=seed_ids)
        print(f"Awaiting human review: {args.csv}")
    elif args.command == "import":
        if not args.csv:
            parser.error("import requires --csv")
        artifact = import_review_batch(args.csv, records, reviews_path=args.reviews)
        print(f"Imported {len(artifact['decisions'])} canonical review decisions")
    else:
        print(json.dumps(diagnostics(records, args.reviews), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
