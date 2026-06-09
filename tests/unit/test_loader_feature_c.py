"""Feature C loader tests for Grasta/Ore lightweight retrieval metadata."""

import pytest

from src.etl.loader import load_grastas, load_ores
from src.etl.models import GrastaRow, OreRow, TAG_DERIVATION_RULE


class FakeSession:
    def __init__(self):
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def run(self, cypher, **params):
        self.calls.append((cypher, params))


class FakeDriver:
    def __init__(self):
        self.fake_session = FakeSession()

    def session(self):
        return self.fake_session


@pytest.mark.asyncio
async def test_load_grastas_persists_effect_tags_without_changing_trait_gate():
    """Feature C: Grasta metadata loads while preserving existing REQUIRES_TRAIT rules."""
    driver = FakeDriver()
    rows = [
        GrastaRow(
            name="Fire Slash Pain Grasta",
            category="Attack",
            tier=3,
            stats="PWR +10 Fire slash damage when target has Pain",
            personality_req="Sword",
            is_shareable=True,
        ),
        GrastaRow(
            name="Proof of Courage",
            category="VC",
            tier=3,
            stats="ATK+10%",
            personality_req=None,
            is_shareable=False,
        ),
    ]

    await load_grastas(driver, rows)

    node_cypher, node_params = driver.fake_session.calls[0]
    edge_cypher, edge_params = driver.fake_session.calls[1]

    assert "g.effect_tags = row.effect_tags" in node_cypher
    assert "g.effect_tag_derivation = row.effect_tag_derivation" in node_cypher
    assert node_params["rows"][0]["effect_tags"] == [
        "category:attack",
        "tier:3",
        "element:fire",
        "attack:slash",
        "status:pain",
        "combat:damage",
        "stat:pwr",
    ]
    assert node_params["rows"][0]["effect_tag_derivation"] == TAG_DERIVATION_RULE
    assert node_params["rows"][1]["effect_tags"] == ["category:vc", "tier:3", "stat:pwr"]
    assert "row.category <> 'VC'" in edge_cypher
    assert "row.personality_req IS NOT NULL" in edge_cypher
    assert edge_params["rows"] == node_params["rows"]


@pytest.mark.asyncio
async def test_load_ores_persists_effect_tags_without_relationships():
    """Feature C: Ore metadata remains node-only and does not introduce ENHANCES edges."""
    driver = FakeDriver()
    rows = [
        OreRow(
            name="AF Speed Ore",
            stats="Restore AF Gauge by 10% on victory and SPD +5",
            source="Fog People Vendor",
        )
    ]

    await load_ores(driver, rows)

    assert len(driver.fake_session.calls) == 1
    cypher, params = driver.fake_session.calls[0]
    assert "o.effect_tags = row.effect_tags" in cypher
    assert "o.effect_tag_derivation = row.effect_tag_derivation" in cypher
    assert "ENHANCES" not in cypher
    assert "]-" not in cypher
    assert params["rows"][0]["effect_tags"] == ["category:ore", "combat:af", "stat:spd"]
    assert params["rows"][0]["effect_tag_derivation"] == TAG_DERIVATION_RULE
