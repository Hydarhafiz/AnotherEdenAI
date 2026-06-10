"""Feature A tests for the battle-mechanics corpus and graph loader."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.etl.loader import ensure_constraints, load_mechanic_references
from src.etl.models import MechanicReferenceRow


class RecordingSession:
    def __init__(self, calls):
        self.calls = calls

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def run(self, cypher, **params):
        self.calls.append((cypher, params))


class RecordingDriver:
    def __init__(self):
        self.calls = []

    def session(self):
        return RecordingSession(self.calls)


def _set_pipeline_paths(monkeypatch, tmp_path):
    import src.etl.pipeline as pipeline

    monkeypatch.setattr(pipeline, "RAW_MECHANICS_DIR", tmp_path / "raw" / "mechanics")
    monkeypatch.setattr(pipeline, "PARSED_MECHANICS_DIR", tmp_path / "parsed" / "mechanics")
    return pipeline


def test_mechanic_reference_requires_rules_or_summary():
    with pytest.raises(ValueError, match="rules_text or summary"):
        MechanicReferenceRow.model_validate(
            {
                "id": "empty-reference",
                "title": "Empty Reference",
                "source_url": "https://anothereden.wiki/w/Battle_Mechanics",
                "source_page": "Battle Mechanics",
                "mechanic_type": "party",
                "topic_tags": ["party"],
                "applies_to": ["lineup_legality"],
            }
        )


def test_curated_mechanics_corpus_covers_feature_a_golden_topics(monkeypatch, tmp_path):
    pipeline = _set_pipeline_paths(monkeypatch, tmp_path)

    rows = pipeline._load_curated_mechanic_references()

    assert len(rows) >= 12
    assert all(row.source_url for row in rows)
    assert all(row.source_page for row in rows)
    assert all(row.section_path for row in rows)
    assert all(row.topic_tags for row in rows)
    assert all(row.schema_version for row in rows)
    assert all(row.rules_text or row.summary for row in rows)

    rows_by_id = {row.id: row for row in rows}
    expected_ids = {
        "battle-party-frontline-reserve",
        "sidekick-main-sub-behavior",
        "affinity-weak-resist-null-absorb",
        "damage-multiplier-high-level-factors",
        "healing-and-sustain-basics",
        "buff-debuff-mitigation-resistance",
        "status-cleanse-protection",
        "zone-stance-basics",
        "another-force-basics",
        "speed-preemptive-delayed-turn-order",
        "stellar-awakening-gated-skills-passives",
        "grasta-ore-dps-support-setup",
    }
    assert expected_ids <= rows_by_id.keys()

    golden_queries = {
        "weakness": ("affinity-weak-resist-null-absorb", "weakness"),
        "sidekick": ("sidekick-main-sub-behavior", "sidekick_legality"),
        "stellar": ("stellar-awakening-gated-skills-passives", "lineup_legality"),
        "speed": ("speed-preemptive-delayed-turn-order", "turn_order"),
        "sustain": ("healing-and-sustain-basics", "sustain"),
        "grasta": ("grasta-ore-dps-support-setup", "build_notes"),
    }
    for _name, (row_id, required_value) in golden_queries.items():
        row = rows_by_id[row_id]
        assert required_value in row.topic_tags or required_value in row.applies_to or required_value == row.mechanic_type

    parsed_artifact = tmp_path / "parsed" / "mechanics" / "mechanic_references.json"
    payload = json.loads(parsed_artifact.read_text(encoding="utf-8"))
    assert payload["kind"] == "mechanic_references"
    assert payload["parsed_counts"] == {"mechanic_references": len(rows)}
    assert payload["quality_status"] == "ok"


def test_build_mechanics_source_targets_cache_all_referenced_pages(monkeypatch, tmp_path):
    pipeline = _set_pipeline_paths(monkeypatch, tmp_path)

    targets = pipeline._build_mechanics_source_targets()

    assert len(targets) == len(pipeline.MECHANICS_PAGE_URLS)
    assert {target["metadata"]["source_key"] for target in targets} == set(pipeline.MECHANICS_PAGE_URLS)
    assert all(target["kind"] == "mechanics_source_page" for target in targets)
    assert all(str(target["raw_path"]).startswith(str(tmp_path / "raw" / "mechanics")) for target in targets)
    assert all(str(target["parsed_path"]).startswith(str(tmp_path / "parsed" / "mechanics" / "sources")) for target in targets)


def test_parse_mechanics_source_page_records_text_cache_accountability(monkeypatch, tmp_path):
    pipeline = _set_pipeline_paths(monkeypatch, tmp_path)
    manifest = pipeline._base_manifest()
    target = pipeline._make_target(
        target_id="mechanics_source::battle_mechanics",
        url="https://anothereden.wiki/w/Battle_Mechanics",
        expected_selector=pipeline.MECHANICS_SOURCE_SELECTOR,
        raw_path=tmp_path / "raw" / "mechanics" / "battle_mechanics.html",
        parsed_path=tmp_path / "parsed" / "mechanics" / "sources" / "battle_mechanics.json",
        kind="mechanics_source_page",
        metadata={"source_key": "battle_mechanics"},
    )
    entry = pipeline._ensure_target_entry(manifest, target)
    Path(entry["raw_path"]).parent.mkdir(parents=True)
    Path(entry["raw_path"]).write_text(
        "<html><body><main id='mw-content-text'>Frontline, reserve, sidekick and turn order text.</main></body></html>",
        encoding="utf-8",
    )

    payload = pipeline._parse_target(entry)
    pipeline._validate_target(entry)

    assert payload["kind"] == "mechanics_source_page"
    assert payload["source_key"] == "battle_mechanics"
    assert payload["parsed_counts"]["mechanics_source_text_chars"] > 0
    assert entry["state"] == "parsed"
    assert entry["quality_status"] == "ok"


@pytest.mark.asyncio
async def test_ensure_constraints_adds_mechanic_reference_id_constraint():
    driver = RecordingDriver()

    await ensure_constraints(driver)

    constraint_cypher = "\n".join(cypher for cypher, _params in driver.calls)
    assert "CREATE CONSTRAINT mechanic_reference_id IF NOT EXISTS" in constraint_cypher
    assert "FOR (m:MechanicReference) REQUIRE m.id IS UNIQUE" in constraint_cypher


@pytest.mark.asyncio
async def test_load_mechanic_references_writes_all_curated_fields():
    driver = RecordingDriver()
    rows = [
        MechanicReferenceRow.model_validate(
            {
                "id": "affinity-weak-resist-null-absorb",
                "title": "Weakness, Resist, Null, And Absorb Handling",
                "source_url": "https://anothereden.wiki/w/Damage_Formula",
                "source_page": "Damage Formula",
                "section_path": ["Enemy affinity"],
                "mechanic_type": "affinity",
                "topic_tags": ["weakness", "resist", "null", "absorb"],
                "applies_to": ["boss_matchup_offense"],
                "rules_text": "Reward weakness and penalize resist, null, or absorb conflicts.",
                "summary": "Affinity grounding.",
                "caveats": "No exact simulator.",
            }
        )
    ]

    await load_mechanic_references(driver, rows)

    assert len(driver.calls) == 1
    cypher, params = driver.calls[0]
    assert "MERGE (m:MechanicReference {id: row.id})" in cypher
    assert "m.source_url = row.source_url" in cypher
    assert "m.section_path = row.section_path" in cypher
    assert "m.topic_tags = row.topic_tags" in cypher
    assert "m.rules_text = row.rules_text" in cypher
    assert "MATCH (" not in cypher
    assert "MERGE (" in cypher

    row = params["rows"][0]
    assert row["id"] == "affinity-weak-resist-null-absorb"
    assert row["mechanic_type"] == "affinity"
    assert "weakness" in row["topic_tags"]
    assert row["schema_version"]
