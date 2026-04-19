"""Integration tests for the nodriver-based ETL scraper.

These tests require:
  - A live internet connection to anothereden.wiki
  - Linux Chromium at CHROMIUM_PATH (installed via Playwright)
  - DISPLAY environment variable set (non-headless Chrome requires X display)

Run with:
    pytest tests/integration/test_etl_scraper.py -x -m integration

Skip condition: these tests are excluded from the default pytest run
(pytest --ignore=tests/integration).
"""
import pytest
from bs4 import BeautifulSoup


CHROMIUM_PATH = "/home/shogunix/.cache/ms-playwright/chromium-1187/chrome-linux/chrome"


@pytest.mark.integration
@pytest.mark.scraper
async def test_fetch_page_returns_beautifulsoup():
    """fetch_page() retrieves the Characters wiki page via nodriver.

    Asserts:
    - Return type is BeautifulSoup
    - Page contains at least one 'tr.character-row-entry' element
    - No Cloudflare "Just a Moment" blocking page returned
    """
    import nodriver as uc
    from src.etl.scraper import fetch_page

    browser = await uc.start(
        browser_executable_path=CHROMIUM_PATH,
        headless=False,
    )
    try:
        soup = await fetch_page(browser, "https://anothereden.wiki/w/Characters", "tr.character-row-entry")
    finally:
        browser.stop()

    assert isinstance(soup, BeautifulSoup), f"Expected BeautifulSoup, got {type(soup)}"
    rows = soup.select("tr.character-row-entry")
    assert len(rows) >= 100, f"Expected >= 100 character rows, got {len(rows)}"
    title = soup.find("title")
    assert title is None or "Just a Moment" not in title.get_text(), \
        "Cloudflare challenge not bypassed — page title is 'Just a Moment'"


@pytest.mark.integration
@pytest.mark.scraper
async def test_scrape_all_returns_expected_structure():
    """scrape_all() returns a dict with characters, grastas, ores keys.

    Asserts:
    - All three keys present
    - characters list has >= 300 entries (EXPECTED_NODE_COUNTS["Character"] = 300)
    - grastas list has >= 460 entries (EXPECTED_NODE_COUNTS["Grasta"] = 460)
    - ores list has >= 50 entries (EXPECTED_NODE_COUNTS["Ore"] = 50)
    """
    from src.etl.scraper import scrape_all
    from src.etl.constants import EXPECTED_NODE_COUNTS

    data = await scrape_all()

    assert set(data.keys()) == {"characters", "grastas", "ores"}
    assert len(data["characters"]) >= EXPECTED_NODE_COUNTS["Character"], (
        f"Expected >= {EXPECTED_NODE_COUNTS['Character']} characters, "
        f"got {len(data['characters'])}"
    )
    assert len(data["grastas"]) >= EXPECTED_NODE_COUNTS["Grasta"], (
        f"Expected >= {EXPECTED_NODE_COUNTS['Grasta']} grastas, "
        f"got {len(data['grastas'])}"
    )
    assert len(data["ores"]) >= EXPECTED_NODE_COUNTS["Ore"], (
        f"Expected >= {EXPECTED_NODE_COUNTS['Ore']} ores, "
        f"got {len(data['ores'])}"
    )
