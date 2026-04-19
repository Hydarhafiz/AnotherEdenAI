"""Async nodriver scraper for the AnotherEden wiki.

Fetches all 7 wiki pages sequentially using a single nodriver browser instance.
Cloudflare Turnstile is bypassed because nodriver drives real Chrome via CDP —
not detectable as a bot. Returns validated model instances.

Critical column mappings (verified against live wiki — see 01-RESEARCH.md):
  Grasta (non-VC):
    col[0] = category/tier label (redundant)
    col[1] = display name (used for non-VC)
    col[2] = personality_req OR "Character: Name" for VC
    col[3] = stats text (NOT col[2])
    col[4] = effect description
    col[5] = source

  Grasta (VC):
    col[1] = display name — USE THIS (data-name includes character suffix)
    col[3] = stats text

  Ore:
    col[0] = image (empty text)
    col[1] = ore name
    col[2] = stats/effect description
    col[3] = source/location
"""
import logging
from typing import Optional

import nodriver as uc
from bs4 import BeautifulSoup

from .constants import WIKI_URLS, GRASTA_CATEGORIES
from .models import CharacterRow, GrastaRow, OreRow, parse_character, parse_grasta, parse_ore

logger = logging.getLogger(__name__)

# Linux Chromium installed by Playwright. Do NOT use Windows Chrome from /mnt/c/...
# WSL2 CDP communication fails with the Windows binary.
CHROMIUM_PATH = "/home/shogunix/.cache/ms-playwright/chromium-1187/chrome-linux/chrome"


async def fetch_page(browser, url: str) -> BeautifulSoup:
    """Navigate to url using the provided nodriver Browser and return parsed HTML.

    Waits 2 seconds after navigation for Cloudflare JS challenge to auto-resolve.
    If the page title is still "Just a Moment" (Turnstile blocking), raises RuntimeError
    so the caller knows to add verify_cf() support.

    Args:
        browser: A nodriver Browser instance (from uc.start()).
        url: The fully-qualified wiki URL to fetch.

    Returns:
        BeautifulSoup parsed from the live DOM after JS execution.
    """
    tab = await browser.get(url)
    await tab.sleep(2)
    html = await tab.get_content()
    soup = BeautifulSoup(html, "html.parser")
    title = soup.find("title")
    if title and "Just a Moment" in title.get_text():
        raise RuntimeError(
            f"Cloudflare Turnstile blocked {url!r}. "
            "Install opencv-python and add 'await tab.verify_cf()' to fetch_page()."
        )
    return soup


# ---------------------------------------------------------------------------
# Parse functions — UNCHANGED from original httpx implementation.
# These operate on BeautifulSoup objects regardless of how the HTML was fetched.
# ---------------------------------------------------------------------------

def parse_characters(soup: BeautifulSoup) -> list[CharacterRow]:
    """Extract CharacterRow instances from a parsed Characters wiki page."""
    rows = []
    for tr in soup.select("tr.character-row-entry"):
        raw = {
            "name": tr.get("data-name", ""),
            "element": tr.get("data-element", ""),
            "weapon": tr.get("data-weapon", ""),
            "light_shadow": tr.get("data-type", ""),
            "personalities": tr.get("data-personality", ""),
        }
        result = parse_character(raw)
        if result is not None:
            rows.append(result)
    return rows


def parse_grastas(soup: BeautifulSoup, category: str) -> list[GrastaRow]:
    """Extract GrastaRow instances from a non-VC Grasta wiki page.

    Uses data-name for the name, data-tier for the tier (never hard-coded),
    and col[3] for stats (col[2] is personality_req).
    """
    rows = []
    for tr in soup.select("tr.grasta-row-entry"):
        cols = tr.find_all("td")
        if len(cols) < 4:
            logger.warning("Skipping grasta row with too few columns: %s", tr)
            continue
        personality_raw = tr.get("data-personality") or None
        raw = {
            "name": tr.get("data-name", ""),
            "category": category,
            "tier": tr.get("data-tier", 0),
            "stats": cols[3].get_text(" ", strip=True),
            "personality_req": personality_raw,
            "is_shareable": tr.get("data-share", "0"),
        }
        result = parse_grasta(raw)
        if result is not None:
            rows.append(result)
    return rows


