"""Idempotent Neo4j MERGE loader for AnotherEden graph data.

All write operations use UNWIND+MERGE for idempotency — running the loader
twice against the same database produces the same node/edge counts.

Uniqueness constraints are created with IF NOT EXISTS so this module is
safe to call multiple times (migrations/re-runs).

Graph schema decisions (SCHEMA.md v1.0.0):
- Ore nodes are STANDALONE ENTITIES — no ENHANCES edges are created.
  Ore application to a Grasta is a dynamic player/AI decision handled
  in Phase 2/3 agents, not a static graph relationship.
- REQUIRES_TRAIT edges are created ONLY for non-VC grastas that have a
  non-empty personality_req.  VC grastas never get REQUIRES_TRAIT edges.
"""
import logging
from typing import Union

from .constants import ETL_SCHEMA_VERSION
from .models import (
    CharacterRow,
    EquipmentRow,
    GrastaRow,
    MechanicReferenceRow,
    OreRow,
    PassiveSkillRow,
    SidekickRow,
    SkillRow,
    SuperbossRow,
)

logger = logging.getLogger(__name__)


SIDEKICK_CHARACTER_OVERLAP_QUERY = """
MATCH (c:Character)
MATCH (s:Sidekick {name: c.name})
OPTIONAL MATCH (c)-[:HAS_SKILL]->(skill:Skill)
WITH c, s, count(skill) AS skill_count
OPTIONAL MATCH (c)-[:HAS_PASSIVE_SKILL]->(passive:PassiveSkill)
WITH c, s, skill_count, count(passive) AS passive_skill_count
OPTIONAL MATCH (c)-[:UNLOCKS_SIDEKICK]->(unlocked:Sidekick)
WITH
    c,
    s,
    skill_count,
    passive_skill_count,
    count(unlocked) AS unlock_relationship_count
WITH
    c,
    s,
    skill_count,
    passive_skill_count,
    unlock_relationship_count,
    (
        skill_count = 0
        AND passive_skill_count = 0
    ) AS lacks_character_detail,
    (
        c.detail_url IS NULL
        OR c.detail_url = ''
        OR c.detail_url = s.source_url
    ) AS sidekick_like_origin
RETURN
    c.name AS name,
    c.element AS element,
    c.weapon AS weapon,
    c.light_shadow AS light_shadow,
    c.detail_url AS character_detail_url,
    s.source_url AS sidekick_source_url,
    skill_count,
    passive_skill_count,
    unlock_relationship_count,
    lacks_character_detail,
    sidekick_like_origin,
    (
        lacks_character_detail
        AND unlock_relationship_count = 0
    ) AS cleanup_candidate
ORDER BY name
"""


async def find_sidekick_character_overlaps(driver) -> list[dict]:
    """Return exact name overlaps between Character and Sidekick nodes."""
    async with driver.session() as session:
        result = await session.run(SIDEKICK_CHARACTER_OVERLAP_QUERY)
        return [dict(record) async for record in result]


async def cleanup_duplicate_sidekick_characters(driver) -> list[dict]:
    """Delete confirmed sidekick duplicates that were also loaded as Character nodes."""
    overlaps = await find_sidekick_character_overlaps(driver)
    cleanup_names = [row["name"] for row in overlaps if row["cleanup_candidate"]]
    if not cleanup_names:
        logger.info("No confirmed duplicate sidekick Character nodes to remove")
        return overlaps

    cypher = """
UNWIND $names AS name
MATCH (c:Character {name: name})
MATCH (:Sidekick {name: name})
WHERE NOT (c)-[:HAS_SKILL]->(:Skill)
  AND NOT (c)-[:HAS_PASSIVE_SKILL]->(:PassiveSkill)
  AND NOT (c)-[:UNLOCKS_SIDEKICK]->(:Sidekick)
DETACH DELETE c
"""
    async with driver.session() as session:
        await session.run(cypher, names=cleanup_names)

    logger.info("Removed %d duplicate sidekick Character nodes", len(cleanup_names))
    return overlaps

# ---------------------------------------------------------------------------
# Constraints
# ---------------------------------------------------------------------------

