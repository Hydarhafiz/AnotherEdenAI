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
        data-accessory="Bangle"
        data-personality="Straw Dummy,Cool">
      <td><a href="/w/Aldo" title="Aldo">Aldo</a></td>
      <td>Aldo</td>
    </tr>
    <tr class="character-row-entry"
        data-name="Hameow"
        data-element=""
        data-weapon=""
        data-type=""
        data-accessory="Sidekick"
        data-personality="">
      <td>Hameow</td>
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

WEAPON_HTML = """
<table>
  <tbody>
    <tr class="equip-row-entry"
        data-name="Lunar Sword"
        data-type="Sword"
        data-level="60"
        data-atk="185"
        data-matk="22"
        data-effect="Type attack +10%"
        data-source="Crafted from Moonlight Forest materials">
      <td></td>
      <td>Lunar Sword</td>
      <td>Sword</td>
      <td>60</td>
      <td>185</td>
      <td>22</td>
      <td>Type attack +10%</td>
      <td>Crafted from Moonlight Forest materials</td>
    </tr>
  </tbody>
</table>
"""

ARMOR_HTML = """
<table>
  <tbody>
    <tr class="equip-row-entry"
        data-name="Dream Ring"
        data-category="Ring"
        data-level="55"
        data-def="138"
        data-mdef="166"
        data-effect="Restore HP after battle"
        data-obtain="Treasure chest">
      <td></td>
      <td>Dream Ring</td>
      <td>Ring</td>
      <td>55</td>
      <td>138</td>
      <td>166</td>
      <td>Restore HP after battle</td>
      <td>Treasure chest</td>
    </tr>
  </tbody>
</table>
"""

CHARACTER_COMBAT_HTML = """
<article class="tabber__panel" title="Active Skills">
  <div class="character-skill-grid-container-title">
    <div class="skill-name">Skill Name</div>
  </div>
  <div class="character-skill-grid-container">
    <div class="character-skill-name-image">
      <div class="skill-name"><a href="/w/Crystal_Rapier">Crystal Rapier</a></div>
      <div class="skill-mp">MP 40</div>
    </div>
    <div class="character-skill-element-type">
      <div class="upper-grid">Crystal</div>
      <div class="lower-grid">Slash</div>
    </div>
    <div class="character-skill-description">
      <div class="skill-description">Crystal type slash attack on a single enemy (L)</div>
    </div>
    <div class="character-skill-mod"><div class="skill-mod">180%</div></div>
    <div class="character-skill-mp"><div>40</div></div>
  </div>
</article>
<article class="tabber__panel" title="Stellar Awakened Skills">
  <div class="character-skill-grid-container">
    <div class="character-skill-name-image">
      <div class="skill-name"><a href="/w/Oath_Arc">Oath Arc</a></div>
      <div class="skill-mp">MP 90</div>
    </div>
    <div class="character-skill-element-type">
      <div class="upper-grid">Crystal</div>
      <div class="lower-grid">Slash</div>
    </div>
    <div class="character-skill-description">
      <div class="skill-description">Deploy Dazzling Slash Stance and attack all enemies.</div>
    </div>
    <div class="character-skill-mod"><div class="skill-mod">450%</div></div>
    <div class="character-skill-mp"><div>90</div></div>
  </div>
</article>
<article class="tabber__panel" title="Stances/Zones">
  <div class="character-stance">
    <div class="stance-title-name"><a href="/w/Dazzling_Slash_Stance">Dazzling Slash Stance</a></div>
    <div class="stance-row-properties">+30% for all Slash moves.</div>
    <div class="stance-row-af">AF gauge charges per move while zone is active.</div>
    <div class="stance-row-end">Zone stays in effect until overwritten.</div>
  </div>
</article>
"""

SIDEKICK_INDEX_HTML = """
<table>
  <tbody>
    <tr class="character-row-entry"
        data-name="Tetra (Another Style)"
        data-sidekick="1"
        data-accessory="Sidekick"
        data-rarity="AS"
        data-role_strict="SR_Bud_Healer_NATK, SR_Aura_Bud_NATK">
      <td><a href="/w/Tetra_(Another_Style)" title="Tetra (Another Style)">Tetra AS</a></td>
    </tr>
    <tr class="character-row-entry"
        data-name="Aldo"
        data-accessory="Bangle"
        data-rarity="5">
      <td><a href="/w/Aldo" title="Aldo">Aldo</a></td>
    </tr>
  </tbody>
</table>
"""

