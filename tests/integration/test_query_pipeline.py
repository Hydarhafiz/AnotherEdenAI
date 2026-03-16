"""Integration tests for Phase 3 query pipeline.

Covers QUERY-01 through QUERY-04 against live Neo4j (loaded graph required).
Run with: pytest tests/integration/test_query_pipeline.py -m integration -x -q

Requires:
  - NEO4J_URI and NEO4J_AUTH set in .env
  - Graph loaded with Phase 1 ETL data (loaded_db fixture handles this)
"""
import pytest
from src.workflow.normalize import normalize_character_name, normalize_roster
from src.workflow.f2p import F2P_CHARACTERS, augment_with_f2p


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
    # At minimum, owned characters should be present
    assert len(returned_names) >= len(owned_roster), (
        f"Expected at least {len(owned_roster)} characters, got {len(returned_names)}"
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
    """QUERY-04: normalize_roster resolves mixed-case inputs to canonical names.

    'ALDO' and 'ciel' should both resolve to their canonical forms.
    """
    result = await normalize_roster(async_driver, ["ALDO", "ciel"])
    assert "Aldo" in result, f"Expected 'Aldo' in normalized roster, got {result}"
    assert "Ciel" in result, f"Expected 'Ciel' in normalized roster, got {result}"
