"""Unit tests for F2P helpers — F2P_CHARACTERS constant and augment_with_f2p.

Pure sync tests — no async needed (no DB calls involved).
"""
import pytest

from src.workflow.f2p import F2P_CHARACTERS, augment_with_f2p


# ---------------------------------------------------------------------------
# F2P_CHARACTERS constant tests
# ---------------------------------------------------------------------------

class TestF2PCharactersConstant:
    """Tests for the F2P_CHARACTERS list."""

    def test_minimum_six_characters(self):
        """F2P_CHARACTERS must contain at least 6 entries."""
        assert len(F2P_CHARACTERS) >= 6

    def test_aldo_is_present(self):
        """'Aldo' must be in F2P_CHARACTERS — he is the permanent story protagonist."""
        assert "Aldo" in F2P_CHARACTERS

    def test_required_story_characters_present(self):
        """Core story-permanent characters must all be present."""
        required = {"Aldo", "Feinne", "Cyrus", "Gariyu", "Cerrine", "Azami"}
        missing = required - set(F2P_CHARACTERS)
        assert not missing, f"Missing required F2P characters: {missing}"

    def test_no_collaboration_characters(self):
        """Collaboration/limited characters must NOT be in F2P_CHARACTERS."""
        collab_chars = ["Joker", "Morgana"]
        for char in collab_chars:
            assert char not in F2P_CHARACTERS, (
                f"Collaboration character '{char}' should not be in F2P_CHARACTERS"
            )

    def test_is_list_of_strings(self):
        """F2P_CHARACTERS must be a list of strings."""
        assert isinstance(F2P_CHARACTERS, list)
        for item in F2P_CHARACTERS:
            assert isinstance(item, str), f"Expected str, got {type(item)} for {item!r}"

    def test_no_duplicates(self):
        """F2P_CHARACTERS must not contain duplicate entries."""
        assert len(F2P_CHARACTERS) == len(set(F2P_CHARACTERS))


# ---------------------------------------------------------------------------
# augment_with_f2p tests
# ---------------------------------------------------------------------------

class TestAugmentWithF2p:
    """Tests for augment_with_f2p(roster)."""

    def test_includes_caller_provided_characters(self):
        """augment_with_f2p(['Ciel']) -> result contains 'Ciel'."""
        result = augment_with_f2p(["Ciel"])
        assert "Ciel" in result

    def test_includes_all_f2p_characters(self):
        """augment_with_f2p(['Ciel']) -> result contains all F2P_CHARACTERS."""
        result = augment_with_f2p(["Ciel"])
        for f2p in F2P_CHARACTERS:
            assert f2p in result, f"F2P character '{f2p}' missing from augmented result"

    def test_no_duplicates_when_f2p_already_in_roster(self):
        """'Aldo' in both roster and F2P_CHARACTERS -> appears exactly once."""
        assert "Aldo" in F2P_CHARACTERS  # precondition
        result = augment_with_f2p(["Aldo"])
        assert result.count("Aldo") == 1

    def test_empty_roster_returns_exactly_f2p(self):
        """augment_with_f2p([]) -> returns exactly F2P_CHARACTERS content."""
        result = augment_with_f2p([])
        assert sorted(result) == sorted(F2P_CHARACTERS)

    def test_does_not_mutate_input(self):
        """augment_with_f2p must not modify the caller's roster list."""
        roster = ["Ciel"]
        augment_with_f2p(roster)
        assert roster == ["Ciel"]

    def test_returned_list_has_no_duplicates(self):
        """Result list must have no duplicate entries."""
        result = augment_with_f2p(["Aldo", "Ciel"])
        assert len(result) == len(set(result))

    def test_roster_characters_preserved_in_order(self):
        """Original roster characters appear before F2P additions."""
        result = augment_with_f2p(["Ciel", "SomeOtherChar"])
        assert result[0] == "Ciel"
        assert result[1] == "SomeOtherChar"