async def ensure_constraints(driver) -> None:
    """Create uniqueness constraints for all graph node types.

    Uses IF NOT EXISTS so this is safe to call multiple times.
    Constraints must exist before any MERGE operations to guarantee
    true uniqueness (no duplicate nodes on concurrent writes).
    """
    constraints = [
        "DROP CONSTRAINT skill_name IF EXISTS",
        "CREATE CONSTRAINT char_name IF NOT EXISTS FOR (c:Character) REQUIRE c.name IS UNIQUE",
        "CREATE CONSTRAINT character_id IF NOT EXISTS FOR (c:Character) REQUIRE c.character_id IS UNIQUE",
        "CREATE CONSTRAINT trait_name IF NOT EXISTS FOR (t:Trait) REQUIRE t.name IS UNIQUE",
        "DROP CONSTRAINT grasta_name IF EXISTS",
        "CREATE CONSTRAINT grasta_id IF NOT EXISTS FOR (g:Grasta) REQUIRE g.grasta_id IS UNIQUE",
        "CREATE CONSTRAINT ore_name IF NOT EXISTS FOR (o:Ore) REQUIRE o.name IS UNIQUE",
        "CREATE CONSTRAINT equipment_identity IF NOT EXISTS FOR (e:Equipment) REQUIRE (e.equipment_slot, e.name) IS UNIQUE",
        "CREATE CONSTRAINT skill_id IF NOT EXISTS FOR (s:Skill) REQUIRE s.skill_id IS UNIQUE",
        "CREATE CONSTRAINT skill_identity IF NOT EXISTS FOR (s:Skill) REQUIRE (s.character_name, s.name) IS UNIQUE",
        "CREATE CONSTRAINT passive_skill_id IF NOT EXISTS FOR (p:PassiveSkill) REQUIRE p.passive_skill_id IS UNIQUE",
        "CREATE CONSTRAINT passive_skill_identity IF NOT EXISTS FOR (p:PassiveSkill) REQUIRE (p.character_name, p.name) IS UNIQUE",
        "CREATE CONSTRAINT sidekick_name IF NOT EXISTS FOR (s:Sidekick) REQUIRE s.name IS UNIQUE",
        "CREATE CONSTRAINT sidekick_skill_identity IF NOT EXISTS FOR (s:SidekickSkill) REQUIRE (s.sidekick_name, s.name, s.skill_kind) IS UNIQUE",
        "CREATE CONSTRAINT sidekick_aura_identity IF NOT EXISTS FOR (a:SidekickAura) REQUIRE (a.sidekick_name, a.name) IS UNIQUE",
        "CREATE CONSTRAINT superboss_name IF NOT EXISTS FOR (s:Superboss) REQUIRE s.name IS UNIQUE",
        "CREATE CONSTRAINT mechanic_reference_id IF NOT EXISTS FOR (m:MechanicReference) REQUIRE m.id IS UNIQUE",
    ]
    async with driver.session() as session:
        for cypher in constraints:
            await session.run(cypher)
    logger.info("Uniqueness constraints ensured (%d constraints)", len(constraints))


# ---------------------------------------------------------------------------
# Node loaders
# ---------------------------------------------------------------------------

async def load_characters(driver, rows: list[CharacterRow]) -> None:
    """Load Character nodes and HAS_TRAIT edges using UNWIND+MERGE.

    For each character row:
    - MERGE the Character node (keyed by name)
    - MERGE each Trait node mentioned in personalities
    - MERGE a HAS_TRAIT edge from Character to each Trait

    Running twice produces the same node/edge count (idempotent).
    """
    if not rows:
        logger.warning("load_characters called with empty list — nothing to load")
        return

    char_data = [
        {
            "character_id": r.character_id,
            "display_name": r.display_name,
            "aliases": r.aliases,
            "detail_url": r.detail_url,
            "name": r.name,
            "element": r.element,
            "weapon": r.weapon,
            "light_shadow": r.light_shadow,
            "personalities": r.personalities,
            "is_SA": r.is_SA,
            "schema_version": r.schema_version,
        }
        for r in rows
    ]

    # Load Character nodes
    cypher_chars = """
UNWIND $rows AS row
MERGE (c:Character {name: row.name})
SET c.character_id = row.character_id,
    c.display_name = row.display_name,
    c.aliases = row.aliases,
    c.detail_url = row.detail_url,
    c.element = row.element,
    c.weapon = row.weapon,
    c.light_shadow = row.light_shadow,
    c.is_SA = row.is_SA,
    c.schema_version = row.schema_version
"""
    # Load Trait nodes and HAS_TRAIT edges
    cypher_traits = """
UNWIND $rows AS row
UNWIND row.personalities AS trait_name
MERGE (t:Trait {name: trait_name})
WITH row, t
MATCH (c:Character {name: row.name})
MERGE (c)-[:HAS_TRAIT]->(t)
"""
    async with driver.session() as session:


        await session.run(cypher_chars, rows=char_data)
        await session.run(cypher_traits, rows=char_data)

    logger.info("Loaded %d Character nodes", len(rows))
