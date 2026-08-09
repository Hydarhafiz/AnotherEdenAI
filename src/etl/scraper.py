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
import asyncio
import logging
import random
import re
from pathlib import Path
from typing import Optional
from urllib.parse import quote, urljoin

try:
    import nodriver as uc
except ModuleNotFoundError:  # pragma: no cover - exercised only in browserless test envs
    uc = None
from bs4 import BeautifulSoup

from .constants import RAW_CHARACTER_DIR, RAW_DATA_DIR, RAW_PAGE_FILES, WIKI_URLS
from .models import (
    CharacterRow,
    EquipmentRow,
    GrastaRow,
    OreRow,
    PassiveSkillRow,
    SidekickAuraRow,
    SidekickRow,
    SidekickSkillRow,
    SkillRow,
    SuperbossIndexRow,
    SuperbossRow,
    parse_character,
    parse_equipment,
    parse_grasta,
    parse_ore,
)

logger = logging.getLogger(__name__)

# Linux Chromium installed by Playwright. Do NOT use Windows Chrome from /mnt/c/...
# WSL2 CDP communication fails with the Windows binary.
CHROMIUM_PATH = "/home/shogunix/.cache/ms-playwright/chromium-1187/chrome-linux/chrome"


def _slugify_title(title: str) -> str:
    """Convert a wiki title to a stable local HTML filename stem."""
    slug = re.sub(r"[^A-Za-z0-9]+", "_", title.strip()).strip("_").lower()
    return slug or "unknown"


def _wiki_page_title(name: str) -> str:
    """Return the canonical wiki page title for index names with comma aliases."""
    if "," in name:
        return name.rsplit(",", 1)[1].strip()
    return name.strip()


def _read_soup(path: Path) -> BeautifulSoup:
    """Read a cached HTML file into BeautifulSoup."""
    return BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")


async def _stop_browser(browser) -> None:
    """Shut down nodriver cleanly before the event loop exits."""
    if browser is None:
        return
    process = getattr(browser, "_process", None)
    try:
        connection = getattr(browser, "connection", None)
        if connection is not None:
            try:
                await connection.disconnect()
            except Exception:  # noqa: BLE001
                logger.debug("Browser disconnect raised during cleanup", exc_info=True)
    finally:
        try:
            browser.stop()
        finally:
            if process is not None:
                try:
                    await asyncio.wait_for(process.wait(), timeout=5)
                except Exception:  # noqa: BLE001
                    logger.debug("Browser process wait raised during cleanup", exc_info=True)
            # Give nodriver's transport cleanup a chance to run before loop shutdown.
            await asyncio.sleep(0.1)


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


async def fetch_raw_html(
    browser,
    url: str,
    expected_selector: str,
    operator_wait_seconds: int = 20,
) -> tuple[str, dict[str, int | bool]]:
    """Politely visit a URL and return raw HTML plus fetch diagnostics."""
    logger.info("Politely caching %s", url)
    tab = await browser.get(url)
    await tab.sleep(random.uniform(2.0, 5.0))
    saw_cloudflare = False

    for attempt in range(10):
        html = await tab.get_content()
        soup = BeautifulSoup(html, "html.parser")
        title = soup.find("title")
        if title and "just a moment" in title.get_text().lower():
            saw_cloudflare = True
            logger.debug("[%d/10] Cloudflare challenge pending on %s", attempt + 1, url)
            await tab.sleep(random.uniform(2.0, 4.0) + operator_wait_seconds / 10)
            continue
        if soup.select(expected_selector):
            return html, {
                "html_byte_size": len(html.encode("utf-8")),
                "cloudflare_detected": saw_cloudflare,
            }
        logger.debug("[%d/10] Waiting for %s on %s", attempt + 1, expected_selector, url)
        await tab.sleep(random.uniform(1.5, 3.0))

    raise RuntimeError(f"Timeout: '{expected_selector}' never appeared on {url!r}")


