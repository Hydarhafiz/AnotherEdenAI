"""C6 legal-kit normalization, receipts, and replay-ready catalog helpers.

The kit catalog is deliberately separate from capability review artifacts.  A
skill can be legal and package-eligible while contributing no capability
evidence; only the existing reviewed materializer can grant that evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from .constants import SCHEMA_VERSION
from .models import (
    CharacterRow,
    PassiveSkillRow,
    SkillRow,
    stable_skill_family_id,
)


KIT_ARTIFACT_TYPE = "character_kit_catalog"
KIT_ARTIFACT_VERSION = "c6.1.0"
KIT_PARSER_VERSION = "c6-parser-1.0"
EXPECTED_CANONICAL_CHARACTER_COUNT = 367

ReceiptState = Literal["complete", "failed", "ambiguous"]
PassiveState = Literal["complete", "verified_absent", "failed", "ambiguous"]
StellarState = Literal["complete", "not_applicable", "failed", "ambiguous"]
DependencyState = Literal["complete", "failed", "ambiguous"]


class KitDiagnostic(BaseModel):
    code: str
    message: str
    source_fact_ids: list[str] = Field(default_factory=list)


class CharacterKitReceipt(BaseModel):
    """Auditable readiness result for one exact character form/style."""

    character_id: str
    character_name: str
    display_name: str
    source_url: str
    source_artifact_fingerprint: str
    source_revision: str
    parser_version: str = KIT_PARSER_VERSION
    schema_version: str = SCHEMA_VERSION
    active_skill_state: ReceiptState
    active_skill_count: int
    active_skill_family_count: int
    active_skill_family_ids: list[str] = Field(default_factory=list)
    passive_state: PassiveState
    passive_count: int
    stellar_awakening_state: StellarState
    dependency_state: DependencyState
    overall_state: ReceiptState
    diagnostics: list[KitDiagnostic] = Field(default_factory=list)


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def artifact_fingerprint(value: Any) -> str:
    """Return a stable fingerprint for a parsed source artifact or payload."""
    if isinstance(value, Path):
        return hashlib.sha256(value.read_bytes()).hexdigest()
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _slugify(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", value.strip()).strip("_").lower() or "unknown"


def canonical_character_key(record: dict[str, Any]) -> str:
    """Match the pipeline's exact-form key, collapsing repeated index rows."""
    return _slugify(record.get("name", ""))


def normalize_skill_rows(rows: list[SkillRow | dict[str, Any]]) -> list[SkillRow]:
    """Deduplicate parser repeats while retaining the richest legal source row."""
    validated = [row if isinstance(row, SkillRow) else SkillRow.model_validate(row) for row in rows]
    by_skill_id: dict[str, SkillRow] = {}
    for row in validated:
        current = by_skill_id.get(row.skill_id)
        if current is None:
            by_skill_id[row.skill_id] = row
            continue
        precedence = {
            "active_equipable": 3,
            "basic_attack_replacement": 2,
            "ordinary_basic_attack": 1,
            "not_equipable": 0,
        }
        current_key = (
            precedence.get(current.slot_eligibility or "not_equipable", 0),
            int(not current.requires_stellar_awakened),
            len(current.description),
            current.description,
        )
        candidate_key = (
            precedence.get(row.slot_eligibility or "not_equipable", 0),
            int(not row.requires_stellar_awakened),
            len(row.description),
            row.description,
        )
        if candidate_key > current_key:
            by_skill_id[row.skill_id] = row
    return sorted(by_skill_id.values(), key=lambda row: (row.skill_family_id, row.skill_id))


def normalize_passive_rows(rows: list[PassiveSkillRow | dict[str, Any]]) -> list[PassiveSkillRow]:
    validated = [row if isinstance(row, PassiveSkillRow) else PassiveSkillRow.model_validate(row) for row in rows]
    return sorted({row.passive_skill_id: row for row in validated}.values(), key=lambda row: row.passive_skill_id)