SIDEKICK_RELEASED_INDEX_HTML = """
<div class="mw-parser-output">
  <h2><span class="mw-headline" id="Released_Sidekicks">Released Sidekicks</span></h2>
  <div class="sidekick-head">
    <div class="sidekick-images">
      <div class="sidekick-icon"><a href="/w/Tetra" title="Tetra"><img alt="2000000001 command.png"></a></div>
      <div class="sidekick-owner"><a href="/w/Minalca" title="Minalca"><img alt="101010131 rank5 command.png"></a></div>
    </div>
    <div class="sidekick-name"><a href="/w/Tetra" title="Tetra">Tetra</a> (5★)</div>
  </div>
  <div class="sidekick-head">
    <div class="sidekick-images">
      <div class="sidekick-icon"><a href="/w/Tetra_(Another_Style)" title="Tetra (Another Style)"><img alt="2000000001 s2 command.png"></a></div>
      <div class="sidekick-owner"><a href="/w/Minalca_(Another_Style)" title="Minalca (Another Style)"><img alt="101010131 s2 rank5 command.png"></a></div>
    </div>
    <div class="sidekick-name"><a href="/w/Tetra_(Another_Style)" title="Tetra (Another Style)">Tetra AS</a> (5★)</div>
  </div>
  <p>
    <a href="/w/File:2000000001_command.png" title="File:2000000001 command.png">Image</a>
    <a href="/w/Mare" title="Mare">Mare</a> (5★)
  </p>
  <h2><span class="mw-headline" id="Contents">Contents</span></h2>
  <p><a href="/w/Characters" title="Characters">Characters</a></p>
</div>
"""

SIDEKICK_DETAIL_HTML = """
<article class="tabber__panel" title="Sidekick Skills">
  <div class="character-skill-grid-container">
    <div class="character-skill-name-image">
      <div class="skill-name"><a href="/w/Nurturing_Roar">Nurturing Roar</a></div>
      <div class="skill-mp">MP 1</div>
    </div>
    <div class="character-skill-element-type">
      <div class="upper-grid">Null</div>
      <div class="lower-grid">Healing</div>
    </div>
    <div class="character-skill-description">
      <div class="skill-description"><b><a href="/w/Turn_Order">Auto</a></b>Restore all party members' HP +15%
      <ul><li><b>[When <a href="/w/Minalca_(Another_Style)" title="Minalca (Another Style)">Minalca (Another Style)</a> is at front]</b>: Stack +1 Charge</li></ul></div>
    </div>
    <div class="character-skill-mp"><div>1</div></div>
  </div>
  <div class="character-skill-grid-container">
    <div class="character-skill-name-image">
      <div class="skill-name"><a href="/w/Life_Bloom">Life Bloom</a></div>
      <div class="skill-mp">MP -5</div>
    </div>
    <div class="character-skill-element-type">
      <div class="upper-grid">Null</div>
      <div class="lower-grid">Buff</div>
    </div>
    <div class="character-skill-description">
      <div class="skill-description"><b><a href="/w/Turn_Order">Charged</a></b>Consumes 5 Charge to restore HP and MP</div>
    </div>
    <div class="character-skill-mp"><div>-5</div></div>
  </div>
  <div class="character-skill-grid-container">
    <div class="character-skill-name-image">
      <div class="skill-name"><a href="/w/Guardian_Aura">Guardian Aura</a></div>
      <div class="skill-mp">MP 0</div>
    </div>
    <div class="character-skill-element-type">
      <div class="upper-grid"></div>
      <div class="lower-grid">Buff</div>
    </div>
    <div class="character-skill-description">
      <div class="skill-description"><b><a href="/w/Aura">Aura</a></b><b>Activation condition:</b> When HP is below 80%
      <ul><li>All party members max HP <b>+30%</b></li></ul></div>
    </div>
    <div class="character-skill-mp"><div>0</div></div>
  </div>
  <div class="character-skill-grid-container">
    <div class="character-skill-name-image">
      <div class="skill-name"><a href="/w/Irregular_Field">Irregular Field</a></div>
    </div>
    <div class="character-skill-description">
      <div class="skill-description">Unrecognized sidekick section text.</div>
    </div>
  </div>
</article>
<h2><span class="mw-headline" id="Encounter">Encounter</span></h2>
<h3><span class="mw-headline" id="Encounter_them_in_the_Gallery_of_Dreams">Encounter them in the Gallery of Dreams</span></h3>
<p>Certain characters have 5 star class styles that add a sidekick to your party.</p>
"""

