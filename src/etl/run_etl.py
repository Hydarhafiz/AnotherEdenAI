"""ETL entry point for the staged cached fetch -> parse -> load pipeline."""

import asyncio
import logging

from neo4j import AsyncGraphDatabase

from .constants import ETL_MODE, NEO4J_AUTH, NEO4J_URI, SCHEMA_VERSION
from .loader import (
    cleanup_duplicate_sidekick_characters,
    audit_character_readiness,
    report_graph_readiness,
    ensure_constraints,
    load_characters,
    load_equipment,
    load_grastas,
    load_mechanic_references,
    load_ores,
    load_passive_skills,
    authoritative_replay_character_kits,
    report_kit_readiness,
    load_sidekicks,
    load_skills,
    remove_collapsed_legacy_grastas,
    remove_unreleased_character_placeholders,
    remove_stale_role_materialization,
    load_superbosses,
)
from .pipeline import CrawlConfig, UNRELEASED_CHARACTER_NAMES, mark_loaded, prepare_parsed_data
from .capability_taxonomy import assert_capability_materialization, validate_c5_handoff
from .kit_readiness import build_receipt, artifact_fingerprint

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

        normalized_characters = []
        receipts = []
        for character in characters:
            receipt, normalized_skills, normalized_passives = build_receipt(
                character,
                character.skills,
                character.passive_skills,
                source_artifact_fingerprint=character.kit_source_artifact_fingerprint or artifact_fingerprint({
                    "character": character.model_dump(mode="json"),
                    "skills": [skill.model_dump(mode="json") for skill in character.skills],
                    "passive_skills": [passive.model_dump(mode="json") for passive in character.passive_skills],
                }),
                source_revision=character.kit_source_revision,
                passive_state=character.kit_passive_state,
                stellar_awakening_state=character.kit_stellar_awakening_state,
                dependency_state=character.kit_dependency_state or "complete",
            )
            normalized_characters.append(
                character.model_copy(update={"skills": normalized_skills, "passive_skills": normalized_passives})
            )
            receipts.append(receipt)
        characters = normalized_characters
        skills = [skill for character in characters for skill in character.skills]
        passive_skills = [passive for character in characters for passive in character.passive_skills]
        capability_records = [
            *(skill.model_dump() for skill in skills),
            *(passive.model_dump() for passive in passive_skills),
            *(skill.model_dump() for sidekick in sidekicks for skill in [*sidekick.auto_skills, *sidekick.charge_skills]),
            *(aura.model_dump() for sidekick in sidekicks for aura in sidekick.auras),
        ]
        manifest["capability_handoff"] = validate_c5_handoff(
            capability_records,
            schema_version=SCHEMA_VERSION,
        )
        logger.info(
            "Feature C5 handoff verified: taxonomy=%s review=%s parsed_facts=%d",
            manifest["capability_handoff"]["taxonomy_version"],
            manifest["capability_handoff"]["review_corpus_version"],
            manifest["capability_handoff"]["parsed_fact_count"],
        )
        await load_characters(driver, characters)
        await remove_unreleased_character_placeholders(driver, list(UNRELEASED_CHARACTER_NAMES))
        await remove_stale_role_materialization(driver)
        await authoritative_replay_character_kits(driver, characters, skills, passive_skills, receipts)
        await load_sidekicks(driver, sidekicks)
        await assert_capability_materialization(driver, skills, passive_skills, sidekicks)
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
        kit_report = await report_kit_readiness(driver, [character.name for character in characters])
        if not kit_report["ready"]:
            raise RuntimeError(f"C6 graph readiness gate failed: {kit_report}")
        await load_superbosses(driver, superbosses)
        await load_mechanic_references(driver, mechanic_references)
        await remove_collapsed_legacy_grastas(driver)
        await load_grastas(driver, grastas)
        await load_ores(driver, ores)
        await load_equipment(driver, equipment)
        manifest["graph_readiness"] = await report_graph_readiness(driver)
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
