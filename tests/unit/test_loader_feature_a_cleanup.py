"""Milestone 5 Feature A sidekick/character cleanup tests."""

import pytest

from src.etl.loader import (
    cleanup_duplicate_sidekick_characters,
    find_sidekick_character_overlaps,
)


class AsyncResult:
    def __init__(self, rows):
        self.rows = rows

    def __aiter__(self):
        self._iterator = iter(self.rows)
        return self

    async def __anext__(self):
        try:
            return next(self._iterator)
        except StopIteration:
            raise StopAsyncIteration


class RecordingSession:
    def __init__(self, calls, query_rows):
        self.calls = calls
        self.query_rows = query_rows

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def run(self, cypher, **params):
        self.calls.append((cypher, params))
        if "RETURN" in cypher:
            return AsyncResult(self.query_rows)
        return AsyncResult([])


class RecordingDriver:
    def __init__(self, query_rows):
        self.calls = []
        self.query_rows = query_rows

    def session(self):
        return RecordingSession(self.calls, self.query_rows)


def overlap_row(name, *, cleanup_candidate):
    return {
        "name": name,
        "element": None,
        "weapon": None,
        "light_shadow": None,
        "character_detail_url": None,
        "sidekick_source_url": f"https://example.test/{name}",
        "skill_count": 0 if cleanup_candidate else 3,
        "passive_skill_count": 0,
        "unlock_relationship_count": 0 if cleanup_candidate else 1,
        "lacks_character_detail": cleanup_candidate,
        "sidekick_like_origin": True,
        "cleanup_candidate": cleanup_candidate,
    }


@pytest.mark.asyncio
async def test_find_sidekick_character_overlaps_reports_exact_name_matches_without_delete():
    driver = RecordingDriver([overlap_row("Tetra", cleanup_candidate=True)])

    rows = await find_sidekick_character_overlaps(driver)

    assert [row["name"] for row in rows] == ["Tetra"]
    assert len(driver.calls) == 1
    cypher, params = driver.calls[0]
    assert "MATCH (c:Character)" in cypher
    assert "MATCH (s:Sidekick {name: c.name})" in cypher
    assert "DETACH DELETE" not in cypher
    assert params == {}


@pytest.mark.asyncio
async def test_cleanup_duplicate_sidekick_characters_deletes_only_confirmed_candidates():
    driver = RecordingDriver(
        [
            overlap_row("Tetra", cleanup_candidate=True),
            overlap_row("Minalca", cleanup_candidate=False),
        ]
    )

    rows = await cleanup_duplicate_sidekick_characters(driver)

    assert [row["name"] for row in rows] == ["Tetra", "Minalca"]
    assert len(driver.calls) == 2
    delete_cypher, delete_params = driver.calls[1]
    assert delete_params == {"names": ["Tetra"]}
    assert "MATCH (:Sidekick {name: name})" in delete_cypher
    assert "NOT (c)-[:HAS_SKILL]->(:Skill)" in delete_cypher
    assert "NOT (c)-[:HAS_PASSIVE_SKILL]->(:PassiveSkill)" in delete_cypher
    assert "NOT (c)-[:UNLOCKS_SIDEKICK]->(:Sidekick)" in delete_cypher
    assert "DETACH DELETE c" in delete_cypher


@pytest.mark.asyncio
async def test_cleanup_duplicate_sidekick_characters_skips_delete_when_no_candidates():
    driver = RecordingDriver([overlap_row("Minalca", cleanup_candidate=False)])

    rows = await cleanup_duplicate_sidekick_characters(driver)

    assert [row["name"] for row in rows] == ["Minalca"]
    assert len(driver.calls) == 1
    assert "DETACH DELETE" not in driver.calls[0][0]
