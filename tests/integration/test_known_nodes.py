"""Integration tests for known graph nodes and relationships.

Requires a running Neo4j instance with loaded data (docker compose up + python src/etl/run_etl.py).

Requirements covered:
- GRAPH-01: Character node has element, weapon, light_shadow, name
- GRAPH-02: Character linked to Trait nodes via HAS_TRAIT
- GRAPH-03: Grasta node has is_shareable, personality_req, category, tier, stats
- GRAPH-04: Shareable Grasta has is_shareable=True
- GRAPH-05: Grasta linked to Trait via REQUIRES_TRAIT
- GRAPH-06: Ore node exists with stats and source (no ENHANCES relationship)
"""
import pytest
from src.etl.run_etl import main as run_etl_main


@pytest.mark.integration
async def test_character_properties(async_driver, clean_db):
    """Query Aldo and verify element, weapon, light_shadow properties.

    Reference: SCHEMA.md — Character node properties
    """
    await run_etl_main(driver=async_driver)
    records, _, _ = await async_driver.execute_query(
        "MATCH (c:Character {name: 'Aldo'}) RETURN c",
        database_="neo4j",
    )
    assert len(records) == 1
    c = records[0]["c"]
    assert c["element"] == "Wind"
    assert c["weapon"] == "Sword"
    assert c["light_shadow"] == "Light"


@pytest.mark.integration
async def test_character_traits(async_driver, clean_db):
    """Verify Aldo is linked to at least one Trait node via HAS_TRAIT.

    Reference: SCHEMA.md — (:Character)-[:HAS_TRAIT]->(:Trait)
    """
    await run_etl_main(driver=async_driver)
    records, _, _ = await async_driver.execute_query(
        "MATCH (c:Character {name: 'Aldo'})-[:HAS_TRAIT]->(t:Trait) RETURN t.name AS name",
        database_="neo4j",
    )
    assert len(records) >= 1


@pytest.mark.integration
async def test_grasta_properties(async_driver, clean_db):
    """Verify a shareable Grasta has all required properties.

    Reference: SCHEMA.md — Grasta node properties
    """
    await run_etl_main(driver=async_driver)
    records, _, _ = await async_driver.execute_query(
        "MATCH (g:Grasta) WHERE g.is_shareable = true RETURN g LIMIT 1",
        database_="neo4j",
    )
    assert len(records) >= 1
    g = records[0]["g"]
    assert g["is_shareable"] is True
    assert g["category"] in ["Attack", "Life", "Support", "Special"]
    assert isinstance(g["tier"], int)
    assert g["stats"]  # non-empty


@pytest.mark.integration
async def test_grasta_requires_trait(async_driver, clean_db):
    """Verify a non-VC Grasta with personality_req has a REQUIRES_TRAIT edge to a Trait node.

    Reference: SCHEMA.md — (:Grasta)-[:REQUIRES_TRAIT]->(:Trait)
    Reference: 01-RESEARCH.md Pitfall 3 — VC Grastas Creating Spurious REQUIRES_TRAIT Edges
    """
    await run_etl_main(driver=async_driver)
    records, _, _ = await async_driver.execute_query(
        """
        MATCH (g:Grasta)-[:REQUIRES_TRAIT]->(t:Trait)
        WHERE g.category <> 'VC'
        RETURN g.name AS name, t.name AS trait LIMIT 1
        """,
        database_="neo4j",
    )
    assert len(records) >= 1


@pytest.mark.integration
async def test_no_vc_requires_trait(async_driver, clean_db):
    """Verify VC Grastas have ZERO REQUIRES_TRAIT edges.

    Reference: 01-RESEARCH.md Pitfall 3 — VC Grastas must not have REQUIRES_TRAIT edges
    """
    await run_etl_main(driver=async_driver)
    records, _, _ = await async_driver.execute_query(
        "MATCH (g:Grasta {category: 'VC'})-[:REQUIRES_TRAIT]->() RETURN count(*) AS cnt",
        database_="neo4j",
    )
    assert records[0]["cnt"] == 0  # VC grastas must have ZERO REQUIRES_TRAIT edges


@pytest.mark.integration
async def test_ore_properties(async_driver, clean_db):
    """Verify Ore nodes have stats and source properties (no ENHANCES relationship tested).

    Reference: SCHEMA.md — Ore is standalone; no ENHANCES relationship
    Reference: 01-CONTEXT.md — Ore nodes are STANDALONE entities
    """
    await run_etl_main(driver=async_driver)
    records, _, _ = await async_driver.execute_query(
        "MATCH (o:Ore) RETURN o LIMIT 1",
        database_="neo4j",
    )
    assert len(records) >= 1
    o = records[0]["o"]
    assert o["name"]
    assert o["stats"]
    assert o["source"]