async def audit_character_readiness(driver, parsed_names: list[str]) -> dict[str, list[str]]:
    """Fail visibly when parsed canonical identities are absent or not roster-selectable."""
    records, _, _ = await driver.execute_query(
        """
MATCH (c:Character)
WHERE c.name IN $parsed_names
OPTIONAL MATCH (s:Sidekick {name: c.name})
WITH collect(DISTINCT c.name) AS graph_names,
     collect(DISTINCT CASE WHEN s IS NULL THEN c.name END) AS selectable_names
RETURN graph_names, [name IN selectable_names WHERE name IS NOT NULL] AS selectable_names
""",
        parsed_names=parsed_names,
        database_="neo4j",
    )
    row = records[0] if records else {}
    graph_names = set(row.get("graph_names", []))
    selectable_names = set(row.get("selectable_names", []))
    report = {
        "missing_from_graph": sorted(set(parsed_names) - graph_names),
        "missing_from_frontend": sorted(set(parsed_names) - selectable_names),
    }
    if any(report.values()):
        raise RuntimeError(f"Character coverage/readiness audit failed: {report}")
    return report


async def report_graph_readiness(driver) -> dict:
    """Return visible identity and fact-coverage gaps after an ETL replay."""
    records, _, _ = await driver.execute_query(
        """
MATCH (c:Character)
OPTIONAL MATCH (c)-[:HAS_SKILL]->(skill:Skill)
WITH c, count(skill) AS skill_count
OPTIONAL MATCH (c)-[:HAS_PASSIVE_SKILL]->(passive:PassiveSkill)
WITH c, skill_count, count(passive) AS passive_count
WITH collect(CASE WHEN skill_count = 0 THEN c.name END) AS no_skills,
     collect(CASE WHEN passive_count = 0 THEN c.name END) AS no_passives,
     sum(CASE WHEN c.character_id IS NULL OR c.character_id = '' THEN 1 ELSE 0 END) AS missing_character_ids
CALL {
  MATCH (b:Superboss)
  RETURN count(b) AS boss_count,
         sum(CASE WHEN b.mechanics_text IS NULL OR b.mechanics_text = '' THEN 1 ELSE 0 END) AS bosses_without_mechanics
}
CALL {
  MATCH (g:Grasta)
  RETURN count(g) AS grasta_count,
         sum(CASE WHEN g.grasta_id IS NULL OR g.grasta_id = '' THEN 1 ELSE 0 END) AS missing_grasta_ids
}
CALL {
  MATCH (s:Skill)
  RETURN sum(CASE WHEN s.skill_id IS NULL OR s.skill_id = '' THEN 1 ELSE 0 END) AS missing_skill_ids
}
CALL {
  MATCH (p:PassiveSkill)
  RETURN sum(CASE WHEN p.passive_skill_id IS NULL OR p.passive_skill_id = '' THEN 1 ELSE 0 END) AS missing_passive_skill_ids
}
CALL {
  MATCH (n)
  WHERE (n:Character OR n:Skill OR n:PassiveSkill OR n:Grasta)
    AND (n.schema_version IS NULL OR n.schema_version <> $schema_version)
  RETURN count(n) AS stale_schema_nodes
}
CALL { MATCH (e:Equipment) RETURN count(e) AS equipment_count }
CALL { MATCH (m:MechanicReference) RETURN count(m) AS mechanic_reference_count }
RETURN [name IN no_skills WHERE name IS NOT NULL] AS characters_without_skills,
       [name IN no_passives WHERE name IS NOT NULL] AS characters_without_passives,
       missing_character_ids, missing_skill_ids, missing_passive_skill_ids,
       stale_schema_nodes, boss_count, bosses_without_mechanics, grasta_count,
       missing_grasta_ids, equipment_count, mechanic_reference_count
""",
        schema_version=ETL_SCHEMA_VERSION,
        database_="neo4j",
    )
    report = dict(records[0]) if records else {}
    report["ready"] = not any(
        (
            report.get("missing_character_ids", 0),
            report.get("missing_skill_ids", 0),
            report.get("missing_passive_skill_ids", 0),
            report.get("stale_schema_nodes", 0),
            report.get("characters_without_skills", []),
            report.get("characters_without_passives", []),
            report.get("bosses_without_mechanics", 0),
            report.get("missing_grasta_ids", 0),
            not report.get("boss_count", 0),
            not report.get("grasta_count", 0),
            not report.get("equipment_count", 0),
            not report.get("mechanic_reference_count", 0),
        )
    )
    logger.info("Graph readiness report: %s", report)
    return report


