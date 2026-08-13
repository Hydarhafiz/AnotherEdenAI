"""Unit tests for Feature B combat graph loading."""

import json

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


@pytest.mark.asyncio
async def test_load_sidekicks_writes_feature_a_nodes_and_relationships():
    from src.etl.loader import load_sidekicks
    from src.etl.models import SidekickRow

    driver = RecordingDriver()

    await load_sidekicks(
        driver,
        [
            SidekickRow.model_validate(
                {
                    "name": "Tetra (Another Style)",
                    "source_url": "https://example.test/Tetra_AS",
                    "acquisition_text": "Unlock through Minalca AS.",
                    "rarity": "AS",
                    "role_tags": ["SR_Bud_Healer_NATK"],
                    "associated_character_names": ["Minalca (Another Style)"],
                    "auto_skills": [
                        {
                            "sidekick_name": "Tetra (Another Style)",
                            "name": "Nurturing Roar",
                            "skill_kind": "auto",
                            "element": "Null",
                            "skill_type": "Healing",
                            "charge_cost": 1,
                            "description": "Auto heal.",
                            "source_url": "https://example.test/Tetra_AS",
                            "section": "Sidekick Skills",
                        }
                    ],
                    "charge_skills": [
                        {
                            "sidekick_name": "Tetra (Another Style)",
                            "name": "Life Bloom",
                            "skill_kind": "charge",
                            "charge_cost": 5,
                            "description": "Consumes 5 Charge.",
                            "source_url": "https://example.test/Tetra_AS",
                            "section": "Sidekick Skills",
                        }
                    ],
                    "auras": [
                        {
                            "sidekick_name": "Tetra (Another Style)",
                            "name": "Guardian Aura",
                            "activation_condition": "When HP is below 80%",
                            "effect_text": "All party members max HP +30%.",
                            "source_url": "https://example.test/Tetra_AS",
                            "section": "Sidekick Skills",
                        }
                    ],
                }
            )
        ],
    )

    sidekick_cypher, sidekick_params = driver.calls[0]
    skill_cypher, skill_params = driver.calls[1]
    aura_cypher, aura_params = driver.calls[2]

    assert "MERGE (s:Sidekick {name: row.name})" in sidekick_cypher
    assert "MERGE (c)-[:UNLOCKS_SIDEKICK]->(s)" in sidekick_cypher
    assert sidekick_params["rows"][0]["name"] == "Tetra (Another Style)"
    assert sidekick_params["rows"][0]["source_url"] == "https://example.test/Tetra_AS"
    assert sidekick_params["rows"][0]["main_slot_behavior"].startswith("Main sidekick")
    assert sidekick_params["rows"][0]["sub_slot_behavior"].startswith("Sub sidekick")
    assert sidekick_params["rows"][0]["associated_character_names"] == ["Minalca (Another Style)"]

    assert "MERGE (skill:SidekickSkill" in skill_cypher
    assert "MERGE (sidekick)-[:HAS_AUTO_SKILL]->(skill)" in skill_cypher
    assert "MERGE (sidekick)-[:HAS_CHARGE_SKILL]->(skill)" in skill_cypher
    assert {row["skill_kind"] for row in skill_params["rows"]} == {"auto", "charge"}

    assert "MERGE (aura:SidekickAura" in aura_cypher
    assert "MERGE (sidekick)-[:HAS_AURA]->(aura)" in aura_cypher
    assert aura_params["rows"][0]["activation_condition"] == "When HP is below 80%"


@pytest.mark.asyncio
async def test_load_superbosses_writes_feature_b_rag_fields():
    from src.etl.loader import load_superbosses
    from src.etl.models import SuperbossRow

    driver = RecordingDriver()

    await load_superbosses(
        driver,
        [
            SuperbossRow.model_validate(
                {
                    "name": "Flame Eater",
                    "source_url": "https://example.test/Gariyu#Flame_Eater",
                    "difficulty_tier": "2",
                    "level": 2,
                    "hp": "1,234,567",
                    "weak": ["Water", "Slash"],
                    "resist": ["Fire"],
                    "null": ["unknown"],
                    "absorb": ["unknown"],
                    "characteristics": "Summons companions",
                    "mechanic_tags": ["companion summon", "hp stopper"],
                    "mechanics_text": "The battle has an HP stopper and summons companions.",
                    "provenance": {"authority": "wiki", "whole_page_fallback": "false"},
                    "mechanics_evidence": {"section_anchor": "Flame_Eater"},
                    "affinity_evidence": {"weak": "icon-backed"},
                    "affinity_observations": [{"field": "weak", "values": ["Water"]}],
                    "selection_rationale": {"mechanics": "summon counterplay"},
                }
            )
        ],
    )

    cypher, params = driver.calls[0]
    row = params["rows"][0]
    assert "MERGE (s:Superboss {name: row.name})" in cypher
    assert "s.weak = row.weak" in cypher
    assert "s.mechanics_text = row.mechanics_text" in cypher
    assert row["name"] == "Flame Eater"
    assert row["source_url"].endswith("#Flame_Eater")
    assert row["difficulty_tier"] == "2"
    assert row["level"] == 2
    assert row["hp"] == 1234567
    assert row["weak"] == ["Water", "Slash"]
    assert row["resist"] == ["Fire"]
    assert row["null"] == ["unknown"]
    assert row["absorb"] == ["unknown"]
    assert row["mechanic_tags"] == ["companion summon", "hp stopper"]
    assert "summons companions" in row["mechanics_text"]
    assert json.loads(row["provenance"]) == {"authority": "wiki", "whole_page_fallback": "false"}
    assert json.loads(row["mechanics_evidence"]) == {"section_anchor": "Flame_Eater"}
    assert json.loads(row["affinity_evidence"]) == {"weak": "icon-backed"}
    assert json.loads(row["affinity_observations"]) == [{"field": "weak", "values": ["Water"]}]
    assert json.loads(row["selection_rationale"]) == {"mechanics": "summon counterplay"}
    assert row["schema_version"]
