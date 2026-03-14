"""Async httpx scraper for the AnotherEden wiki.

Fetches all 7 wiki pages concurrently using a single AsyncClient with
Semaphore(5) to limit concurrent requests. Returns validated model instances.

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
import asyncio
import logging
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from .constants import WIKI_URLS, GRASTA_CATEGORIES
from .models import CharacterRow, GrastaRow, OreRow, parse_character, parse_grasta, parse_ore

logger = logging.getLogger(__name__)

SEMAPHORE = asyncio.Semaphore(5)
LIMITS = httpx.Limits(max_keepalive_connections=5, max_connections=10)
HEADERS = {"User-Agent": "Mozilla/5.0 (AnotherEdenAI-research-bot)"}
TIMEOUT = 15.0


async def fetch_page(client: httpx.AsyncClient, url: str) -> BeautifulSoup:
    """Fetch a URL and return a parsed BeautifulSoup object.

    Acquires SEMAPHORE before each request to honour the 5-connection limit.
    Raises httpx.HTTPError on non-2xx responses.
    """
    async with SEMAPHORE:
        response = await client.get(url, timeout=TIMEOUT)
        response.raise_for_status()
        return BeautifulSoup(response.text, "html.parser")


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
    """Scrape all 7 wiki pages concurrently and return validated model instances.

    Returns a dict with keys "characters", "grastas", "ores":
      - characters: list[CharacterRow]
      - grastas:    list[GrastaRow]  (all 5 categories combined)
      - ores:       list[OreRow]
    """
    async with httpx.AsyncClient(limits=LIMITS, headers=HEADERS) as client:
        # Fetch all pages concurrently
        pages = await asyncio.gather(
            fetch_page(client, WIKI_URLS["characters"]),
            fetch_page(client, WIKI_URLS["grasta_attack"]),
            fetch_page(client, WIKI_URLS["grasta_life"]),
            fetch_page(client, WIKI_URLS["grasta_support"]),
            fetch_page(client, WIKI_URLS["grasta_special"]),
            fetch_page(client, WIKI_URLS["grasta_vc"]),
            fetch_page(client, WIKI_URLS["grasta_ores"]),
        )

    char_soup, attack_soup, life_soup, support_soup, special_soup, vc_soup, ore_soup = pages

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