async def load_skills(driver, rows: list[SkillRow]) -> None:
    """Load Skill nodes and Character-HAS_SKILL edges using UNWIND+MERGE."""
    if not rows:
        logger.warning("load_skills called with empty list -- nothing to load")
        return

    skill_data = [
        {
            "skill_id": r.skill_id,
            "character_name": r.character_name,
            "name": r.name,
            "element": r.element,
            "skill_type": r.skill_type,
            "mp": r.mp,
            "description": r.description,
            "multiplier": r.multiplier,
            "source_url": r.source_url,
            "section": r.section,
            "requires_stellar_awakened": r.requires_stellar_awakened,
            "schema_version": r.schema_version,
            "role_tags": r.role_tags,
            "role_evidence_json": r.role_evidence_json,
            "role_taxonomy_version": r.role_taxonomy_version,
        }
        for r in rows
    ]
    cypher = """
UNWIND $rows AS row
MATCH (c:Character {name: row.character_name})
MERGE (s:Skill {character_name: row.character_name, name: row.name})
SET s.skill_id = row.skill_id,
    s.element = row.element,
    s.skill_type = row.skill_type,
    s.mp = row.mp,
    s.description = row.description,
    s.multiplier = row.multiplier,
    s.source_url = row.source_url,
    s.section = row.section,
    s.requires_stellar_awakened = row.requires_stellar_awakened,
    s.schema_version = row.schema_version,
    s.role_tags = row.role_tags,
    s.role_evidence_json = row.role_evidence_json,
    s.role_taxonomy_version = row.role_taxonomy_version
MERGE (c)-[:HAS_SKILL]->(s)
"""
    async with driver.session() as session:
        await session.run(cypher, rows=skill_data)

    logger.info("Loaded %d Skill nodes", len(rows))


async def load_passive_skills(driver, rows: list[PassiveSkillRow]) -> None:
    """Load PassiveSkill nodes and Character-HAS_PASSIVE_SKILL edges."""
    if not rows:
        logger.warning("load_passive_skills called with empty list -- nothing to load")
        return

    passive_data = [
        {
            "passive_skill_id": r.passive_skill_id,
            "character_name": r.character_name,
            "name": r.name,
            "description": r.description,
            "source_url": r.source_url,
            "section": r.section,
            "passive_type": r.passive_type,
            "requires_stellar_awakened": r.requires_stellar_awakened,
            "schema_version": r.schema_version,
            "role_tags": r.role_tags,
            "role_evidence_json": r.role_evidence_json,
            "role_taxonomy_version": r.role_taxonomy_version,
        }
        for r in rows
    ]
    cypher = """
UNWIND $rows AS row
MATCH (c:Character {name: row.character_name})
MERGE (p:PassiveSkill {character_name: row.character_name, name: row.name})
SET p.passive_skill_id = row.passive_skill_id,
    p.description = row.description,
    p.source_url = row.source_url,
    p.section = row.section,
    p.passive_type = row.passive_type,
    p.requires_stellar_awakened = row.requires_stellar_awakened,
    p.schema_version = row.schema_version,
    p.role_tags = row.role_tags,
    p.role_evidence_json = row.role_evidence_json,
    p.role_taxonomy_version = row.role_taxonomy_version
MERGE (c)-[:HAS_PASSIVE_SKILL]->(p)
"""
    async with driver.session() as session:
        await session.run(cypher, rows=passive_data)

    logger.info("Loaded %d PassiveSkill nodes", len(rows))


