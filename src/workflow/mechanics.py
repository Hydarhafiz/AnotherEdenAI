"""Mechanics-reference retrieval helpers for recommendation reasoning."""

from __future__ import annotations

from typing import Any


async def retrieve_mechanic_references(
    driver,
    *,
    topic_tags: list[str] | None = None,
    applies_to: list[str] | None = None,
    mechanic_types: list[str] | None = None,
    limit: int = 8,
) -> list[dict[str, Any]]:
    """Retrieve curated battle mechanics separately from entity facts."""
    topic_tags = topic_tags or []
    applies_to = applies_to or []
    mechanic_types = mechanic_types or []

    cypher = """
MATCH (m:MechanicReference)
WITH m,
     size([tag IN $topic_tags WHERE tag IN m.topic_tags]) AS topic_hits,
     size([target IN $applies_to WHERE target IN m.applies_to]) AS applies_hits,
     CASE WHEN m.mechanic_type IN $mechanic_types THEN 1 ELSE 0 END AS type_hit
WHERE ($topic_tags = [] AND $applies_to = [] AND $mechanic_types = [])
   OR topic_hits > 0
   OR applies_hits > 0
   OR type_hit > 0
RETURN m {
    .id,
    .title,
    .source_url,
    .source_page,
    .section_path,
    .mechanic_type,
    .topic_tags,
    .applies_to,
    .rules_text,
    .summary,
    .caveats,
    .schema_version
} AS reference,
(topic_hits + applies_hits + type_hit) AS score
ORDER BY score DESC, m.id ASC
LIMIT $limit
"""
    async with driver.session() as session:
        result = await session.run(
            cypher,
            topic_tags=topic_tags,
            applies_to=applies_to,
            mechanic_types=mechanic_types,
            limit=limit,
        )
        return [record["reference"] async for record in result]
