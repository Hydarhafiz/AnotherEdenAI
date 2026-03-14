import os

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

# Minimum node counts for post-load assertion (from wiki audit 2026-03-14)
EXPECTED_NODE_COUNTS = {
    "Character": 300,  # wiki has 393
    "Grasta": 460,     # wiki audit 2026-03-15: actual=489 unique nodes (647 wiki rows deduplicate by name via MERGE), floor=460 (~4% buffer)
    "Ore": 50,         # wiki has 61
    "Trait": 10,
}
