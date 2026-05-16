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

from .models import CharacterRow, GrastaRow, OreRow, PassiveSkillRow, SkillRow

logger = logging.getLogger(__name__)

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
        "CREATE CONSTRAINT skill_identity IF NOT EXISTS FOR (s:Skill) REQUIRE (s.character_name, s.name) IS UNIQUE",
        "CREATE CONSTRAINT passive_skill_identity IF NOT EXISTS FOR (p:PassiveSkill) REQUIRE (p.character_name, p.name) IS UNIQUE",
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
    g.is_shareable = row.is_shareable
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
        }
        for r in rows
    ]

    # Ore nodes only — no relationship edges created (standalone per GRAPH-06)
    cypher_nodes = """
UNWIND $rows AS row
MERGE (o:Ore {name: row.name})
SET o.stats = row.stats,
    o.source = row.source
"""
    async with driver.session() as session:
        await session.run(cypher_nodes, rows=ore_data)

    logger.info("Loaded %d Ore nodes", len(rows))


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