async def cache_url(browser, url: str, destination: Path, expected_selector: str) -> Path:
    """Fetch one page with polite jitter and persist the exact raw HTML."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    html, _diagnostics = await fetch_raw_html(browser, url, expected_selector)
    destination.write_text(html, encoding="utf-8")
    logger.info("Cached %s -> %s", url, destination)
    return destination


async def cache_character_pages(browser, character_names: list[str]) -> list[Path]:
    """Cache individual character detail pages under data/raw/characters/."""
    cached = []
    for name in character_names:
        page_title = _wiki_page_title(name).replace(" ", "_")
        url = f"https://anothereden.wiki/w/{quote(page_title, safe='(),')}"
        path = RAW_CHARACTER_DIR / f"{_slugify_title(name)}.html"
        cached.append(await cache_url(browser, url, path, "body"))
    return cached


async def cache_all_raw_pages(include_character_pages: bool = False) -> dict[str, Path]:
    """Cache source wiki HTML locally without parsing it in-memory."""
    if uc is None:
        raise RuntimeError("nodriver is required for live wiki scraping")
    browser = await uc.start(
        browser_executable_path=CHROMIUM_PATH,
        headless=False,
        browser_args=["--no-sandbox", "--disable-setuid-sandbox"],
    )
    try:
        selectors = {
            "characters": "tr.character-row-entry",
            "sidekick": "#Released_Sidekicks",
            "superbosses": "#List_of_Optional_Bosses, table, tr",
            "grasta_attack": "tr.grasta-row-entry",
            "grasta_life": "tr.grasta-row-entry",
            "grasta_support": "tr.grasta-row-entry",
            "grasta_special": "tr.grasta-row-entry",
            "grasta_vc": "tr.grasta-row-entry",
            "grasta_ores": "tr.equip-row-entry",
            "weapons": "tr.equip-row-entry",
            "armor": "tr.equip-row-entry",
        }
        cached = {}
        for key, url in WIKI_URLS.items():
            cached[key] = await cache_url(browser, url, RAW_PAGE_FILES[key], selectors[key])

        if include_character_pages:
            characters = parse_characters(_read_soup(RAW_PAGE_FILES["characters"]))
            await cache_character_pages(browser, [c.name for c in characters])
        return cached
    finally:
        await _stop_browser(browser)


# ---------------------------------------------------------------------------
# Parse functions — UNCHANGED from original httpx implementation.
# These operate on BeautifulSoup objects regardless of how the HTML was fetched.
# ---------------------------------------------------------------------------

def parse_characters(soup: BeautifulSoup) -> list[CharacterRow]:
    """Extract CharacterRow instances from a parsed Characters wiki page."""
    rows = []
    for tr in soup.select("tr.character-row-entry"):
        if tr.get("data-accessory", "").strip().lower() == "sidekick":
            continue
        # Upcoming-content placeholders have no usable combat-detail page.
        if tr.get("data-released", "").strip() == "1":
            continue
        detail_link = tr.select_one('a[href^="/w/"]')
        raw = {
            "name": tr.get("data-name", ""),
            "element": tr.get("data-element", ""),
            "weapon": tr.get("data-weapon", ""),
            "light_shadow": tr.get("data-type", ""),
            "personalities": tr.get("data-personality", ""),
            "detail_url": urljoin("https://anothereden.wiki", detail_link.get("href")) if detail_link else None,
            "is_SA": tr.get("data-sa", tr.get("data-stellar-awakening", "0")),
        }
        result = parse_character(raw)
        if result is not None:
            rows.append(result)
    return rows


def parse_sidekick_index(soup: BeautifulSoup) -> list[SidekickRow]:
    """Extract sidekick discovery rows from the Sidekick index page."""
    rows = []
    for tr in soup.select("tr.character-row-entry"):
        is_sidekick = (
            tr.get("data-sidekick", "").strip() == "1"
            or tr.get("data-accessory", "").strip().lower() == "sidekick"
        )
        if not is_sidekick:
            continue
        detail_link = tr.select_one('a[href^="/w/"]')
        name = _clean_cell_text(tr.get("data-name", ""))
        if not name:
            continue
        raw = {
            "name": name,
            "source_url": urljoin("https://anothereden.wiki", detail_link.get("href")) if detail_link else (
                f"https://anothereden.wiki/w/{quote(_wiki_page_title(name).replace(' ', '_'), safe='(),')}"
            ),
            "rarity": _clean_cell_text(tr.get("data-rarity", "")) or None,
        }
        try:
            rows.append(SidekickRow.model_validate(raw))
        except Exception as exc:  # noqa: BLE001
            logger.debug("Skipping sidekick index row %s: %s", name, exc)
    if rows:
        return rows

    released_heading = soup.select_one("#Released_Sidekicks")
    if released_heading is None:
        return rows

    seen: set[str] = set()
    for card in released_heading.find_all_next("div", class_="sidekick-head"):
        previous_heading = card.find_previous("h2")
        if previous_heading and previous_heading.select_one(".mw-headline") is not released_heading:
            continue
        name_link = card.select_one(".sidekick-name a[href^='/w/']")
        if not name_link:
            continue
        href = name_link.get("href", "")
        title = _clean_cell_text(name_link.get("title") or name_link.get_text(" ", strip=True))
        if not href.startswith("/w/") or not title or title in seen:
            continue
        name_text = _clean_cell_text(card.select_one(".sidekick-name").get_text(" ", strip=True))
        rarity_match = re.search(r"\(([^)]*★[^)]*)\)", name_text)
        associated_character_names = [
            _clean_cell_text(link.get("title") or link.get_text(" ", strip=True))
            for link in card.select(".sidekick-owner a[href^='/w/']")
        ]
        raw = {
            "name": title,
            "source_url": urljoin("https://anothereden.wiki", href),
            "rarity": rarity_match.group(1) if rarity_match else None,
            "associated_character_names": [name for name in associated_character_names if name],
        }
        try:
            rows.append(SidekickRow.model_validate(raw))
            seen.add(title)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Skipping sidekick card row %s: %s", title, exc)
    if rows:
        return rows

    for node in released_heading.find_all_next():
        if node.name == "h2" and node.select_one(".mw-headline") is not released_heading:
            break
        if node.name != "a":
            continue
        href = node.get("href", "")
        title = _clean_cell_text(node.get("title") or node.get_text(" ", strip=True))
        if not href.startswith("/w/") or not title:
            continue
        if ":" in title or title.lower().startswith(("image", "file", "category")):
            continue
        if title in seen:
            continue
        parent_text = _clean_cell_text(node.parent.get_text(" ", strip=True)) if node.parent else ""
        rarity_match = re.search(r"\(([^)]*★[^)]*)\)", parent_text)
        raw = {
            "name": title,
            "source_url": urljoin("https://anothereden.wiki", href),
            "rarity": rarity_match.group(1) if rarity_match else None,
        }
        try:
            rows.append(SidekickRow.model_validate(raw))
            seen.add(title)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Skipping sidekick link row %s: %s", title, exc)
    return rows


def parse_superboss_index(soup: BeautifulSoup) -> list[SuperbossIndexRow]:
    """Extract weak superboss discovery rows from the canonical Superbosses index."""
    rows: list[SuperbossIndexRow] = []
    seen: set[str] = set()
    for tr in soup.find_all("tr"):
        cells = tr.find_all(["td", "th"])
        if len(cells) < 4:
            continue
        difficulty_tier = _clean_cell_text(cells[0].get_text(" ", strip=True))
        if not re.fullmatch(r"\d+(?:\.\d+)?", difficulty_tier):
            continue
        name_cell = cells[1]
        link = name_cell.select_one('a[href^="/w/"]')
        raw_name = _clean_cell_text(
            (link.get("title") if link else None)
            or name_cell.get_text(" ", strip=True).split("/")[0]
        )
        if not raw_name:
            continue
        canonical_name = _clean_boss_name(raw_name)
        if canonical_name not in {_clean_boss_name(name) for name in CURATED_WEAK_SUPERBOSS_NAMES}:
            continue
        source_url = CURATED_WEAK_SUPERBOSS_URL_OVERRIDES.get(raw_name) or CURATED_WEAK_SUPERBOSS_URL_OVERRIDES.get(canonical_name)
        if source_url is None and link:
            source_url = urljoin("https://anothereden.wiki", link.get("href"))
        if source_url is None:
            continue
        raw = {
            "name": canonical_name,
            "source_url": source_url,
            "difficulty_tier": difficulty_tier,
            "level": _boss_level_from_tier(difficulty_tier),
            "refight_status": _clean_cell_text(cells[2].get_text(" ", strip=True)) or None,
            "version": _clean_cell_text(cells[3].get_text(" ", strip=True)) or None,
            "characteristics": _clean_cell_text(" ".join(cell.get_text(" ", strip=True) for cell in cells[4:])),
        }
        try:
            row = SuperbossIndexRow.model_validate(raw)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Skipping superboss index row %s: %s", raw_name, exc)
            continue
        if row.name not in seen:
            rows.append(row)
            seen.add(row.name)
    return rows


def _fragment_section_nodes(soup: BeautifulSoup, source_url: str):
    fragment = source_url.rsplit("#", 1)[1] if "#" in source_url else ""
    if not fragment:
        return []
    anchor = soup.find(id=fragment) or soup.find("span", id=fragment)
    if anchor is None:
        return []
    heading = anchor.find_parent(["h2", "h3", "h4"]) or anchor
    heading_rank = int(heading.name[1]) if getattr(heading, "name", "").startswith("h") else 2
    nodes = []
    sibling = heading.find_next_sibling()
    while sibling is not None:
        if sibling.name in {"h2", "h3", "h4"} and int(sibling.name[1]) <= heading_rank:
            break
        nodes.append(sibling)
        sibling = sibling.find_next_sibling()
    return nodes


def _boss_search_nodes(soup: BeautifulSoup, source_url: str):
    section_nodes = _fragment_section_nodes(soup, source_url)
    if section_nodes:
        return section_nodes
    content = soup.select_one("#mw-content-text") or soup.select_one("main") or soup.body or soup
    return list(content.find_all(["table", "p", "ul", "ol", "article", "div"], recursive=True))


def _extract_labeled_boss_fields(nodes) -> dict[str, str]:
    fields: dict[str, str] = {}
    label_map = {
        "hp": "hp",
        "weak": "weak",
        "weakness": "weak",
        "resist": "resist",
        "resistance": "resist",
        "null": "null",
        "immune": "null",
        "absorb": "absorb",
    }
    for node in nodes:
        for tr in node.find_all("tr") if hasattr(node, "find_all") else []:
            cells = tr.find_all(["th", "td"])
            if len(cells) < 2:
                continue
            label = _clean_cell_text(cells[0].get_text(" ", strip=True)).lower().strip(":")
            for needle, field in label_map.items():
                if needle in label:
                    fields.setdefault(field, _cell_text_with_media(cells[1]))
                    break
    return fields


def _boss_mechanics_text(nodes, fallback_soup: BeautifulSoup) -> str:
    parts: list[str] = []
    allowed_terms = re.compile(
        r"skill|move|action|turn|hp|weak|resist|null|absorb|battle|strategy|stopper|summon|"
        r"barrier|damage|buff|debuff|af|zone|attack|condition|mechanic|chance encounter",
        flags=re.IGNORECASE,
    )
    for node in nodes:
        if not hasattr(node, "get_text"):
            continue
        text = _clean_cell_text(_cell_text_with_media(node))
        if len(text) < 20:
            continue
        if allowed_terms.search(text):
            parts.append(text)
    if not parts:
        content = fallback_soup.select_one("#mw-content-text") or fallback_soup.body or fallback_soup
        text = _clean_cell_text(content.get_text(" ", strip=True))
        parts.append(text)
    return _clean_cell_text(" ".join(parts))[:5000]


def parse_superboss_detail(
    soup: BeautifulSoup,
    candidate: SuperbossIndexRow,
    source_url: str | None = None,
) -> SuperbossRow:
    """Parse a curated superboss detail page into a RAG-grounded graph row."""
    source_url = source_url or candidate.source_url
    nodes = _boss_search_nodes(soup, source_url)
    fields = _extract_labeled_boss_fields(nodes)
    mechanics_text = _boss_mechanics_text(nodes, soup)
    raw = {
        "name": candidate.name,
        "source_url": source_url,
        "difficulty_tier": candidate.difficulty_tier,
        "level": candidate.level,
        "hp": fields.get("hp"),
        "weak": _split_boss_values(fields.get("weak")),
        "resist": _split_boss_values(fields.get("resist")),
        "null": _split_boss_values(fields.get("null")),
        "absorb": _split_boss_values(fields.get("absorb")),
        "characteristics": candidate.characteristics,
        "mechanic_tags": _mechanic_tags(candidate.characteristics, mechanics_text),
        "mechanics_text": mechanics_text,
    }
    return SuperbossRow.model_validate(raw)


def character_has_stellar_awakened(soup: BeautifulSoup) -> bool:
    """Detect Stellar Awakening availability from a character detail page."""
    for article in soup.select("article[title]"):
        if "stellar awaken" in article.get("title", "").lower():
            return True
    for heading in soup.find_all(["h2", "h3", "h4"]):
        text = heading.get_text(" ", strip=True).lower()
        if "stellar awaken" in text:
            return True
    return bool(soup.select('[id*="Stellar_Awaken"], [data-section*="Stellar"]'))


def _clean_cell_text(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip()


def _clean_boss_name(value: str) -> str:
    return _clean_cell_text(value).replace("♀", "").replace("♂", "").strip()


def _cell_text_with_media(cell) -> str:
    parts = [cell.get_text(" ", strip=True)]
    for media in cell.select("img[alt], img[title], a[title]"):
        parts.append(media.get("alt") or media.get("title") or "")
    return _clean_cell_text(" ".join(part for part in parts if part))


def _boss_level_from_tier(difficulty_tier: str | None) -> int | None:
    if not difficulty_tier:
        return None
    match = re.search(r"\d+", difficulty_tier)
    return int(match.group(0)) if match else None


def _split_boss_values(value: str | None) -> list[str]:
    text = _clean_cell_text(value)
    if not text:
        return ["unknown"]
    values = [
        _clean_cell_text(part)
        for part in re.split(r"[,;/|・]+|\band\b", text, flags=re.IGNORECASE)
        if _clean_cell_text(part)
    ]
    return values or ["unknown"]


def _mechanic_tags(characteristics: str, mechanics_text: str) -> list[str]:
    text = f"{characteristics} {mechanics_text}".lower()
    candidates = {
        "af seal": ["af seal", "another force seal", "af sealed"],
        "barrier": ["barrier"],
        "buff/debuff reset": ["buff debuff reset", "buff/debuff reset", "buff and debuff reset"],
        "companion summon": ["summon companion", "summon companions", "summons companion", "summons companions", "companion summon"],
        "fixed damage": ["fixed damage", "percentage damage"],
        "high firepower": ["high firepower", "high damage"],
        "hp stopper": ["stopper"],
        "long battle": ["long battle", "endurance battle"],
        "resistance change": ["resistance change", "weakness change"],
        "status ailment": ["status ailment", "status abnormal", "poison", "stun", "seal"],
    }
    return sorted(tag for tag, needles in candidates.items() if any(needle in text for needle in needles))


CURATED_WEAK_SUPERBOSS_NAMES = {
    "Zennon Ogre's Shadow",
    "Flame Eater",
    "Flame Eater ♀",
    "Nameless Girl",
    "Mimi",
    "Cradle System",
    "Insula Ventorum",
}

CURATED_WEAK_SUPERBOSS_URL_OVERRIDES = {
    "Flame Eater": "https://anothereden.wiki/w/Gariyu_(Chance_Encounter)#Flame_Eater",
    "Flame Eater ♀": "https://anothereden.wiki/w/Gariyu_(Chance_Encounter)#Flame_Eater",
}


def _table_headers(tr) -> list[str]:
    table = tr.find_parent("table")
    if not table:
        return []
    header_row = table.find("tr")
    if not header_row:
        return []
    return [_clean_cell_text(cell.get_text(" ", strip=True)).lower() for cell in header_row.find_all(["th", "td"])]


def _section_for_row(tr) -> str | None:
    for previous in tr.find_all_previous(["h2", "h3", "h4"], limit=1):
        headline = previous.get_text(" ", strip=True)
        if headline:
            return headline
    return None


def _row_is_stellar_gated(tr, section: str | None) -> bool:
    marker = " ".join(
        value
        for value in [
            tr.get("data-sa", ""),
            tr.get("data-stellar", ""),
            tr.get("data-stellar-awakened", ""),
            section or "",
            tr.get_text(" ", strip=True),
        ]
        if value
    ).lower()
    return "stellar awaken" in marker or "stellar awakened" in marker


def _value_for(headers: list[str], cols: list[str], names: set[str]) -> str | None:
    for idx, header in enumerate(headers):
        if idx < len(cols) and any(name in header for name in names):
            return cols[idx]
    return None


def _looks_like_passive(section: str | None, headers: list[str], cols: list[str], tr) -> bool:
    marker = " ".join([section or "", " ".join(headers), " ".join(cols[:2]), " ".join(tr.get("class", []))]).lower()
    passive_terms = {
        "passive",
        "ability",
        "abilities",
        "stance",
        "zone",
        "battle start",
        "battle-start",
        "stack",
        "valor chant",
        "stellar awakening passive",
    }
    active_terms = {"mp", "skill", "type", "element", "basic attack"}
    if any(term in marker for term in passive_terms):
        return True
    return not any(term in marker for term in active_terms)


def _passive_type(section: str | None, description: str) -> str | None:
    text = f"{section or ''} {description}".lower()
    for passive_type in ["zone", "stance", "stack", "battle-start", "stellar awakening", "valor chant", "passive"]:
        if passive_type in text:
            return passive_type
    return None


def _article_title(node) -> str | None:
    article = node.find_parent("article")
    if article and article.get("title"):
        return article.get("title")
    return None


def _first_text(node, selector: str) -> str:
    found = node.select_one(selector)
    return _clean_cell_text(found.get_text(" ", strip=True)) if found else ""


def _description_text(container) -> str:
    description = container.select_one(".skill-description")
    return _clean_cell_text(description.get_text(" ", strip=True)) if description else ""


def _sidekick_skill_kind(description: str) -> str | None:
    text = description.lower()
    if "aura" in text and "activation condition" in text:
        return "aura"
    if "charged" in text or "consumes" in text and "charge" in text:
        return "charge"
    if "auto" in text:
        return "auto"
    return None


def _sidekick_charge_cost(description: str, mp_text: str) -> int | None:
    match = re.search(r"consumes\s+(\d+)\s+charge", description, flags=re.IGNORECASE)
    if match:
        return int(match.group(1))
    return SidekickSkillRow.coerce_charge_cost(mp_text)


def _aura_condition(description: str) -> str | None:
    parts = re.split(r"activation condition:\s*", description, maxsplit=1, flags=re.IGNORECASE)
    if len(parts) != 2:
        return None
    condition = re.split(
        r"\s+(?:Damage dealt|Inflicted Damage|All party|Power|Intelligence|Type resistance|Physical resistance|Magic resistance)\b",
        parts[1],
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    if condition:
        return _clean_cell_text(condition)
    return None


def _associated_characters_from_descriptions(soup: BeautifulSoup) -> list[str]:
    names: set[str] = set()
    for description in soup.select(".skill-description"):
        text = description.get_text(" ", strip=True)
        if " is at front" not in text and " at front" not in text:
            continue
        for link in description.select('a[href^="/w/"]'):
            href = link.get("href", "")
            title = _clean_cell_text(link.get("title") or link.get_text(" ", strip=True))
            if href == "/w/Turn_Order" or title in {"Aura", "Auto", "Charged", "Charge", "Turn Order"}:
                continue
            if title:
                names.add(title)
    return sorted(names)


GOLDEN_SIDEKICK_ASSOCIATIONS = {
    "Tetra (Another Style)": ["Minalca (Another Style)"],
}


def parse_sidekick_detail(
    soup: BeautifulSoup,
    sidekick: SidekickRow,
    source_url: str | None = None,
) -> SidekickRow:
    """Parse structured sidekick abilities and association facts from a detail page."""
    source_url = source_url or sidekick.source_url
    auto_skills: list[SidekickSkillRow] = []
    charge_skills: list[SidekickSkillRow] = []
    auras: list[SidekickAuraRow] = []
    unknown_sections: list[str] = []

    for container in soup.select("div.character-skill-grid-container"):
        name = _first_text(container, ".skill-name")
        description = _description_text(container)
        if not name or name.lower() == "skill name" or not description:
            continue
        section = _article_title(container) or _section_for_row(container)
        kind = _sidekick_skill_kind(description)
        if kind == "aura":
            try:
                auras.append(
                    SidekickAuraRow.model_validate(
                        {
                            "sidekick_name": sidekick.name,
                            "name": name,
                            "activation_condition": _aura_condition(description),
                            "effect_text": description,
                            "source_url": source_url,
                            "section": section,
                        }
                    )
                )
            except Exception as exc:  # noqa: BLE001
                logger.debug("Skipping aura row for %s: %s", sidekick.name, exc)
        elif kind in {"auto", "charge"}:
            raw = {
                "sidekick_name": sidekick.name,
                "name": name,
                "skill_kind": kind,
                "element": _first_text(container, ".character-skill-element-type .upper-grid"),
                "skill_type": _first_text(container, ".character-skill-element-type .lower-grid"),
                "charge_cost": _sidekick_charge_cost(description, _first_text(container, ".character-skill-mp")),
                "description": description,
                "source_url": source_url,
                "section": section,
            }
            try:
                skill = SidekickSkillRow.model_validate(raw)
            except Exception as exc:  # noqa: BLE001
                logger.debug("Skipping sidekick skill row for %s: %s", sidekick.name, exc)
                continue
            if kind == "auto":
                auto_skills.append(skill)
            else:
                charge_skills.append(skill)
        else:
            unknown_sections.append(f"{section or 'Unknown'}: {name} - {description}")

    associations = set(sidekick.associated_character_names)
    associations.update(_associated_characters_from_descriptions(soup))
    associations.update(GOLDEN_SIDEKICK_ASSOCIATIONS.get(sidekick.name, []))

    acquisition_parts = []
    for heading in soup.find_all(["h2", "h3"]):
        heading_text = heading.get_text(" ", strip=True)
        if "encounter" not in heading_text.lower():
            continue
        sibling = heading.find_next_sibling()
        while sibling is not None and sibling.name not in {"h2", "h3"}:
            if sibling.name in {"p", "ul"}:
                text = _clean_cell_text(sibling.get_text(" ", strip=True))
                if text:
                    acquisition_parts.append(text)
            sibling = sibling.find_next_sibling()

    return sidekick.model_copy(
        update={
            "source_url": source_url,
            "acquisition_text": _clean_cell_text(" ".join(acquisition_parts)) or sidekick.acquisition_text,
            "associated_character_names": sorted(associations),
            "diagnostics_text": "\n".join(unknown_sections) or sidekick.diagnostics_text,
            "auto_skills": auto_skills,
            "charge_skills": charge_skills,
            "auras": auras,
        }
    )


def _parse_skill_grid(soup: BeautifulSoup, character_name: str, source_url: str | None) -> list[SkillRow]:
    skills = []
    for container in soup.select("article[title*='Skills'] div.character-skill-grid-container"):
        name = _first_text(container, ".skill-name")
        description = _first_text(container, ".skill-description")
        if not name or name.lower() == "skill name" or not description:
            continue
        section = _article_title(container) or _section_for_row(container)
        raw = {
            "character_name": character_name,
            "name": name,
            "element": _first_text(container, ".character-skill-element-type .upper-grid"),
            "skill_type": _first_text(container, ".character-skill-element-type .lower-grid"),
            "mp": _first_text(container, ".character-skill-mp"),
            "description": description,
            "multiplier": _first_text(container, ".skill-mod"),
            "source_url": source_url,
            "section": section,
            "requires_stellar_awakened": _row_is_stellar_gated(container, section),
        }
        try:
            skills.append(SkillRow.model_validate(raw))
        except Exception as exc:  # noqa: BLE001
            logger.debug("Skipping skill grid row for %s: %s", character_name, exc)
    return skills


def parse_character_skills(
    soup: BeautifulSoup,
    character_name: str,
    source_url: str | None = None,
) -> list[SkillRow]:
    """Extract active SkillRow instances from one cached character page."""
    grid_skills = _parse_skill_grid(soup, character_name, source_url)
    if grid_skills:
        return grid_skills

    skills = []
    selectors = "tr.skill-row-entry, tr[data-skill-name]"
    for tr in soup.select(selectors):
        cols = [td.get_text(" ", strip=True) for td in tr.find_all(["td", "th"])]
        headers = _table_headers(tr)
        section = _section_for_row(tr)
        if _looks_like_passive(section, headers, cols, tr):
            continue
        name = tr.get("data-skill-name") or (cols[0] if cols and cols[0].lower() != "skill" else "")
        if not name:
            continue
        description = (
            tr.get("data-description")
            or _value_for(headers, cols, {"description", "effect"})
            or (cols[-1] if len(cols) > 1 else "")
        )
        raw = {
            "character_name": character_name,
            "name": _clean_cell_text(name),
            "element": tr.get("data-element") or _value_for(headers, cols, {"element", "attribute"}),
            "skill_type": tr.get("data-type") or _value_for(headers, cols, {"type", "attack type"}),
            "mp": tr.get("data-mp") or _value_for(headers, cols, {"mp"}),
            "description": _clean_cell_text(description),
            "multiplier": tr.get("data-multiplier") or _value_for(headers, cols, {"multiplier", "mod"}),
            "source_url": source_url,
            "section": section,
            "requires_stellar_awakened": _row_is_stellar_gated(tr, section),
        }
        try:
            skills.append(SkillRow.model_validate(raw))
        except Exception as exc:  # noqa: BLE001
            logger.debug("Skipping skill row for %s: %s", character_name, exc)
    return skills


def parse_character_passive_skills(
    soup: BeautifulSoup,
    character_name: str,
    source_url: str | None = None,
) -> list[PassiveSkillRow]:
    """Extract passive and non-executable mechanics from one cached character page."""
    passives = []
    for stance in soup.select("article[title='Stances/Zones'] div.character-stance"):
        name = _first_text(stance, ".stance-title-name a") or _first_text(stance, ".stance-title-name")
        description_parts = [
            _first_text(stance, ".stance-row-properties"),
            _first_text(stance, ".stance-row-af"),
            _first_text(stance, ".stance-row-end"),
        ]
        description = _clean_cell_text(" ".join(part for part in description_parts if part))
        if name and description:
            raw = {
                "character_name": character_name,
                "name": name,
                "description": description,
                "source_url": source_url,
                "section": "Stances/Zones",
                "passive_type": "zone",
                "requires_stellar_awakened": _row_is_stellar_gated(stance, "Stances/Zones"),
            }
            try:
                passives.append(PassiveSkillRow.model_validate(raw))
            except Exception as exc:  # noqa: BLE001
                logger.debug("Skipping stance row for %s: %s", character_name, exc)

    selectors = "tr.passive-row-entry, tr[data-passive-name]"
    for tr in soup.select(selectors):
        cols = [td.get_text(" ", strip=True) for td in tr.find_all(["td", "th"])]
        headers = _table_headers(tr)
        section = _section_for_row(tr)
        if not _looks_like_passive(section, headers, cols, tr):
            continue
        name = tr.get("data-passive-name") or (cols[0] if cols and cols[0].lower() not in {"skill", "name"} else "")
        if not name:
            continue
        description = (
            tr.get("data-description")
            or _value_for(headers, cols, {"description", "effect"})
            or (cols[-1] if len(cols) > 1 else "")
        )
        raw = {
            "character_name": character_name,
            "name": _clean_cell_text(name),
            "description": _clean_cell_text(description),
            "source_url": source_url,
            "section": section,
            "passive_type": tr.get("data-passive-type") or _passive_type(section, description or ""),
            "requires_stellar_awakened": _row_is_stellar_gated(tr, section),
        }
        try:
            passives.append(PassiveSkillRow.model_validate(raw))
        except Exception as exc:  # noqa: BLE001
            logger.debug("Skipping passive row for %s: %s", character_name, exc)
    return passives


def _classify_grasta_acquisition(obtain_text: str, tier: int) -> tuple[str, int | None]:
    if "\u221e" in obtain_text or re.search(r"\b(?:unlimited|repeatable)\b", obtain_text, re.IGNORECASE):
        return "repeatable", None
    count_match = re.match(r"^(\d+)\s*[:x]", obtain_text.strip())
    if count_match:
        count = int(count_match.group(1))
        return ("unique" if count == 1 else "finite"), count
    if tier == 3:
        return "unique", 1
    return "unknown", None


def parse_grastas(soup: BeautifulSoup, category: str) -> list[GrastaRow]:
    """Extract exact, compatibility-aware Grasta variants from a wiki page."""
    rows = []
    weapon_aliases = {
        "staff": "Staff", "sword": "Sword", "katana": "Katana",
        "ax": "Axe", "lance": "Spear", "bow": "Bow",
        "fists": "Fist", "hammer": "Hammer",
    }
    for tr in soup.select("tr.grasta-row-entry"):
        cols = tr.find_all("td")
        if len(cols) < 4:
            logger.warning("Skipping grasta row with too few columns: %s", tr)
            continue
        personality_raw = tr.get("data-personality") or None
        weapon_group = [
            display for attribute, display in weapon_aliases.items()
            if tr.get(f"data-{attribute}", "0") == "1"
        ]
        tier = int(tr.get("data-tier", 0))
        obtain_text = cols[5].get_text(" ", strip=True) if len(cols) > 5 else ""
        acquisition_class, max_copies = _classify_grasta_acquisition(obtain_text, tier)
        raw = {
            "name": tr.get("data-name", ""),
            "category": category,
            "tier": tier,
            "stats": cols[3].get_text(" ", strip=True),
            "personality_req": personality_raw,
            "weapon_req": weapon_group[0] if len(weapon_group) == 1 else None,
            "weapon_group": weapon_group,
            "is_shareable": tr.get("data-share", "0"),
            "source_url": WIKI_URLS[f"grasta_{category.lower()}"],
            "effect_text": cols[4].get_text(" ", strip=True) if len(cols) > 4 else "",
            "obtain_text": obtain_text,
            "acquisition_class": acquisition_class,
            "max_theoretical_copies": max_copies,
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
            "source_url": WIKI_URLS["grasta_vc"],
            "source_variant": tr.get("data-name", ""),
            "effect_text": cols[4].get_text(" ", strip=True) if len(cols) > 4 else "",
            "obtain_text": cols[5].get_text(" ", strip=True) if len(cols) > 5 else "",
            "acquisition_class": "unique",
            "max_theoretical_copies": 1,
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


def _value_for_any(headers: list[str], cols: list[str], names: set[str]) -> str:
    normalized_names = {name.lower() for name in names}
    for idx, header in enumerate(headers):
        normalized_header = header.lower().strip()
        if normalized_header in normalized_names and idx < len(cols):
            return cols[idx]
    for idx, header in enumerate(headers):
        normalized_header = header.lower().strip()
        if any(name in normalized_header for name in normalized_names) and idx < len(cols):
            return cols[idx]
    return ""


def parse_equipment_index(soup: BeautifulSoup, equipment_slot: str, source_url: str) -> list[EquipmentRow]:
    """Extract baseline Weapon/Armor rows from a wiki equipment index."""
    rows = []
    for tr in soup.select("tr.equip-row-entry"):
        cells = tr.find_all(["td", "th"])
        if len(cells) < 2:
            logger.warning("Skipping equipment row with too few columns: %s", tr)
            continue

        cols = [_clean_cell_text(cell.get_text(" ", strip=True)) for cell in cells]
        headers = _table_headers(tr)
        name = (
            _clean_cell_text(tr.get("data-name", ""))
            or _value_for_any(headers, cols, {"name", "weapon", "armor", "equipment"})
            or (cols[1] if len(cols) > 1 else cols[0])
        )
        category = (
            _clean_cell_text(tr.get("data-type", ""))
            or _clean_cell_text(tr.get("data-category", ""))
            or _value_for_any(headers, cols, {"type", "category", "weapon type", "armor type"})
        )
        level = (
            tr.get("data-level")
            or tr.get("data-lv")
            or _value_for_any(headers, cols, {"level", "lv", "tier"})
        )
        attack = tr.get("data-atk") or _value_for_any(headers, cols, {"atk", "attack"})
        magic_attack = (
            tr.get("data-matk")
            or tr.get("data-m_atk")
            or _value_for_any(headers, cols, {"matk", "m.atk", "magic attack"})
        )
        defense = tr.get("data-def") or _value_for_any(headers, cols, {"def", "defense"})
        magic_defense = (
            tr.get("data-mdef")
            or tr.get("data-m_def")
            or _value_for_any(headers, cols, {"mdef", "m.def", "magic defense"})
        )
        effect_text = (
            _clean_cell_text(tr.get("data-effect", ""))
            or _value_for_any(headers, cols, {"effect", "ability", "bonus"})
        )
        obtain_text = (
            _clean_cell_text(tr.get("data-source", ""))
            or _clean_cell_text(tr.get("data-obtain", ""))
            or _value_for_any(headers, cols, {"source", "obtain", "obtained", "location", "how to obtain"})
        )
        raw = {
            "name": name,
            "equipment_slot": equipment_slot,
            "category": category or None,
            "level": level,
            "attack": attack if equipment_slot == "weapon" else None,
            "magic_attack": magic_attack if equipment_slot == "weapon" else None,
            "defense": defense if equipment_slot == "armor" else None,
            "magic_defense": magic_defense if equipment_slot == "armor" else None,
            "effect_text": effect_text,
            "obtain_text": obtain_text,
            "source_url": source_url,
        }
        result = parse_equipment(raw)
        if result is not None:
            rows.append(result)
    return rows


async def scrape_all() -> dict:
    from .pipeline import prepare_parsed_data

    data, _manifest = await prepare_parsed_data()
    return data

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
        weapon_soup = await fetch_page(browser, WIKI_URLS["weapons"], "tr.equip-row-entry")
        armor_soup = await fetch_page(browser, WIKI_URLS["armor"], "tr.equip-row-entry")
    finally:
        await _stop_browser(browser)

    characters = parse_characters(char_soup)

    grastas = []
    grastas.extend(parse_grastas(attack_soup, "Attack"))
    grastas.extend(parse_grastas(life_soup, "Life"))
    grastas.extend(parse_grastas(support_soup, "Support"))
    grastas.extend(parse_grastas(special_soup, "Special"))
    grastas.extend(parse_vc_grastas(vc_soup))

    ores = parse_ores(ore_soup)
    equipment = [
        *parse_equipment_index(weapon_soup, "weapon", WIKI_URLS["weapons"]),
        *parse_equipment_index(armor_soup, "armor", WIKI_URLS["armor"]),
    ]

    logger.info(
        "Scraped %d characters, %d grastas, %d ores, %d equipment rows",
        len(characters), len(grastas), len(ores), len(equipment),
    )

    return {"characters": characters, "grastas": grastas, "ores": ores, "equipment": equipment}


def parse_all_from_cache() -> dict:
    """Parse ETL rows only from files in data/raw/.

    This keeps the parse/load phase fully detached from live wiki traffic.
    """
    char_soup = _read_soup(RAW_PAGE_FILES["characters"])
    sidekick_soup = _read_soup(RAW_PAGE_FILES["sidekick"])
    superboss_soup = _read_soup(RAW_PAGE_FILES["superbosses"])
    attack_soup = _read_soup(RAW_PAGE_FILES["grasta_attack"])
    life_soup = _read_soup(RAW_PAGE_FILES["grasta_life"])
    support_soup = _read_soup(RAW_PAGE_FILES["grasta_support"])
    special_soup = _read_soup(RAW_PAGE_FILES["grasta_special"])
    vc_soup = _read_soup(RAW_PAGE_FILES["grasta_vc"])
    ore_soup = _read_soup(RAW_PAGE_FILES["grasta_ores"])
    weapon_soup = _read_soup(RAW_PAGE_FILES["weapons"])
    armor_soup = _read_soup(RAW_PAGE_FILES["armor"])

    characters = parse_characters(char_soup)
    sidekicks = parse_sidekick_index(sidekick_soup)
    superbosses = []
    for candidate in parse_superboss_index(superboss_soup):
        detail_path = RAW_DATA_DIR / "superbosses" / f"{_slugify_title(candidate.name)}.html"
        if detail_path.exists():
            detail_soup = _read_soup(detail_path)
            superbosses.append(parse_superboss_detail(detail_soup, candidate, source_url=candidate.source_url))
    for idx, char in enumerate(characters):
        detail_path = RAW_CHARACTER_DIR / f"{_slugify_title(char.name)}.html"
        if detail_path.exists():
            detail_soup = _read_soup(detail_path)
            skills = parse_character_skills(detail_soup, char.name)
            passive_skills = parse_character_passive_skills(detail_soup, char.name)
            is_sa = char.is_SA or character_has_stellar_awakened(detail_soup)
            characters[idx] = char.model_copy(
                update={"skills": skills, "passive_skills": passive_skills, "is_SA": is_sa}
            )

    grastas = []
    grastas.extend(parse_grastas(attack_soup, "Attack"))
    grastas.extend(parse_grastas(life_soup, "Life"))
    grastas.extend(parse_grastas(support_soup, "Support"))
    grastas.extend(parse_grastas(special_soup, "Special"))
    grastas.extend(parse_vc_grastas(vc_soup))

    ores = parse_ores(ore_soup)
    equipment = [
        *parse_equipment_index(weapon_soup, "weapon", WIKI_URLS["weapons"]),
        *parse_equipment_index(armor_soup, "armor", WIKI_URLS["armor"]),
    ]
    return {
        "characters": characters,
        "sidekicks": sidekicks,
        "superbosses": superbosses,
        "grastas": grastas,
        "ores": ores,
        "equipment": equipment,
    }
