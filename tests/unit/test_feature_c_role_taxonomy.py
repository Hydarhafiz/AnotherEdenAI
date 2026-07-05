"""Milestone 5 Feature C role taxonomy and materialization regressions."""

import json

import pytest

from src.etl.loader import load_passive_skills, load_skills
from src.etl.models import PassiveSkillRow, SkillRow
from src.etl.role_taxonomy import (
    assert_role_materialization,
    load_role_taxonomy,
)


class AsyncRows:
    def __init__(self, rows):
        self._rows = rows

    def __aiter__(self):
        return self._iterate()

    async def _iterate(self):
        for row in self._rows:
            yield row


class Session:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def run(self, cypher, **params):
        self.calls.append((cypher, params))
        return AsyncRows(self.rows)


class Driver:
    def __init__(self, rows=None):
        self.session_instance = Session(rows)

    def session(self):
        return self.session_instance


def test_same_fact_and_artifact_reproduce_identical_tags_and_evidence():
    fact = {
        "character_name": "Mariel",
        "name": "Pure Cradle",
        "description": "Restore HP and remove status effects.",
        "skill_type": "Healing",
    }

    first = SkillRow.model_validate(fact)
    replay = SkillRow.model_validate(first.model_dump())

    assert replay.role_tags == first.role_tags
    assert replay.role_evidence_json == first.role_evidence_json
    assert replay.role_taxonomy_version == first.role_taxonomy_version == load_role_taxonomy()["version"]


def test_every_tag_has_rule_and_source_fact_evidence():
    skill = SkillRow(
        character_name="Yuna",
        name="Support Weave",
        description="Buff allies, debuff enemies, and restore MP.",
    )
    evidence = json.loads(skill.role_evidence_json)

    assert set(skill.role_tags) == {"buffer", "debuffer", "mp_sustain"}
    assert {item["role"] for item in evidence} == set(skill.role_tags)
    assert all(item["source"] == "rule" for item in evidence)
    assert all(item["source_id"] and item["source_fact_id"] == skill.skill_id for item in evidence)
    assert all(item["confidence"] in {"low", "medium", "high"} for item in evidence)


def test_one_character_can_materialize_multiple_roles_across_source_facts():
    skill = SkillRow(character_name="Aldo", name="X Slash", description="Attack and damage enemies.")
    passive = PassiveSkillRow(character_name="Aldo", name="Fire Zone", description="Deploy Fire Zone.")

    assert "primary_dps" in skill.role_tags
    assert "zone_setter" in passive.role_tags


@pytest.mark.asyncio
async def test_loaders_materialize_role_metadata_on_skill_and_passive_nodes():
    driver = Driver()
    skill = SkillRow(character_name="Aldo", name="X Slash", description="Damage enemies.")
    passive = PassiveSkillRow(character_name="Aldo", name="Fire Zone", description="Deploy zone.")

    await load_skills(driver, [skill])
    await load_passive_skills(driver, [passive])

    skill_query, skill_params = driver.session_instance.calls[0]
    passive_query, passive_params = driver.session_instance.calls[1]
    assert "s.role_taxonomy_version = row.role_taxonomy_version" in skill_query
    assert "p.role_evidence_json = row.role_evidence_json" in passive_query
    assert skill_params["rows"][0]["role_tags"] == skill.role_tags
    assert passive_params["rows"][0]["role_evidence_json"] == passive.role_evidence_json


@pytest.mark.asyncio
async def test_drift_detection_accepts_exact_graph_materialization():
    skill = SkillRow(character_name="Aldo", name="X Slash", description="Damage enemies.")
    graph_rows = [{
        "id": skill.skill_id,
        "tags": skill.role_tags,
        "evidence": skill.role_evidence_json,
        "version": skill.role_taxonomy_version,
    }]

    await assert_role_materialization(Driver(graph_rows), [skill], [])


@pytest.mark.asyncio
@pytest.mark.parametrize("graph_rows", [
    [],
    [{"id": "placeholder", "tags": ["buffer"], "evidence": "[]", "version": "0.0.0"}],
])
async def test_drift_detection_fails_for_missing_or_mismatched_materialization(graph_rows):
    skill = SkillRow(character_name="Aldo", name="X Slash", description="Damage enemies.")
    if graph_rows:
        graph_rows[0]["id"] = skill.skill_id

    with pytest.raises(RuntimeError, match="materialization drift detected"):
        await assert_role_materialization(Driver(graph_rows), [skill], [])


def test_taxonomy_rejects_rules_outside_declared_vocabulary(monkeypatch, tmp_path):
    artifact = tmp_path / "taxonomy.json"
    artifact.write_text(json.dumps({
        "version": "test",
        "roles": ["buffer"],
        "rules": [{
            "id": "bad-role", "record_types": ["skill"], "role": "invented",
            "confidence": "high", "pattern": "buff",
        }],
        "overrides": [],
    }), encoding="utf-8")
    monkeypatch.setattr("src.etl.role_taxonomy.TAXONOMY_PATH", artifact)
    load_role_taxonomy.cache_clear()

    with pytest.raises(ValueError, match="Invalid role taxonomy rule"):
        load_role_taxonomy()

    load_role_taxonomy.cache_clear()


def test_taxonomy_rejects_malformed_overrides(monkeypatch, tmp_path):
    artifact = tmp_path / "taxonomy.json"
    artifact.write_text(json.dumps({
        "version": "test",
        "roles": ["buffer"],
        "rules": [],
        "overrides": [{
            "id": "missing-record", "record_type": "skill", "role": "buffer",
            "confidence": "high",
        }],
    }), encoding="utf-8")
    monkeypatch.setattr("src.etl.role_taxonomy.TAXONOMY_PATH", artifact)
    load_role_taxonomy.cache_clear()

    with pytest.raises(ValueError, match="Invalid role taxonomy override"):
        load_role_taxonomy()

    load_role_taxonomy.cache_clear()