async def load_sidekicks(driver, rows: list[SidekickRow]) -> None:
    """Load Sidekick nodes, ability child nodes, and official association edges."""
    if not rows:
        logger.warning("load_sidekicks called with empty list -- nothing to load")
        return

    sidekick_data = [
        {
            "name": r.name,
            "source_url": r.source_url,
            "acquisition_text": r.acquisition_text,
            "rarity": r.rarity,
            "role_tags": r.role_tags,
            "main_slot_behavior": r.main_slot_behavior,
            "sub_slot_behavior": r.sub_slot_behavior,
            "diagnostics_text": r.diagnostics_text,
            "schema_version": r.schema_version,
            "associated_character_names": r.associated_character_names,
        }
        for r in rows
    ]
    skill_data = [
        {
            "sidekick_name": r.name,
            "name": skill.name,
            "skill_kind": skill.skill_kind,
            "element": skill.element,
            "skill_type": skill.skill_type,
            "charge_cost": skill.charge_cost,
            "description": skill.description,
            "source_url": skill.source_url,
            "section": skill.section,
            "schema_version": skill.schema_version,
        }
        for r in rows
        for skill in [*r.auto_skills, *r.charge_skills]
    ]
    aura_data = [
        {
            "sidekick_name": r.name,
            "name": aura.name,
            "activation_condition": aura.activation_condition,
            "effect_text": aura.effect_text,
            "source_url": aura.source_url,
            "section": aura.section,
            "schema_version": aura.schema_version,
        }
        for r in rows
        for aura in r.auras
    ]

    cypher_sidekicks = """
UNWIND $rows AS row
MERGE (s:Sidekick {name: row.name})
SET s.source_url = row.source_url,
    s.acquisition_text = row.acquisition_text,
    s.rarity = row.rarity,
    s.role_tags = row.role_tags,
    s.main_slot_behavior = row.main_slot_behavior,
    s.sub_slot_behavior = row.sub_slot_behavior,
    s.diagnostics_text = row.diagnostics_text,
    s.schema_version = row.schema_version
WITH row, s
UNWIND row.associated_character_names AS character_name
MATCH (c:Character {name: character_name})
MERGE (c)-[:UNLOCKS_SIDEKICK]->(s)
"""
    cypher_skills = """
UNWIND $rows AS row
MATCH (sidekick:Sidekick {name: row.sidekick_name})
MERGE (skill:SidekickSkill {sidekick_name: row.sidekick_name, name: row.name, skill_kind: row.skill_kind})
SET skill.element = row.element,
    skill.skill_type = row.skill_type,
    skill.charge_cost = row.charge_cost,
    skill.description = row.description,
    skill.source_url = row.source_url,
    skill.section = row.section,
    skill.schema_version = row.schema_version
WITH sidekick, skill, row
FOREACH (_ IN CASE WHEN row.skill_kind = 'auto' THEN [1] ELSE [] END |
    MERGE (sidekick)-[:HAS_AUTO_SKILL]->(skill)
)
FOREACH (_ IN CASE WHEN row.skill_kind = 'charge' THEN [1] ELSE [] END |
    MERGE (sidekick)-[:HAS_CHARGE_SKILL]->(skill)
)
"""
    cypher_auras = """
UNWIND $rows AS row
MATCH (sidekick:Sidekick {name: row.sidekick_name})
MERGE (aura:SidekickAura {sidekick_name: row.sidekick_name, name: row.name})
SET aura.activation_condition = row.activation_condition,
    aura.effect_text = row.effect_text,
    aura.source_url = row.source_url,
    aura.section = row.section,
    aura.schema_version = row.schema_version
MERGE (sidekick)-[:HAS_AURA]->(aura)
"""
    async with driver.session() as session:
        await session.run(cypher_sidekicks, rows=sidekick_data)
        if skill_data:
            await session.run(cypher_skills, rows=skill_data)
        if aura_data:
            await session.run(cypher_auras, rows=aura_data)

    logger.info("Loaded %d Sidekick nodes", len(rows))