SUPERBOSS_INDEX_HTML = """
<table>
  <tbody>
    <tr>
      <th>Difficulty</th><th>Name</th><th>Refight</th><th>Version</th><th>Characteristics</th>
    </tr>
    <tr>
      <td>1</td>
      <td><a href="/w/Zennon_Ogre%27s_Shadow" title="Zennon Ogre's Shadow">Zennon Ogre's Shadow</a></td>
      <td>Refightable</td>
      <td>1.0.0</td>
      <td>HP stopper, high firepower</td>
    </tr>
    <tr>
      <td>2</td>
      <td><a href="/w/Gariyu_(Chance_Encounter)" title="Flame Eater">Flame Eater</a></td>
      <td>No</td>
      <td>1.2.5</td>
      <td>Summons companions</td>
    </tr>
    <tr>
      <td>4</td>
      <td><a href="/w/Melvillithan" title="Melvillithan">Melvillithan</a></td>
      <td>Yes</td>
      <td>3.0.0</td>
      <td>Not in the weak curated seed set</td>
    </tr>
  </tbody>
</table>
"""

SUPERBOSS_DETAIL_HTML = """
<div id="mw-content-text">
  <h2><span class="mw-headline" id="Flame_Eater">Flame Eater</span></h2>
  <table>
    <tr><th>HP</th><td>1,234,567</td></tr>
    <tr><th>Weak</th><td>Water / Slash</td></tr>
    <tr><th>Resist</th><td>Fire</td></tr>
    <tr><th>Null</th><td>Earth</td></tr>
    <tr><th>Absorb</th><td>None</td></tr>
  </table>
  <p>The battle has an HP stopper and summons companions on later turns.</p>
  <ul><li>Uses fire damage and debuffs party resistance.</li></ul>
  <h2><span class="mw-headline" id="Other_Boss">Other Boss</span></h2>
  <p>This later section should not be included in Flame Eater mechanics text.</p>
</div>
"""


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_parse_character():
    """Parse character rows while excluding sidekick-only records."""
    from src.etl.scraper import parse_characters
    soup = BeautifulSoup(CHARACTER_HTML, "html.parser")
    rows = parse_characters(soup)
    assert len(rows) == 1
    char = rows[0]
    assert char.name == "Aldo"
    assert char.element == "Wind"
    assert char.weapon == "Sword"
    assert char.light_shadow == "Light"
    assert char.detail_url == "https://anothereden.wiki/w/Aldo"
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


def test_parse_equipment_index_weapon_baseline_fields():
    """Feature D: weapon indexes produce baseline attack context with source attribution."""
    from src.etl.scraper import parse_equipment_index

    soup = BeautifulSoup(WEAPON_HTML, "html.parser")
    rows = parse_equipment_index(soup, "weapon", "https://anothereden.wiki/w/Weapons")

    assert len(rows) == 1
    weapon = rows[0]
    assert weapon.name == "Lunar Sword"
    assert weapon.equipment_slot == "weapon"
    assert weapon.category == "Sword"
    assert weapon.level == 60
    assert weapon.attack == 185
    assert weapon.magic_attack == 22
    assert weapon.defense is None
    assert weapon.magic_defense is None
    assert weapon.effect_text == "Type attack +10%"
    assert weapon.obtain_text.startswith("Crafted")
    assert weapon.source_url == "https://anothereden.wiki/w/Weapons"
    assert weapon.schema_version


def test_parse_equipment_index_armor_baseline_fields():
    """Feature D: armor indexes produce defense/sustainability context."""
    from src.etl.scraper import parse_equipment_index

    soup = BeautifulSoup(ARMOR_HTML, "html.parser")
    rows = parse_equipment_index(soup, "armor", "https://anothereden.wiki/w/Armor")

    assert len(rows) == 1
    armor = rows[0]
    assert armor.name == "Dream Ring"
    assert armor.equipment_slot == "armor"
    assert armor.category == "Ring"
    assert armor.level == 55
    assert armor.attack is None
    assert armor.magic_attack is None
    assert armor.defense == 138
    assert armor.magic_defense == 166
    assert armor.effect_text == "Restore HP after battle"
    assert armor.obtain_text == "Treasure chest"
    assert armor.source_url == "https://anothereden.wiki/w/Armor"


