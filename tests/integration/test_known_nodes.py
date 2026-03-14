"""Integration tests for known graph nodes and relationships.

Wave 0 stubs — these tests are skipped until ETL loads real data in Plan 01-03.
Requires a running Neo4j instance with loaded data (docker compose up + python -m src.etl.loader).

Requirements covered:
- GRAPH-01: Character node has element, weapon, light_shadow, name
- GRAPH-02: Character linked to Trait nodes via HAS_TRAIT
- GRAPH-03: Grasta node has is_shareable, personality_req, category, tier, stats
- GRAPH-04: Shareable Grasta has is_shareable=True
- GRAPH-05: Grasta linked to Trait via REQUIRES_TRAIT
- GRAPH-06: Ore node exists with stats and source (no ENHANCES relationship)
"""
import pytest


@pytest.mark.skip(reason="TODO Plan 01-03: load real data and verify against known wiki values")
async def test_character_properties(async_driver):
    """Query a known character and verify element, weapon, light_shadow properties.

    TODO: Choose a known character (e.g., "Aldo") and query the graph.
    Expected: Character node exists with correct element, weapon, and light_shadow values
    matching the wiki.

    Reference: SCHEMA.md — Character node properties
    """
    pass


@pytest.mark.skip(reason="TODO Plan 01-03: load real data and verify HAS_TRAIT relationships")
async def test_character_traits(async_driver):
    """Verify a known character is linked to expected Trait nodes via HAS_TRAIT.

    TODO: Choose a character with known personality traits.
    Query: MATCH (c:Character {name: $name})-[:HAS_TRAIT]->(t:Trait) RETURN t.name
    Expected: All known personality traits appear as linked Trait nodes.

    Reference: SCHEMA.md — (:Character)-[:HAS_TRAIT]->(:Trait)
    """
    pass


@pytest.mark.skip(reason="TODO Plan 01-03: load real data and verify Grasta node properties")
async def test_grasta_properties(async_driver):
    """Verify a known Grasta node has all required properties.

    TODO: Choose a known grasta and query the graph.
    Expected: Grasta node has is_shareable, personality_req, category, tier, stats properties.

    Reference: SCHEMA.md — Grasta node properties
    """
    pass


@pytest.mark.skip(reason="TODO Plan 01-03: load real data and verify is_shareable flag")
async def test_shareable_grasta(async_driver):
    """Verify that a known shareable Grasta has is_shareable=True.

    TODO: Choose a grasta that is known to be shareable (data-share="1" on wiki).
    Query: MATCH (g:Grasta {name: $name}) RETURN g.is_shareable
    Expected: is_shareable = True

    Reference: SCHEMA.md — Grasta.is_shareable
    """
    pass


@pytest.mark.skip(reason="TODO Plan 01-03: load real data and verify REQUIRES_TRAIT relationships")
async def test_grasta_requires_trait(async_driver):
    """Verify a non-VC Grasta is linked to a Trait via REQUIRES_TRAIT.

    TODO: Choose a non-VC grasta with a known personality_req.
    Query: MATCH (g:Grasta {name: $name})-[:REQUIRES_TRAIT]->(t:Trait) RETURN t.name
    Expected: Trait node with correct name is linked.
    Also verify: VC grastas do NOT have REQUIRES_TRAIT edges.

    Reference: SCHEMA.md — (:Grasta)-[:REQUIRES_TRAIT]->(:Trait)
    Reference: 01-RESEARCH.md Pitfall 3 — VC Grastas Creating Spurious REQUIRES_TRAIT Edges
    """
    pass


@pytest.mark.skip(reason="TODO Plan 01-03: load real data and verify Ore node properties")
async def test_ore_properties(async_driver):
    """Verify an Ore node has stats and source properties (no ENHANCES relationship tested).

    TODO: Choose a known ore (e.g., "AF After Victory Ore").
    Query: MATCH (o:Ore {name: $name}) RETURN o.stats, o.source
    Expected: stats and source match wiki values.
    Also verify: No (:Ore)-[:ENHANCES]->(:Grasta) relationships exist in the graph.

    Reference: SCHEMA.md — Ore is standalone; no ENHANCES relationship
    Reference: 01-CONTEXT.md — Ore nodes are STANDALONE entities
    """
    pass
