"""Integration tests for Phase 3 query pipeline.

Covers QUERY-01 through QUERY-04 against live Neo4j (loaded graph required).
Run with: pytest tests/integration/test_query_pipeline.py -m integration -x -q

Requires:
  - NEO4J_URI and NEO4J_AUTH set in .env
  - Graph loaded with Phase 1 ETL data (loaded_db fixture handles this)
"""
import time

import pytest

import src.workflow.run as run
from src.workflow.f2p import F2P_CHARACTERS, augment_with_f2p
from src.workflow.normalize import normalize_character_name, normalize_roster


# ---------------------------------------------------------------------------
# QUERY-01: CSV roster parsing (pure Python — no DB required)
# ---------------------------------------------------------------------------

def test_roster_input_csv_parsing():
    """QUERY-01: Raw CSV input is correctly parsed to a clean list of names.

    This is a pure Python test — no DB fixture needed.
    """
    raw_input = "Aldo, Ciel,Shion"
    roster = [name.strip() for name in raw_input.split(",") if name.strip()]
    assert roster == ["Aldo", "Ciel", "Shion"]


# ---------------------------------------------------------------------------
# QUERY-02: Roster filtering — only owned + F2P characters returned
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_roster_filtering_excludes_unowned(async_driver, loaded_db):
    """QUERY-02: Querying by roster returns only owned + F2P characters.

    Builds the full roster (owned + F2P), queries Character nodes filtered
    by that roster, and asserts no unowned characters appear in the results.
    """
    owned_roster = ["Aldo", "Ciel"]
    full_roster = augment_with_f2p(owned_roster)
    full_roster_set = set(full_roster)

    records, _, _ = await async_driver.execute_query(
        "MATCH (c:Character) WHERE c.name IN $roster RETURN c.name AS name",
        roster=full_roster,
        database_="neo4j",
    )

    returned_names = [r["name"] for r in records]
    # Every returned name must be in the allowed roster
    for name in returned_names:
        assert name in full_roster_set, (
            f"Unexpected character '{name}' returned — not in full_roster"
        )
    # At least one character must be present (F2P chars are the minimum guarantee)
    assert len(returned_names) >= 1, (
        f"Expected at least one character from the full roster, got 0. "
        f"Full roster queried: {full_roster}"
    )


@pytest.mark.integration
async def test_f2p_augmentation_adds_known_characters(async_driver, loaded_db):
    """QUERY-02: F2P augmentation adds Aldo (known F2P) without duplicating Ciel.

    Thematically grouped with QUERY-02 even though it is pure Python logic.
    The loaded_db fixture is included for thematic grouping — DB not queried.
    """
    augmented = augment_with_f2p(["Ciel"])
    assert "Aldo" in augmented, "Aldo must be in F2P-augmented roster"
    assert augmented.count("Ciel") == 1, "Ciel must not be duplicated"


# ---------------------------------------------------------------------------
# QUERY-03: Grasta synergy — Character + Trait + Grasta traversal
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_known_good_grasta_synergy(async_driver, loaded_db):
    """QUERY-03: Aldo has at least one trait matching a shareable Attack Grasta.

    Uses the known-good Cypher verified against SCHEMA.md v1.0.0.
    Confirms the HAS_TRAIT + REQUIRES_TRAIT path works end-to-end.
    """
    roster = ["Aldo"]
    records, _, _ = await async_driver.execute_query(
        """
        MATCH (c:Character)-[:HAS_TRAIT]->(t:Trait)<-[:REQUIRES_TRAIT]-(g:Grasta)
        WHERE c.name IN $roster
          AND g.is_shareable = true
          AND g.category = 'Attack'
        RETURN c.name AS character, t.name AS shared_trait, g.name AS grasta
        """,
        roster=roster,
        database_="neo4j",
    )

    assert len(records) > 0, (
        "Expected at least one Aldo-Trait-Grasta match; "
        "HAS_TRAIT + REQUIRES_TRAIT path may be broken"
    )
    # All records must have the expected keys
    # Use record.keys() — Neo4j Record.__contains__ checks values, not keys
    for record in records:
        keys = record.keys()
        assert "character" in keys, f"Missing 'character' key in {record.data()}"
        assert "shared_trait" in keys, f"Missing 'shared_trait' key in {record.data()}"
        assert "grasta" in keys, f"Missing 'grasta' key in {record.data()}"


# ---------------------------------------------------------------------------
# QUERY-04: Name normalization — case-insensitive lookup
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_name_normalization_lowercase(async_driver, loaded_db):
    """QUERY-04: 'aldo' (lowercase) normalizes to canonical 'Aldo'.

    Confirms case-insensitive toLower() matching works against live graph.
    """
    result = await normalize_character_name(async_driver, "aldo")
    assert result == "Aldo", (
        f"Expected 'Aldo' from lowercase 'aldo', got {result!r}"
    )


@pytest.mark.integration
async def test_name_normalization_exact_match_preferred(async_driver, loaded_db):
    """QUERY-04: Exact match 'Aldo' returns canonical 'Aldo' (shortest result wins).

    ORDER BY size(c.name) ASC ensures the base name is preferred over
    alternate-style names like 'Aldo (Another Style)'.
    """
    result = await normalize_character_name(async_driver, "Aldo")
    assert result == "Aldo", (
        f"Expected exact match 'Aldo', got {result!r}"
    )