def build_receipt(
    character: CharacterRow,
    skills: list[SkillRow | dict[str, Any]],
    passives: list[PassiveSkillRow | dict[str, Any]],
    *,
    source_artifact_fingerprint: str,
    source_revision: str | None = None,
    stellar_awakening_state: StellarState | None = None,
    passive_state: PassiveState | None = None,
    dependency_state: DependencyState = "complete",
) -> tuple[CharacterKitReceipt, list[SkillRow], list[PassiveSkillRow]]:
    normalized_skills = normalize_skill_rows(skills)
    normalized_passives = normalize_passive_rows(passives)
    eligible = [
        row for row in normalized_skills
        if row.slot_eligibility in {"active_equipable", "basic_attack_replacement"}
    ]
    families = sorted({row.skill_family_id for row in eligible})
    diagnostics: list[KitDiagnostic] = []
    active_state: ReceiptState = "complete"
    if len(families) < 3:
        active_state = "failed"
        diagnostics.append(KitDiagnostic(
            code="insufficient_active_skill_families",
            message=(
                f"{character.name} has {len(families)} distinct equipable active-skill "
                "families; at least three are required."
            ),
            source_fact_ids=[row.skill_id for row in normalized_skills],
        ))
    if passive_state is None:
        passive_state = "complete" if normalized_passives else "verified_absent"
    if stellar_awakening_state is None:
        stellar_awakening_state = (
            "complete"
            if character.is_SA or any(row.requires_stellar_awakened for row in normalized_skills + normalized_passives)
            else "not_applicable"
        )
    if dependency_state != "complete":
        diagnostics.append(KitDiagnostic(
            code="dependency_extraction_incomplete",
            message="Manifest/equipment dependency extraction did not complete.",
        ))
    if passive_state in {"failed", "ambiguous"}:
        diagnostics.append(KitDiagnostic(
            code="passive_extraction_incomplete",
            message=f"Passive extraction state is {passive_state}.",
        ))
    if stellar_awakening_state in {"failed", "ambiguous"}:
        diagnostics.append(KitDiagnostic(
            code="stellar_awakening_extraction_incomplete",
            message=f"Stellar Awakening extraction state is {stellar_awakening_state}.",
        ))
    overall_state: ReceiptState = (
        "complete"
        if active_state == "complete"
        and passive_state in {"complete", "verified_absent"}
        and stellar_awakening_state in {"complete", "not_applicable"}
        and dependency_state == "complete"
        else "failed"
    )
    receipt = CharacterKitReceipt(
        character_id=character.character_id,
        character_name=character.name,
        display_name=character.display_name,
        source_url=character.detail_url or "",
        source_artifact_fingerprint=source_artifact_fingerprint,
        source_revision=source_revision or source_artifact_fingerprint,
        active_skill_state=active_state,
        active_skill_count=len(eligible),
        active_skill_family_count=len(families),
        active_skill_family_ids=families,
        passive_state=passive_state,
        passive_count=len(normalized_passives),
        stellar_awakening_state=stellar_awakening_state,
        dependency_state=dependency_state,
        overall_state=overall_state,
        diagnostics=diagnostics,
    )
    return receipt, normalized_skills, normalized_passives


