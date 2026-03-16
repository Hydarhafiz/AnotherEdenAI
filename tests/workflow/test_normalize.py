"""Unit tests for normalize helpers — normalize_character_name and normalize_roster.

Uses AsyncMock driver to avoid requiring a real Neo4j connection.
All tests are async (normalized functions use await internally).
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.workflow.normalize import normalize_character_name, normalize_roster


@pytest.fixture
def mock_driver():
    """AsyncMock driver where execute_query is an AsyncMock."""
    driver = MagicMock()
    driver.execute_query = AsyncMock()
    return driver


# ---------------------------------------------------------------------------
# normalize_character_name tests
# ---------------------------------------------------------------------------

class TestNormalizeCharacterName:
    """Tests for normalize_character_name(driver, input_name)."""

    @pytest.mark.asyncio
    async def test_returns_canonical_for_lowercase_input(self, mock_driver):
        """'aldo' with driver returning [{'canonical': 'Aldo'}] -> returns 'Aldo'."""
        mock_driver.execute_query.return_value = ([{"canonical": "Aldo"}], None, None)
        result = await normalize_character_name(mock_driver, "aldo")
        assert result == "Aldo"

    @pytest.mark.asyncio
    async def test_returns_none_for_unknown_input(self, mock_driver):
        """Unknown character with driver returning [] -> returns None."""
        mock_driver.execute_query.return_value = ([], None, None)
        result = await normalize_character_name(mock_driver, "unknown_char_xyz")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_canonical_for_alternate_style(self, mock_driver):
        """'Aldo AS' with driver returning [{'canonical': 'Aldo (Another Style)'}] -> returns full canonical."""
        mock_driver.execute_query.return_value = (
            [{"canonical": "Aldo (Another Style)"}], None, None
        )
        result = await normalize_character_name(mock_driver, "Aldo AS")
        assert result == "Aldo (Another Style)"

    @pytest.mark.asyncio
    async def test_calls_execute_query_with_correct_params(self, mock_driver):
        """execute_query called with input kwarg and database_='neo4j'."""
        mock_driver.execute_query.return_value = ([{"canonical": "Ciel"}], None, None)
        await normalize_character_name(mock_driver, "ciel")
        mock_driver.execute_query.assert_called_once()
        call_kwargs = mock_driver.execute_query.call_args.kwargs
        assert call_kwargs.get("input") == "ciel"
        assert call_kwargs.get("database_") == "neo4j"

    @pytest.mark.asyncio
    async def test_returns_first_canonical_when_multiple(self, mock_driver):
        """When driver returns multiple records, first canonical is returned."""
        mock_driver.execute_query.return_value = (
            [{"canonical": "Aldo"}, {"canonical": "Aldo (Another Style)"}], None, None
        )
        result = await normalize_character_name(mock_driver, "aldo")
        assert result == "Aldo"


# ---------------------------------------------------------------------------
# normalize_roster tests
# ---------------------------------------------------------------------------

class TestNormalizeRoster:
    """Tests for normalize_roster(driver, roster)."""

    @pytest.mark.asyncio
    async def test_drops_none_entries(self, mock_driver):
        """['ALDO', 'unknown_char'] with mock returning ['Aldo', None] -> ['Aldo']."""
        # First call returns "Aldo", second returns None (empty records)
        mock_driver.execute_query.side_effect = [
            ([{"canonical": "Aldo"}], None, None),
            ([], None, None),
        ]
        result = await normalize_roster(mock_driver, ["ALDO", "unknown_char"])
        assert result == ["Aldo"]

    @pytest.mark.asyncio
    async def test_empty_input_returns_empty(self, mock_driver):
        """Empty list input -> returns []."""
        result = await normalize_roster(mock_driver, [])
        assert result == []
        mock_driver.execute_query.assert_not_called()

    @pytest.mark.asyncio
    async def test_all_resolved_entries_returned(self, mock_driver):
        """All roster entries resolved -> all returned in order."""
        mock_driver.execute_query.side_effect = [
            ([{"canonical": "Aldo"}], None, None),
            ([{"canonical": "Ciel"}], None, None),
        ]
        result = await normalize_roster(mock_driver, ["aldo", "ciel"])
        assert result == ["Aldo", "Ciel"]

    @pytest.mark.asyncio
    async def test_all_unknown_returns_empty(self, mock_driver):
        """All unknown entries -> returns []."""
        mock_driver.execute_query.side_effect = [
            ([], None, None),
            ([], None, None),
        ]
        result = await normalize_roster(mock_driver, ["xyz1", "xyz2"])
        assert result == []
