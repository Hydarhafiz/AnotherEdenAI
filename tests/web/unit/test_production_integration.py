"""Isolated app.js -> HTTP/SSE -> real production graph -> rendered Mushroom output."""
from __future__ import annotations

import asyncio
import json
from unittest.mock import patch

from src.web.app import app
from src.web.dependencies import get_driver
from src.workflow.nodes.format import format_and_validate_node
from tests.web.production_fixture import PilotGraphRecords


async def production_smoke(client, records, payload):
    """Keep production nodes real; observe the final boundary without replacing it."""
    observed = {}

    async def driver():
        return records

    async def observe_format(state, graph_driver):
        observed["state"] = state
        result = await format_and_validate_node(state, graph_driver)
        observed.update(result)
        return result

    app.dependency_overrides[get_driver] = driver
    with patch("src.workflow.graph.format_and_validate_node", observe_format):
        posted = await client.post("/api/query", json=payload)
        assert posted.status_code == 200
        job_id = next(iter(app.state.jobs))
        response = await asyncio.wait_for(client.get(f"/api/stream/{job_id}"), timeout=15)
    assert response.status_code == 200
    assert "event: result" in response.text
    assert "event: done" in response.text
    nodes = []
    for block in response.text.split("\n\n"):
        if block.startswith("event: node_status\n"):
            data = "\n".join(line.removeprefix("data: ") for line in block.splitlines() if line.startswith("data: "))
            # This is exactly the single JSON.parse used by the browser.
            nodes.append(json.loads(data)["node"])
    for node in ("RETRIEVE", "CANDIDATES", "ANALYZE", "FORMAT"):
        assert node in nodes
    for node in ("PLAN", "CYPHER", "VALIDATE"):
        assert node not in nodes
    final = observed["final_output"]
    assert final["error"] is None
    assert final["degraded"] is True
    assert 1 <= len(final["recommendations"]) <= 3
    assert records.legality_reads == len(final["recommendations"])
    assert observed["final_legality_errors"] == []
    assert final["boss_affinity"] == {key: records.boss[key] for key in ("weak", "resist", "null", "absorb")}
    assert "Deterministic-only result" in response.text
    assert "Lineup Recommendations" in response.text
    for recommendation in final["recommendations"]:
        assert len(recommendation["frontline"]) == 4
        assert len(recommendation["reserve"]) == 2
        heroes = recommendation["frontline"] + recommendation["reserve"]
        assert len({hero["name"] for hero in heroes}) == 6
        assert {hero["name"] for hero in heroes} <= set(records.roster)
        assert all(len(hero["recommended_skills"]) == 3 for hero in heroes)
        assert recommendation["confidence_label"] == "low"
    state = observed["state"]
    assert state["analysis_failure"] == {}
    assert state["analyzer_call_count"] == 1  # local unconfigured-adapter attempt
    assert state["provider_transport_retries"] == 0
    assert state["analyzer_usage"][0]["served_model"] is None
    assert state["analyzer_port"] is None and state["analyzer_transport"] is None
    assert state["typed_retrieval"]["lineup_candidates"]["candidates"]
    assert state["typed_retrieval"]["request_coverage"]
    assert state["boss_id"] == "celestial-mushroom"
    assert job_id not in app.state.jobs
    return observed


async def test_mushroom_frontend_request_reaches_real_production_and_renders(
    async_client, frontend_payload, tmp_path
):
    records = PilotGraphRecords(tmp_path)
    payload = frontend_payload(roster=records.roster)
    assert payload["boss_id"] == "Celestial Mushroom"
    observed = await production_smoke(async_client, records, payload)
    assert "provider.transport_unconfigured" in json.dumps(observed["final_output"]["warnings"])