def test_parse_character_detail_combat_graph_rows():
    """Character pages produce active skills, SA-gated skills, and passive zone rows."""
    from src.etl.scraper import (
        character_has_stellar_awakened,
        parse_character_passive_skills,
        parse_character_skills,
    )

    soup = BeautifulSoup(CHARACTER_COMBAT_HTML, "html.parser")
    skills = parse_character_skills(soup, "Eleanor", source_url="https://example.test/Eleanor")
    passives = parse_character_passive_skills(soup, "Eleanor", source_url="https://example.test/Eleanor")

    assert character_has_stellar_awakened(soup) is True
    assert [skill.name for skill in skills] == ["Crystal Rapier", "Oath Arc"]
    assert skills[0].element == "Crystal"
    assert skills[0].skill_type == "Slash"
    assert skills[0].mp == 40
    assert skills[0].description.startswith("Crystal type slash")
    assert skills[0].multiplier == 180.0
    assert skills[0].requires_stellar_awakened is False
    assert skills[1].section == "Stellar Awakened Skills"
    assert skills[1].requires_stellar_awakened is True
    assert [passive.name for passive in passives] == ["Dazzling Slash Stance"]
    assert passives[0].passive_type == "zone"
    assert "AF gauge" in passives[0].description


def test_parse_sidekick_index_discovers_only_sidekick_rows():
    """Sidekick index rows become Sidekick records without entering Character rows."""
    from src.etl.scraper import parse_sidekick_index

    soup = BeautifulSoup(SIDEKICK_INDEX_HTML, "html.parser")
    rows = parse_sidekick_index(soup)

    assert [row.name for row in rows] == ["Tetra (Another Style)"]
    assert rows[0].source_url == "https://anothereden.wiki/w/Tetra_(Another_Style)"
    assert rows[0].rarity == "AS"
    assert "role_tags" not in type(rows[0]).model_fields
    assert rows[0].schema_version


def test_parse_sidekick_index_discovers_released_sidekick_links():
    """The canonical Sidekick page lists released sidekicks as links, not Cargo rows."""
    from src.etl.scraper import parse_sidekick_index

    soup = BeautifulSoup(SIDEKICK_RELEASED_INDEX_HTML, "html.parser")
    rows = parse_sidekick_index(soup)

    assert [row.name for row in rows] == ["Tetra", "Tetra (Another Style)"]
    assert rows[1].source_url == "https://anothereden.wiki/w/Tetra_(Another_Style)"
    assert rows[1].rarity == "5★"
    assert rows[0].associated_character_names == ["Minalca"]
    assert rows[1].associated_character_names == ["Minalca (Another Style)"]
    assert "Minalca" not in [row.name for row in rows]


def test_parse_sidekick_detail_splits_abilities_auras_associations_and_diagnostics():
    """Sidekick detail pages produce queryable auto skill, charge skill, aura, and association facts."""
    from src.etl.models import SidekickRow
    from src.etl.scraper import parse_sidekick_detail

    soup = BeautifulSoup(SIDEKICK_DETAIL_HTML, "html.parser")
    row = parse_sidekick_detail(
        soup,
        SidekickRow(name="Tetra (Another Style)", source_url="https://example.test/Tetra_AS"),
    )

    assert row.main_slot_behavior.startswith("Main sidekick")
    assert row.sub_slot_behavior.startswith("Sub sidekick")
    assert row.acquisition_text.startswith("Certain characters")
    assert row.associated_character_names == ["Minalca (Another Style)"]
    assert [skill.name for skill in row.auto_skills] == ["Nurturing Roar"]
    assert row.auto_skills[0].skill_kind == "auto"
    assert row.auto_skills[0].skill_type == "Healing"
    assert [skill.name for skill in row.charge_skills] == ["Life Bloom"]
    assert row.charge_skills[0].charge_cost == 5
    assert [aura.name for aura in row.auras] == ["Guardian Aura"]
    assert row.auras[0].activation_condition == "When HP is below 80%"
    assert "All party members max HP" in row.auras[0].effect_text
    assert "Irregular Field" in row.diagnostics_text


