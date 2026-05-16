"""Unit tests for the resumable ETL pipeline."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _set_pipeline_paths(monkeypatch, tmp_path):
    import src.etl.pipeline as pipeline

    monkeypatch.setattr(pipeline, "CRAWL_MANIFEST_PATH", tmp_path / "etl" / "crawl_manifest.json")
    monkeypatch.setattr(pipeline, "RAW_CHARACTER_DIR", tmp_path / "raw" / "characters")
    monkeypatch.setattr(pipeline, "PARSED_CHARACTER_DIR", tmp_path / "parsed" / "characters")
    monkeypatch.setattr(pipeline, "PARSED_INDEX_DIR", tmp_path / "parsed" / "indexes")
    monkeypatch.setattr(
        pipeline,
        "RAW_PAGE_FILES",
        {key: tmp_path / "raw" / "indexes" / f"{key}.html" for key in pipeline.WIKI_URLS},
    )
    return pipeline


def test_build_character_targets_respects_small_scope(monkeypatch, tmp_path):
    pipeline = _set_pipeline_paths(monkeypatch, tmp_path)

    config = pipeline.CrawlConfig(crawl_scope="small", include_character_pages=True, small_character_limit=3)
    targets = pipeline._build_character_targets(
        [
            {"name": "Aldo", "detail_url": "https://anothereden.wiki/w/Aldo"},
            {"name": "Mighty (Alter),Dark Devourer", "detail_url": "https://anothereden.wiki/w/Dark_Devourer"},
            {"name": "Cyrus", "detail_url": "https://anothereden.wiki/w/Cyrus"},
        ],
        config,
    )

    assert [target["metadata"]["character_name"] for target in targets] == ["Aldo", "Mighty (Alter),Dark Devourer", "Cyrus"]
    assert all(target["kind"] == "character_detail" for target in targets)
    assert all("character-skill" in target["expected_selector"] for target in targets)
    assert targets[1]["url"].endswith("/Dark_Devourer")


def test_should_refetch_empty_character_detail_when_resuming(monkeypatch, tmp_path):
    pipeline = _set_pipeline_paths(monkeypatch, tmp_path)
    entry = {
        "kind": "character_detail",
        "state": "parsed",
        "quality_status": "empty",
        "raw_path": str(tmp_path / "raw" / "characters" / "partial.html"),
    }
    Path(entry["raw_path"]).parent.mkdir(parents=True)
    Path(entry["raw_path"]).write_text("<html><body>partial</body></html>", encoding="utf-8")

    assert pipeline._should_fetch(entry, pipeline.CrawlConfig(source_mode="live", resume=True)) is True
    assert pipeline._should_fetch(entry, pipeline.CrawlConfig(source_mode="parsed", resume=True)) is False


def test_should_refetch_character_detail_with_zero_skill_artifact(monkeypatch, tmp_path):
    pipeline = _set_pipeline_paths(monkeypatch, tmp_path)
    parsed_path = tmp_path / "parsed" / "characters" / "partial.json"
    _write_json(
        parsed_path,
        {
            "schema_version": pipeline.ETL_SCHEMA_VERSION,
            "kind": "character_detail",
            "character_name": "Partial",
            "rows": [],
            "passive_rows": [],
            "parsed_counts": {"skills": 0, "passive_skills": 0},
        },
    )
    entry = {
        "kind": "character_detail",
        "state": "parsed",
        "quality_status": "pending",
        "raw_path": str(tmp_path / "raw" / "characters" / "partial.html"),
        "parsed_path": str(parsed_path),
    }
    Path(entry["raw_path"]).parent.mkdir(parents=True)
    Path(entry["raw_path"]).write_text("<html><body>partial</body></html>", encoding="utf-8")

    assert pipeline._should_fetch(entry, pipeline.CrawlConfig(source_mode="live", resume=True)) is True


def test_ensure_target_entry_resets_when_url_or_selector_changes(monkeypatch, tmp_path):
    pipeline = _set_pipeline_paths(monkeypatch, tmp_path)
    manifest = pipeline._base_manifest()
    original = pipeline._make_target(
        target_id="character::alias",
        url="https://example.test/Old_Alias",
        expected_selector="body",
        raw_path=tmp_path / "raw" / "characters" / "alias.html",
        parsed_path=tmp_path / "parsed" / "characters" / "alias.json",
        kind="character_detail",
        metadata={"character_name": "Alias"},
    )
    entry = pipeline._ensure_target_entry(manifest, original)
    entry["state"] = "parsed"
    entry["quality_status"] = "empty"
    entry["parsed_counts"] = {"skills": 0}

    updated = {**original, "url": "https://example.test/Canonical", "expected_selector": "div.character-skills"}
    refreshed = pipeline._ensure_target_entry(manifest, updated)

    assert refreshed["state"] == "pending"
    assert refreshed["quality_status"] == "pending"
    assert refreshed["parsed_counts"] == {}
    assert refreshed["url"] == "https://example.test/Canonical"


@pytest.mark.asyncio
async def test_fetch_target_retries_and_records_diagnostics(monkeypatch, tmp_path):
    pipeline = _set_pipeline_paths(monkeypatch, tmp_path)

    attempts = {"count": 0}

    async def fake_fetch_raw_html(_browser, _url, _selector, operator_wait_seconds):
        attempts["count"] += 1
        assert operator_wait_seconds == 7
        if attempts["count"] < 3:
            raise RuntimeError("temporary block")
        return "<html>ok</html>", {"html_byte_size": 15, "cloudflare_detected": True}

    monkeypatch.setattr(pipeline, "fetch_raw_html", fake_fetch_raw_html)

    target = pipeline._make_target(
        target_id="characters",
        url="https://example.test/Characters",
        expected_selector="tr.character-row-entry",
        raw_path=tmp_path / "raw" / "indexes" / "characters.html",
        parsed_path=tmp_path / "parsed" / "indexes" / "characters.json",
        kind="characters_index",
    )
    manifest = pipeline._base_manifest()
    entry = pipeline._ensure_target_entry(manifest, target)

    await pipeline._fetch_target(object(), entry, pipeline.CrawlConfig(max_retries=3, operator_wait_seconds=7))

    assert attempts["count"] == 3
    assert entry["attempt_count"] == 3
    assert entry["state"] == "cached"
    assert entry["cloudflare_detected"] is True
    assert entry["html_byte_size"] == 15
    assert Path(entry["raw_path"]).read_text(encoding="utf-8") == "<html>ok</html>"


@pytest.mark.asyncio
async def test_prepare_parsed_data_uses_schema_versioned_artifacts_without_fetch(monkeypatch, tmp_path):
    pipeline = _set_pipeline_paths(monkeypatch, tmp_path)

    manifest = pipeline._base_manifest()
    for target in pipeline._build_index_targets():
        entry = pipeline._ensure_target_entry(manifest, target)
        entry["state"] = "parsed"

    character_targets = pipeline._build_character_targets(
        [{"name": "Aldo", "detail_url": "https://example.test/Aldo"}],
        pipeline.CrawlConfig(source_mode="parsed"),
    )
    for target in character_targets:
        entry = pipeline._ensure_target_entry(manifest, target)
        entry["state"] = "parsed"

    pipeline._save_manifest(manifest)

    for key, kind in pipeline.INDEX_KINDS.items():
        parsed_path = pipeline.PARSED_INDEX_DIR / f"{key}.json"
        if key == "characters":
            rows = [{
                "name": "Aldo",
                "element": "Wind",
                "weapon": "Sword",
                "light_shadow": "Light",
                "personalities": ["Straw Dummy", "Cool"],
                "detail_url": "https://example.test/Aldo",
                "is_SA": False,
                "skills": [],
                "passive_skills": [],
            }]
            counts = {"characters": 1}
        elif kind in {"grasta_index", "grasta_vc_index"}:
            rows = [{
                "name": f"{key}-grasta",
                "category": "VC" if key == "grasta_vc" else pipeline.INDEX_CATEGORIES.get(key, "Attack"),
                "tier": 1,
                "stats": "ATK+5%",
                "personality_req": None,
                "is_shareable": key != "grasta_vc",
            }]
            counts = {"grastas": 1}
        else:
            rows = [{"name": "Ore Alpha", "stats": "SPD+5", "source": "Shop"}]
            counts = {"ores": 1}

        _write_json(
            parsed_path,
            {
                "schema_version": pipeline.ETL_SCHEMA_VERSION,
                "kind": kind,
                "rows": rows,
                "parsed_counts": counts,
            },
        )

    _write_json(
        pipeline.PARSED_CHARACTER_DIR / "aldo.json",
        {
            "schema_version": pipeline.ETL_SCHEMA_VERSION,
            "kind": "character_detail",
            "character_name": "Aldo",
            "rows": [{
                "character_name": "Aldo",
                "name": "X Slash",
                "multiplier": 180.0,
                "element": "Wind",
                "skill_type": "Slash",
                "mp": 20,
                "description": "Wind slash attack.",
                "source_url": "https://example.test/Aldo",
                "section": "Active Skills",
                "requires_stellar_awakened": False,
                "schema_version": pipeline.ETL_SCHEMA_VERSION,
            }],
            "passive_rows": [{
                "character_name": "Aldo",
                "name": "Wind Zone",
                "description": "Boosts Wind moves.",
                "source_url": "https://example.test/Aldo",
                "section": "Stances/Zones",
                "passive_type": "zone",
                "requires_stellar_awakened": True,
                "schema_version": pipeline.ETL_SCHEMA_VERSION,
            }],
            "is_SA": True,
            "parsed_counts": {"skills": 1, "passive_skills": 1},
        },
    )

    async def fail_if_browser_started(_config):
        raise AssertionError("parsed mode should not start a browser")

    monkeypatch.setattr(pipeline, "_start_browser", fail_if_browser_started)

    data, loaded_manifest = await pipeline.prepare_parsed_data(
        config=pipeline.CrawlConfig(source_mode="parsed", include_character_pages=True)
    )

    assert [character.name for character in data["characters"]] == ["Aldo"]
    assert data["characters"][0].is_SA is True
    assert [skill.name for skill in data["characters"][0].skills] == ["X Slash"]
    assert data["characters"][0].skills[0].mp == 20
    assert [passive.name for passive in data["characters"][0].passive_skills] == ["Wind Zone"]
    assert data["characters"][0].passive_skills[0].requires_stellar_awakened is True
    assert len(data["grastas"]) == 5
    assert len(data["ores"]) == 1
    assert loaded_manifest["targets"]["characters"]["quality_status"] == "ok"


def test_validate_character_detail_rejects_partial_page_without_skills(monkeypatch, tmp_path):
    pipeline = _set_pipeline_paths(monkeypatch, tmp_path)
    target = pipeline._make_target(
        target_id="character::blocked",
        url="https://example.test/Blocked",
        expected_selector="body",
        raw_path=tmp_path / "raw" / "characters" / "blocked.html",
        parsed_path=tmp_path / "parsed" / "characters" / "blocked.json",
        kind="character_detail",
        metadata={"character_name": "Blocked"},
    )
    manifest = pipeline._base_manifest()
    entry = pipeline._ensure_target_entry(manifest, target)
    entry["state"] = "parsed"
    _write_json(
        Path(entry["parsed_path"]),
        {
            "schema_version": pipeline.ETL_SCHEMA_VERSION,
            "kind": "character_detail",
            "character_name": "Blocked",
            "rows": [],
            "passive_rows": [],
            "parsed_counts": {"skills": 0, "passive_skills": 0},
        },
    )

    with pytest.raises(RuntimeError, match="no recognizable active combat skills"):
        pipeline._validate_target(entry)

    assert entry["state"] == "failed"
    assert entry["quality_status"] == "failed"


@pytest.mark.asyncio
async def test_prepare_parsed_data_rejects_stale_schema_artifacts(monkeypatch, tmp_path):
    pipeline = _set_pipeline_paths(monkeypatch, tmp_path)

    manifest = pipeline._base_manifest()
    for target in pipeline._build_index_targets():
        entry = pipeline._ensure_target_entry(manifest, target)
        entry["state"] = "parsed"
    pipeline._save_manifest(manifest)

    _write_json(
        pipeline.PARSED_INDEX_DIR / "characters.json",
        {
            "schema_version": "0.0.0",
            "kind": "characters_index",
            "rows": [],
            "parsed_counts": {"characters": 0},
        },
    )

    with pytest.raises(RuntimeError, match="current characters parsed snapshot"):
        await pipeline.prepare_parsed_data(config=pipeline.CrawlConfig(source_mode="parsed"))


def test_mark_loaded_advances_parsed_targets(monkeypatch, tmp_path):
    pipeline = _set_pipeline_paths(monkeypatch, tmp_path)

    manifest = pipeline._base_manifest()
    char_entry = pipeline._ensure_target_entry(
        manifest,
        pipeline._make_target(
            target_id="characters",
            url="https://example.test/Characters",
            expected_selector="tr.character-row-entry",
            raw_path=tmp_path / "raw" / "indexes" / "characters.html",
            parsed_path=tmp_path / "parsed" / "indexes" / "characters.json",
            kind="characters_index",
        ),
    )
    char_entry["state"] = "parsed"
    detail_entry = pipeline._ensure_target_entry(
        manifest,
        pipeline._make_target(
            target_id="character::aldo",
            url="https://example.test/Aldo",
            expected_selector="body",
            raw_path=tmp_path / "raw" / "characters" / "aldo.html",
            parsed_path=tmp_path / "parsed" / "characters" / "aldo.json",
            kind="character_detail",
            metadata={"character_name": "Aldo"},
        ),
    )
    detail_entry["state"] = "parsed"
    pipeline._save_manifest(manifest)

    data = {
        "characters": [
            pipeline.CharacterRow.model_validate(
                {
                    "name": "Aldo",
                    "element": "Wind",
                    "weapon": "Sword",
                    "light_shadow": "Light",
                    "personalities": ["Cool"],
                    "skills": [],
                }
            )
        ],
        "grastas": [],
        "ores": [],
    }

    pipeline.mark_loaded(manifest, data)

    reloaded = pipeline._load_manifest()
    assert reloaded["targets"]["characters"]["state"] == "loaded"
    assert reloaded["targets"]["character::aldo"]["state"] == "loaded"
