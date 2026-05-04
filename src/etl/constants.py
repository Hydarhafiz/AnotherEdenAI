import os
from pathlib import Path

SCHEMA_VERSION = "1.0.0"

ETL_MODE = os.getenv("ETL_MODE", "strict")
STRICT = ETL_MODE == "strict"

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_AUTH = tuple(os.getenv("NEO4J_AUTH", "neo4j/anothereden").split("/", 1))

WIKI_URLS = {
    "characters": "https://anothereden.wiki/w/Characters",
    "grasta_attack": "https://anothereden.wiki/w/Grasta_Attack",
    "grasta_life": "https://anothereden.wiki/w/Grasta_Life",
    "grasta_support": "https://anothereden.wiki/w/Grasta_Support",
    "grasta_special": "https://anothereden.wiki/w/Grasta_Special",
    "grasta_vc": "https://anothereden.wiki/w/Grasta_VC",
    "grasta_ores": "https://anothereden.wiki/w/Grasta_Ores",
}

GRASTA_CATEGORIES = ["Attack", "Life", "Support", "Special", "VC"]

RAW_DATA_DIR = Path(os.getenv("RAW_DATA_DIR", "data/raw"))
RAW_PAGE_FILES = {
    "characters": RAW_DATA_DIR / "indexes" / "characters.html",
    "grasta_attack": RAW_DATA_DIR / "indexes" / "grasta_attack.html",
    "grasta_life": RAW_DATA_DIR / "indexes" / "grasta_life.html",
    "grasta_support": RAW_DATA_DIR / "indexes" / "grasta_support.html",
    "grasta_special": RAW_DATA_DIR / "indexes" / "grasta_special.html",
    "grasta_vc": RAW_DATA_DIR / "indexes" / "grasta_vc.html",
    "grasta_ores": RAW_DATA_DIR / "indexes" / "grasta_ores.html",
}
RAW_CHARACTER_DIR = RAW_DATA_DIR / "characters"

# Minimum node counts for post-load assertion (from wiki audit 2026-03-14)
EXPECTED_NODE_COUNTS = {
    "Character": 300,  # wiki has 393
    "Grasta": 460,     # wiki audit 2026-03-15: actual=489 unique nodes (647 wiki rows deduplicate by name via MERGE), floor=460 (~4% buffer)
    "Ore": 50,         # wiki has 61
    "Trait": 10,
}