def validate_catalog_payload(
    payload: dict[str, Any],
    *,
    expected_count: int = EXPECTED_CANONICAL_CHARACTER_COUNT,
) -> dict[str, Any]:
    if payload.get("artifact_type") != KIT_ARTIFACT_TYPE:
        raise ValueError("kit catalog artifact_type is invalid")
    records = payload.get("characters")
    if not isinstance(records, list):
        raise ValueError("kit catalog characters must be a list")
    ids = [record.get("receipt", {}).get("character_id") for record in records]
    duplicate_ids = sorted({value for value in ids if ids.count(value) > 1})
    if duplicate_ids:
        raise ValueError(f"kit catalog contains duplicate character IDs: {duplicate_ids[:5]}")
    receipts: list[CharacterKitReceipt] = []
    for record in records:
        receipt = CharacterKitReceipt.model_validate(record["receipt"])
        character = CharacterRow.model_validate(record["character"])
        normalized_skills = normalize_skill_rows(record.get("skills", []))
        normalized_passives = normalize_passive_rows(record.get("passive_skills", []))
        if _canonical([row.model_dump(mode="json") for row in normalized_skills]) != _canonical(
            sorted(record.get("skills", []), key=lambda row: (row.get("skill_family_id", ""), row.get("skill_id", "")))
        ):
            raise ValueError(f"kit catalog skill normalization drifted for {receipt.character_name}")
        if _canonical([row.model_dump(mode="json") for row in normalized_passives]) != _canonical(
            sorted(record.get("passive_skills", []), key=lambda row: row.get("passive_skill_id", ""))
        ):
            raise ValueError(f"kit catalog passive normalization drifted for {receipt.character_name}")
        computed, _, _ = build_receipt(
            character,
            normalized_skills,
            normalized_passives,
            source_artifact_fingerprint=receipt.source_artifact_fingerprint,
            source_revision=receipt.source_revision,
            stellar_awakening_state=receipt.stellar_awakening_state,
            passive_state=receipt.passive_state,
            dependency_state=receipt.dependency_state,
        )
        if computed.model_dump(mode="json") != receipt.model_dump(mode="json"):
            raise ValueError(f"kit catalog receipt drifted for {receipt.character_name}")
        receipts.append(receipt)
    return {
        "expected_count": expected_count,
        "receipt_count": len(receipts),
        "count_ok": len(receipts) == expected_count,
        "complete_count": sum(receipt.overall_state == "complete" for receipt in receipts),
        "failed_count": sum(receipt.overall_state == "failed" for receipt in receipts),
        "ambiguous_count": sum(receipt.overall_state == "ambiguous" for receipt in receipts),
        "insufficient_family_characters": [
            receipt.character_name for receipt in receipts if receipt.active_skill_family_count < 3
        ],
        "ready": len(receipts) == expected_count and all(receipt.overall_state == "complete" for receipt in receipts),
    }


def assert_catalog_ready(payload: dict[str, Any], *, expected_count: int = EXPECTED_CANONICAL_CHARACTER_COUNT) -> dict[str, Any]:
    report = validate_catalog_payload(payload, expected_count=expected_count)
    if not report["ready"]:
        raise RuntimeError(
            "C6 kit readiness gate failed: "
            f"receipts={report['receipt_count']}/{expected_count}, "
            f"complete={report['complete_count']}, "
            f"insufficient_families={report['insufficient_family_characters'][:10]}"
        )
    return report


def build_catalog_from_parsed_dir(
    parsed_dir: Path,
    *,
    expected_count: int = EXPECTED_CANONICAL_CHARACTER_COUNT,
) -> dict[str, Any]:
    """Build a replayable C6 artifact from a schema-versioned parsed corpus."""
    index_path = parsed_dir / "indexes" / "characters.json"
    index_payload = json.loads(index_path.read_text(encoding="utf-8"))
    canonical: dict[str, dict[str, Any]] = {}
    for record in index_payload.get("rows", []):
        canonical[canonical_character_key(record)] = record
    records: list[dict[str, Any]] = []
    for key in sorted(canonical):
        character_record = CharacterRow.model_validate(canonical[key])
        source_path = parsed_dir / "characters" / f"{key}.json"
        if not source_path.exists():
            raise FileNotFoundError(f"missing parsed character artifact for {character_record.name}: {source_path}")
        source_payload = json.loads(source_path.read_text(encoding="utf-8"))
        receipt, skills, passives = build_receipt(
            character_record,
            source_payload.get("rows", []),
            source_payload.get("passive_rows", []),
            source_artifact_fingerprint=artifact_fingerprint(source_path),
            source_revision=str(source_payload.get("source_revision") or artifact_fingerprint(source_path)),
            stellar_awakening_state=(
                "complete"
                if source_payload.get("is_SA") or any(row.get("requires_stellar_awakened") for row in source_payload.get("rows", []))
                else "not_applicable"
            ),
        )
        character_record = character_record.model_copy(update={"skills": skills, "passive_skills": passives})
        records.append({
            "character": character_record.model_dump(mode="json"),
            "skills": [row.model_dump(mode="json") for row in skills],
            "passive_skills": [row.model_dump(mode="json") for row in passives],
            "receipt": receipt.model_dump(mode="json"),
        })
    payload = {
        "artifact_type": KIT_ARTIFACT_TYPE,
        "artifact_version": KIT_ARTIFACT_VERSION,
        "parser_version": KIT_PARSER_VERSION,
        "schema_version": SCHEMA_VERSION,
        "source_schema_version": index_payload.get("schema_version", "unknown"),
        "canonical_count": len(records),
        "characters": records,
    }
    payload["validation"] = validate_catalog_payload(payload, expected_count=expected_count)
    return payload


def build_catalog_from_raw_dir(
    raw_dir: Path,
    *,
    expected_count: int = EXPECTED_CANONICAL_CHARACTER_COUNT,
) -> dict[str, Any]:
    """Parse the exact cached character scope without fetching or mutating data/."""
    from bs4 import BeautifulSoup

    from .scraper import (
        character_has_stellar_awakened,
        parse_character_passive_skills,
        parse_character_skills,
        parse_characters,
    )

    index_path = raw_dir / "indexes" / "characters.html"
    index_soup = BeautifulSoup(index_path.read_text(encoding="utf-8"), "html.parser")
    canonical: dict[str, CharacterRow] = {}
    for character in parse_characters(index_soup):
        canonical[canonical_character_key(character.model_dump(mode="json"))] = character
    records: list[dict[str, Any]] = []
    for key in sorted(canonical):
        character = canonical[key]
        source_path = raw_dir / "characters" / f"{key}.html"
        if not source_path.exists():
            raise FileNotFoundError(f"missing raw character artifact for {character.name}: {source_path}")
        soup = BeautifulSoup(source_path.read_text(encoding="utf-8"), "html.parser")
        skills = parse_character_skills(soup, character.name, source_url=character.detail_url)
        passives = parse_character_passive_skills(soup, character.name, source_url=character.detail_url)
        is_sa = character_has_stellar_awakened(soup)
        character = character.model_copy(update={"is_SA": is_sa})
        fingerprint = artifact_fingerprint(source_path)
        receipt, skills, passives = build_receipt(
            character,
            skills,
            passives,
            source_artifact_fingerprint=fingerprint,
            source_revision=fingerprint,
            stellar_awakening_state="complete" if is_sa else "not_applicable",
        )
        character = character.model_copy(update={"skills": skills, "passive_skills": passives})
        records.append({
            "character": character.model_dump(mode="json"),
            "skills": [row.model_dump(mode="json") for row in skills],
            "passive_skills": [row.model_dump(mode="json") for row in passives],
            "receipt": receipt.model_dump(mode="json"),
        })
    payload = {
        "artifact_type": KIT_ARTIFACT_TYPE,
        "artifact_version": KIT_ARTIFACT_VERSION,
        "parser_version": KIT_PARSER_VERSION,
        "schema_version": SCHEMA_VERSION,
        "source_schema_version": "raw-cached-html",
        "canonical_count": len(records),
        "characters": records,
    }
    payload["validation"] = validate_catalog_payload(payload, expected_count=expected_count)
    return payload


def _main() -> None:
    parser = argparse.ArgumentParser(description="Build and validate the C6 character kit catalog")
    parser.add_argument("command", choices=("build", "validate"))
    parser.add_argument("--parsed-dir", type=Path)
    parser.add_argument("--raw-dir", type=Path)
    parser.add_argument("--catalog", type=Path, default=Path("src/etl/kit_catalog.json"))
    parser.add_argument("--require-ready", action="store_true")
    args = parser.parse_args()
    if args.command == "build":
        if args.parsed_dir is not None and args.raw_dir is not None:
            parser.error("build accepts only one of --parsed-dir or --raw-dir")
        if args.raw_dir is not None:
            payload = build_catalog_from_raw_dir(args.raw_dir)
        elif args.parsed_dir is not None:
            payload = build_catalog_from_parsed_dir(args.parsed_dir)
        else:
            parser.error("build requires --parsed-dir or --raw-dir")
        args.catalog.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    else:
        payload = json.loads(args.catalog.read_text(encoding="utf-8"))
        report = validate_catalog_payload(payload)
        print(json.dumps(report, indent=2, sort_keys=True))
        if args.require_ready and not report["ready"]:
            raise SystemExit(1)


if __name__ == "__main__":
    _main()
