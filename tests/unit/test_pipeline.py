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
    monkeypatch.setattr(pipeline, "RAW_SIDEKICK_DIR", tmp_path / "raw" / "sidekicks")
    monkeypatch.setattr(pipeline, "RAW_SUPERBOSS_DIR", tmp_path / "raw" / "superbosses")
    monkeypatch.setattr(pipeline, "PARSED_CHARACTER_DIR", tmp_path / "parsed" / "characters")
    monkeypatch.setattr(pipeline, "PARSED_SIDEKICK_DIR", tmp_path / "parsed" / "sidekicks")
    monkeypatch.setattr(pipeline, "PARSED_SUPERBOSS_DIR", tmp_path / "parsed" / "superbosses")
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


def test_build_sidekick_targets_respects_small_scope(monkeypatch, tmp_path):
    pipeline = _set_pipeline_paths(monkeypatch, tmp_path)

    config = pipeline.CrawlConfig(crawl_scope="small", include_sidekick_pages=True, small_sidekick_limit=2)
    targets = pipeline._build_sidekick_targets(
        [
            {"name": "Tetra (Another Style)", "source_url": "https://anothereden.wiki/w/Tetra_(Another_Style)"},
            {"name": "Mare", "source_url": "https://anothereden.wiki/w/Mare"},
            {"name": "Hameow", "source_url": "https://anothereden.wiki/w/Hameow"},
        ],
        config,
    )

    assert [target["metadata"]["sidekick"]["name"] for target in targets] == ["Tetra (Another Style)", "Mare"]
    assert all(target["kind"] == "sidekick_detail" for target in targets)
    assert all("skill-description" in target["expected_selector"] for target in targets)
    assert str(targets[0]["raw_path"]).endswith("tetra_another_style.html")


def test_build_superboss_targets_uses_curated_detail_metadata(monkeypatch, tmp_path):
    pipeline = _set_pipeline_paths(monkeypatch, tmp_path)

    targets = pipeline._build_superboss_targets(
        [
            {
                "name": "Flame Eater",
                "source_url": "https://anothereden.wiki/w/Gariyu_(Chance_Encounter)#Flame_Eater",
                "difficulty_tier": "2",
                "level": 2,
                "characteristics": "Summons companions",
            },
            {
                "name": "Nameless Girl",
                "source_url": "https://anothereden.wiki/w/Nameless_Girl",
                "difficulty_tier": "3",
                "level": 3,
            },
        ],
        pipeline.CrawlConfig(source_mode="parsed"),
    )

    assert [target["metadata"]["superboss"]["name"] for target in targets] == ["Flame Eater", "Nameless Girl"]
    assert all(target["kind"] == "superboss_detail" for target in targets)
    assert targets[0]["url"].endswith("#Flame_Eater")
    assert str(targets[0]["raw_path"]).endswith("flame_eater.html")
    assert str(targets[0]["parsed_path"]).endswith("flame_eater.json")