def parse_vc_grastas(soup: BeautifulSoup) -> list[GrastaRow]:
    """Extract GrastaRow instances from the VC Grasta wiki page.

    VC-specific rules:
    - name comes from col[1].get_text(strip=True), NOT data-name
      (data-name includes the character name suffix, e.g. "Proof of Courage Aldo")
    - tier comes from data-tier attribute (NOT hard-coded to 4; wiki shows tier=3)
    - stats come from col[3]
    - personality_req is always None (enforced in parse_grasta too)
    """
    rows = []
    for tr in soup.select("tr.grasta-row-entry"):
        cols = tr.find_all("td")
        if len(cols) < 4:
            logger.warning("Skipping VC grasta row with too few columns: %s", tr)
            continue
        raw = {
            "name": cols[1].get_text(strip=True),
            "category": "VC",
            "tier": tr.get("data-tier", 0),
            "stats": cols[3].get_text(" ", strip=True),
            "personality_req": None,
            "is_shareable": tr.get("data-share", "0"),
        }
        result = parse_grasta(raw)
        if result is not None:
            rows.append(result)
    return rows


def parse_ores(soup: BeautifulSoup) -> list[OreRow]:
    """Extract OreRow instances from the Grasta Ores wiki page.

    Column layout: col[0]=image, col[1]=name, col[2]=stats, col[3]=source.
    """
    rows = []
    for tr in soup.select("tr.equip-row-entry"):
        cols = tr.find_all("td")
        if len(cols) < 4:
            logger.warning("Skipping ore row with too few columns: %s", tr)
            continue
        raw = {
            "name": cols[1].get_text(strip=True),
            "stats": cols[2].get_text(strip=True),
            "source": cols[3].get_text(strip=True),
        }
        result = parse_ore(raw)
        if result is not None:
            rows.append(result)
    return rows


async def scrape_all() -> dict:
    """Scrape all 7 wiki pages sequentially using a single nodriver browser.

    Opens one Chrome process, navigates to each URL in order, closes Chrome
    when done. Sequential (not parallel) — nodriver's Browser is not designed
    for concurrent CDP tab streams.

    Returns a dict with keys "characters", "grastas", "ores":
      - characters: list[CharacterRow]
      - grastas:    list[GrastaRow]  (all 5 categories combined)
      - ores:       list[OreRow]
    """
    browser = await uc.start(
        browser_executable_path=CHROMIUM_PATH,
        headless=False,  # headless=True has known stability issues in nodriver
        # DISPLAY=:0 is set in WSL2 — non-headless Chrome can render there.
        # For CI/headless-only: use browser_args=["--headless=new"] instead.
    )
    try:
        char_soup = await fetch_page(browser, WIKI_URLS["characters"])
        attack_soup = await fetch_page(browser, WIKI_URLS["grasta_attack"])
        life_soup = await fetch_page(browser, WIKI_URLS["grasta_life"])
        support_soup = await fetch_page(browser, WIKI_URLS["grasta_support"])
        special_soup = await fetch_page(browser, WIKI_URLS["grasta_special"])
        vc_soup = await fetch_page(browser, WIKI_URLS["grasta_vc"])
        ore_soup = await fetch_page(browser, WIKI_URLS["grasta_ores"])
    finally:
        browser.stop()

    characters = parse_characters(char_soup)

    grastas = []
    grastas.extend(parse_grastas(attack_soup, "Attack"))
    grastas.extend(parse_grastas(life_soup, "Life"))
    grastas.extend(parse_grastas(support_soup, "Support"))
    grastas.extend(parse_grastas(special_soup, "Special"))
    grastas.extend(parse_vc_grastas(vc_soup))

    ores = parse_ores(ore_soup)

    logger.info(
        "Scraped %d characters, %d grastas, %d ores",
        len(characters), len(grastas), len(ores),
    )

    return {"characters": characters, "grastas": grastas, "ores": ores}
