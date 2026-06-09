"""Feature D loader tests for baseline Weapon/Armor equipment context."""

import pytest

from src.etl.loader import ensure_constraints, load_equipment
from src.etl.models import EquipmentRow


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
async def test_ensure_constraints_adds_equipment_identity_constraint():
    """Feature D: shared Equipment nodes are unique by slot and name."""
    driver = RecordingDriver()

    await ensure_constraints(driver)

    constraint_cypher = "\n".join(cypher for cypher, _params in driver.calls)
    assert "CREATE CONSTRAINT equipment_identity IF NOT EXISTS" in constraint_cypher
    assert "FOR (e:Equipment) REQUIRE (e.equipment_slot, e.name) IS UNIQUE" in constraint_cypher


@pytest.mark.asyncio
async def test_load_equipment_writes_baseline_weapon_and_armor_fields():
    """Feature D: Equipment nodes persist stats, effects, obtain text, and source URL."""
    driver = RecordingDriver()
    rows = [
        EquipmentRow.model_validate({
            "name": "Lunar Sword",
            "equipment_slot": "weapon",
            "category": "Sword",
            "level": "60",
            "attack": "185",
            "magic_attack": "22",
            "effect_text": "Type attack +10%",
            "obtain_text": "Crafted from Moonlight Forest materials",
            "source_url": "https://anothereden.wiki/w/Weapons",
        }),
        EquipmentRow.model_validate({
            "name": "Dream Ring",
            "equipment_slot": "armor",
            "category": "Ring",
            "level": "55",
            "defense": "138",
            "magic_defense": "166",
            "effect_text": "Restore HP after battle",
            "obtain_text": "Treasure chest",
            "source_url": "https://anothereden.wiki/w/Armor",
        }),
    ]

    await load_equipment(driver, rows)

    assert len(driver.calls) == 1
    cypher, params = driver.calls[0]
    assert "MERGE (e:Equipment {equipment_slot: row.equipment_slot, name: row.name})" in cypher
    assert "e.effect_text = row.effect_text" in cypher
    assert "e.obtain_text = row.obtain_text" in cypher
    assert "e.source_url = row.source_url" in cypher
    assert "rank_score" not in cypher
    assert "best_in_slot" not in cypher
    assert "RECOMMENDS" not in cypher
    assert "]-" not in cypher

    weapon = params["rows"][0]
    armor = params["rows"][1]
    assert weapon["equipment_slot"] == "weapon"
    assert weapon["attack"] == 185
    assert weapon["magic_attack"] == 22
    assert weapon["defense"] is None
    assert weapon["effect_text"] == "Type attack +10%"
    assert weapon["source_url"].endswith("/Weapons")

    assert armor["equipment_slot"] == "armor"
    assert armor["attack"] is None
    assert armor["defense"] == 138
    assert armor["magic_defense"] == 166
    assert armor["effect_text"] == "Restore HP after battle"
    assert armor["source_url"].endswith("/Armor")
    assert all(row["schema_version"] for row in params["rows"])