async def load_superbosses(driver, rows: list[SuperbossRow]) -> None:
    """Load curated Superboss nodes that passed detail-page quality gates."""
    if not rows:
        logger.warning("load_superbosses called with empty list -- nothing to load")
        return

    boss_data = [
        {
            "name": r.name,
            "source_url": r.source_url,
            "difficulty_tier": r.difficulty_tier,
            "level": r.level,
            "hp": r.hp,
            "weak": r.weak,
            "resist": r.resist,
            "null": r.null,
            "absorb": r.absorb,
            "characteristics": r.characteristics,
            "mechanic_tags": r.mechanic_tags,
            "mechanics_text": r.mechanics_text,
            "schema_version": r.schema_version,
        }
        for r in rows
    ]
    cypher = """
UNWIND $rows AS row
MERGE (s:Superboss {name: row.name})
SET s.source_url = row.source_url,
    s.difficulty_tier = row.difficulty_tier,
    s.level = row.level,
    s.hp = row.hp,
    s.weak = row.weak,
    s.resist = row.resist,
    s.null = row.null,
    s.absorb = row.absorb,
    s.characteristics = row.characteristics,
    s.mechanic_tags = row.mechanic_tags,
    s.mechanics_text = row.mechanics_text,
    s.schema_version = row.schema_version
"""
    async with driver.session() as session:
        await session.run(cypher, rows=boss_data)

    logger.info("Loaded %d Superboss nodes", len(rows))


async def load_mechanic_references(driver, rows: list[MechanicReferenceRow]) -> None:
    """Load curated battle mechanics as standalone RAG reference nodes."""
    if not rows:
        logger.warning("load_mechanic_references called with empty list -- nothing to load")
        return

    reference_data = [
        {
            "id": r.id,
            "title": r.title,
            "source_url": r.source_url,
            "source_page": r.source_page,
            "section_path": r.section_path,
            "mechanic_type": r.mechanic_type,
            "topic_tags": r.topic_tags,
            "applies_to": r.applies_to,
            "rules_text": r.rules_text,
            "summary": r.summary,
            "caveats": r.caveats,
            "schema_version": r.schema_version,
        }
        for r in rows
    ]

    cypher = """
UNWIND $rows AS row
MERGE (m:MechanicReference {id: row.id})
SET m.title = row.title,
    m.source_url = row.source_url,
    m.source_page = row.source_page,
    m.section_path = row.section_path,
    m.mechanic_type = row.mechanic_type,
    m.topic_tags = row.topic_tags,
    m.applies_to = row.applies_to,
    m.rules_text = row.rules_text,
    m.summary = row.summary,
    m.caveats = row.caveats,
    m.schema_version = row.schema_version
"""
    async with driver.session() as session:
        await session.run(cypher, rows=reference_data)

    logger.info("Loaded %d MechanicReference nodes", len(rows))




async def remove_collapsed_legacy_grastas(driver) -> int:
    """Remove name-keyed legacy nodes before replaying exact Grasta variants."""
    cypher = """
MATCH (g:Grasta)
WHERE g.grasta_id IS NULL OR g.grasta_id = ''
WITH collect(g) AS legacy
FOREACH (node IN legacy | DETACH DELETE node)
RETURN size(legacy) AS removed
"""
    async with driver.session() as session:
        record = await (await session.run(cypher)).single()
    removed = record["removed"] if record else 0
    logger.info("Removed %d collapsed legacy Grasta nodes", removed)
    return removed


