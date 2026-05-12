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
    ETL_INCLUDE_CHARACTER_PAGES,
    ETL_INCREMENTAL,
    ETL_MAX_RETRIES,
    ETL_OPERATOR_WAIT_SECONDS,
    ETL_RESUME,
    ETL_SCHEMA_VERSION,
    ETL_SMALL_CHARACTER_LIMIT,
    ETL_SOURCE_MODE,
    PARSED_CHARACTER_DIR,
    PARSED_INDEX_DIR,
    RAW_CHARACTER_DIR,
    RAW_PAGE_FILES,
    WIKI_URLS,
)
from .models import CharacterRow, GrastaRow, OreRow, SkillRow
from .scraper import (
    CHROMIUM_PATH,
    _read_soup,
    _slugify_title,
    _stop_browser,
    fetch_raw_html,
    parse_character_skills,
    parse_characters,
    parse_grastas,
    parse_ores,
    parse_vc_grastas,
)

logger = logging.getLogger(__name__)

INDEX_SELECTORS = {
    "characters": "tr.character-row-entry",
    "grasta_attack": "tr.grasta-row-entry",
    "grasta_life": "tr.grasta-row-entry",
    "grasta_support": "tr.grasta-row-entry",
    "grasta_special": "tr.grasta-row-entry",
    "grasta_vc": "tr.grasta-row-entry",
    "grasta_ores": "tr.equip-row-entry",
}

