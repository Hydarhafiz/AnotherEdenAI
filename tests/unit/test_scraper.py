"""Unit tests for ETL scraper parse functions.

Wave 0 stubs — these tests are skipped until src/etl/scraper.py is implemented in Plan 01-02.
Tests operate against fixture HTML (no network calls).

Requirements covered:
- DATA-01: Characters scraped with correct attributes
- DATA-02: All 5 Grasta categories scraped correctly
- DATA-03: Ores scraped with name, stats, source
"""
import pytest


@pytest.mark.skip(reason="TODO Plan 01-02: implement src/etl/scraper.py and fixture HTML")
def test_parse_character():
    """Parse a fixture character HTML row and verify all properties.

    TODO: Load fixture HTML containing a tr.character-row-entry row.
    Expected: CharacterRow with correct element, weapon, light_shadow, personalities.

    Key validations:
    - data-element maps to element field
    - data-weapon maps to weapon field
    - data-type maps to light_shadow field ("Light" or "Shadow")
    - data-personality (comma-separated) maps to personalities list
    - data-name maps to name field

    Reference: 01-RESEARCH.md Wiki Audit Results — Characters Page
    """
    pass


@pytest.mark.skip(reason="TODO Plan 01-02: implement src/etl/scraper.py and fixture HTML")
def test_parse_grasta_categories():
    """Parse all 5 grasta categories and verify correct column mapping.

    TODO: Load fixture HTML for Attack, Life, Support, Special, VC categories.
    Expected: GrastaRow instances with correct category, tier, stats, personality_req, is_shareable.

    Key validations:
    - All 5 categories (Attack, Life, Support, Special, VC) are parsed
    - VC grastas use col[1] for name (NOT data-name which includes character name)
    - stats comes from col[3] (NOT col[2] — master_scraper.py bug)
    - personality_req comes from col[2] or data-personality
    - VC grastas have personality_req=None (no REQUIRES_TRAIT edge)
    - tier is read from data-tier (do NOT hard-code VC=4, wiki shows tier=3)

    Reference: 01-RESEARCH.md Wiki Audit — Grasta Pages, Anti-Patterns
    """
    pass


@pytest.mark.skip(reason="TODO Plan 01-02: implement src/etl/scraper.py and fixture HTML")
def test_parse_ores():
    """Parse ore fixture HTML and verify all properties.

    TODO: Load fixture HTML containing tr.equip-row-entry rows.
    Expected: OreRow with name (col[1]), stats (col[2]), source (col[3]).

    Key validations:
    - col[1] = ore name (text or anchor tag text)
    - col[2] = stats/effect description
    - col[3] = source/drop location

    Reference: 01-RESEARCH.md Wiki Audit — Ore Page
    """
    pass