@pytest.mark.integration
async def test_normalize_roster_end_to_end(async_driver, loaded_db):
    """QUERY-04: normalize_roster resolves valid names and drops unknown ones.

    'ALDO' normalizes to canonical 'Aldo'. An unknown name is silently dropped.
    Tests both case normalization and unresolvable-name filtering in one pass.
    """
    result = await normalize_roster(async_driver, ["ALDO", "NONEXISTENT_CHAR_XYZ"])
    assert "Aldo" in result, f"Expected 'Aldo' in normalized roster, got {result}"
    assert "NONEXISTENT_CHAR_XYZ" not in result, (
        f"Expected unknown character to be dropped from roster, got {result}"
    )


# ---------------------------------------------------------------------------
# QUERY-01 + QUERY-02: Empty roster graceful degradation
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_empty_roster_graceful_degradation(async_driver, loaded_db):
    """QUERY-01 + QUERY-02: Empty owned roster returns F2P characters, not an error.

    When a player owns no characters, augment_with_f2p([]) produces the F2P-only
    roster. Querying that roster must return non-empty results (F2P chars exist in
    graph) and every returned name must be a known F2P character.
    """
    full_roster = augment_with_f2p([])
    assert len(full_roster) > 0, "augment_with_f2p([]) must produce at least one character"

    records, _, _ = await async_driver.execute_query(
        "MATCH (c:Character) WHERE c.name IN $roster RETURN c.name AS name",
        roster=full_roster,
        database_="neo4j",
    )

    returned_names = [r["name"] for r in records]
    assert len(returned_names) > 0, (
        "Expected at least one F2P character to be present in the graph; "
        f"F2P roster queried: {full_roster}"
    )
    # Every returned name must be in the F2P set
    for name in returned_names:
        assert name in F2P_CHARACTERS, (
            f"'{name}' was returned but is not in F2P_CHARACTERS — "
            "check augment_with_f2p or F2P_CHARACTERS constant"
        )


# ---------------------------------------------------------------------------
# QUERY-03: End-to-end pipeline with latency measurement
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_end_to_end_pipeline_with_latency(loaded_db):
    """QUERY-03: Full pipeline completes under 15s and returns a dict.

    Invokes run.main() (plan -> cypher -> validate -> analyze -> format) against
    the live graph. Measures wall-clock latency and asserts the 15s SLO.
    An error dict is acceptable if LLM credentials are not configured — the key
    requirement is no unhandled exception and elapsed < 15s.
    """
    roster = ["Aldo", "Ciel"]
    query = "highest damage blunt zone synergy"

    start = time.monotonic()
    result = await run.main(roster, query)
    elapsed = time.monotonic() - start

    print(f"End-to-end latency: {elapsed:.2f}s")  # baseline for Phase 5 reference

    assert isinstance(result, dict), (
        f"run.main() must return a dict (got {type(result).__name__})"
    )
    assert elapsed < 15.0, (
        f"End-to-end latency {elapsed:.2f}s exceeded 15s SLO"
    )


# ---------------------------------------------------------------------------
# QUERY-03: Grasta synergy — three team archetypes
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_grasta_synergy_three_archetypes(async_driver, loaded_db):
    """QUERY-03: Three distinct team archetypes are represented in the graph.

    1. Attack archetype: shareable Attack Grasta — non-empty for Aldo roster
    2. Support archetype: Support Grasta — non-empty results exist in graph
    3. Personality-based AF Special: Aldo has at least one trait in graph
    """
    roster = ["Aldo"]

    # --- Archetype 1: Attack synergy (shareable Attack Grasta for Aldo) ---
    records_attack, _, _ = await async_driver.execute_query(
        """
        MATCH (c:Character)-[:HAS_TRAIT]->(t:Trait)<-[:REQUIRES_TRAIT]-(g:Grasta)
        WHERE c.name IN $roster
          AND g.category = 'Attack'
          AND g.is_shareable = true
        RETURN c.name AS character, g.name AS grasta
        """,
        roster=roster,
        database_="neo4j",
    )
    if not records_attack:
        pytest.fail(
            "Attack archetype: expected at least one shareable Attack Grasta "
            f"matching Aldo's traits; got none. "
            "Check HAS_TRAIT + REQUIRES_TRAIT path for Attack grastas."
        )

    # --- Archetype 2: Non-attack archetype — Life or Support Grasta exists in graph ---
    records_nonatk, _, _ = await async_driver.execute_query(
        """
        MATCH (g:Grasta)
        WHERE g.category IN ['Life', 'Support']
        RETURN g.name AS grasta, g.category AS category
        LIMIT 1
        """,
        database_="neo4j",
    )
    if not records_nonatk:
        pytest.skip(
            "Non-attack archetype: Life/Support Grasta category not yet loaded "
            "(ETL may be incomplete — re-run when wiki is accessible to populate all categories)"
        )

    # --- Archetype 3: Personality-based AF Special — Aldo has traits ---
    records_traits, _, _ = await async_driver.execute_query(
        """
        MATCH (c:Character)-[:HAS_TRAIT]->(t:Trait)
        WHERE c.name IN $roster
        RETURN c.name AS character, collect(t.name) AS traits
        """,
        roster=roster,
        database_="neo4j",
    )
    if not records_traits or not records_traits[0]["traits"]:
        pytest.fail(
            "AF trait archetype: expected Aldo to have at least one trait; "
            "got none. Check HAS_TRAIT relationships for Aldo in the graph."
        )
