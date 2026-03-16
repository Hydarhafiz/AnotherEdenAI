"""Free-to-play (F2P) character helpers for the AnotherEdenAI workflow.

F2P characters are story-permanent — every player has them regardless of roster.
The workflow uses these to ensure recommendations always have a valid fallback set.

Constants:
    F2P_CHARACTERS: List of canonical F2P character names (story-permanent only).

Functions:
    augment_with_f2p(roster) -> list[str]

Source: anothereden.wiki/w/Free_Characters (story-permanent only)
NOTE: Do NOT include collaboration characters (Joker, Morgana) — limited availability.
TODO: expand list from anothereden.wiki/w/Free_Characters as new story content is added.
"""

# F2P characters are always available regardless of roster.
# Source: anothereden.wiki/w/Free_Characters (story-permanent only)
# NOTE: Do NOT include collaboration characters (Joker, Morgana) — limited availability.
# TODO: expand list from anothereden.wiki/w/Free_Characters as new story content is added
F2P_CHARACTERS = [
    "Aldo", "Feinne", "Cyrus", "Deirdre", "Azami",
    "Gariyu", "Cerrine", "Levia",
]


def augment_with_f2p(roster: list[str]) -> list[str]:
    """Add F2P characters to a roster, deduplicating as needed.

    Preserves the caller's roster order, then appends any F2P characters not
    already present. Does not modify the caller's list.

    Args:
        roster: Player's current character roster (canonical names).

    Returns:
        New list containing all roster entries plus any F2P characters not
        already in the roster. No duplicates.
    """
    combined = list(roster)
    for f2p in F2P_CHARACTERS:
        if f2p not in combined:
            combined.append(f2p)
    return combined