INDEX_KINDS = {
    "characters": "characters_index",
    "grasta_attack": "grasta_index",
    "grasta_life": "grasta_index",
    "grasta_support": "grasta_index",
    "grasta_special": "grasta_index",
    "grasta_vc": "grasta_vc_index",
    "grasta_ores": "ore_index",
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
    max_retries: int = ETL_MAX_RETRIES
    operator_wait_seconds: int = ETL_OPERATOR_WAIT_SECONDS
    small_character_limit: int = ETL_SMALL_CHARACTER_LIMIT
    fallback_character_limit: int = ETL_FALLBACK_CHARACTER_LIMIT
    browser_profile_dir: str | None = ETL_BROWSER_PROFILE_DIR


def _timestamp() -> str:
    return datetime.now(UTC).isoformat()


def _base_manifest() -> dict[str, Any]:
    return {
        "etl_schema_version": ETL_SCHEMA_VERSION,
        "updated_at": _timestamp(),
        "targets": {},
    }


def _load_manifest() -> dict[str, Any]:
    if not CRAWL_MANIFEST_PATH.exists():
        return _base_manifest()
    manifest = json.loads(CRAWL_MANIFEST_PATH.read_text(encoding="utf-8"))
    manifest.setdefault("etl_schema_version", ETL_SCHEMA_VERSION)
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


def _build_character_targets(character_names: list[str], config: CrawlConfig) -> list[dict[str, Any]]:
    if not config.include_character_pages:
        return []

    if config.crawl_scope == "small":
        selected = character_names[: config.small_character_limit]
    elif config.crawl_scope == "fallback":
        selected = character_names[: config.fallback_character_limit]
    elif config.crawl_scope == "full":
        selected = character_names
    else:
        raise ValueError(f"Unsupported ETL_CRAWL_SCOPE={config.crawl_scope!r}")

    targets = []
    for name in selected:
        slug = _slugify_title(name)
        targets.append(
            _make_target(
                target_id=f"character::{slug}",
                url=f"https://anothereden.wiki/w/{quote(name.replace(' ', '_'))}",
                expected_selector="body",
                raw_path=RAW_CHARACTER_DIR / f"{slug}.html",
                parsed_path=PARSED_CHARACTER_DIR / f"{slug}.json",
                kind="character_detail",
                metadata={"character_name": name},
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
        },
    )
    entry["url"] = target["url"]
    entry["expected_selector"] = target["expected_selector"]
    entry["kind"] = target["kind"]
    entry["raw_path"] = target["raw_path"]
    entry["parsed_path"] = target["parsed_path"]
    entry["metadata"] = target["metadata"]
    return entry


def _should_fetch(entry: dict[str, Any], config: CrawlConfig) -> bool:
    if config.source_mode == "parsed":
        return False
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
    elif kind == "character_detail":
        character_name = entry["metadata"]["character_name"]
        rows = parse_character_skills(soup, character_name)
        payload = {
            "schema_version": ETL_SCHEMA_VERSION,
            "kind": kind,
            "character_name": character_name,
            "rows": _serialize_models(rows),
            "parsed_counts": {"skills": len(rows)},
            "quality_status": "ok" if rows else "empty",
        }
    else:
        raise ValueError(f"Unsupported target kind {kind!r}")

    _write_json(Path(entry["parsed_path"]), payload)
    entry["state"] = "parsed"
    entry["parsed_counts"] = payload["parsed_counts"]
    entry["quality_status"] = payload["quality_status"]
    entry["last_error"] = None
    entry["last_parsed_at"] = _timestamp()
    return payload


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

    if kind in {"characters_index", "grasta_index", "grasta_vc_index", "ore_index"}:
        total = sum(int(value) for value in parsed_counts.values())
        if total <= 0:
            entry["quality_status"] = "failed"
            entry["state"] = "failed"
            entry["last_error"] = "Parsed artifact was empty"
            raise RuntimeError(f"Validation failed for {entry['id']}: parsed artifact was empty")

    if kind == "character_detail" and parsed_counts.get("skills", 0) <= 0:
        entry["quality_status"] = "empty"
    else:
        entry["quality_status"] = "ok"

    entry["last_error"] = None


def _aggregate_parsed_data(manifest: dict[str, Any]) -> dict[str, list[Any]]:
    characters_by_name: dict[str, CharacterRow] = {}
    grastas: list[GrastaRow] = []
    ores: list[OreRow] = []
    character_skills: dict[str, list[SkillRow]] = {}

    for entry in manifest["targets"].values():
        if entry["state"] not in {"parsed", "loaded"}:
            continue
        payload = _load_rows(Path(entry["parsed_path"]))
        kind = payload["kind"]
        rows = payload.get("rows", [])
        if kind == "characters_index":
            for row in rows:
                character = CharacterRow.model_validate(row)
                characters_by_name[character.name] = character
        elif kind in {"grasta_index", "grasta_vc_index"}:
            grastas.extend(GrastaRow.model_validate(row) for row in rows)
        elif kind == "ore_index":
            ores.extend(OreRow.model_validate(row) for row in rows)
        elif kind == "character_detail":
            character_name = payload["character_name"]
            character_skills[character_name] = [SkillRow.model_validate(row) for row in rows]

    characters = []
    for character in characters_by_name.values():
        skills = character_skills.get(character.name, [])
        characters.append(character.model_copy(update={"skills": skills}))

    return {"characters": characters, "grastas": grastas, "ores": ores}


def _selected_targets(manifest: dict[str, Any], kinds: set[str] | None = None) -> list[dict[str, Any]]:
    entries = list(manifest["targets"].values())
    if kinds is not None:
        entries = [entry for entry in entries if entry["kind"] in kinds]
    return sorted(entries, key=lambda entry: entry["id"])


def _selected_target_ids(targets: list[dict[str, Any]]) -> set[str]:
    return {target["id"] for target in targets}


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
            entry["last_cached_at"] = _timestamp()
            return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            entry["last_error"] = str(exc)
            entry["state"] = "pending"

    entry["state"] = "failed"
    raise RuntimeError(f"Failed to fetch {entry['id']} after {config.max_retries} attempts") from last_error


def _failed_entries(manifest: dict[str, Any], selected_ids: set[str]) -> list[dict[str, Any]]:
    return [
        entry
        for entry in manifest["targets"].values()
        if entry["id"] in selected_ids and entry["state"] == "failed"
    ]


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
        if not _parsed_is_current(characters_entry):
            raise RuntimeError(
                "Parsed source mode requires a current characters parsed snapshot "
                f"at {characters_entry['parsed_path']}"
            )
        characters_payload = _load_rows(Path(characters_entry["parsed_path"]))
    else:
        if not Path(manifest["targets"]["characters"]["raw_path"]).exists():
            raise RuntimeError("Characters index was not cached successfully; cannot continue ETL parse stage.")
        characters_payload = _parse_target(manifest["targets"]["characters"])
        _save_manifest(manifest)

    character_names = [
        row["name"] for row in characters_payload["rows"]
    ]

    character_targets = _build_character_targets(character_names, config)
    active_target_ids.update(_selected_target_ids(character_targets))

    for target in character_targets:
        _ensure_target_entry(manifest, target)
    _save_manifest(manifest)

    if config.source_mode != "parsed":
        browser = await _start_browser(config)
        try:
            for entry in _selected_targets(manifest):
                if entry["id"] not in active_target_ids:
                    continue
                if entry["kind"] != "character_detail":
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
            _validate_target(entry)
            _save_manifest(manifest)
            continue
        if _should_parse(entry):
            _parse_target(entry)
            _save_manifest(manifest)
        if entry["state"] in {"parsed", "loaded"}:
            _validate_target(entry)
            _save_manifest(manifest)

    failures = _failed_entries(manifest, active_target_ids)
    if failures:
        failed_urls = ", ".join(f"{entry['id']} ({entry['attempt_count']} attempts)" for entry in failures)
        raise RuntimeError(f"ETL fetch failures remain after retries: {failed_urls}")

    return _aggregate_parsed_data(manifest), manifest


def mark_loaded(manifest: dict[str, Any], data: dict[str, list[Any]]) -> None:
    loaded_character_names = {character.name for character in data["characters"]}

    for entry in manifest["targets"].values():
        if entry["state"] != "parsed":
            continue
        if entry["kind"] == "character_detail":
            if entry["metadata"]["character_name"] not in loaded_character_names:
                continue
        entry["state"] = "loaded"
        entry["last_loaded_at"] = _timestamp()

    _save_manifest(manifest)
