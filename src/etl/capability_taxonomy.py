"""Reviewed atomic capability materialization and repository-native review tooling."""

from __future__ import annotations

import argparse
import csv
import hashlib
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
IMMUTABLE_COLUMNS = (
    "proposal_id", "record_type", "source_fact_id", "character_name", "fact_name",
    "source_text", "source_url", "rule_id", "proposed_kind", "proposed_value",
    "proposed_direction", "proposed_target", "proposed_availability",
    "proposed_magnitude_value", "proposed_magnitude_unit",
    "proposed_activation_count", "proposed_duration_turns", "proposed_trigger",
    "matched_phrase", "artifact_version",
)
REVIEW_COLUMNS = (
    "decision", "corrected_kind", "corrected_value", "corrected_direction",
    "corrected_target", "corrected_availability", "corrected_magnitude_value",
    "corrected_magnitude_unit", "corrected_activation_count",
    "corrected_duration_turns", "corrected_trigger", "reviewer", "reviewer_notes",
)

RECORD_TYPES = {"skill", "passive", "sidekick_skill", "sidekick_aura"}


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


@lru_cache(maxsize=1)
def load_capability_taxonomy() -> dict[str, Any]:
    artifact = json.loads(TAXONOMY_PATH.read_text(encoding="utf-8"))
    required = (
        "artifact_version", "review_schema_version", "capabilities", "dependencies",
        "directions", "targets", "availability", "magnitude_units", "triggers",
        "review_states",
    )
    if any(not artifact.get(key) for key in required):
        raise ValueError("Capability taxonomy is missing required vocabulary or version fields")
    vocabulary_keys = (
        "capabilities", "dependencies", "directions", "targets", "availability",
        "magnitude_units", "triggers", "review_states",
    )
    for key in vocabulary_keys:
        if len(artifact[key]) != len(set(artifact[key])):
            raise ValueError(f"Capability taxonomy has duplicate {key}")
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
    return {
        "proposed_magnitude_value": percent.group(1) if percent else "",
        "proposed_magnitude_unit": "percent" if percent else "",
        "proposed_activation_count": activations.group(1) if activations else "",
        "proposed_duration_turns": turns.group(1) if turns else "",
        "proposed_trigger": trigger,
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
            "character_name": str(record.get("character_name") or ""),
            "fact_name": str(record.get("name") or ""), "source_text": source_text.strip(),
            "source_url": str(record.get("source_url") or ""), "rule_id": rule["id"],
            "phase": rule["phase"], "proposed_kind": rule["kind"], "proposed_value": rule["value"],
            "proposed_direction": rule["direction"], "proposed_target": rule["target"],
            "proposed_availability": availability, **_qualifiers(source_text, taxonomy),
            "matched_phrase": match.group(0), "artifact_version": taxonomy["artifact_version"],
            "proposal_origin": "rule",
        })
    for override in taxonomy.get("overrides", []):
        if override["record_type"] != record_type or override["record_id"] != source_id or (phase and override["phase"] != phase):
            continue
        identity = f"{record_type}|{source_id}|{override['id']}"
        availability = "main_only" if record_type == "sidekick_skill" else "main_or_sub" if record_type == "sidekick_aura" else "not_applicable"
        proposals.append({
            "proposal_id": hashlib.sha256(identity.encode()).hexdigest()[:24],
            "record_type": record_type, "source_fact_id": source_id,
            "character_name": str(record.get("character_name") or ""),
            "fact_name": str(record.get("name") or ""), "source_text": source_text.strip(),
            "source_url": str(record.get("source_url") or ""), "rule_id": override["id"],
            "phase": override["phase"], "proposed_kind": override["kind"], "proposed_value": override["value"],
            "proposed_direction": override["direction"], "proposed_target": override["target"],
            "proposed_availability": override.get("availability", availability),
            **_qualifiers(source_text, taxonomy),
            "matched_phrase": str(override.get("matched_phrase") or source_text).strip(),
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
        evidence.append({
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
        })
    evidence.sort(key=lambda row: (row["kind"], row["value"], row["source_id"]))
    capabilities = sorted({row["value"] for row in evidence if row["kind"] == "capability"})
    dependencies = sorted({row["value"] for row in evidence if row["kind"] == "dependency"})
    diagnostics = {key: states.get(key, 0) for key in ("proposed", "proven", "candidate", "rejected", "ambiguous", "reviewed")}
    diagnostics["untagged"] = int(not all_proposals)
    return capabilities, dependencies, evidence, taxonomy["artifact_version"], diagnostics


def _iter_records(paths: Iterable[Path]) -> Iterable[dict[str, Any]]:
    for path in sorted(paths, key=str):
        payload = json.loads(path.read_text(encoding="utf-8"))
        for row in payload.get("rows", []):
            if row.get("skill_id"):
                yield row
        for row in payload.get("passive_rows", []):
            if row.get("passive_skill_id"):
                yield row
        for sidekick in payload.get("rows", []):
            for row in (*sidekick.get("auto_skills", []), *sidekick.get("charge_skills", [])):
                if row.get("sidekick_skill_id"):
                    yield row
            for row in sidekick.get("auras", []):
                if row.get("sidekick_aura_id"):
                    yield row


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
    reference_path.write_text(json.dumps({
        "allowed_values": {
            "decision": taxonomy["review_states"] if (taxonomy := load_capability_taxonomy()) else [],
            "kind": ["capability", "dependency"],
            "capability": taxonomy["capabilities"], "dependency": taxonomy["dependencies"],
            "direction": taxonomy["directions"], "target": taxonomy["targets"],
            "availability": taxonomy["availability"],
            "magnitude_unit": taxonomy["magnitude_units"], "trigger": taxonomy["triggers"],
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


def import_review_batch(csv_path: Path, records: Iterable[dict[str, Any]], *, reviews_path: Path = REVIEWS_PATH) -> dict[str, Any]:
    taxonomy = load_capability_taxonomy()
    proposals = {row["proposal_id"]: row for record in records for row in propose(record)}
    with csv_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != BATCH_SIZE:
        raise ValueError(f"Review import requires exactly {BATCH_SIZE} rows")
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
            for field in ("corrected_magnitude_value", "corrected_activation_count", "corrected_duration_turns"):
                if row.get(field) and not re.fullmatch(r"\d+(?:\.\d+)?", row[field]):
                    raise ValueError(f"Invalid numeric qualifier for {row['proposal_id']}")
        elif any(row.get(key, "").strip() for key in REVIEW_COLUMNS if key.startswith("corrected_")):
            raise ValueError(f"Correction fields require decision=correct for {row['proposal_id']}")
    artifact = load_reviews(reviews_path)
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
    parser.add_argument("command", choices=("generate", "import", "diagnostics"))
    parser.add_argument("--parsed-dir", type=Path, required=True)
    parser.add_argument("--csv", type=Path)
    parser.add_argument("--phase", choices=sorted(PHASES))
    parser.add_argument("--batch-number", type=int, default=1)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--reviews", type=Path, default=REVIEWS_PATH)
    args = parser.parse_args()
    paths = list(args.parsed_dir.rglob("*.json"))
    records = list(_iter_records(paths))
    if args.command == "generate":
        if not args.csv or not args.phase:
            parser.error("generate requires --csv and --phase")
        generate_review_batch(records, phase=args.phase, batch_number=args.batch_number, seed=args.seed, output=args.csv, reviews_path=args.reviews)
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
