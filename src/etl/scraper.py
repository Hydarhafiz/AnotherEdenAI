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
import random
import re
from pathlib import Path
from typing import Optional
from urllib.parse import quote

import nodriver as uc
from bs4 import BeautifulSoup

from .constants import RAW_CHARACTER_DIR, RAW_PAGE_FILES, WIKI_URLS
from .models import CharacterRow, GrastaRow, OreRow, SkillRow, parse_character, parse_grasta, parse_ore

logger = logging.getLogger(__name__)

# Linux Chromium installed by Playwright. Do NOT use Windows Chrome from /mnt/c/...
# WSL2 CDP communication fails with the Windows binary.
CHROMIUM_PATH = "/home/shogunix/.cache/ms-playwright/chromium-1187/chrome-linux/chrome"


def _slugify_title(title: str) -> str:
    """Convert a wiki title to a stable local HTML filename stem."""
    slug = re.sub(r"[^A-Za-z0-9]+", "_", title.strip()).strip("_").lower()
    return slug or "unknown"


def _read_soup(path: Path) -> BeautifulSoup:
    """Read a cached HTML file into BeautifulSoup."""
    return BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")


async def fetch_page(browser, url: str, expected_selector: str) -> BeautifulSoup:
    """Navigate to url and poll until expected_selector appears in the live DOM.

    Cloudflare's JS challenge auto-resolves in ~2-5s for non-headless Chrome.
    Wiki tables (Cargo macro) render async after the challenge clears. Polling
    waits for both — static sleep would silently return 0 rows on a slow page.

    Raises RuntimeError after 10 polls (~18s total) if the selector never appears.
    """
    logger.info("Fetching %s", url)
    tab = await browser.get(url)
    await tab.sleep(3)  # initial window for CF challenge to auto-resolve

    for attempt in range(10):
        html = await tab.get_content()
        soup = BeautifulSoup(html, "html.parser")
        title = soup.find("title")
        if title and "just a moment" in title.get_text().lower():
            logger.debug("[%d/10] Cloudflare challenge pending on %s", attempt + 1, url)
            await tab.sleep(2)
            continue
        if soup.select(expected_selector):
            logger.info("Found %s on %s", expected_selector, url)
            return soup
        logger.debug("[%d/10] Waiting for tables to render on %s", attempt + 1, url)
        await tab.sleep(1.5)

    raise RuntimeError(
        f"Timeout: '{expected_selector}' never appeared on {url!r}. "
        "Cloudflare may be blocking, or the wiki table structure changed."
    )


async def fetch_raw_html(browser, url: str, expected_selector: str) -> str:
    """Politely visit a URL and return raw HTML after table readiness."""
    logger.info("Politely caching %s", url)
    tab = await browser.get(url)
    await tab.sleep(random.uniform(2.0, 5.0))

    for attempt in range(10):
        html = await tab.get_content()
        soup = BeautifulSoup(html, "html.parser")
        title = soup.find("title")
        if title and "just a moment" in title.get_text().lower():
            logger.debug("[%d/10] Cloudflare challenge pending on %s", attempt + 1, url)
            await tab.sleep(random.uniform(2.0, 4.0))
            continue
        if soup.select(expected_selector):
            return html
        logger.debug("[%d/10] Waiting for %s on %s", attempt + 1, expected_selector, url)
        await tab.sleep(random.uniform(1.5, 3.0))

    raise RuntimeError(f"Timeout: '{expected_selector}' never appeared on {url!r}")


