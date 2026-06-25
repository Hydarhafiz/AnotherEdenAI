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
        "CREATE CONSTRAINT trait_name IF NOT EXISTS FOR (t:Trait) REQUIRE t.name IS UNIQUE",
        "CREATE CONSTRAINT grasta_name IF NOT EXISTS FOR (g:Grasta) REQUIRE g.name IS UNIQUE",
        "CREATE CONSTRAINT ore_name IF NOT EXISTS FOR (o:Ore) REQUIRE o.name IS UNIQUE",
        "CREATE CONSTRAINT equipment_identity IF NOT EXISTS FOR (e:Equipment) REQUIRE (e.equipment_slot, e.name) IS UNIQUE",
        "CREATE CONSTRAINT skill_identity IF NOT EXISTS FOR (s:Skill) REQUIRE (s.character_name, s.name) IS UNIQUE",
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
            "name": r.name,
            "element": r.element,
            "weapon": r.weapon,
            "light_shadow": r.light_shadow,
            "personalities": r.personalities,
            "is_SA": r.is_SA,
        }
        for r in rows
    ]

    # Load Character nodes
    cypher_chars = """
UNWIND $rows AS row
MERGE (c:Character {name: row.name})
SET c.element = row.element,
    c.weapon = row.weapon,
    c.light_shadow = row.light_shadow,
    c.is_SA = row.is_SA
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


async def load_skills(driver, rows: list[SkillRow]) -> None:
    """Load Skill nodes and Character-HAS_SKILL edges using UNWIND+MERGE."""
    if not rows:
        logger.warning("load_skills called with empty list -- nothing to load")
        return

    skill_data = [
        {
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
        }
        for r in rows
    ]
    cypher = """
UNWIND $rows AS row
MATCH (c:Character {name: row.character_name})
MERGE (s:Skill {character_name: row.character_name, name: row.name})
SET s.element = row.element,
    s.skill_type = row.skill_type,
    s.mp = row.mp,
    s.description = row.description,
    s.multiplier = row.multiplier,
    s.source_url = row.source_url,
    s.section = row.section,
    s.requires_stellar_awakened = row.requires_stellar_awakened,
    s.schema_version = row.schema_version
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
            "character_name": r.character_name,
            "name": r.name,
            "description": r.description,
            "source_url": r.source_url,
            "section": r.section,
            "passive_type": r.passive_type,
            "requires_stellar_awakened": r.requires_stellar_awakened,
            "schema_version": r.schema_version,
        }
        for r in rows
    ]
    cypher = """
UNWIND $rows AS row
MATCH (c:Character {name: row.character_name})
MERGE (p:PassiveSkill {character_name: row.character_name, name: row.name})
SET p.description = row.description,
    p.source_url = row.source_url,
    p.section = row.section,
    p.passive_type = row.passive_type,
    p.requires_stellar_awakened = row.requires_stellar_awakened,
    p.schema_version = row.schema_version
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


async def load_grastas(driver, rows: list[GrastaRow]) -> None:
    """Load Grasta nodes and REQUIRES_TRAIT edges using UNWIND+MERGE.

    Grasta nodes: all categories loaded via MERGE.
    REQUIRES_TRAIT edges: created only when category != 'VC' AND
    personality_req is not None/empty.  VC grastas never get REQUIRES_TRAIT.
    """
    if not rows:
        logger.warning("load_grastas called with empty list — nothing to load")
        return

    grasta_data = [
        {
            "name": r.name,
            "category": r.category,
            "tier": r.tier,
            "stats": r.stats,
            "personality_req": r.personality_req,
            "is_shareable": r.is_shareable,
            "effect_tags": r.effect_tags,
            "effect_tag_derivation": r.effect_tag_derivation,
        }
        for r in rows
    ]

    # Load Grasta nodes
    cypher_nodes = """
UNWIND $rows AS row
MERGE (g:Grasta {name: row.name})
SET g.category = row.category,
    g.tier = row.tier,
    g.stats = row.stats,
    g.is_shareable = row.is_shareable,
    g.effect_tags = row.effect_tags,
    g.effect_tag_derivation = row.effect_tag_derivation
"""
    # Load REQUIRES_TRAIT edges — gated: non-VC only, personality_req not null/empty
    cypher_edges = """
UNWIND $rows AS row
WITH row WHERE row.category <> 'VC' AND row.personality_req IS NOT NULL AND row.personality_req <> ''
MATCH (g:Grasta {name: row.name})
MERGE (t:Trait {name: row.personality_req})
MERGE (g)-[:REQUIRES_TRAIT]->(t)
"""
    async with driver.session() as session:
        await session.run(cypher_nodes, rows=grasta_data)
        await session.run(cypher_edges, rows=grasta_data)

    logger.info("Loaded %d Grasta nodes", len(rows))


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
