"""Character name normalization helpers for the AnotherEdenAI workflow.

Resolves player-supplied character names (case-insensitive, partial match)
to the canonical graph names stored in Neo4j.

Functions:
    normalize_character_name(driver, input_name) -> str | None
    normalize_roster(driver, roster) -> list[str]

Both functions require an async Neo4j driver and must be awaited.
"""


async def normalize_character_name(driver, input_name: str) -> str | None:
    """Resolve a player-supplied name to the canonical graph name.

    Performs a case-insensitive exact-or-contains match against Character nodes,\n    excluding stale nodes whose names exactly overlap Sidekick nodes.
    Returns the shortest matching canonical name (prioritises exact matches via
    ORDER BY size(c.name) ASC), or None if no match is found.

    Args:
        driver: Async Neo4j driver instance (AsyncGraphDatabase.driver).
        input_name: Player-supplied character name (any case, may be abbreviated).

    Returns:
        Canonical name string as stored in Neo4j, or None if no match found.
    """
    records, _, _ = await driver.execute_query(
        """
        MATCH (c:Character)
        WHERE (
          toLower(c.name) = toLower($input)
          OR toLower(c.name) CONTAINS toLower($input)
        )
        AND NOT EXISTS {
          MATCH (s:Sidekick)
          WHERE toLower(s.name) = toLower(c.name)
        }
        RETURN c.name AS canonical
        ORDER BY size(c.name) ASC
        LIMIT 1
        """,
        input=input_name,
        database_="neo4j",
    )
    return records[0]["canonical"] if records else None


async def normalize_roster(driver, roster: list[str]) -> list[str]:
    """Normalize a list of player-supplied names to canonical graph names.

    Processes each name through normalize_character_name and drops any that
    cannot be resolved (returns None). Preserves order of successfully resolved
    entries.

    Args:
        driver: Async Neo4j driver instance.
        roster: List of player-supplied character names.

    Returns:
        List of canonical names; unknown/unresolvable names are omitted.
    """
    normalized = []
    for name in roster:
        canonical = await normalize_character_name(driver, name)
        if canonical:
            normalized.append(canonical)
    return normalized
