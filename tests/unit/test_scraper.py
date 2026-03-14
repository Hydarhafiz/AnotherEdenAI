"""Unit tests for ETL scraper parse functions.

Tests operate against fixture HTML (no network calls).

Requirements covered:
- DATA-01: Characters scraped with correct attributes
- DATA-02: All 5 Grasta categories scraped correctly
- DATA-03: Ores scraped with name, stats, source
"""
import pytest
from bs4 import BeautifulSoup


# ---------------------------------------------------------------------------
# Fixture HTML fragments
# ---------------------------------------------------------------------------

CHARACTER_HTML = """
<table>
  <tbody>
    <tr class="character-row-entry"
        data-name="Aldo"
        data-element="Wind"
        data-weapon="Sword"
        data-type="Light"
        data-personality="Straw Dummy,Cool">
      <td>Aldo</td>
    </tr>
  </tbody>
</table>
"""

GRASTA_ATTACK_HTML = """
<table>
  <tbody>
    <tr class="grasta-row-entry"
        data-name="Courageous Strike"
        data-tier="2"
        data-personality="Straw Dummy"
        data-share="1">
      <td>Attack/2</td>
      <td>Courageous Strike</td>
      <td>Straw Dummy</td>
      <td>ATK+5%</td>
      <td>Deal 150% damage</td>
      <td>Drop</td>
    </tr>
  </tbody>
</table>
"""

GRASTA_VC_HTML = """
<table>
  <tbody>
    <tr class="grasta-row-entry"
        data-name="Proof of Courage Aldo"
        data-tier="3"
        data-personality=""
        data-share="0">
      <td>VC/3</td>
      <td>Proof of Courage</td>
      <td>Character: Aldo</td>
      <td>ATK+10%</td>
      <td>Boost ATK of party</td>
      <td>Another Dungeon</td>
    </tr>
  </tbody>
</table>
"""

ORE_HTML = """
<table>
  <tbody>
    <tr class="equip-row-entry">
      <td></td>
      <td>AF After Victory Ore</td>
      <td>Restore AF Gauge by 10% on victory</td>
      <td>Fog People Vendor (5000 Fog Medals)</td>
    </tr>
  </tbody>
</table>
"""


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_parse_character():
    """Parse a fixture character HTML row and verify all properties."""
    from src.etl.scraper import parse_characters
    soup = BeautifulSoup(CHARACTER_HTML, "html.parser")
    rows = parse_characters(soup)
    assert len(rows) == 1
    char = rows[0]
    assert char.name == "Aldo"
    assert char.element == "Wind"
    assert char.weapon == "Sword"
    assert char.light_shadow == "Light"
    assert "Straw Dummy" in char.personalities
    assert "Cool" in char.personalities


def test_parse_grasta_attack():
    """Parse Attack grasta fixture and verify correct column mapping."""
    from src.etl.scraper import parse_grastas
    soup = BeautifulSoup(GRASTA_ATTACK_HTML, "html.parser")
    rows = parse_grastas(soup, "Attack")
    assert len(rows) == 1
    g = rows[0]
    assert g.name == "Courageous Strike"
    assert g.category == "Attack"
    assert g.tier == 2
    assert g.stats == "ATK+5%"
    assert g.personality_req == "Straw Dummy"
    assert g.is_shareable is True


def test_parse_vc_grasta():
    """Parse VC grasta fixture — name from col[1], tier from data-tier, personality_req=None."""
    from src.etl.scraper import parse_vc_grastas
    soup = BeautifulSoup(GRASTA_VC_HTML, "html.parser")
    rows = parse_vc_grastas(soup)
    assert len(rows) == 1
    g = rows[0]
    # VC grastas use col[1] text as name, not data-name (which contains "Proof of Courage Aldo")
    assert g.name == "Proof of Courage"
    assert g.category == "VC"
    assert g.tier == 3  # from data-tier, NOT hard-coded
    assert g.stats == "ATK+10%"  # from col[3]
    assert g.personality_req is None  # never set for VC


def test_parse_grasta_stats_from_col3():
    """Verify stats comes from col[3], not col[2]."""
    from src.etl.scraper import parse_grastas
    soup = BeautifulSoup(GRASTA_ATTACK_HTML, "html.parser")
    rows = parse_grastas(soup, "Attack")
    # col[2] = "Straw Dummy" (personality_req), col[3] = "ATK+5%" (stats)
    assert rows[0].stats == "ATK+5%"
    assert rows[0].personality_req == "Straw Dummy"


def test_parse_ores():
    """Parse ore fixture HTML and verify all properties."""
    from src.etl.scraper import parse_ores
    soup = BeautifulSoup(ORE_HTML, "html.parser")
    rows = parse_ores(soup)
    assert len(rows) == 1
    ore = rows[0]
    assert ore.name == "AF After Victory Ore"
    assert "AF Gauge" in ore.stats
    assert "Fog" in ore.source
