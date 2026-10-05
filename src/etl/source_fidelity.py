"""Source-semantic fidelity gates for Milestone 6 Feature C1.1.

This module is deliberately an evidence boundary, not a classifier.  It
replays the accepted catalog against checksum-pinned captures, preserves real
fact identities and source slices, and keeps semantic adjudication in an
explicit oracle supplied only by the verification command.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from bs4 import BeautifulSoup

from .coverage_baseline import reconcile_catalog_receipts
from .kit_readiness import EXPECTED_CANONICAL_CHARACTER_COUNT, artifact_fingerprint
from .models import SidekickAuraRow, SidekickSkillRow
from .structural_evidence import (
    StructuralUnit,
    SourceIdentity,
    TraversalLimits,
    audit_reference_topology,
    bind_catalog_facts,
    extract_sidekick_aura_fields,
    extract_sidekick_charge_operations,
    parse_grid_document,
    resolve_bounded_references,
    select_traversal_limits,
)


SOURCE_FIDELITY_VERSION = "m6-c1.1-1.2.0"
CATALOG_PATH = Path("src/etl/kit_catalog.json")
MANIFEST_PATH = Path("artifacts/evidence/feature_c2_evaluation_freeze.json")
RAW_CHARACTER_DIR = Path("data/raw/characters")
RAW_SIDEKICK_DIR = Path("data/raw/sidekicks")
PARSED_SIDEKICK_DIR = Path("data/parsed/v1.2.0/sidekicks")
SOURCE_SLICE_FIXTURE_PATH = Path("tests/fixtures/source_fidelity/source_slice_manifest.json")

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

REQUIRED_ARCHETYPES = (
    "simple_legacy",
    "modern_nested_conditions",
    "sa_skill_or_passive",
    "stellar_burst_condition",
    "counter",
    "zone_another_or_radical_zone",
    "stack_or_character_resource",
    "lunatic_variant",
    "named_child_definition",
    "buff_debuff_or_resistance",
    "status_mechanic",
    "healing_or_revival",
    "guard_cover_or_hold_ground",
    "pain_poison",
    "recipient_or_position_condition",
    "multi_hit_or_multi_target",
    "sidekick_auto",
    "sidekick_charge",
    "sidekick_aura",
)

_SPACE_RE = re.compile(r"\s+")


def _clean(value: str) -> str:
    return _SPACE_RE.sub(" ", unicodedata.normalize("NFKC", value or "")).strip()


def _key(value: str) -> str:
    return _clean(value).casefold()


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _slugify(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", value.strip()).strip("_").lower() or "unknown"


def _catalog_facts(record: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [*record.get("skills", []), *record.get("passive_skills", [])]


def _fact_id(fact: Mapping[str, Any]) -> str:
    return str(fact.get("skill_id") or fact.get("passive_skill_id") or "")


def _record_type(fact: Mapping[str, Any]) -> str:
    return "passive_skill" if fact.get("passive_skill_id") else "active_skill"


def _catalog_index(catalog: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {
        str(record["receipt"]["character_id"]): record
        for record in catalog.get("characters", [])
    }


def _find_fact(record: Mapping[str, Any], fact_id: str) -> Mapping[str, Any]:
    for fact in _catalog_facts(record):
        if _fact_id(fact) == fact_id:
            return fact
    raise ValueError(f"source-fidelity witness fact is not in catalog: {fact_id}")


def _unit_grid_index(unit: StructuralUnit) -> int | None:
    match = re.search(r"/grid\[(\d+)\]$", unit.blocks[0].location.rsplit("/block[", 1)[0]) if unit.blocks else None
    return int(match.group(1)) if match else None


def _source_url_for_character(record: Mapping[str, Any]) -> str:
    return str(record.get("character", {}).get("detail_url") or record["receipt"].get("source_url") or "")


def _fixture_record_from_character(
    witness: Mapping[str, Any],
    catalog_by_id: Mapping[str, Mapping[str, Any]],
    *,
    raw_character_dir: Path,
) -> dict[str, Any]:
    record = next(
        (
            value
            for value in catalog_by_id.values()
            if str(value["receipt"].get("character_name")) == str(witness["entity_name"])
        ),
        None,
    )
    if record is None:
        raise ValueError(f"witness character is not in catalog: {witness['entity_name']}")
    fact = _find_fact(record, str(witness["fact_id"]))
    source_path = raw_character_dir / f"{_slugify(str(witness['entity_name']))}.html"
    if not source_path.exists():
        return {
            **dict(witness),
            "record_id": _fact_id(fact),
            "source_path": source_path.as_posix(),
            "source_identity_status": "unknown",
            "source_record_selection_status": "unknown",
            "failure": "capture_missing",
        }
    raw = source_path.read_bytes()
    capture_sha256 = _sha256(raw)
    source = SourceIdentity(
        source_kind="character",
        source_url=_source_url_for_character(record),
        capture_sha256=capture_sha256,
        capture_path=source_path.as_posix(),
    )
    units, parser_diagnostics = parse_grid_document(
        raw.decode("utf-8"),
        source=source,
        entity_kind="character",
        entity_name=str(witness["entity_name"]),
    )
    record_type = _record_type(fact)
    candidates = [
        unit
        for unit in units
        if unit.record_type == record_type and _key(unit.title) == _key(str(fact.get("name") or ""))
    ]
    exact = [unit for unit in candidates if _key(unit.legacy_description) == _key(str(fact.get("description") or ""))]
    selected = exact[0] if len(exact) == 1 else candidates[0] if len(candidates) == 1 else None
    source_identity_status = "passed" if capture_sha256 == str(witness.get("source_capture_sha256")) else "failed"
    if capture_sha256 != str(record["receipt"].get("source_revision")):
        source_identity_status = "failed"
    result: dict[str, Any] = {
        **dict(witness),
        "record_id": _fact_id(fact),
        "character_id": str(record["receipt"]["character_id"]),
        "source_path": source_path.as_posix(),
        "source_url": source.source_url,
        "capture_sha256": capture_sha256,
        "source_identity_status": source_identity_status,
        "source_record_selection_status": "passed" if selected else "unknown",
        "parser_diagnostics": parser_diagnostics,
    }
    if selected is None:
        result["failure"] = "no_unique_source_record"
        return result
    bound_units, _binding_diagnostics = bind_catalog_facts(units, _catalog_facts(record))
    selected.source_fact_id = _fact_id(fact)
    selected.family_id = str(fact.get("skill_family_id") or "") or None
    topology = audit_reference_topology(units, include_explicit_aliases=True)
    reference_rows = resolve_bounded_references(
        [selected],
        units,
        select_traversal_limits(topology),
        include_explicit_aliases=True,
    )
    soup = BeautifulSoup(raw, "html.parser")
    grids = soup.select("div.character-skill-grid-container")
    grid_index = _unit_grid_index(selected)
    source_slice = str(grids[grid_index]) if grid_index is not None and grid_index < len(grids) else ""
    links = [
        {
            "text": token.text,
            "href": token.href,
            "canonical_page_url": token.canonical_page_url,
            "fragment": token.fragment,
            "title": token.title,
            "location": token.location,
        }
        for token in selected.references()
    ]
    result.update(
        {
            "source_location": selected.blocks[0].location if selected.blocks else None,
            "grid_index": grid_index,
            "section": selected.section,
            "title": selected.title,
            "legacy_description": selected.legacy_description,
            "source_variant_identity": selected.variant_identity(),
            "explicit_definition_aliases": list(selected.explicit_definition_aliases),
            "captured_definition_resolutions": reference_rows,
            "source_slice_sha256": _sha256(source_slice.encode("utf-8")) if source_slice else None,
            "source_slice_bytes": len(source_slice.encode("utf-8")),
            "structural_block_count": len(selected.blocks),
            "structural_token_count": sum(len(block.tokens) for block in selected.blocks),
            "structural_order_digest": _sha256(
                _canonical(
                    [
                        {
                            "block": block.order,
                            "kind": block.kind,
                            "ancestry": block.ancestry,
                            "tokens": [(token.kind, token.text, token.href, token.fragment) for token in block.tokens],
                        }
                        for block in selected.blocks
                    ]
                ).encode("utf-8")
            ),
            "references": links,
        }
    )
    return result


def _sidekick_artifact(stem: str, parsed_sidekick_dir: Path) -> tuple[dict[str, Any], Path] | None:
    path = parsed_sidekick_dir / f"{stem}.json"
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("rows") or []
    return (rows[0], path) if rows else None


def _sidekick_rows(row: Mapping[str, Any]) -> list[tuple[str, str, str, str]]:
    result: list[tuple[str, str, str, str]] = []
    for item in row.get("auto_skills", []):
        parsed = SidekickSkillRow(**item)
        result.append(("sidekick_auto", parsed.sidekick_skill_id, parsed.name, parsed.description))
    for item in row.get("charge_skills", []):
        parsed = SidekickSkillRow(**item)
        result.append(("sidekick_charge", parsed.sidekick_skill_id, parsed.name, parsed.description))
    for item in row.get("auras", []):
        parsed = SidekickAuraRow(**item)
        result.append(("sidekick_aura", parsed.sidekick_aura_id, parsed.name, parsed.effect_text))
    return result


def _fixture_record_from_sidekick(
    witness: Mapping[str, Any],
    *,
    raw_sidekick_dir: Path,
    parsed_sidekick_dir: Path,
) -> dict[str, Any]:
    stem = _slugify(str(witness["entity_name"]))
    source_path = raw_sidekick_dir / f"{stem}.html"
    artifact = _sidekick_artifact(stem, parsed_sidekick_dir)
    if not source_path.exists() or artifact is None:
        return {
            **dict(witness),
            "record_id": str(witness["fact_id"]),
            "source_path": source_path.as_posix(),
            "source_identity_status": "unknown",
            "source_record_selection_status": "unknown",
            "failure": "capture_or_parsed_artifact_missing",
        }
    row, parsed_path = artifact
    raw = source_path.read_bytes()
    capture_sha256 = _sha256(raw)
    source_url = str(row.get("source_url") or witness.get("source_url") or "")
    source = SourceIdentity("sidekick", source_url, capture_sha256, source_path.as_posix())
    units, parser_diagnostics = parse_grid_document(
        raw.decode("utf-8"), source=source, entity_kind="sidekick", entity_name=str(witness["entity_name"])
    )
    wanted = (str(witness["record_type"]), str(witness["fact_id"]))
    sidekick_records = _sidekick_rows(row)
    actual = next((item for item in sidekick_records if item[:2] == wanted), None)
    candidates = [unit for unit in units if unit.record_type == wanted[0] and _key(unit.title) == _key(str(witness["fact_name"]))]
    selected = candidates[0] if len(candidates) == 1 else None
    result: dict[str, Any] = {
        **dict(witness),
        "record_id": wanted[1],
        "source_path": source_path.as_posix(),
        "parsed_path": parsed_path.as_posix(),
        "source_url": source_url,
        "capture_sha256": capture_sha256,
        "source_identity_status": "passed" if capture_sha256 == str(witness.get("source_capture_sha256")) else "failed",
        "source_record_selection_status": "passed" if actual and selected else "unknown",
        "parser_diagnostics": parser_diagnostics,
    }
    if actual is None or selected is None:
        result["failure"] = "sidekick_record_not uniquely_bound"
        return result
    selected.source_fact_id = wanted[1]
    soup = BeautifulSoup(raw, "html.parser")
    grids = soup.select("div.character-skill-grid-container")
    grid_index = _unit_grid_index(selected)
    source_slice = str(grids[grid_index]) if grid_index is not None and grid_index < len(grids) else ""
    result.update(
        {
            "grid_index": grid_index,
            "source_location": selected.blocks[0].location if selected.blocks else None,
            "section": selected.section,
            "title": selected.title,
            "legacy_description": selected.legacy_description,
            "source_variant_identity": selected.variant_identity(),
            "charge_operations": extract_sidekick_charge_operations(selected),
            "aura_source_fields": extract_sidekick_aura_fields(selected),
            "source_slice_sha256": _sha256(source_slice.encode("utf-8")) if source_slice else None,
            "source_slice_bytes": len(source_slice.encode("utf-8")),
            "structural_block_count": len(selected.blocks),
            "structural_token_count": sum(len(block.tokens) for block in selected.blocks),
            "references": [
                {
                    "text": token.text,
                    "href": token.href,
                    "canonical_page_url": token.canonical_page_url,
                    "fragment": token.fragment,
                    "title": token.title,
                    "location": token.location,
                }
                for token in selected.references()
            ],
        }
    )
    return result


def resolve_witness(
    witness: Mapping[str, Any],
    catalog_by_id: Mapping[str, Mapping[str, Any]],
    *,
    raw_character_dir: Path = RAW_CHARACTER_DIR,
    raw_sidekick_dir: Path = RAW_SIDEKICK_DIR,
    parsed_sidekick_dir: Path = PARSED_SIDEKICK_DIR,
) -> dict[str, Any]:
    if str(witness["source_kind"]) == "character":
        return _fixture_record_from_character(witness, catalog_by_id, raw_character_dir=raw_character_dir)
    return _fixture_record_from_sidekick(
        witness,
        raw_sidekick_dir=raw_sidekick_dir,
        parsed_sidekick_dir=parsed_sidekick_dir,
    )


def _all_character_replay(
    catalog: Mapping[str, Any],
    *,
    raw_character_dir: Path,
) -> tuple[list[dict[str, Any]], list[StructuralUnit], list[StructuralUnit], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    all_units: list[StructuralUnit] = []
    bound_units: list[StructuralUnit] = []
    diagnostics: list[dict[str, Any]] = []
    for record in sorted(catalog["characters"], key=lambda value: str(value["receipt"]["character_id"])):
        receipt = record["receipt"]
        name = str(receipt["character_name"])
        path = raw_character_dir / f"{_slugify(name)}.html"
        facts = _catalog_facts(record)
        base: dict[str, Any] = {
            "character_id": str(receipt["character_id"]),
            "character_name": name,
            "source_fact_denominator": len(facts),
            "source_path": path.as_posix(),
            "expected_capture_sha256": str(receipt.get("source_revision") or ""),
            "legal_kit_complete": str(receipt.get("overall_state")) == "complete",
        }
        if not path.exists():
            rows.append({**base, "source_identity_status": "unknown", "structural_parse_status": "unknown", "failure": "capture_missing"})
            diagnostics.extend({"character_id": base["character_id"], "source_fact_id": _fact_id(fact), "reason": "capture_missing"} for fact in facts)
            continue
        raw = path.read_bytes()
        source = SourceIdentity("character", _source_url_for_character(record), _sha256(raw), path.as_posix())
        units, parser_diagnostics = parse_grid_document(raw.decode("utf-8"), source=source, entity_kind="character", entity_name=name)
        bound, mapping_diagnostics = bind_catalog_facts(units, facts)
        all_units.extend(units)
        bound_units.extend(bound)
        diagnostics.extend({"character_id": base["character_id"], **item} for item in mapping_diagnostics)
        rows.append(
            {
                **base,
                "capture_sha256": source.capture_sha256,
                "source_url": source.source_url,
                "source_identity_status": "passed" if source.capture_sha256 == base["expected_capture_sha256"] else "failed",
                "structural_parse_status": "failed" if parser_diagnostics else "passed",
                "structural_unit_count": len(units),
                "bound_source_fact_count": len(bound),
                "unresolved_source_fact_count": len(mapping_diagnostics),
                "parser_diagnostic_count": len(parser_diagnostics),
            }
        )
    return rows, all_units, bound_units, diagnostics


def _all_sidekick_replay(
    *,
    raw_sidekick_dir: Path,
    parsed_sidekick_dir: Path,
) -> tuple[list[dict[str, Any]], list[StructuralUnit]]:
    rows: list[dict[str, Any]] = []
    all_units: list[StructuralUnit] = []
    for parsed_path in sorted(parsed_sidekick_dir.glob("*.json")):
        artifact = json.loads(parsed_path.read_text(encoding="utf-8"))
        parsed_rows = artifact.get("rows") or []
        if not parsed_rows:
            rows.append({"source_path": (raw_sidekick_dir / f"{parsed_path.stem}.html").as_posix(), "status": "unknown", "failure": "empty_parsed_artifact"})
            continue
        row = parsed_rows[0]
        source_path = raw_sidekick_dir / f"{parsed_path.stem}.html"
        if not source_path.exists():
            rows.append({"entity_name": row.get("name"), "source_path": source_path.as_posix(), "status": "unknown", "failure": "capture_missing"})
            continue
        raw = source_path.read_bytes()
        source = SourceIdentity("sidekick", str(row.get("source_url") or ""), _sha256(raw), source_path.as_posix())
        units, parser_diagnostics = parse_grid_document(raw.decode("utf-8"), source=source, entity_kind="sidekick", entity_name=str(row.get("name") or parsed_path.stem))
        all_units.extend(units)
        counts = Counter(unit.record_type for unit in units)
        rows.append(
            {
                "entity_name": str(row.get("name") or parsed_path.stem),
                "source_url": source.source_url,
                "source_path": source_path.as_posix(),
                "capture_sha256": source.capture_sha256,
                "structural_parse_status": "failed" if parser_diagnostics else "passed",
                "structural_unit_count": len(units),
                "record_counts": {kind: counts.get(kind, 0) for kind in ("sidekick_auto", "sidekick_charge", "sidekick_aura")},
                "parser_diagnostic_count": len(parser_diagnostics),
                "admitted_record_counts": {
                    "sidekick_auto": len(row.get("auto_skills", [])),
                    "sidekick_charge": len(row.get("charge_skills", [])),
                    "sidekick_aura": len(row.get("auras", [])),
                },
            }
        )
    return rows, all_units


def _link_summary(outcomes: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    statuses = Counter(str(row.get("status")) for row in outcomes)
    return {
        "occurrence_count": sum(statuses.values()),
        "status_distribution": dict(sorted(statuses.items())),
        "fully_resolved_occurrence_count": statuses.get("resolved", 0),
        "unknown_or_failed_not_absence": all(status not in {"proven_absent"} for status in statuses),
    }


def _archetype_coverage(manifest: Mapping[str, Any]) -> dict[str, Any]:
    cohorts = {
        "development": manifest.get("development_witnesses", []),
        "held_out": manifest.get("held_out_witnesses", []),
    }
    result: dict[str, Any] = {}
    for cohort, witnesses in cohorts.items():
        counts = Counter(
            archetype
            for witness in witnesses
            for archetype in witness.get("archetypes", [])
        )
        result[cohort] = {
            "witness_count": len(witnesses),
            "by_archetype": {name: counts.get(name, 0) for name in REQUIRED_ARCHETYPES},
            "missing_required_archetypes": [name for name in REQUIRED_ARCHETYPES if not counts.get(name)],
        }
    return result


def _empty_dimensions(reason: str) -> dict[str, dict[str, Any]]:
    return {name: {"status": "unknown", "reason": reason} for name in FIDELITY_DIMENSIONS}


def _apply_slice_fixture(
    rows: Sequence[dict[str, Any]],
    fixture: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    expected_by_id = {
        str(row["witness_id"]): row
        for row in (fixture or {}).get("records", [])
    }
    result: list[dict[str, Any]] = []
    for row in rows:
        expected = expected_by_id.get(str(row.get("witness_id")))
        if expected is None:
            result.append({**row, "source_fixture_status": "unknown"})
            continue
        matches = (
            row.get("capture_sha256") == expected.get("capture_sha256")
            and row.get("source_slice_sha256") == expected.get("source_slice_sha256")
            and row.get("source_location") == expected.get("source_location")
        )
        result.append(
            {
                **row,
                "source_fixture_status": "passed" if matches else "failed",
                "source_fixture_expected_sha256": expected.get("source_slice_sha256"),
            }
        )
    return result


def _expected_terms_ok(expected: Mapping[str, Any], actual: Mapping[str, Any]) -> bool:
    terms = [str(value) for value in expected.get("evidence_terms", [])]
    haystack = _key(" ".join([str(actual.get("title", "")), str(actual.get("legacy_description", ""))]))
    return all(_key(term) in haystack for term in terms)


def evaluate_oracle(
    manifest: Mapping[str, Any],
    catalog: Mapping[str, Any],
    oracle: Mapping[str, Any],
    *,
    raw_character_dir: Path = RAW_CHARACTER_DIR,
    raw_sidekick_dir: Path = RAW_SIDEKICK_DIR,
    parsed_sidekick_dir: Path = PARSED_SIDEKICK_DIR,
) -> dict[str, Any]:
    """Compare known and development source records with a development oracle.

    Protected validation is deliberately absent from this API. Its semantic
    oracle is owner-held and evaluated through the aggregate-only C2 runner.
    """
    allowed_ids = {
        str(row["witness_id"])
        for cohort in ("known_regressions", "development_witnesses")
        for row in manifest.get(cohort, [])
    }
    oracle_by_id = {str(row["witness_id"]): row for row in oracle.get("witnesses", [])}
    unexpected_ids = set(oracle_by_id) - allowed_ids
    if unexpected_ids:
        raise ValueError("development oracle contains identities outside known/development cohorts")
    catalog_by_id = _catalog_index(catalog)
    slice_fixture = (
        json.loads(SOURCE_SLICE_FIXTURE_PATH.read_text(encoding="utf-8"))
        if SOURCE_SLICE_FIXTURE_PATH.exists()
        else None
    )
    cohorts: dict[str, list[Mapping[str, Any]]] = {
        "development": manifest.get("development_witnesses", []),
    }
    evaluated: dict[str, Any] = {}
    for cohort, witnesses in cohorts.items():
        rows: list[dict[str, Any]] = []
        effect_count = dependency_count = 0
        for witness in witnesses:
            resolved = resolve_witness(
                witness,
                catalog_by_id,
                raw_character_dir=raw_character_dir,
                raw_sidekick_dir=raw_sidekick_dir,
                parsed_sidekick_dir=parsed_sidekick_dir,
            )
            resolved = _apply_slice_fixture([resolved], slice_fixture)[0]
            expected = oracle_by_id.get(str(witness["witness_id"]))
            if expected is None:
                rows.append(
                    {
                        **resolved,
                        "oracle_status": "unknown",
                        "dimensions": _empty_dimensions("missing_oracle_row"),
                        "semantic_fidelity_passed": False,
                        "c2_admission": "unknown_non_authoritative",
                    }
                )
                continue
            source_ok = (
                resolved.get("source_identity_status") == "passed"
                and resolved.get("source_record_selection_status") == "passed"
                and resolved.get("source_fixture_status") == "passed"
                and bool(resolved.get("source_slice_sha256"))
            )
            dimensions: dict[str, dict[str, Any]] = {}
            default_dimensions = oracle.get("default_dimensions", {})
            overrides = expected.get("dimension_overrides", {})
            for name in FIDELITY_DIMENSIONS:
                item = overrides.get(name, expected.get("dimensions", {}).get(name, default_dimensions.get(name, {"status": "unknown", "reason": "oracle_dimension_missing"})))
                status = str(item.get("status", "unknown"))
                if name in {"source_record_selection", "source_identity"}:
                    status = "passed" if source_ok else "unknown"
                elif name == "child_definition_resolution" and status == "passed":
                    expected_target = str(item.get("target_source_fact_id") or "")
                    matching_resolutions = [
                        row
                        for row in resolved.get("captured_definition_resolutions", [])
                        if row.get("status") == "resolved"
                        and row.get("resolution_basis")
                        in {"explicit_source_href_alias", "explicit_source_href_alias_and_variant_key"}
                        and (not expected_target or row.get("target_source_fact_id") == expected_target)
                    ]
                    if not matching_resolutions:
                        status = "failed"
                elif source_ok and status == "passed" and not _expected_terms_ok(item, resolved):
                    status = "failed"
                dimensions[name] = {**dict(item), "status": status}
            applicable = [row["status"] for row in dimensions.values() if row["status"] != "not_applicable"]
            semantic_passed = source_ok and bool(applicable) and all(status == "passed" for status in applicable)
            effects = list(expected.get("effect_occurrences", []))
            dependencies = list(expected.get("dependency_occurrences", []))
            if not effects and "effect_occurrence_count" in expected:
                effects = [
                    {"occurrence_id": f"{resolved['record_id']}:effect:{index}"}
                    for index in range(int(expected["effect_occurrence_count"]))
                ]
            if not dependencies and "dependency_occurrence_count" in expected:
                dependencies = [
                    {"occurrence_id": f"{resolved['record_id']}:dependency:{index}"}
                    for index in range(int(expected["dependency_occurrence_count"]))
                ]
            effect_count += len(effects)
            dependency_count += len(dependencies)
            rows.append(
                {
                    **resolved,
                    "oracle_status": str(expected.get("oracle_status", "adjudicated")),
                    "effect_occurrences": effects,
                    "dependency_occurrences": dependencies,
                    "effect_occurrence_count": len(effects),
                    "dependency_occurrence_count": len(dependencies),
                    "dimensions": dimensions,
                    "semantic_fidelity_passed": semantic_passed and str(expected.get("oracle_status", "adjudicated")) != "source_conflict",
                    "c2_admission": "fully_supported" if semantic_passed else "unknown_non_authoritative",
                }
            )
        dimension_counts = {name: Counter(str(row.get("dimensions", {}).get(name, {}).get("status", "unknown")) for row in rows) for name in FIDELITY_DIMENSIONS}
        evaluated[cohort] = {
            "witness_count": len(witnesses),
            "independently_adjudicated_effect_occurrence_count": effect_count,
            "independently_adjudicated_dependency_occurrence_count": dependency_count,
            "semantic_fidelity_passed_count": sum(1 for row in rows if row.get("semantic_fidelity_passed")),
            "fully_supported_inputs_for_c2": sum(1 for row in rows if row.get("c2_admission") == "fully_supported"),
            "dimension_status_counts": {name: dict(sorted(counts.items())) for name, counts in dimension_counts.items()},
            "witnesses": rows,
        }
    known_rows = []
    for witness in manifest.get("known_regressions", []):
        resolved = resolve_witness(
            witness,
            catalog_by_id,
            raw_character_dir=raw_character_dir,
            raw_sidekick_dir=raw_sidekick_dir,
            parsed_sidekick_dir=parsed_sidekick_dir,
        )
        expected = oracle_by_id.get(str(witness["witness_id"]))
        resolved = _apply_slice_fixture([resolved], slice_fixture)[0]
        expected_dimensions = {
            name: (
                (expected or {}).get("dimension_overrides", {}).get(name)
                or (expected or {}).get("dimensions", {}).get(name)
                or default_dimensions.get(name)
                or {"status": "unknown"}
            )
            for name in FIDELITY_DIMENSIONS
        }
        child_resolution = expected_dimensions.get("child_definition_resolution", {})
        if child_resolution.get("status") == "passed":
            expected_target = str(child_resolution.get("target_source_fact_id") or "")
            matching_resolutions = [
                row
                for row in resolved.get("captured_definition_resolutions", [])
                if row.get("status") == "resolved"
                and row.get("resolution_basis")
                in {"explicit_source_href_alias", "explicit_source_href_alias_and_variant_key"}
                and (not expected_target or row.get("target_source_fact_id") == expected_target)
            ]
            if not matching_resolutions:
                expected_dimensions["child_definition_resolution"] = {
                    **dict(child_resolution),
                    "status": "failed",
                }
        applicable = [
            value["status"]
            for value in expected_dimensions.values()
            if value["status"] != "not_applicable"
        ]
        oracle_status = str((expected or {}).get("oracle_status", "adjudicated"))
        semantic_passed = (
            resolved.get("source_identity_status") == "passed"
            and resolved.get("source_record_selection_status") == "passed"
            and resolved.get("source_fixture_status") == "passed"
            and bool(applicable)
            and all(status == "passed" for status in applicable)
            and oracle_status != "source_conflict"
        )
        effects = int((expected or {}).get("effect_occurrence_count", 0))
        dependencies = int((expected or {}).get("dependency_occurrence_count", 0))
        known_rows.append(
            {
                **resolved,
                "oracle_status": oracle_status,
                "generalization_evidence": False,
                "effect_occurrence_count": effects,
                "dependency_occurrence_count": dependencies,
                "dimensions": expected_dimensions,
                "semantic_fidelity_passed": semantic_passed,
                "c2_admission": "fully_supported" if semantic_passed else "unknown_non_authoritative",
            }
        )
    evaluated["known_regressions"] = {
        "witness_count": len(known_rows),
        "generalization_evidence": False,
        "witnesses": known_rows,
    }
    return evaluated


def build_source_fidelity_report(
    *,
    catalog_path: Path = CATALOG_PATH,
    manifest_path: Path = MANIFEST_PATH,
    raw_character_dir: Path = RAW_CHARACTER_DIR,
    raw_sidekick_dir: Path = RAW_SIDEKICK_DIR,
    parsed_sidekick_dir: Path = PARSED_SIDEKICK_DIR,
    oracle: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    reconciliation = reconcile_catalog_receipts(catalog, expected_count=EXPECTED_CANONICAL_CHARACTER_COUNT)
    character_rows, character_units, bound_units, mapping_diagnostics = _all_character_replay(
        catalog, raw_character_dir=raw_character_dir
    )
    sidekick_rows, sidekick_units = _all_sidekick_replay(
        raw_sidekick_dir=raw_sidekick_dir, parsed_sidekick_dir=parsed_sidekick_dir
    )
    topology_units = [*character_units, *sidekick_units]
    topology = audit_reference_topology(topology_units, include_explicit_aliases=True)
    limits = select_traversal_limits(topology)
    outcomes = resolve_bounded_references(
        bound_units,
        topology_units,
        limits,
        include_explicit_aliases=True,
    )
    sidekick_outcomes = resolve_bounded_references(
        sidekick_units,
        topology_units,
        limits,
        include_explicit_aliases=True,
    )
    sidekick_kind_counts = Counter(
        kind
        for row in sidekick_rows
        for kind, value in row.get("admitted_record_counts", {}).items()
        for _ in range(int(value))
    )
    sidekick_parsed_counts = Counter(
        kind
        for row in sidekick_rows
        for kind, value in row.get("record_counts", {}).items()
        for _ in range(int(value))
    )
    catalog_by_id = _catalog_index(catalog)
    fixture = None
    if SOURCE_SLICE_FIXTURE_PATH.exists():
        fixture = json.loads(SOURCE_SLICE_FIXTURE_PATH.read_text(encoding="utf-8"))
    fixture_records = {
        str(row["witness_id"]): dict(row)
        for row in (fixture or {}).get("records", [])
    }
    for cohort in ("known_regressions", "development_witnesses", "held_out_witnesses"):
        for witness in manifest.get(cohort, []):
            if not all(witness.get(key) for key in ("source_capture_sha256", "source_location", "source_slice_sha256")):
                continue
            fixture_records[str(witness["witness_id"])] = {
                "witness_id": str(witness["witness_id"]),
                "capture_sha256": str(witness["source_capture_sha256"]),
                "source_location": str(witness["source_location"]),
                "source_slice_sha256": str(witness["source_slice_sha256"]),
            }
    fixture = {"records": list(fixture_records.values())} if fixture_records else None
    witness_replay: dict[str, list[dict[str, Any]]] = {}
    replay_cohorts = [
        ("known_regressions", manifest.get("known_regressions", [])),
        ("development", manifest.get("development_witnesses", [])),
    ]
    for cohort, witnesses in replay_cohorts:
        resolved_rows = [
            resolve_witness(
                witness,
                catalog_by_id,
                raw_character_dir=raw_character_dir,
                raw_sidekick_dir=raw_sidekick_dir,
                parsed_sidekick_dir=parsed_sidekick_dir,
            )
            for witness in witnesses
        ]
        witness_replay[cohort] = _apply_slice_fixture(resolved_rows, fixture)
    known = [{**row, "generalization_evidence": False} for row in witness_replay["known_regressions"]]
    report: dict[str, Any] = {
        "artifact_version": SOURCE_FIDELITY_VERSION,
        "authority": {
            "accepted_catalog": catalog_path.as_posix(),
            "accepted_catalog_fingerprint": artifact_fingerprint(catalog),
            "source_capture_identity": "raw capture SHA-256 and source URL/page are authoritative; rewritten prose is never sufficient",
            "semantic_oracle": "separate adjudication artifact; not read by automatic replay",
            "generated_capability_authority": False,
            "definitions_grant_capabilities": False,
            "graph_schema_mutated": False,
            "legal_kit_mutated": False,
        },
        "legal_kit": {
            "canonical_identity_count": reconciliation["canonical_identity_count"],
            "complete_receipt_count": reconciliation["complete_receipt_count"],
            "ready": reconciliation["ready"],
            "identity_or_receipt_drift": not reconciliation["ready"],
        },
        "manifest": {
            "path": manifest_path.as_posix(),
            "manifest_sha256": _sha256(manifest_path.read_bytes()),
            "selection_policy": manifest.get("selection_policy"),
            "known_regression_count": len(manifest.get("known_regressions", [])),
            "development_witness_count": len(manifest.get("development_witnesses", [])),
            "held_out_witness_count": len(manifest.get("held_out_witnesses", [])),
            "archetype_coverage": _archetype_coverage(manifest),
        },
        "known_regressions": known,
        "witness_replay": {
            **witness_replay,
            "source_slice_fixture": {
                "path": SOURCE_SLICE_FIXTURE_PATH.as_posix(),
                "loaded": fixture is not None,
                "passed_count": sum(row.get("source_fixture_status") == "passed" for rows in witness_replay.values() for row in rows),
                "failed_count": sum(row.get("source_fixture_status") == "failed" for rows in witness_replay.values() for row in rows),
                "unknown_count": sum(row.get("source_fixture_status") == "unknown" for rows in witness_replay.values() for row in rows),
            },
        },
        "full_catalog_replay": {
            "character_identity_denominator": len(character_rows),
            "structural_parse_coverage": {
                "identities_with_capture": sum(row.get("source_identity_status") != "unknown" for row in character_rows),
                "identities_with_structural_parse": sum(row.get("structural_parse_status") == "passed" for row in character_rows),
                "facts_bound": sum(row.get("bound_source_fact_count", 0) for row in character_rows),
                "facts_unresolved": sum(row.get("unresolved_source_fact_count", 0) for row in character_rows),
                "mapping_diagnostic_count": len(mapping_diagnostics),
                "mapping_diagnostics_by_reason": dict(
                    sorted(Counter(str(row.get("reason") or "unknown") for row in mapping_diagnostics).items())
                ),
                "mapping_diagnostics_by_record_type": dict(
                    sorted(Counter(str(row.get("record_type") or "unknown") for row in mapping_diagnostics).items())
                ),
            },
            "source_identity_status_counts": dict(sorted(Counter(row.get("source_identity_status") for row in character_rows).items())),
            "failure_counts": dict(sorted(Counter(row.get("failure", "none") for row in character_rows).items())),
            "link_resolution": _link_summary(outcomes),
            "child_definition_resolution": {
                "resolved": sum(row.get("status") == "resolved" for row in outcomes),
                "unresolved_or_failed": sum(row.get("status") != "resolved" for row in outcomes),
                "status_distribution": dict(sorted(Counter(row.get("status") for row in outcomes).items())),
            },
        },
        "sidekick_replay": {
            "sidekick_identity_denominator": len(sidekick_rows),
            "record_kind_coverage": {
                kind: {
                    "admitted_record_count": sidekick_kind_counts.get(kind, 0),
                    "structurally_parsed_record_count": sidekick_parsed_counts.get(kind, 0),
                    "unresolved_record_count": max(0, sidekick_kind_counts.get(kind, 0) - sidekick_parsed_counts.get(kind, 0)),
                }
                for kind in ("sidekick_auto", "sidekick_charge", "sidekick_aura")
            },
            "link_resolution": _link_summary(sidekick_outcomes),
        },
        "topology_audit": topology,
        "traversal_limits": {**limits.__dict__, "selected_after_topology_audit": True},
        "fidelity_dimensions": {
            "dimensions": list(FIDELITY_DIMENSIONS),
            "unresolved_state": "unknown",
            "inapplicable_state": "not_applicable",
            "failed_state": "failed",
            "fully_supported_rule": "source identity and record selection must pass; every applicable dimension must pass; unknown, failed, and unresolved dimensions are non-authoritative",
        },
        "known_regression_policy": {
            "count": len(known),
            "excluded_from_generalization": True,
            "reason": "Known failures are targeted compatibility/regression evidence, not a sample of generalization performance.",
        },
        "authority_boundary": {
            "fidelity_passed_only_enters_c2": True,
            "unresolved_source_selection_is_unknown": True,
            "unresolved_semantic_attachment_is_unknown": True,
            "automatic_approval": False,
            "capability_materialization": False,
        },
    }
    if oracle is not None:
        report["oracle_evaluation"] = evaluate_oracle(
            manifest,
            catalog,
            oracle,
            raw_character_dir=raw_character_dir,
            raw_sidekick_dir=raw_sidekick_dir,
            parsed_sidekick_dir=parsed_sidekick_dir,
        )
    replay_digest_payload = {
        "characters": character_rows,
        "sidekicks": sidekick_rows,
        "character_links": outcomes,
        "sidekick_links": sidekick_outcomes,
    }
    report["deterministic_replay"] = {
        "replay_digest": _sha256(_canonical(replay_digest_payload).encode("utf-8")),
        "same_input_same_digest": True,
        "generated_sidecar": "ignored",
    }
    return report


def write_source_fidelity_report(destination: Path, **kwargs: Any) -> dict[str, Any]:
    payload = build_source_fidelity_report(**kwargs)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload
