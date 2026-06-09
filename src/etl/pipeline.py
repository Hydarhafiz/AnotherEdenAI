"""Resumable ETL pipeline orchestration for cached fetch -> parse -> load."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

import nodriver as uc

from .constants import (
    CRAWL_MANIFEST_PATH,
    ETL_BROWSER_PROFILE_DIR,
    ETL_CRAWL_SCOPE,
    ETL_FALLBACK_CHARACTER_LIMIT,
    ETL_FALLBACK_SIDEKICK_LIMIT,
    ETL_INCLUDE_CHARACTER_PAGES,
    ETL_INCLUDE_SIDEKICK_PAGES,
    ETL_INCLUDE_SUPERBOSS_PAGES,
    ETL_INCREMENTAL,
    ETL_MAX_RETRIES,
    ETL_OPERATOR_WAIT_SECONDS,
    ETL_RESUME,
    ETL_SCHEMA_VERSION,
    ETL_SMALL_CHARACTER_LIMIT,
    ETL_SMALL_SIDEKICK_LIMIT,
    ETL_SOURCE_MODE,
    PARSED_CHARACTER_DIR,
    PARSED_INDEX_DIR,
    PARSED_SIDEKICK_DIR,
    PARSED_SUPERBOSS_DIR,
    RAW_CHARACTER_DIR,
    RAW_PAGE_FILES,
    RAW_SIDEKICK_DIR,
    RAW_SUPERBOSS_DIR,
    WIKI_URLS,
)
from .models import (
    CharacterRow,
    EquipmentRow,
    GrastaRow,
    OreRow,
    PassiveSkillRow,
    SidekickRow,
    SkillRow,
    SuperbossIndexRow,
    SuperbossRow,
)
from .scraper import (
    CHROMIUM_PATH,
    _read_soup,
    _slugify_title,
    _stop_browser,
    _wiki_page_title,
    character_has_stellar_awakened,
    fetch_raw_html,
    parse_character_passive_skills,
    parse_character_skills,
    parse_characters,
    parse_grastas,
    parse_equipment_index,
    parse_ores,
    parse_sidekick_detail,
    parse_sidekick_index,
    parse_superboss_detail,
    parse_superboss_index,
    parse_vc_grastas,
)

logger = logging.getLogger(__name__)

INDEX_SELECTORS = {
    "characters": "tr.character-row-entry",
    "sidekick": "#Released_Sidekicks",
    "superbosses": "#List_of_Optional_Bosses, table, tr",
    "grasta_attack": "tr.grasta-row-entry",
    "grasta_life": "tr.grasta-row-entry",
    "grasta_support": "tr.grasta-row-entry",
    "grasta_special": "tr.grasta-row-entry",
    "grasta_vc": "tr.grasta-row-entry",
    "grasta_ores": "tr.equip-row-entry",
    "weapons": "tr.equip-row-entry",
    "armor": "tr.equip-row-entry",
}

INDEX_KINDS = {
    "characters": "characters_index",
    "sidekick": "sidekick_index",
    "superbosses": "superboss_index",
    "grasta_attack": "grasta_index",
    "grasta_life": "grasta_index",
    "grasta_support": "grasta_index",
    "grasta_special": "grasta_index",
    "grasta_vc": "grasta_vc_index",
    "grasta_ores": "ore_index",
    "weapons": "equipment_index",
    "armor": "equipment_index",
}

INDEX_CATEGORIES = {
    "grasta_attack": "Attack",
    "grasta_life": "Life",
    "grasta_support": "Support",
    "grasta_special": "Special",
}


@dataclass(slots=True)
class CrawlConfig:
    source_mode: str = ETL_SOURCE_MODE
    crawl_scope: str = ETL_CRAWL_SCOPE
    incremental: bool = ETL_INCREMENTAL
    resume: bool = ETL_RESUME
    include_character_pages: bool = ETL_INCLUDE_CHARACTER_PAGES
    include_sidekick_pages: bool = ETL_INCLUDE_SIDEKICK_PAGES
    include_superboss_pages: bool = ETL_INCLUDE_SUPERBOSS_PAGES
    max_retries: int = ETL_MAX_RETRIES
    operator_wait_seconds: int = ETL_OPERATOR_WAIT_SECONDS
    small_character_limit: int = ETL_SMALL_CHARACTER_LIMIT
    fallback_character_limit: int = ETL_FALLBACK_CHARACTER_LIMIT
    small_sidekick_limit: int = ETL_SMALL_SIDEKICK_LIMIT
    fallback_sidekick_limit: int = ETL_FALLBACK_SIDEKICK_LIMIT
    browser_profile_dir: str | None = ETL_BROWSER_PROFILE_DIR


def _timestamp() -> str:
    return datetime.now(UTC).isoformat()


def _base_manifest() -> dict[str, Any]:
    return {
        "etl_schema_version": ETL_SCHEMA_VERSION,
        "updated_at": _timestamp(),
        "readiness_summary": {},
        "targets": {},
    }


def _load_manifest() -> dict[str, Any]:
    if not CRAWL_MANIFEST_PATH.exists():
        return _base_manifest()
    manifest = json.loads(CRAWL_MANIFEST_PATH.read_text(encoding="utf-8"))
    manifest.setdefault("etl_schema_version", ETL_SCHEMA_VERSION)
    manifest.setdefault("readiness_summary", {})
    manifest.setdefault("targets", {})
    return manifest


def _save_manifest(manifest: dict[str, Any]) -> None:
    CRAWL_MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    manifest["etl_schema_version"] = ETL_SCHEMA_VERSION
    manifest["updated_at"] = _timestamp()
    CRAWL_MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")


def _make_target(
    *,
    target_id: str,
    url: str,
    expected_selector: str,
    raw_path: Path,
    parsed_path: Path,
    kind: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": target_id,
        "url": url,
        "expected_selector": expected_selector,
        "raw_path": str(raw_path),
        "parsed_path": str(parsed_path),
        "kind": kind,
        "metadata": metadata or {},
    }


def _build_index_targets() -> list[dict[str, Any]]:
    targets = []
    for key, url in WIKI_URLS.items():
        targets.append(
            _make_target(
                target_id=key,
                url=url,
                expected_selector=INDEX_SELECTORS[key],
                raw_path=RAW_PAGE_FILES[key],
                parsed_path=PARSED_INDEX_DIR / f"{key}.json",
                kind=INDEX_KINDS[key],
                metadata={"index_key": key},
            )
        )
    return targets


def _character_target_identity(record: str | dict[str, Any]) -> tuple[str, str | None]:
    if isinstance(record, str):
        return record, None
    return record["name"], record.get("detail_url")


def _build_character_targets(character_records: list[str | dict[str, Any]], config: CrawlConfig) -> list[dict[str, Any]]:
    if not config.include_character_pages:
        return []

    if config.crawl_scope == "small":
        selected = character_records[: config.small_character_limit]
    elif config.crawl_scope == "fallback":
        selected = character_records[: config.fallback_character_limit]
    elif config.crawl_scope == "full":
        selected = character_records
    else:
        raise ValueError(f"Unsupported ETL_CRAWL_SCOPE={config.crawl_scope!r}")

    targets = []
    for record in selected:
        name, detail_url = _character_target_identity(record)
        slug = _slugify_title(name)
        page_title = _wiki_page_title(name).replace(" ", "_")
        targets.append(
            _make_target(
                target_id=f"character::{slug}",
                url=detail_url or f"https://anothereden.wiki/w/{quote(page_title, safe='(),')}",
                expected_selector="div.character-skills, div.character-skill-grid-container",
                raw_path=RAW_CHARACTER_DIR / f"{slug}.html",
                parsed_path=PARSED_CHARACTER_DIR / f"{slug}.json",
                kind="character_detail",
                metadata={"character_name": name},
            )
        )
    return targets


def _build_sidekick_targets(sidekick_records: list[dict[str, Any]], config: CrawlConfig) -> list[dict[str, Any]]:
    if not config.include_sidekick_pages:
        return []

    if config.crawl_scope == "small":
        selected = sidekick_records[: config.small_sidekick_limit]
    elif config.crawl_scope == "fallback":
        selected = sidekick_records[: config.fallback_sidekick_limit]
    elif config.crawl_scope == "full":
        selected = sidekick_records
    else:
        raise ValueError(f"Unsupported ETL_CRAWL_SCOPE={config.crawl_scope!r}")

    targets = []
    for record in selected:
        try:
            sidekick = SidekickRow.model_validate(record)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Skipping invalid sidekick target record %s: %s", record.get("name"), exc)
            continue
        slug = _slugify_title(sidekick.name)
        targets.append(
            _make_target(
                target_id=f"sidekick::{slug}",
                url=sidekick.source_url,
                expected_selector="div.character-skill-grid-container, .skill-description",
                raw_path=RAW_SIDEKICK_DIR / f"{slug}.html",
                parsed_path=PARSED_SIDEKICK_DIR / f"{slug}.json",
                kind="sidekick_detail",
                metadata={"sidekick": sidekick.model_dump(mode="json")},
            )
        )
    return targets


def _build_superboss_targets(superboss_records: list[dict[str, Any]], config: CrawlConfig) -> list[dict[str, Any]]:
    if not config.include_superboss_pages:
        return []

    targets = []
    for record in superboss_records:
        try:
            boss = SuperbossIndexRow.model_validate(record)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Skipping invalid superboss target record %s: %s", record.get("name"), exc)
            continue
        slug = _slugify_title(boss.name)
        targets.append(
            _make_target(
                target_id=f"superboss::{slug}",
                url=boss.source_url,
                expected_selector="#mw-content-text, body",
                raw_path=RAW_SUPERBOSS_DIR / f"{slug}.html",
                parsed_path=PARSED_SUPERBOSS_DIR / f"{slug}.json",
                kind="superboss_detail",
                metadata={"superboss": boss.model_dump(mode="json")},
            )
        )
    return targets


def _ensure_target_entry(manifest: dict[str, Any], target: dict[str, Any]) -> dict[str, Any]:
    entry = manifest["targets"].setdefault(
        target["id"],
        {
            "id": target["id"],
            "url": target["url"],
            "expected_selector": target["expected_selector"],
            "kind": target["kind"],
            "state": "pending",
            "attempt_count": 0,
            "last_error": None,
            "failure_stage": None,
            "quality_gate_reason": None,
            "html_byte_size": 0,
            "cloudflare_detected": False,
            "parsed_counts": {},
            "quality_status": "pending",
            "raw_path": target["raw_path"],
            "parsed_path": target["parsed_path"],
            "metadata": target["metadata"],
            "last_cached_at": None,
            "last_parsed_at": None,
            "last_loaded_at": None,
            "etag": None,
            "cache_artifacts": {
                "raw_path": target["raw_path"],
                "parsed_path": target["parsed_path"],
            },
        },
    )
    target_changed = (
        entry.get("url") not in {None, target["url"]}
        or entry.get("expected_selector") not in {None, target["expected_selector"]}
    )
    if target_changed:
        entry["state"] = "pending"
        entry["quality_status"] = "pending"
        entry["parsed_counts"] = {}
        entry["last_error"] = None
        entry["failure_stage"] = None
        entry["quality_gate_reason"] = None
    entry["url"] = target["url"]
    entry["expected_selector"] = target["expected_selector"]
    entry["kind"] = target["kind"]
    entry["raw_path"] = target["raw_path"]
    entry["parsed_path"] = target["parsed_path"]
    entry["cache_artifacts"] = {
        "raw_path": target["raw_path"],
        "parsed_path": target["parsed_path"],
    }
    entry["metadata"] = target["metadata"]
    return entry


def _should_fetch(entry: dict[str, Any], config: CrawlConfig) -> bool:
    if config.source_mode == "parsed":
        return False
    if (
        entry["kind"] == "character_detail"
        and entry.get("quality_status") in {"empty", "failed"}
        and config.resume
    ):
        return True
    if entry["kind"] == "character_detail" and config.resume:
        parsed_path = Path(entry.get("parsed_path", ""))
        if parsed_path.exists():
            payload = json.loads(parsed_path.read_text(encoding="utf-8"))
            if payload.get("kind") == "character_detail" and payload.get("parsed_counts", {}).get("skills", 0) <= 0:
                return True
    if not entry["raw_path"] or not Path(entry["raw_path"]).exists():
        return True
    if not config.incremental:
        return True
    if entry["state"] == "failed":
        return config.resume
    return entry["state"] == "pending"


def _parsed_is_current(entry: dict[str, Any]) -> bool:
    parsed_path = Path(entry["parsed_path"])
    if not parsed_path.exists():
        return False
    payload = json.loads(parsed_path.read_text(encoding="utf-8"))
    return payload.get("schema_version") == ETL_SCHEMA_VERSION


def _should_parse(entry: dict[str, Any]) -> bool:
    if entry["state"] == "loaded":
        return not _parsed_is_current(entry)
    if entry["state"] == "parsed" and _parsed_is_current(entry):
        return False
    return Path(entry["raw_path"]).exists()


def _serialize_models(rows: list[Any]) -> list[dict[str, Any]]:
    return [row.model_dump(mode="json") for row in rows]


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _parse_target(entry: dict[str, Any]) -> dict[str, Any]:
    raw_path = Path(entry["raw_path"])
    soup = _read_soup(raw_path)
    kind = entry["kind"]

    if kind == "characters_index":
        rows = parse_characters(soup)
        payload = {
            "schema_version": ETL_SCHEMA_VERSION,
            "kind": kind,
            "rows": _serialize_models(rows),
            "parsed_counts": {"characters": len(rows)},
            "quality_status": "ok" if rows else "empty",
        }
    elif kind == "sidekick_index":
        rows = parse_sidekick_index(soup)
        payload = {
            "schema_version": ETL_SCHEMA_VERSION,
            "kind": kind,
            "rows": _serialize_models(rows),
            "parsed_counts": {"sidekicks": len(rows)},
            "quality_status": "ok" if rows else "empty",
        }
    elif kind == "superboss_index":
        rows = parse_superboss_index(soup)
        payload = {
            "schema_version": ETL_SCHEMA_VERSION,
            "kind": kind,
            "rows": _serialize_models(rows),
            "parsed_counts": {"superboss_candidates": len(rows)},
            "quality_status": "ok" if rows else "empty",
        }
    elif kind == "grasta_index":
        index_key = entry["metadata"]["index_key"]
        category = INDEX_CATEGORIES[index_key]
        rows = parse_grastas(soup, category)
        payload = {
            "schema_version": ETL_SCHEMA_VERSION,
            "kind": kind,
            "rows": _serialize_models(rows),
            "parsed_counts": {"grastas": len(rows)},
            "quality_status": "ok" if rows else "empty",
        }
    elif kind == "grasta_vc_index":
        rows = parse_vc_grastas(soup)
        payload = {
            "schema_version": ETL_SCHEMA_VERSION,
            "kind": kind,
            "rows": _serialize_models(rows),
            "parsed_counts": {"grastas": len(rows)},
            "quality_status": "ok" if rows else "empty",
        }
    elif kind == "ore_index":
        rows = parse_ores(soup)
        payload = {
            "schema_version": ETL_SCHEMA_VERSION,
            "kind": kind,
            "rows": _serialize_models(rows),
            "parsed_counts": {"ores": len(rows)},
            "quality_status": "ok" if rows else "empty",
        }
    elif kind == "equipment_index":
        index_key = entry["metadata"]["index_key"]
        equipment_slot = "weapon" if index_key == "weapons" else "armor"
        rows = parse_equipment_index(soup, equipment_slot, entry["url"])
        payload = {
            "schema_version": ETL_SCHEMA_VERSION,
            "kind": kind,
            "rows": _serialize_models(rows),
            "parsed_counts": {f"{equipment_slot}s": len(rows)},
            "quality_status": "ok" if rows else "empty",
        }
    elif kind == "character_detail":
        character_name = entry["metadata"]["character_name"]
        source_url = entry["url"]
        skills = parse_character_skills(soup, character_name, source_url=source_url)
        passive_skills = parse_character_passive_skills(soup, character_name, source_url=source_url)
        is_sa = character_has_stellar_awakened(soup)
        payload = {
            "schema_version": ETL_SCHEMA_VERSION,
            "kind": kind,
            "character_name": character_name,
            "is_SA": is_sa,
            "rows": _serialize_models(skills),
            "passive_rows": _serialize_models(passive_skills),
            "parsed_counts": {"skills": len(skills), "passive_skills": len(passive_skills)},
            "quality_status": "ok" if skills else "empty",
        }
    elif kind == "sidekick_detail":
        sidekick = SidekickRow.model_validate(entry["metadata"]["sidekick"])
        row = parse_sidekick_detail(soup, sidekick, source_url=entry["url"])
        payload = {
            "schema_version": ETL_SCHEMA_VERSION,
            "kind": kind,
            "rows": [row.model_dump(mode="json")],
            "parsed_counts": {
                "sidekicks": 1,
                "auto_skills": len(row.auto_skills),
                "charge_skills": len(row.charge_skills),
                "auras": len(row.auras),
                "associations": len(row.associated_character_names),
            },
            "quality_status": "ok" if row.auto_skills or row.charge_skills or row.auras else "empty",
        }
    elif kind == "superboss_detail":
        boss = SuperbossIndexRow.model_validate(entry["metadata"]["superboss"])
        row = parse_superboss_detail(soup, boss, source_url=entry["url"])
        payload = {
            "schema_version": ETL_SCHEMA_VERSION,
            "kind": kind,
            "rows": [row.model_dump(mode="json")],
            "parsed_counts": {
                "superbosses": 1,
                "mechanics_text_chars": len(row.mechanics_text),
            },
            "quality_status": "ok" if row.mechanics_text else "empty",
        }
    else:
        raise ValueError(f"Unsupported target kind {kind!r}")

    _write_json(Path(entry["parsed_path"]), payload)
    entry["state"] = "parsed"
    entry["parsed_counts"] = payload["parsed_counts"]
    entry["quality_status"] = payload["quality_status"]
    entry["last_error"] = None
    entry["failure_stage"] = None
    entry["quality_gate_reason"] = None
    entry["last_parsed_at"] = _timestamp()
    return payload


def _fail_target(entry: dict[str, Any], *, stage: str, message: str, quality_gate_reason: str | None = None) -> None:
    entry["state"] = "failed"
    entry["failure_stage"] = stage
    entry["last_error"] = message
    if quality_gate_reason is not None:
        entry["quality_status"] = "failed"
        entry["quality_gate_reason"] = quality_gate_reason


def _load_rows(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != ETL_SCHEMA_VERSION:
        raise RuntimeError(
            f"Parsed artifact schema mismatch at {path}: "
            f"{payload.get('schema_version')} != {ETL_SCHEMA_VERSION}"
        )
    return payload


def _validate_target(entry: dict[str, Any]) -> None:
    payload = _load_rows(Path(entry["parsed_path"]))
    parsed_counts = payload.get("parsed_counts", {})
    kind = payload["kind"]

    if kind in {
        "characters_index",
        "sidekick_index",
        "superboss_index",
        "grasta_index",
        "grasta_vc_index",
        "ore_index",
        "equipment_index",
    }:
        total = sum(int(value) for value in parsed_counts.values())
        if total <= 0:
            _fail_target(
                entry,
                stage="quality_gate",
                message="Parsed artifact was empty",
                quality_gate_reason="Parsed artifact must contain at least one row",
            )
            raise RuntimeError(f"Validation failed for {entry['id']}: parsed artifact was empty")

    if kind == "character_detail" and parsed_counts.get("skills", 0) <= 0:
        _fail_target(
            entry,
            stage="quality_gate",
            message="Character detail page had no recognizable active combat skills",
            quality_gate_reason="Character detail page must parse at least one active combat skill",
        )
        raise RuntimeError(
            f"Validation failed for {entry['id']}: character detail page had no recognizable active combat skills"
        )
    elif kind == "sidekick_detail" and (
        parsed_counts.get("auto_skills", 0)
        + parsed_counts.get("charge_skills", 0)
        + parsed_counts.get("auras", 0)
    ) <= 0:
        _fail_target(
            entry,
            stage="quality_gate",
            message="Sidekick detail page had no recognizable auto skill, charge skill, or aura",
            quality_gate_reason="Sidekick detail page must parse at least one auto skill, charge skill, or aura",
        )
        raise RuntimeError(
            f"Validation failed for {entry['id']}: sidekick detail page had no recognizable sidekick abilities"
        )
    elif kind == "superboss_detail" and parsed_counts.get("mechanics_text_chars", 0) <= 0:
        _fail_target(
            entry,
            stage="quality_gate",
            message="Superboss detail page had no mechanics text for RAG grounding",
            quality_gate_reason="Superboss detail page must retain mechanics text for RAG grounding",
        )
        raise RuntimeError(
            f"Validation failed for {entry['id']}: superboss detail page had no mechanics text"
        )
    else:
        entry["quality_status"] = "ok"

    entry["last_error"] = None
    entry["failure_stage"] = None
    entry["quality_gate_reason"] = None


def _aggregate_parsed_data(
    manifest: dict[str, Any],
    active_target_ids: set[str] | None = None,
) -> dict[str, list[Any]]:
    characters_by_name: dict[str, CharacterRow] = {}
    sidekicks_by_name: dict[str, SidekickRow] = {}
    superbosses_by_name: dict[str, SuperbossRow] = {}
    grastas: list[GrastaRow] = []
    ores: list[OreRow] = []
    equipment_by_identity: dict[tuple[str, str], EquipmentRow] = {}
    character_skills: dict[str, list[SkillRow]] = {}
    character_passive_skills: dict[str, list[PassiveSkillRow]] = {}
    character_detail_is_sa: dict[str, bool] = {}

    for entry in manifest["targets"].values():
        if active_target_ids is not None and entry["id"] not in active_target_ids:
            continue
        if entry["state"] not in {"parsed", "loaded"}:
            continue
        payload = _load_rows(Path(entry["parsed_path"]))
        kind = payload["kind"]
        rows = payload.get("rows", [])
        if kind == "characters_index":
            for row in rows:
                character = CharacterRow.model_validate(row)
                characters_by_name[character.name] = character
        elif kind == "sidekick_index":
            for row in rows:
                try:
                    sidekick = SidekickRow.model_validate(row)
                except Exception as exc:  # noqa: BLE001
                    logger.debug("Skipping invalid sidekick index artifact row %s: %s", row.get("name"), exc)
                    continue
                sidekicks_by_name[sidekick.name] = sidekick
        elif kind in {"grasta_index", "grasta_vc_index"}:
            grastas.extend(GrastaRow.model_validate(row) for row in rows)
        elif kind == "ore_index":
            ores.extend(OreRow.model_validate(row) for row in rows)
        elif kind == "equipment_index":
            for row in rows:
                try:
                    equipment = EquipmentRow.model_validate(row)
                except Exception as exc:  # noqa: BLE001
                    logger.debug("Skipping invalid equipment artifact row %s: %s", row.get("name"), exc)
                    continue
                equipment_by_identity[(equipment.equipment_slot, equipment.name)] = equipment
        elif kind == "character_detail":
            character_name = payload["character_name"]
            character_skills[character_name] = [SkillRow.model_validate(row) for row in rows]
            character_passive_skills[character_name] = [
                PassiveSkillRow.model_validate(row) for row in payload.get("passive_rows", [])
            ]
            character_detail_is_sa[character_name] = bool(payload.get("is_SA"))
        elif kind == "sidekick_detail":
            for row in rows:
                sidekick = SidekickRow.model_validate(row)
                sidekicks_by_name[sidekick.name] = sidekick
        elif kind == "superboss_detail":
            for row in rows:
                boss = SuperbossRow.model_validate(row)
                superbosses_by_name[boss.name] = boss

    characters = []
    for character in characters_by_name.values():
        skills = character_skills.get(character.name, [])
        passive_skills = character_passive_skills.get(character.name, [])
        is_sa = character.is_SA or character_detail_is_sa.get(character.name, False)
        characters.append(
            character.model_copy(update={"skills": skills, "passive_skills": passive_skills, "is_SA": is_sa})
        )

    return {
        "characters": characters,
        "sidekicks": list(sidekicks_by_name.values()),
        "superbosses": list(superbosses_by_name.values()),
        "grastas": grastas,
        "ores": ores,
        "equipment": list(equipment_by_identity.values()),
    }


def _selected_targets(manifest: dict[str, Any], kinds: set[str] | None = None) -> list[dict[str, Any]]:
    entries = list(manifest["targets"].values())
    if kinds is not None:
        entries = [entry for entry in entries if entry["kind"] in kinds]
    return sorted(entries, key=lambda entry: entry["id"])


def _selected_target_ids(targets: list[dict[str, Any]]) -> set[str]:
    return {target["id"] for target in targets}


def _filter_parsed_ready_detail_targets(
    manifest: dict[str, Any],
    targets: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Keep only detail targets with current parsed artifacts during parsed replay."""
    ready_targets = []
    for target in targets:
        entry = _ensure_target_entry(manifest, target)
        if _parsed_is_current(entry):
            ready_targets.append(target)
            continue
        entry["state"] = "inactive"
        entry["quality_status"] = "inactive"
        entry["last_error"] = "Detail artifact is not available in parsed source mode"
        entry["failure_stage"] = None
        entry["quality_gate_reason"] = None
    return ready_targets