def test_parse_superboss_index_discovers_only_curated_weak_candidates():
    """Superbosses index rows provide discovery metadata without broad all-boss expansion."""
    from src.etl.scraper import parse_superboss_index

    soup = BeautifulSoup(SUPERBOSS_INDEX_HTML, "html.parser")
    rows = parse_superboss_index(soup)

    assert [row.name for row in rows] == ["Zennon Ogre's Shadow", "Flame Eater"]
    assert rows[0].source_url == "https://anothereden.wiki/w/Zennon_Ogre%27s_Shadow"
    assert rows[0].difficulty_tier == "1"
    assert rows[0].level == 1
    assert rows[0].refight_status == "Refightable"
    assert rows[0].version == "1.0.0"
    assert "HP stopper" in rows[0].characteristics
    assert rows[1].source_url == "https://anothereden.wiki/w/Gariyu_(Chance_Encounter)#Flame_Eater"


def test_parse_superboss_detail_keeps_section_anchor_and_structured_fields():
    """Section-anchored pages produce explicit affinity fields and RAG mechanics text."""
    from src.etl.models import SuperbossIndexRow
    from src.etl.scraper import parse_superboss_detail

    soup = BeautifulSoup(SUPERBOSS_DETAIL_HTML, "html.parser")
    row = parse_superboss_detail(
        soup,
        SuperbossIndexRow.model_validate(
            {
                "name": "Flame Eater",
                "source_url": "https://anothereden.wiki/w/Gariyu_(Chance_Encounter)#Flame_Eater",
                "difficulty_tier": "2",
                "level": 2,
                "characteristics": "Summons companions",
            }
        ),
    )

    assert row.name == "Flame Eater"
    assert row.source_url.endswith("#Flame_Eater")
    assert row.hp == 1234567
    assert row.weak == ["Water", "Slash"]
    assert row.resist == ["Fire"]
    assert row.null == ["Earth"]
    assert row.absorb == ["None"]
    assert "HP stopper" in row.mechanics_text
    assert "Other Boss" not in row.mechanics_text
    assert {"companion summon", "hp stopper"}.issubset(set(row.mechanic_tags))
    assert row.schema_version


def test_wiki_page_title_uses_style_alias_after_comma():
    """Character index names can include base/form metadata before the canonical page title."""
    from src.etl.scraper import _wiki_page_title

    assert _wiki_page_title("Mighty (Alter),Dark Devourer") == "Dark Devourer"
    assert _wiki_page_title("Aldo") == "Aldo"


def test_parse_character_overrides():
    """Manual weapon overrides are applied after model_validate.

    Anabel ES and Mazrika have incorrect weapon data on the wiki.
    WEAPON_OVERRIDES in models.py corrects them post-validation.
    """
    from src.etl.models import parse_character

    # Anabel ES: wiki has wrong weapon; override sets Spear
    anabel = parse_character({
        "name": "Anabel ES",
        "element": "Water",
        "weapon": "",           # simulate missing/wrong wiki value
        "light_shadow": "Light",
        "personalities": "Cool",
    })
    assert anabel is not None
    assert anabel.weapon == "Spear", f"Expected Spear, got {anabel.weapon!r}"

    # Mazrika: wiki has wrong weapon; override sets Axe
    mazrika = parse_character({
        "name": "Mazrika",
        "element": "Fire",
        "weapon": "",           # simulate missing/wrong wiki value
        "light_shadow": "Shadow",
        "personalities": "Wild",
    })
    assert mazrika is not None
    assert mazrika.weapon == "Axe", f"Expected Axe, got {mazrika.weapon!r}"

    # Non-override character: weapon unchanged
    aldo = parse_character({
        "name": "Aldo",
        "element": "Wind",
        "weapon": "Sword",
        "light_shadow": "Light",
        "personalities": "Straw Dummy,Cool",
    })
    assert aldo is not None
    assert aldo.weapon == "Sword"


@pytest.mark.asyncio
async def test_stop_browser_disconnects_before_stop():
    """Browser cleanup awaits disconnect and still calls stop."""
    from src.etl.scraper import _stop_browser

    events = []

    class FakeConnection:
        async def disconnect(self):
            events.append("disconnect")

    class FakeBrowser:
        def __init__(self):
            self.connection = FakeConnection()
            self._process = FakeProcess()

        def stop(self):
            events.append("stop")

    class FakeProcess:
        async def wait(self):
            events.append("wait")

    await _stop_browser(FakeBrowser())

    assert events == ["disconnect", "stop", "wait"]