async def cache_url(browser, url: str, destination: Path, expected_selector: str) -> Path:
    """Fetch one page with polite jitter and persist the exact raw HTML."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    html = await fetch_raw_html(browser, url, expected_selector)
    destination.write_text(html, encoding="utf-8")
    logger.info("Cached %s -> %s", url, destination)
    return destination


async def cache_character_pages(browser, character_names: list[str]) -> list[Path]:
    """Cache individual character detail pages under data/raw/characters/."""
    cached = []
    for name in character_names:
        page_title = name.replace(" ", "_")
        url = f"https://anothereden.wiki/w/{quote(page_title)}"
        path = RAW_CHARACTER_DIR / f"{_slugify_title(name)}.html"
        cached.append(await cache_url(browser, url, path, "body"))
    return cached


async def cache_all_raw_pages(include_character_pages: bool = False) -> dict[str, Path]:
    """Cache source wiki HTML locally without parsing it in-memory."""
    browser = await uc.start(
        browser_executable_path=CHROMIUM_PATH,
        headless=False,
        browser_args=["--no-sandbox", "--disable-setuid-sandbox"],
    )
    try:
        selectors = {
            "characters": "tr.character-row-entry",
            "grasta_attack": "tr.grasta-row-entry",
            "grasta_life": "tr.grasta-row-entry",
            "grasta_support": "tr.grasta-row-entry",
            "grasta_special": "tr.grasta-row-entry",
            "grasta_vc": "tr.grasta-row-entry",
            "grasta_ores": "tr.equip-row-entry",
        }
        cached = {}
        for key, url in WIKI_URLS.items():
            cached[key] = await cache_url(browser, url, RAW_PAGE_FILES[key], selectors[key])

        if include_character_pages:
            characters = parse_characters(_read_soup(RAW_PAGE_FILES["characters"]))
            await cache_character_pages(browser, [c.name for c in characters])
        return cached
    finally:
        browser.stop()


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
            "is_SA": tr.get("data-sa", tr.get("data-stellar-awakening", "0")),
        }
        result = parse_character(raw)
        if result is not None:
            rows.append(result)
    return rows


def parse_character_skills(soup: BeautifulSoup, character_name: str) -> list[SkillRow]:
    """Extract best-effort SkillRow instances from one cached character page."""
    skills = []
    selectors = "tr.skill-row-entry, tr[data-skill-name], table.wikitable tr"
    for tr in soup.select(selectors):
        cols = [td.get_text(" ", strip=True) for td in tr.find_all(["td", "th"])]
        name = tr.get("data-skill-name") or (cols[0] if cols and cols[0].lower() != "skill" else "")
        if not name:
            continue
        raw = {
            "character_name": character_name,
            "name": name,
            "multiplier": tr.get("data-multiplier") or (cols[1] if len(cols) > 1 else None),
            "element": tr.get("data-element") or (cols[2] if len(cols) > 2 else None),
        }
        try:
            skills.append(SkillRow.model_validate(raw))
        except Exception as exc:  # noqa: BLE001
            logger.debug("Skipping skill row for %s: %s", character_name, exc)
    return skills


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
    await cache_all_raw_pages(include_character_pages=False)
    return parse_all_from_cache()

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
        headless=False,  # non-headless required — Cloudflare detects headless fingerprint
        browser_args=[
            "--no-sandbox",            # required in WSL2 — kernel lacks user namespaces
            "--disable-setuid-sandbox",
        ],
    )
    try:
        char_soup = await fetch_page(browser, WIKI_URLS["characters"], "tr.character-row-entry")
        attack_soup = await fetch_page(browser, WIKI_URLS["grasta_attack"], "tr.grasta-row-entry")
        life_soup = await fetch_page(browser, WIKI_URLS["grasta_life"], "tr.grasta-row-entry")
        support_soup = await fetch_page(browser, WIKI_URLS["grasta_support"], "tr.grasta-row-entry")
        special_soup = await fetch_page(browser, WIKI_URLS["grasta_special"], "tr.grasta-row-entry")
        vc_soup = await fetch_page(browser, WIKI_URLS["grasta_vc"], "tr.grasta-row-entry")
        ore_soup = await fetch_page(browser, WIKI_URLS["grasta_ores"], "tr.equip-row-entry")
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


def parse_all_from_cache() -> dict:
    """Parse ETL rows only from files in data/raw/.

    This keeps the parse/load phase fully detached from live wiki traffic.
    """
    char_soup = _read_soup(RAW_PAGE_FILES["characters"])
    attack_soup = _read_soup(RAW_PAGE_FILES["grasta_attack"])
    life_soup = _read_soup(RAW_PAGE_FILES["grasta_life"])
    support_soup = _read_soup(RAW_PAGE_FILES["grasta_support"])
    special_soup = _read_soup(RAW_PAGE_FILES["grasta_special"])
    vc_soup = _read_soup(RAW_PAGE_FILES["grasta_vc"])
    ore_soup = _read_soup(RAW_PAGE_FILES["grasta_ores"])

    characters = parse_characters(char_soup)
    for idx, char in enumerate(characters):
        detail_path = RAW_CHARACTER_DIR / f"{_slugify_title(char.name)}.html"
        if detail_path.exists():
            skills = parse_character_skills(_read_soup(detail_path), char.name)
            characters[idx] = char.model_copy(update={"skills": skills})

    grastas = []
    grastas.extend(parse_grastas(attack_soup, "Attack"))
    grastas.extend(parse_grastas(life_soup, "Life"))
    grastas.extend(parse_grastas(support_soup, "Support"))
    grastas.extend(parse_grastas(special_soup, "Special"))
    grastas.extend(parse_vc_grastas(vc_soup))

    ores = parse_ores(ore_soup)
    return {"characters": characters, "grastas": grastas, "ores": ores}
