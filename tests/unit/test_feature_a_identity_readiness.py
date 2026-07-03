"""Focused Milestone 5 Feature A identity and readiness regressions."""

from unittest.mock import AsyncMock

import pytest

from src.etl.constants import SCHEMA_VERSION
from src.etl.loader import (
    ensure_constraints,
    load_passive_skills,
    load_skills,
    report_graph_readiness,
)
from src.etl.models import PassiveSkillRow, SkillRow


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


def test_skill_and_passive_ids_are_stable_and_owner_scoped():
    skill = SkillRow(character_name="Aldo", name="X Slash")
    same_skill = SkillRow(character_name="Aldo", name="X Slash")
    other_owner = SkillRow(character_name="Miyu", name="X Slash")
    passive = PassiveSkillRow(character_name="Aldo", name="Dragon God")
    same_passive = PassiveSkillRow(character_name="Aldo", name="Dragon God")

    assert skill.skill_id == same_skill.skill_id
    assert skill.skill_id != other_owner.skill_id
    assert skill.skill_id.startswith("skill:")
    assert passive.passive_skill_id == same_passive.passive_skill_id
    assert passive.passive_skill_id.startswith("passive:")
    assert skill.schema_version == passive.schema_version == SCHEMA_VERSION


@pytest.mark.asyncio
async def test_skill_identities_are_constrained_and_persisted_by_loaders():
    driver = RecordingDriver()
    skill = SkillRow(character_name="Aldo", name="X Slash")
    passive = PassiveSkillRow(character_name="Aldo", name="Dragon God")

    await ensure_constraints(driver)
    await load_skills(driver, [skill])
    await load_passive_skills(driver, [passive])

    statements = [cypher for cypher, _ in driver.calls]
    assert any("REQUIRE s.skill_id IS UNIQUE" in cypher for cypher in statements)
    assert any("REQUIRE p.passive_skill_id IS UNIQUE" in cypher for cypher in statements)

    skill_cypher, skill_params = driver.calls[-2]
    passive_cypher, passive_params = driver.calls[-1]
    assert "SET s.skill_id = row.skill_id" in skill_cypher
    assert skill_params["rows"][0]["skill_id"] == skill.skill_id
    assert "SET p.passive_skill_id = row.passive_skill_id" in passive_cypher
    assert passive_params["rows"][0]["passive_skill_id"] == passive.passive_skill_id


@pytest.mark.asyncio
async def test_readiness_is_false_and_gaps_are_visible_for_missing_facts_and_ids():
    graph_row = {
        "characters_without_skills": ["Aldo"],
        "characters_without_passives": ["Miyu"],
        "missing_character_ids": 1,
        "missing_skill_ids": 2,
        "missing_passive_skill_ids": 3,
        "stale_schema_nodes": 4,
        "boss_count": 1,
        "bosses_without_mechanics": 1,
        "grasta_count": 2,
        "missing_grasta_ids": 1,
        "equipment_count": 0,
        "mechanic_reference_count": 0,
    }
    driver = AsyncMock()
    driver.execute_query.return_value = ([graph_row], None, None)

    report = await report_graph_readiness(driver)

    assert report == {**graph_row, "ready": False}
    cypher = driver.execute_query.call_args.args[0]
    assert "missing_skill_ids" in cypher
    assert "missing_passive_skill_ids" in cypher
    assert "stale_schema_nodes" in cypher


@pytest.mark.asyncio
async def test_readiness_is_true_when_identity_and_fact_coverage_is_current():
    driver = AsyncMock()
    driver.execute_query.return_value = ([{
        "characters_without_skills": [],
        "characters_without_passives": [],
        "missing_character_ids": 0,
        "missing_skill_ids": 0,
        "missing_passive_skill_ids": 0,
        "stale_schema_nodes": 0,
        "boss_count": 1,
        "bosses_without_mechanics": 0,
        "grasta_count": 1,
        "missing_grasta_ids": 0,
        "equipment_count": 1,
        "mechanic_reference_count": 1,
    }], None, None)

    report = await report_graph_readiness(driver)

    assert report["ready"] is True
