"""ETL entry point — orchestrates scrape → validate → load pipeline.

Usage:
    python src/etl/run_etl.py

Environment variables:
    ETL_MODE    "strict" (default) or "lenient"
    NEO4J_URI   bolt://localhost:7687 (default)
    NEO4J_AUTH  neo4j/anothereden (default)

Requires Docker Neo4j to be running (see docker-compose.yml).
"""
import asyncio
import logging

from neo4j import AsyncGraphDatabase

from .constants import SCHEMA_VERSION, ETL_MODE, NEO4J_URI, NEO4J_AUTH
from .scraper import scrape_all
from .loader import ensure_constraints, load_characters, load_grastas, load_ores

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main(driver=None) -> None:
    """Run the full ETL pipeline: scrape → validate → load → report.

    Args:
        driver: Optional pre-created AsyncGraphDatabase driver. If None, a new driver
                is created and closed after the pipeline completes. When provided (e.g.,
                in test context), the caller is responsible for closing the driver.
    """
    print(f"Starting ETL — SCHEMA_VERSION={SCHEMA_VERSION} ETL_MODE={ETL_MODE}")

    _own_driver = driver is None
    if _own_driver:
        driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)

    try:
        await driver.verify_connectivity()
        logger.info("Neo4j connection verified at %s", NEO4J_URI)

        await ensure_constraints(driver)

        logger.info("Scraping wiki pages...")
        data = await scrape_all()

        characters = data["characters"]
        grastas = data["grastas"]
        ores = data["ores"]

        logger.info(
            "Scraped: %d characters, %d grastas, %d ores",
            len(characters), len(grastas), len(ores),
        )

        await load_characters(driver, characters)
        await load_grastas(driver, grastas)
        await load_ores(driver, ores)

        print(
            f"ETL complete — loaded {len(characters)} characters, "
            f"{len(grastas)} grastas, {len(ores)} ores"
        )

    finally:
        if _own_driver:
            await driver.close()


if __name__ == "__main__":
    asyncio.run(main())