def test_parse_equipment_index_target_records_manifest_counts(monkeypatch, tmp_path):
    """Feature D: equipment index parsing writes rows and pass/fail counts to artifacts."""
    pipeline = _set_pipeline_paths(monkeypatch, tmp_path)
    manifest = pipeline._base_manifest()
    target = pipeline._make_target(
        target_id="weapons",
        url="https://anothereden.wiki/w/Weapons",
        expected_selector="tr.equip-row-entry",
        raw_path=tmp_path / "raw" / "indexes" / "weapons.html",
        parsed_path=tmp_path / "parsed" / "indexes" / "weapons.json",
        kind="equipment_index",
        metadata={"index_key": "weapons"},
    )
    entry = pipeline._ensure_target_entry(manifest, target)
    Path(entry["raw_path"]).parent.mkdir(parents=True)
    Path(entry["raw_path"]).write_text(
        """
        <table><tbody>
          <tr class="equip-row-entry" data-name="Lunar Sword" data-type="Sword"
              data-level="60" data-atk="185" data-matk="22"
              data-effect="Type attack +10%" data-source="Crafted">
            <td></td><td>Lunar Sword</td>
          </tr>
        </tbody></table>
        """,
        encoding="utf-8",
    )

    payload = pipeline._parse_target(entry)

    assert payload["kind"] == "equipment_index"
    assert payload["parsed_counts"] == {"weapons": 1}
    assert payload["quality_status"] == "ok"
    assert entry["state"] == "parsed"
    assert entry["quality_status"] == "ok"
    row = payload["rows"][0]
    assert row["name"] == "Lunar Sword"
    assert row["equipment_slot"] == "weapon"
    assert row["attack"] == 185
    assert row["effect_text"] == "Type attack +10%"
    assert row["source_url"] == "https://anothereden.wiki/w/Weapons"


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

    sidekick_targets = pipeline._build_sidekick_targets(
        [{"name": "Tetra (Another Style)", "source_url": "https://example.test/Tetra_AS"}],
        pipeline.CrawlConfig(source_mode="parsed"),
    )
    for target in sidekick_targets:
        entry = pipeline._ensure_target_entry(manifest, target)
        entry["state"] = "parsed"

    superboss_targets = pipeline._build_superboss_targets(
        [{
            "name": "Flame Eater",
            "source_url": "https://example.test/Gariyu#Flame_Eater",
            "difficulty_tier": "2",
            "level": 2,
            "characteristics": "Summons companions",
        }],
        pipeline.CrawlConfig(source_mode="parsed"),
    )
    for target in superboss_targets:
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
        elif key == "sidekick":
            rows = [{
                "name": "Tetra (Another Style)",
                "source_url": "https://example.test/Tetra_AS",
                "rarity": "AS",
                "role_tags": ["SR_Bud_Healer_NATK"],
                "schema_version": pipeline.ETL_SCHEMA_VERSION,
            }]
            counts = {"sidekicks": 1}
        elif key == "superbosses":
            rows = [{
                "name": "Flame Eater",
                "source_url": "https://example.test/Gariyu#Flame_Eater",
                "difficulty_tier": "2",
                "level": 2,
                "refight_status": "No",
                "version": "1.2.5",
                "characteristics": "Summons companions",
            }]
            counts = {"superboss_candidates": 1}
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
        elif kind == "ore_index":
            rows = [{"name": "Ore Alpha", "stats": "SPD+5", "source": "Shop"}]
            counts = {"ores": 1}
        elif key == "weapons":
            rows = [{
                "name": "Lunar Sword",
                "equipment_slot": "weapon",
                "category": "Sword",
                "level": 60,
                "attack": 185,
                "magic_attack": 22,
                "effect_text": "Type attack +10%",
                "obtain_text": "Crafted",
                "source_url": "https://anothereden.wiki/w/Weapons",
                "schema_version": pipeline.ETL_SCHEMA_VERSION,
            }]
            counts = {"weapons": 1}
        else:
            rows = [{
                "name": "Dream Ring",
                "equipment_slot": "armor",
                "category": "Ring",
                "level": 55,
                "defense": 138,
                "magic_defense": 166,
                "effect_text": "Restore HP after battle",
                "obtain_text": "Treasure chest",
                "source_url": "https://anothereden.wiki/w/Armor",
                "schema_version": pipeline.ETL_SCHEMA_VERSION,
            }]
            counts = {"armors": 1}

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

    _write_json(
        pipeline.PARSED_SIDEKICK_DIR / "tetra_another_style.json",
        {
            "schema_version": pipeline.ETL_SCHEMA_VERSION,
            "kind": "sidekick_detail",
            "rows": [{
                "name": "Tetra (Another Style)",
                "source_url": "https://example.test/Tetra_AS",
                "acquisition_text": "Unlock through Minalca AS.",
                "rarity": "AS",
                "role_tags": ["SR_Bud_Healer_NATK"],
                "associated_character_names": ["Minalca (Another Style)"],
                "auto_skills": [{
                    "sidekick_name": "Tetra (Another Style)",
                    "name": "Nurturing Roar",
                    "skill_kind": "auto",
                    "description": "Auto heal.",
                    "source_url": "https://example.test/Tetra_AS",
                    "schema_version": pipeline.ETL_SCHEMA_VERSION,
                }],
                "charge_skills": [{
                    "sidekick_name": "Tetra (Another Style)",
                    "name": "Life Bloom",
                    "skill_kind": "charge",
                    "charge_cost": 5,
                    "description": "Consumes 5 Charge.",
                    "source_url": "https://example.test/Tetra_AS",
                    "schema_version": pipeline.ETL_SCHEMA_VERSION,
                }],
                "auras": [{
                    "sidekick_name": "Tetra (Another Style)",
                    "name": "Guardian Aura",
                    "activation_condition": "When HP is below 80%",
                    "effect_text": "All party members max HP +30%.",
                    "source_url": "https://example.test/Tetra_AS",
                    "schema_version": pipeline.ETL_SCHEMA_VERSION,
                }],
                "schema_version": pipeline.ETL_SCHEMA_VERSION,
            }],
            "parsed_counts": {"sidekicks": 1, "auto_skills": 1, "charge_skills": 1, "auras": 1, "associations": 1},
        },
    )

    _write_json(
        pipeline.PARSED_SUPERBOSS_DIR / "flame_eater.json",
        {
            "schema_version": pipeline.ETL_SCHEMA_VERSION,
            "kind": "superboss_detail",
            "rows": [{
                "name": "Flame Eater",
                "source_url": "https://example.test/Gariyu#Flame_Eater",
                "difficulty_tier": "2",
                "level": 2,
                "hp": 123456,
                "weak": ["Water"],
                "resist": ["Fire"],
                "null": ["unknown"],
                "absorb": ["unknown"],
                "characteristics": "Summons companions",
                "mechanic_tags": ["companion summon"],
                "mechanics_text": "Summons companions and uses fire damage.",
                "schema_version": pipeline.ETL_SCHEMA_VERSION,
            }],
            "parsed_counts": {"superbosses": 1, "mechanics_text_chars": 40},
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
    assert [sidekick.name for sidekick in data["sidekicks"]] == ["Tetra (Another Style)"]
    assert [skill.name for skill in data["sidekicks"][0].auto_skills] == ["Nurturing Roar"]
    assert [skill.name for skill in data["sidekicks"][0].charge_skills] == ["Life Bloom"]
    assert [aura.name for aura in data["sidekicks"][0].auras] == ["Guardian Aura"]
    assert data["sidekicks"][0].associated_character_names == ["Minalca (Another Style)"]
    assert [boss.name for boss in data["superbosses"]] == ["Flame Eater"]
    assert data["superbosses"][0].weak == ["Water"]
    assert "fire damage" in data["superbosses"][0].mechanics_text
    assert len(data["grastas"]) == 5
    assert len(data["ores"]) == 1
    equipment_by_slot = {row.equipment_slot: row for row in data["equipment"]}
    assert set(equipment_by_slot) == {"weapon", "armor"}
    assert equipment_by_slot["weapon"].name == "Lunar Sword"
    assert equipment_by_slot["weapon"].effect_text == "Type attack +10%"
    assert equipment_by_slot["armor"].name == "Dream Ring"
    assert equipment_by_slot["armor"].source_url.endswith("/Armor")
    assert loaded_manifest["targets"]["characters"]["quality_status"] == "ok"


@pytest.mark.asyncio
async def test_parsed_mode_skips_missing_detail_artifacts_without_fetch(monkeypatch, tmp_path):
    pipeline = _set_pipeline_paths(monkeypatch, tmp_path)

    manifest = pipeline._base_manifest()
    for target in pipeline._build_index_targets():
        entry = pipeline._ensure_target_entry(manifest, target)
        entry["state"] = "parsed"

    missing_target = pipeline._build_character_targets(
        [{"name": "Akane (Alter),Blooming Blade", "detail_url": "https://example.test/Blooming_Blade"}],
        pipeline.CrawlConfig(source_mode="parsed", crawl_scope="small", small_character_limit=1),
    )[0]
    missing_entry = pipeline._ensure_target_entry(manifest, missing_target)
    missing_entry["state"] = "pending"

    pipeline._save_manifest(manifest)

    for key, kind in pipeline.INDEX_KINDS.items():
        parsed_path = pipeline.PARSED_INDEX_DIR / f"{key}.json"
        if key == "characters":
            rows = [{
                "name": "Akane (Alter),Blooming Blade",
                "element": "Fire",
                "weapon": "Katana",
                "light_shadow": "Light",
                "personalities": ["Eastern"],
                "detail_url": "https://example.test/Blooming_Blade",
                "is_SA": False,
                "skills": [],
                "passive_skills": [],
            }]
            counts = {"characters": 1}
        elif key == "sidekick":
            rows = [{"name": "Tetra", "source_url": "https://example.test/Tetra"}]
            counts = {"sidekicks": 1}
        elif key == "superbosses":
            rows = [{
                "name": "Flame Eater",
                "source_url": "https://example.test/Gariyu#Flame_Eater",
                "difficulty_tier": "2",
                "level": 2,
            }]
            counts = {"superboss_candidates": 1}
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
        elif kind == "ore_index":
            rows = [{"name": "Ore Alpha", "stats": "SPD+5", "source": "Shop"}]
            counts = {"ores": 1}
        elif key == "weapons":
            rows = [{
                "name": "Lunar Sword",
                "equipment_slot": "weapon",
                "attack": 185,
                "source_url": "https://anothereden.wiki/w/Weapons",
                "schema_version": pipeline.ETL_SCHEMA_VERSION,
            }]
            counts = {"weapons": 1}
        else:
            rows = [{
                "name": "Dream Ring",
                "equipment_slot": "armor",
                "defense": 138,
                "source_url": "https://anothereden.wiki/w/Armor",
                "schema_version": pipeline.ETL_SCHEMA_VERSION,
            }]
            counts = {"armors": 1}

        _write_json(
            parsed_path,
            {
                "schema_version": pipeline.ETL_SCHEMA_VERSION,
                "kind": kind,
                "rows": rows,
                "parsed_counts": counts,
            },
        )

    async def fail_if_browser_started(_config):
        raise AssertionError("parsed mode should not start a browser")

    monkeypatch.setattr(pipeline, "_start_browser", fail_if_browser_started)

    data, loaded_manifest = await pipeline.prepare_parsed_data(
        config=pipeline.CrawlConfig(source_mode="parsed", crawl_scope="small", small_character_limit=1)
    )

    assert [character.name for character in data["characters"]] == ["Akane (Alter),Blooming Blade"]
    assert data["characters"][0].skills == []
    assert {(row.equipment_slot, row.name) for row in data["equipment"]} == {
        ("weapon", "Lunar Sword"),
        ("armor", "Dream Ring"),
    }
    assert loaded_manifest["targets"]["character::akane_alter_blooming_blade"]["state"] == "inactive"
    assert "not available in parsed source mode" in loaded_manifest["targets"]["character::akane_alter_blooming_blade"]["last_error"]


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


def test_validate_sidekick_detail_rejects_partial_page_without_abilities(monkeypatch, tmp_path):
    pipeline = _set_pipeline_paths(monkeypatch, tmp_path)
    target = pipeline._make_target(
        target_id="sidekick::blocked",
        url="https://example.test/Blocked",
        expected_selector="body",
        raw_path=tmp_path / "raw" / "sidekicks" / "blocked.html",
        parsed_path=tmp_path / "parsed" / "sidekicks" / "blocked.json",
        kind="sidekick_detail",
        metadata={"sidekick": {"name": "Blocked", "source_url": "https://example.test/Blocked"}},
    )
    manifest = pipeline._base_manifest()
    entry = pipeline._ensure_target_entry(manifest, target)
    entry["state"] = "parsed"
    _write_json(
        Path(entry["parsed_path"]),
        {
            "schema_version": pipeline.ETL_SCHEMA_VERSION,
            "kind": "sidekick_detail",
            "rows": [],
            "parsed_counts": {"sidekicks": 1, "auto_skills": 0, "charge_skills": 0, "auras": 0},
        },
    )

    with pytest.raises(RuntimeError, match="no recognizable sidekick abilities"):
        pipeline._validate_target(entry)

    assert entry["state"] == "failed"
    assert entry["quality_status"] == "failed"


def test_validate_superboss_detail_rejects_page_without_mechanics_text(monkeypatch, tmp_path):
    pipeline = _set_pipeline_paths(monkeypatch, tmp_path)
    target = pipeline._make_target(
        target_id="superboss::blocked",
        url="https://example.test/Blocked#Boss",
        expected_selector="body",
        raw_path=tmp_path / "raw" / "superbosses" / "blocked.html",
        parsed_path=tmp_path / "parsed" / "superbosses" / "blocked.json",
        kind="superboss_detail",
        metadata={
            "superboss": {
                "name": "Blocked",
                "source_url": "https://example.test/Blocked#Boss",
            }
        },
    )
    manifest = pipeline._base_manifest()
    entry = pipeline._ensure_target_entry(manifest, target)
    entry["state"] = "parsed"
    _write_json(
        Path(entry["parsed_path"]),
        {
            "schema_version": pipeline.ETL_SCHEMA_VERSION,
            "kind": "superboss_detail",
            "rows": [],
            "parsed_counts": {"superbosses": 1, "mechanics_text_chars": 0},
        },
    )

    with pytest.raises(RuntimeError, match="no mechanics text"):
        pipeline._validate_target(entry)

    assert entry["state"] == "failed"
    assert entry["quality_status"] == "failed"
    assert "RAG grounding" in entry["last_error"]


def test_aggregate_parsed_data_ignores_inactive_stale_targets(monkeypatch, tmp_path):
    pipeline = _set_pipeline_paths(monkeypatch, tmp_path)
    manifest = pipeline._base_manifest()

    active_entry = pipeline._ensure_target_entry(
        manifest,
        pipeline._make_target(
            target_id="sidekick",
            url="https://example.test/Sidekick",
            expected_selector="#Released_Sidekicks",
            raw_path=tmp_path / "raw" / "indexes" / "sidekick.html",
            parsed_path=tmp_path / "parsed" / "indexes" / "sidekick.json",
            kind="sidekick_index",
        ),
    )
    active_entry["state"] = "parsed"
    stale_entry = pipeline._ensure_target_entry(
        manifest,
        pipeline._make_target(
            target_id="sidekick::stale_character",
            url="https://example.test/Stale",
            expected_selector="body",
            raw_path=tmp_path / "raw" / "sidekicks" / "stale.html",
            parsed_path=tmp_path / "parsed" / "sidekicks" / "stale.json",
            kind="sidekick_detail",
            metadata={"sidekick": {"name": "Stale Character", "source_url": "https://example.test/Stale"}},
        ),
    )
    stale_entry["state"] = "parsed"

    _write_json(
        Path(active_entry["parsed_path"]),
        {
            "schema_version": pipeline.ETL_SCHEMA_VERSION,
            "kind": "sidekick_index",
            "rows": [{"name": "Tetra", "source_url": "https://example.test/Tetra"}],
            "parsed_counts": {"sidekicks": 1},
        },
    )
    _write_json(
        Path(stale_entry["parsed_path"]),
        {
            "schema_version": pipeline.ETL_SCHEMA_VERSION,
            "kind": "sidekick_detail",
            "rows": [{"name": "Stale Character", "source_url": "https://example.test/Stale"}],
            "parsed_counts": {"sidekicks": 1, "auto_skills": 1, "charge_skills": 0, "auras": 0},
        },
    )

    data = pipeline._aggregate_parsed_data(manifest, active_target_ids={"sidekick"})

    assert [sidekick.name for sidekick in data["sidekicks"]] == ["Tetra"]


def test_mark_inactive_targets_marks_stale_detail_entries(monkeypatch, tmp_path):
    pipeline = _set_pipeline_paths(monkeypatch, tmp_path)
    manifest = pipeline._base_manifest()
    active_entry = pipeline._ensure_target_entry(
        manifest,
        pipeline._make_target(
            target_id="sidekick::tetra",
            url="https://example.test/Tetra",
            expected_selector="body",
            raw_path=tmp_path / "raw" / "sidekicks" / "tetra.html",
            parsed_path=tmp_path / "parsed" / "sidekicks" / "tetra.json",
            kind="sidekick_detail",
            metadata={"sidekick": {"name": "Tetra", "source_url": "https://example.test/Tetra"}},
        ),
    )
    stale_entry = pipeline._ensure_target_entry(
        manifest,
        pipeline._make_target(
            target_id="sidekick::minalca",
            url="https://example.test/Minalca",
            expected_selector="body",
            raw_path=tmp_path / "raw" / "sidekicks" / "minalca.html",
            parsed_path=tmp_path / "parsed" / "sidekicks" / "minalca.json",
            kind="sidekick_detail",
            metadata={"sidekick": {"name": "Minalca", "source_url": "https://example.test/Minalca"}},
        ),
    )
    active_entry["state"] = "parsed"
    active_entry["quality_status"] = "ok"
    stale_entry["state"] = "parsed"
    stale_entry["quality_status"] = "ok"

    pipeline._mark_inactive_targets(manifest, {"sidekick::tetra"})

    assert active_entry["state"] == "parsed"
    assert stale_entry["state"] == "inactive"
    assert stale_entry["quality_status"] == "inactive"
    assert "not selected" in stale_entry["last_error"]


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
        "sidekicks": [
            pipeline.SidekickRow.model_validate(
                {
                    "name": "Tetra (Another Style)",
                    "source_url": "https://example.test/Tetra_AS",
                }
            )
        ],
        "superbosses": [
            pipeline.SuperbossRow.model_validate(
                {
                    "name": "Flame Eater",
                    "source_url": "https://example.test/Gariyu#Flame_Eater",
                    "mechanics_text": "Uses fire damage.",
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
