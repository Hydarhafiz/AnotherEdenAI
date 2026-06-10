"""Tests for mechanics-reference retrieval."""

from __future__ import annotations

import pytest

from src.workflow.mechanics import retrieve_mechanic_references


class AsyncRecordStream:
    def __init__(self, records):
        self._records = list(records)

    def __aiter__(self):
        self._iter = iter(self._records)
        return self

    async def __anext__(self):
        try:
            return next(self._iter)
        except StopIteration as exc:
            raise StopAsyncIteration from exc


class RecordingSession:
    def __init__(self, calls, records):
        self.calls = calls
        self.records = records

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def run(self, cypher, **params):
        self.calls.append((cypher, params))
        return AsyncRecordStream(self.records)


class RecordingDriver:
    def __init__(self, records):
        self.calls = []
        self.records = records

    def session(self):
        return RecordingSession(self.calls, self.records)


@pytest.mark.asyncio
async def test_retrieve_mechanic_references_queries_only_mechanic_reference_nodes():
    reference = {
        "id": "speed-preemptive-delayed-turn-order",
        "title": "Speed, Preemptive, Delayed, And Turn Order Basics",
        "topic_tags": ["speed", "turn-order"],
    }
    driver = RecordingDriver(records=[{"reference": reference}])

    rows = await retrieve_mechanic_references(
        driver,
        topic_tags=["speed"],
        applies_to=["boss_counterplay"],
        mechanic_types=["turn_order"],
        limit=3,
    )

    assert rows == [reference]
    assert len(driver.calls) == 1
    cypher, params = driver.calls[0]
    assert "MATCH (m:MechanicReference)" in cypher
    assert ":Superboss" not in cypher
    assert ":Character" not in cypher
    assert ":Sidekick" not in cypher
    assert ":Equipment" not in cypher
    assert params == {
        "topic_tags": ["speed"],
        "applies_to": ["boss_counterplay"],
        "mechanic_types": ["turn_order"],
        "limit": 3,
    }
