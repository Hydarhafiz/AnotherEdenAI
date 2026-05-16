"""Unit tests for Feature B combat graph loading."""

import pytest


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


@pytest.mark.asyncio
async def test_load_skills_writes_feature_b_properties_and_relationship():
    from src.etl.loader import load_skills
    from src.etl.models import SkillRow

    driver = RecordingDriver()

    await load_skills(
        driver,
        [
            SkillRow.model_validate(
                {
                    "character_name": "Eleanor",
                    "name": "Oath Arc",
                    "element": "Crystal",
                    "skill_type": "Slash",
                    "mp": "90",
                    "description": "Deploy stance and attack all enemies.",
                    "multiplier": "450%",
                    "source_url": "https://example.test/Eleanor",
                    "section": "Stellar Awakened Skills",
                    "requires_stellar_awakened": True,
                }
            )
        ],
    )

    cypher, params = driver.calls[0]
    row = params["rows"][0]
    assert "MERGE (s:Skill {character_name: row.character_name, name: row.name})" in cypher
    assert "MERGE (c)-[:HAS_SKILL]->(s)" in cypher
    assert row["character_name"] == "Eleanor"
    assert row["name"] == "Oath Arc"
    assert row["skill_type"] == "Slash"
    assert row["mp"] == 90
    assert row["description"].startswith("Deploy stance")
    assert row["multiplier"] == 450.0
    assert row["requires_stellar_awakened"] is True
    assert row["schema_version"]


@pytest.mark.asyncio
async def test_load_passive_skills_writes_feature_b_properties_and_relationship():
    from src.etl.loader import load_passive_skills
    from src.etl.models import PassiveSkillRow

    driver = RecordingDriver()

    await load_passive_skills(
        driver,
        [
            PassiveSkillRow.model_validate(
                {
                    "character_name": "Eleanor",
                    "name": "Dazzling Slash Stance",
                    "description": "+30% for Slash moves.",
                    "source_url": "https://example.test/Eleanor",
                    "section": "Stances/Zones",
                    "passive_type": "zone",
                    "requires_stellar_awakened": False,
                }
            )
        ],
    )

    cypher, params = driver.calls[0]
    row = params["rows"][0]
    assert "MERGE (p:PassiveSkill {character_name: row.character_name, name: row.name})" in cypher
    assert "MERGE (c)-[:HAS_PASSIVE_SKILL]->(p)" in cypher
    assert row["character_name"] == "Eleanor"
    assert row["name"] == "Dazzling Slash Stance"
    assert row["passive_type"] == "zone"
    assert row["description"] == "+30% for Slash moves."
    assert row["requires_stellar_awakened"] is False
    assert row["schema_version"]