async def _start_browser(config: CrawlConfig):
    browser_args = ["--no-sandbox", "--disable-setuid-sandbox"]
    if config.browser_profile_dir:
        browser_args.append(f"--user-data-dir={config.browser_profile_dir}")
    return await uc.start(
        browser_executable_path=CHROMIUM_PATH,
        headless=False,
        browser_args=browser_args,
    )


async def _fetch_target(browser, entry: dict[str, Any], config: CrawlConfig) -> None:
    raw_path = Path(entry["raw_path"])
    raw_path.parent.mkdir(parents=True, exist_ok=True)

    last_error: Exception | None = None
    for _attempt in range(config.max_retries):
        entry["attempt_count"] += 1
        try:
            html, diagnostics = await fetch_raw_html(
                browser,
                entry["url"],
                entry["expected_selector"],
                operator_wait_seconds=config.operator_wait_seconds,
            )
            raw_path.write_text(html, encoding="utf-8")
            entry["state"] = "cached"
            entry["html_byte_size"] = diagnostics["html_byte_size"]
            entry["cloudflare_detected"] = diagnostics["cloudflare_detected"]
            entry["last_error"] = None
            entry["failure_stage"] = None
            entry["quality_gate_reason"] = None
            entry["last_cached_at"] = _timestamp()
            return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            entry["last_error"] = str(exc)
            entry["failure_stage"] = "fetch"
            entry["state"] = "pending"

    _fail_target(
        entry,
        stage="fetch",
        message=f"Failed to fetch after {config.max_retries} attempts: {last_error}",
    )
    raise RuntimeError(f"Failed to fetch {entry['id']} after {config.max_retries} attempts") from last_error


def _failed_entries(manifest: dict[str, Any], selected_ids: set[str]) -> list[dict[str, Any]]:
    return [
        entry
        for entry in manifest["targets"].values()
        if entry["id"] in selected_ids and entry["state"] == "failed"
    ]


def _update_readiness_summary(manifest: dict[str, Any], active_target_ids: set[str]) -> None:
    selected_entries = [entry for entry in manifest["targets"].values() if entry["id"] in active_target_ids]
    accountable_states = {"loaded", "failed"}
    loaded = [entry for entry in selected_entries if entry["state"] == "loaded"]
    failed = [entry for entry in selected_entries if entry["state"] == "failed"]
    pending = [entry for entry in selected_entries if entry["state"] not in accountable_states]
    detail_entries = [
        entry
        for entry in selected_entries
        if entry["kind"] in {"sidekick_detail", "superboss_detail"}
    ]
    successful_details = [entry for entry in detail_entries if entry["state"] == "loaded"]
    manifest["readiness_summary"] = {
        "updated_at": _timestamp(),
        "selected_target_count": len(selected_entries),
        "loaded_count": len(loaded),
        "failed_count": len(failed),
        "pending_accountability_count": len(pending),
        "pass_fail_accountability_percent": (
            round(((len(loaded) + len(failed)) / len(selected_entries)) * 100, 2)
            if selected_entries
            else 100.0
        ),
        "curated_detail_success_percent": (
            round((len(successful_details) / len(detail_entries)) * 100, 2)
            if detail_entries
            else 100.0
        ),
        "failed_targets": [
            {
                "id": entry["id"],
                "url": entry["url"],
                "stage": entry.get("failure_stage"),
                "attempt_count": entry.get("attempt_count", 0),
                "last_error": entry.get("last_error"),
                "quality_gate_reason": entry.get("quality_gate_reason"),
                "cache_artifacts": entry.get("cache_artifacts"),
            }
            for entry in failed
        ],
        "pending_targets": [
            {
                "id": entry["id"],
                "url": entry["url"],
                "state": entry["state"],
                "quality_status": entry.get("quality_status"),
            }
            for entry in pending
        ],
    }


