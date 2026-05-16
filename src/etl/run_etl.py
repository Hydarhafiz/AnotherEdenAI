"""ETL entry point for the staged cached fetch -> parse -> load pipeline."""

import asyncio
import logging

from neo4j import AsyncGraphDatabase

from .constants import ETL_MODE, NEO4J_AUTH, NEO4J_URI, SCHEMA_VERSION
from .loader import ensure_constraints, load_characters, load_grastas, load_ores, load_passive_skills, load_skills
from .pipeline import CrawlConfig, mark_loaded, prepare_parsed_data

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main(driver=None, config: CrawlConfig | None = None) -> None:
    """Run the full ETL pipeline and load Neo4j from parsed artifacts."""
    config = config or CrawlConfig()
    print(
        f"Starting ETL -- SCHEMA_VERSION={SCHEMA_VERSION} ETL_MODE={ETL_MODE} "
        f"SOURCE_MODE={config.source_mode} CRAWL_SCOPE={config.crawl_scope}"
    )

    own_driver = driver is None
    if own_driver:
        driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)

    try:
        await driver.verify_connectivity()
        logger.info("Neo4j connection verified at %s", NEO4J_URI)

        await ensure_constraints(driver)

        logger.info("Preparing ETL data through staged cache/parse pipeline...")
        data, manifest = await prepare_parsed_data(config=config)

        characters = data["characters"]
        grastas = data["grastas"]
        ores = data["ores"]

        logger.info(
            "Prepared: %d characters, %d grastas, %d ores",
            len(characters), len(grastas), len(ores),
        )

        await load_characters(driver, characters)
        skills = [skill for character in characters for skill in character.skills]
        passive_skills = [passive for character in characters for passive in character.passive_skills]
        await load_skills(driver, skills)
        await load_passive_skills(driver, passive_skills)
        await load_grastas(driver, grastas)
        await load_ores(driver, ores)
        mark_loaded(manifest, data)

        print(
            f"ETL complete -- loaded {len(characters)} characters, "
            f"{len(grastas)} grastas, {len(ores)} ores"
        )
    finally:
        if own_driver:
            await driver.close()


if __name__ == "__main__":
    asyncio.run(main())
