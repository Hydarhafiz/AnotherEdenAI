import os
from pathlib import Path

SCHEMA_VERSION = "1.0.0"
ETL_SCHEMA_VERSION = os.getenv("ETL_SCHEMA_VERSION", SCHEMA_VERSION)


def _env_flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


ETL_MODE = os.getenv("ETL_MODE", "strict")
STRICT = ETL_MODE == "strict"

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_AUTH = tuple(os.getenv("NEO4J_AUTH", "neo4j/anothereden").split("/", 1))

WIKI_URLS = {
    "characters": "https://anothereden.wiki/w/Characters",
    "sidekick": "https://anothereden.wiki/w/Sidekick",
    "superbosses": "https://anothereden.wiki/w/Superbosses",
    "grasta_attack": "https://anothereden.wiki/w/Grasta_Attack",
    "grasta_life": "https://anothereden.wiki/w/Grasta_Life",
    "grasta_support": "https://anothereden.wiki/w/Grasta_Support",
    "grasta_special": "https://anothereden.wiki/w/Grasta_Special",
    "grasta_vc": "https://anothereden.wiki/w/Grasta_VC",
    "grasta_ores": "https://anothereden.wiki/w/Grasta_Ores",
    "weapons": "https://anothereden.wiki/w/Weapons",
    "armor": "https://anothereden.wiki/w/Armor",
}

GRASTA_CATEGORIES = ["Attack", "Life", "Support", "Special", "VC"]

RAW_DATA_DIR = Path(os.getenv("RAW_DATA_DIR", "data/raw"))
PARSED_DATA_DIR = Path(os.getenv("PARSED_DATA_DIR", f"data/parsed/v{ETL_SCHEMA_VERSION}"))
ETL_STATE_DIR = Path(os.getenv("ETL_STATE_DIR", "data/etl"))
CRAWL_MANIFEST_PATH = ETL_STATE_DIR / "crawl_manifest.json"
RAW_PAGE_FILES = {
    "characters": RAW_DATA_DIR / "indexes" / "characters.html",
    "sidekick": RAW_DATA_DIR / "indexes" / "sidekick.html",
    "superbosses": RAW_DATA_DIR / "indexes" / "superbosses.html",
    "grasta_attack": RAW_DATA_DIR / "indexes" / "grasta_attack.html",
    "grasta_life": RAW_DATA_DIR / "indexes" / "grasta_life.html",
    "grasta_support": RAW_DATA_DIR / "indexes" / "grasta_support.html",
    "grasta_special": RAW_DATA_DIR / "indexes" / "grasta_special.html",
    "grasta_vc": RAW_DATA_DIR / "indexes" / "grasta_vc.html",
    "grasta_ores": RAW_DATA_DIR / "indexes" / "grasta_ores.html",
    "weapons": RAW_DATA_DIR / "indexes" / "weapons.html",
    "armor": RAW_DATA_DIR / "indexes" / "armor.html",
}
RAW_CHARACTER_DIR = RAW_DATA_DIR / "characters"
RAW_SIDEKICK_DIR = RAW_DATA_DIR / "sidekicks"
RAW_SUPERBOSS_DIR = RAW_DATA_DIR / "superbosses"
PARSED_INDEX_DIR = PARSED_DATA_DIR / "indexes"
PARSED_CHARACTER_DIR = PARSED_DATA_DIR / "characters"
PARSED_SIDEKICK_DIR = PARSED_DATA_DIR / "sidekicks"
PARSED_SUPERBOSS_DIR = PARSED_DATA_DIR / "superbosses"

ETL_SOURCE_MODE = os.getenv("ETL_SOURCE_MODE", "live")
ETL_CRAWL_SCOPE = os.getenv("ETL_CRAWL_SCOPE", "fallback")
ETL_INCREMENTAL = _env_flag("ETL_INCREMENTAL", True)
ETL_RESUME = _env_flag("ETL_RESUME", True)
ETL_INCLUDE_CHARACTER_PAGES = _env_flag("ETL_INCLUDE_CHARACTER_PAGES", True)
ETL_INCLUDE_SIDEKICK_PAGES = _env_flag("ETL_INCLUDE_SIDEKICK_PAGES", True)
ETL_INCLUDE_SUPERBOSS_PAGES = _env_flag("ETL_INCLUDE_SUPERBOSS_PAGES", True)
ETL_MAX_RETRIES = int(os.getenv("ETL_MAX_RETRIES", "3"))
ETL_SMALL_CHARACTER_LIMIT = int(os.getenv("ETL_SMALL_CHARACTER_LIMIT", "10"))
ETL_SMALL_SIDEKICK_LIMIT = int(os.getenv("ETL_SMALL_SIDEKICK_LIMIT", "25"))
ETL_FALLBACK_CHARACTER_LIMIT = int(os.getenv("ETL_FALLBACK_CHARACTER_LIMIT", "100"))
ETL_FALLBACK_SIDEKICK_LIMIT = int(os.getenv("ETL_FALLBACK_SIDEKICK_LIMIT", "25"))
ETL_OPERATOR_WAIT_SECONDS = int(os.getenv("ETL_OPERATOR_WAIT_SECONDS", "20"))
ETL_BROWSER_PROFILE_DIR = os.getenv("ETL_BROWSER_PROFILE_DIR")

# Minimum node counts for post-load assertion (from wiki audit 2026-03-14)
EXPECTED_NODE_COUNTS = {
    "Character": 300,  # wiki has 393
    "Grasta": 460,     # wiki audit 2026-03-15: actual=489 unique nodes (647 wiki rows deduplicate by name via MERGE), floor=460 (~4% buffer)
    "Ore": 50,         # wiki has 61
    "Trait": 10,
}