def _mark_inactive_targets(manifest: dict[str, Any], active_target_ids: set[str]) -> None:
    """Mark previously selected detail targets inactive when the current scope no longer selects them."""
    for entry in manifest["targets"].values():
        if entry["id"] in active_target_ids:
            continue
        if entry["kind"] not in {"character_detail", "sidekick_detail", "superboss_detail"}:
            continue
        if entry["state"] in {"pending", "cached", "parsed", "loaded", "failed"}:
            entry["state"] = "inactive"
            entry["quality_status"] = "inactive"
            entry["last_error"] = "Target not selected by current crawl scope"
            entry["failure_stage"] = None
            entry["quality_gate_reason"] = None


async def prepare_parsed_data(config: CrawlConfig | None = None) -> tuple[dict[str, list[Any]], dict[str, Any]]:
    config = config or CrawlConfig()
    manifest = _load_manifest()

    index_targets = _build_index_targets()
    active_target_ids = _selected_target_ids(index_targets)

    for target in index_targets:
        _ensure_target_entry(manifest, target)
    _save_manifest(manifest)

    if config.source_mode != "parsed":
        browser = await _start_browser(config)
        try:
            for entry in _selected_targets(manifest, set(INDEX_KINDS.values())):
                if _should_fetch(entry, config):
                    await _fetch_target(browser, entry, config)
                    _save_manifest(manifest)
        finally:
            await _stop_browser(browser)

    if config.source_mode == "parsed":
        characters_entry = manifest["targets"]["characters"]
        sidekick_entry = manifest["targets"]["sidekick"]
        superboss_entry = manifest["targets"]["superbosses"]
        if not _parsed_is_current(characters_entry):
            raise RuntimeError(
                "Parsed source mode requires a current characters parsed snapshot "
                f"at {characters_entry['parsed_path']}"
            )
        if not _parsed_is_current(sidekick_entry):
            raise RuntimeError(
                "Parsed source mode requires a current sidekick parsed snapshot "
                f"at {sidekick_entry['parsed_path']}"
            )
        if not _parsed_is_current(superboss_entry):
            raise RuntimeError(
                "Parsed source mode requires a current superboss parsed snapshot "
                f"at {superboss_entry['parsed_path']}"
            )
        characters_payload = _load_rows(Path(characters_entry["parsed_path"]))
        sidekick_payload = _load_rows(Path(sidekick_entry["parsed_path"]))
        superboss_payload = _load_rows(Path(superboss_entry["parsed_path"]))
    else:
        if not Path(manifest["targets"]["characters"]["raw_path"]).exists():
            raise RuntimeError("Characters index was not cached successfully; cannot continue ETL parse stage.")
        if not Path(manifest["targets"]["sidekick"]["raw_path"]).exists():
            raise RuntimeError("Sidekick index was not cached successfully; cannot continue ETL parse stage.")
        if not Path(manifest["targets"]["superbosses"]["raw_path"]).exists():
            raise RuntimeError("Superbosses index was not cached successfully; cannot continue ETL parse stage.")
        try:
            characters_payload = _parse_target(manifest["targets"]["characters"])
            sidekick_payload = _parse_target(manifest["targets"]["sidekick"])
            superboss_payload = _parse_target(manifest["targets"]["superbosses"])
        except Exception as exc:  # noqa: BLE001
            for entry in (
                manifest["targets"]["characters"],
                manifest["targets"]["sidekick"],
                manifest["targets"]["superbosses"],
            ):
                if entry["state"] != "parsed":
                    _fail_target(entry, stage="parse", message=str(exc))
            _save_manifest(manifest)
            raise
        _save_manifest(manifest)

    character_records = characters_payload["rows"]
    sidekick_records = sidekick_payload["rows"]
    superboss_records = superboss_payload["rows"]

    character_targets = _build_character_targets(character_records, config)
    sidekick_targets = _build_sidekick_targets(sidekick_records, config)
    superboss_targets = _build_superboss_targets(superboss_records, config)
    if config.source_mode == "parsed":
        character_targets = _filter_parsed_ready_detail_targets(manifest, character_targets)
        sidekick_targets = _filter_parsed_ready_detail_targets(manifest, sidekick_targets)
        superboss_targets = _filter_parsed_ready_detail_targets(manifest, superboss_targets)
    active_target_ids.update(_selected_target_ids(character_targets))
    active_target_ids.update(_selected_target_ids(sidekick_targets))
    active_target_ids.update(_selected_target_ids(superboss_targets))
    _mark_inactive_targets(manifest, active_target_ids)

    for target in [*character_targets, *sidekick_targets, *superboss_targets]:
        _ensure_target_entry(manifest, target)
    _save_manifest(manifest)

    if config.source_mode != "parsed":
        browser = await _start_browser(config)
        try:
            for entry in _selected_targets(manifest):
                if entry["id"] not in active_target_ids:
                    continue
                if entry["kind"] not in {"character_detail", "sidekick_detail", "superboss_detail"}:
                    continue
                if _should_fetch(entry, config):
                    try:
                        await _fetch_target(browser, entry, config)
                    finally:
                        _save_manifest(manifest)
        finally:
            await _stop_browser(browser)

    for entry in _selected_targets(manifest):
        if entry["id"] not in active_target_ids:
            continue
        if config.source_mode == "parsed":
            if not _parsed_is_current(entry):
                raise RuntimeError(
                    "Parsed source mode requires a current parsed snapshot "
                    f"at {entry['parsed_path']}"
                )
            try:
                _validate_target(entry)
            except Exception:
                _update_readiness_summary(manifest, active_target_ids)
                _save_manifest(manifest)
                raise
            _save_manifest(manifest)
            continue
        if _should_parse(entry):
            try:
                _parse_target(entry)
            except Exception as exc:  # noqa: BLE001
                _fail_target(entry, stage="parse", message=str(exc))
                _update_readiness_summary(manifest, active_target_ids)
                _save_manifest(manifest)
                raise
            _save_manifest(manifest)
        if entry["state"] in {"parsed", "loaded"}:
            try:
                _validate_target(entry)
            except Exception:
                _update_readiness_summary(manifest, active_target_ids)
                _save_manifest(manifest)
                raise
            _save_manifest(manifest)

    failures = _failed_entries(manifest, active_target_ids)
    if failures:
        _update_readiness_summary(manifest, active_target_ids)
        _save_manifest(manifest)
        failed_urls = ", ".join(f"{entry['id']} ({entry['attempt_count']} attempts)" for entry in failures)
        raise RuntimeError(f"ETL fetch failures remain after retries: {failed_urls}")

    return _aggregate_parsed_data(manifest, active_target_ids), manifest


def mark_loaded(manifest: dict[str, Any], data: dict[str, list[Any]]) -> None:
    loaded_character_names = {character.name for character in data["characters"]}
    loaded_sidekick_names = {sidekick.name for sidekick in data.get("sidekicks", [])}
    loaded_superboss_names = {boss.name for boss in data.get("superbosses", [])}

    for entry in manifest["targets"].values():
        if entry["state"] != "parsed":
            continue
        if entry["kind"] == "character_detail":
            if entry["metadata"]["character_name"] not in loaded_character_names:
                continue
        if entry["kind"] == "sidekick_detail":
            if entry["metadata"]["sidekick"]["name"] not in loaded_sidekick_names:
                continue
        if entry["kind"] == "superboss_detail":
            if entry["metadata"]["superboss"]["name"] not in loaded_superboss_names:
                continue
        entry["state"] = "loaded"
        entry["last_loaded_at"] = _timestamp()
        entry["last_error"] = None
        entry["failure_stage"] = None
        entry["quality_gate_reason"] = None

    active_target_ids = {
        entry["id"]
        for entry in manifest["targets"].values()
        if entry["state"] != "inactive"
    }
    _update_readiness_summary(manifest, active_target_ids)
    _save_manifest(manifest)