async def load_grastas(driver, rows: list[GrastaRow]) -> None:
    """Load exact Grasta variants and their isolated trait requirements."""
    if not rows:
        logger.warning("load_grastas called with empty list - nothing to load")
        return

    grasta_data = [row.model_dump() for row in rows]
    cypher_nodes = """
UNWIND $rows AS row
MERGE (g:Grasta {grasta_id: row.grasta_id})
SET g.name = row.name,
    g.display_name = row.display_name,
    g.category = row.category,
    g.tier = row.tier,
    g.stats = row.stats,
    g.personality_req = row.personality_req,
    g.weapon_req = row.weapon_req,
    g.weapon_group = row.weapon_group,
    g.is_shareable = row.is_shareable,
    g.source_url = row.source_url,
    g.obtain_text = row.obtain_text,
    g.effect_text = row.effect_text,
    g.source_variant = row.source_variant,
    g.acquisition_class = row.acquisition_class,
    g.max_theoretical_copies = row.max_theoretical_copies,
    g.effect_tags = row.effect_tags,
    g.effect_tag_derivation = row.effect_tag_derivation,
    g.schema_version = row.schema_version
"""
    cypher_edges = """
UNWIND $rows AS row
WITH row WHERE row.category <> 'VC' AND row.personality_req IS NOT NULL AND row.personality_req <> ''
MATCH (g:Grasta {grasta_id: row.grasta_id})
MERGE (t:Trait {name: row.personality_req})
MERGE (g)-[:REQUIRES_TRAIT]->(t)
"""
    async with driver.session() as session:
        await session.run(cypher_nodes, rows=grasta_data)
        await session.run(cypher_edges, rows=grasta_data)

    logger.info("Loaded %d exact Grasta variants", len(rows))


async def load_ores(driver, rows: list[OreRow]) -> None:
    """Load Ore nodes as standalone entities using UNWIND+MERGE.

    NO relationship edges are created from Ore nodes.

    Per GRAPH-06 user decision (2026-03-14): Ore application to a Grasta
    is a dynamic player/AI decision handled by PLAN and ANALYZE agents in
    Phase 2/3, not a static graph edge.  The ENHANCES relationship type is
    intentionally absent from SCHEMA.md v1.0.0.
    """
    if not rows:
        logger.warning("load_ores called with empty list — nothing to load")
        return

    ore_data = [
        {
            "name": r.name,
            "stats": r.stats,
            "source": r.source,
            "effect_tags": r.effect_tags,
            "effect_tag_derivation": r.effect_tag_derivation,
        }
        for r in rows
    ]

    # Ore nodes only — no relationship edges created (standalone per GRAPH-06)
    cypher_nodes = """
UNWIND $rows AS row
MERGE (o:Ore {name: row.name})
SET o.stats = row.stats,
    o.source = row.source,
    o.effect_tags = row.effect_tags,
    o.effect_tag_derivation = row.effect_tag_derivation
"""
    async with driver.session() as session:
        await session.run(cypher_nodes, rows=ore_data)

    logger.info("Loaded %d Ore nodes", len(rows))


async def load_equipment(driver, rows: list[EquipmentRow]) -> None:
    """Load baseline Weapon/Armor context as standalone Equipment nodes."""
    if not rows:
        logger.warning("load_equipment called with empty list -- nothing to load")
        return

    equipment_data = [
        {
            "name": r.name,
            "equipment_slot": r.equipment_slot,
            "category": r.category,
            "level": r.level,
            "attack": r.attack,
            "magic_attack": r.magic_attack,
            "defense": r.defense,
            "magic_defense": r.magic_defense,
            "effect_text": r.effect_text,
            "obtain_text": r.obtain_text,
            "source_url": r.source_url,
            "schema_version": r.schema_version,
        }
        for r in rows
    ]

    cypher = """
UNWIND $rows AS row
MERGE (e:Equipment {equipment_slot: row.equipment_slot, name: row.name})
SET e.category = row.category,
    e.level = row.level,
    e.attack = row.attack,
    e.magic_attack = row.magic_attack,
    e.defense = row.defense,
    e.magic_defense = row.magic_defense,
    e.effect_text = row.effect_text,
    e.obtain_text = row.obtain_text,
    e.source_url = row.source_url,
    e.schema_version = row.schema_version
"""
    async with driver.session() as session:
        await session.run(cypher, rows=equipment_data)

    logger.info("Loaded %d Equipment nodes", len(rows))


# ---------------------------------------------------------------------------
# Relationship loader (additional post-load pass if needed)
# ---------------------------------------------------------------------------

async def load_relationships(driver, characters: list[CharacterRow],
                              grastas: list[GrastaRow]) -> None:
    """Post-load relationship pass (currently a no-op — relationships are
    created inline in load_characters and load_grastas).

    Kept as a hook for any cross-entity relationships discovered in later phases.
    """
    logger.info("load_relationships: no additional cross-entity edges to create")
