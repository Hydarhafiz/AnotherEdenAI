"""ETL entry point for the staged cached fetch -> parse -> load pipeline."""

import asyncio
import logging

from neo4j import AsyncGraphDatabase

from .constants import ETL_MODE, NEO4J_AUTH, NEO4J_URI, SCHEMA_VERSION
from .loader import (
    cleanup_duplicate_sidekick_characters,
    audit_character_readiness,
    ensure_constraints,
    load_characters,
    load_equipment,
    load_grastas,
    load_mechanic_references,
    load_ores,
    load_passive_skills,
    load_sidekicks,
    load_skills,
    remove_collapsed_legacy_grastas,
    load_superbosses,
)
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
        sidekicks = data["sidekicks"]
        superbosses = data["superbosses"]
        grastas = data["grastas"]
        ores = data["ores"]
        equipment = data["equipment"]
        mechanic_references = data["mechanic_references"]

        logger.info(
            "Prepared: %d characters, %d sidekicks, %d superbosses, %d mechanic references, "
            "%d grastas, %d ores, %d equipment rows",
            len(characters),
            len(sidekicks),
            len(superbosses),
            len(mechanic_references),
            len(grastas),
            len(ores),
            len(equipment),
        )

        await load_characters(driver, characters)
        skills = [skill for character in characters for skill in character.skills]
        passive_skills = [passive for character in characters for passive in character.passive_skills]
        await load_skills(driver, skills)
        await load_passive_skills(driver, passive_skills)
        await load_sidekicks(driver, sidekicks)
        overlap_report = await cleanup_duplicate_sidekick_characters(driver)
        overlap_names = [row["name"] for row in overlap_report]
        cleanup_names = [row["name"] for row in overlap_report if row["cleanup_candidate"]]
        if overlap_names:
            logger.info(
                "Sidekick/Character overlap report: %s",
                ", ".join(overlap_names),
            )
        if cleanup_names:
            logger.info(
                "Confirmed duplicate sidekick Character nodes removed: %s",
                ", ".join(cleanup_names),
            )
        await audit_character_readiness(driver, [character.name for character in characters])
        await load_superbosses(driver, superbosses)
        await load_mechanic_references(driver, mechanic_references)
        await remove_collapsed_legacy_grastas(driver)
        await load_grastas(driver, grastas)
        await load_ores(driver, ores)
        await load_equipment(driver, equipment)
        mark_loaded(manifest, data)

        print(
            f"ETL complete -- loaded {len(characters)} characters, "
            f"{len(sidekicks)} sidekicks, {len(superbosses)} superbosses, "
            f"{len(mechanic_references)} mechanic references, "
            f"{len(grastas)} grastas, {len(ores)} ores, {len(equipment)} equipment rows"
        )
    finally:
        if own_driver:
            await driver.close()


if __name__ == "__main__":
    asyncio.run(main())
